"""Atomic counters only. Use one SQLite file on a single host, or shared REST Redis on Vercel."""
import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from archive_web import APIError

# Check every limit before incrementing any counter; Redis executes the script atomically.
RESERVE = """
for i,key in ipairs(KEYS) do
  local n = tonumber(redis.call('GET',key) or '0')
  if n + tonumber(ARGV[1]) > tonumber(ARGV[i+2]) then return 0 end
end
if tonumber(ARGV[1]) == 0 then return 1 end
for i,key in ipairs(KEYS) do
  redis.call('INCRBY',key,ARGV[1])
  redis.call('EXPIRE',key,ARGV[2])
end
return 1
"""


def integer(name, default, low, high):
    try:
        value = int(os.environ.get(name, default))
        if low <= value <= high:
            return value
    except (TypeError, ValueError):
        pass
    raise APIError('The guide needs a valid server budget.', 503)


def reserve(limits, amount, ttl):
    endpoint = (
        os.environ.get('TSSE_CHAT_REDIS_URL')
        or os.environ.get('KV_REST_API_URL')
    )
    if endpoint:
        token = (
            os.environ.get('TSSE_CHAT_REDIS_TOKEN')
            or os.environ.get('KV_REST_API_TOKEN')
        )
        if not token or urlsplit(endpoint).scheme != 'https':
            raise APIError('The shared guide limits are unavailable.', 503)
        command = ['EVAL', RESERVE, len(limits), *limits, amount, ttl, *limits.values()]
        req = Request(endpoint, data=json.dumps(command).encode(), headers={'Content-Type':'application/json'})
        req.add_unredirected_header('Authorization', 'Bearer ' + token)
        try:
            with urlopen(req, timeout=2) as response:
                result = json.loads(response.read(4096))['result']
            if type(result) is not int or result not in (0, 1):
                raise ValueError()
            return bool(result)
        except (KeyError, OSError, ValueError, TypeError):
            raise APIError('The shared guide limits are unavailable.', 503) from None
    path = os.environ.get('TSSE_CHAT_LIMIT_DB')
    if os.environ.get('VERCEL') or not path or not os.path.isabs(path):
        raise APIError('The shared guide limits are unavailable.', 503)
    with sqlite3.connect(path, timeout=2) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE IF NOT EXISTS counters (key TEXT PRIMARY KEY, used INTEGER, expires INTEGER)')
        now = int(time.time())
        db.execute('DELETE FROM counters WHERE expires <= ?', (now,))
        for key, limit in limits.items():
            row = db.execute('SELECT used FROM counters WHERE key=?', (key,)).fetchone()
            if (row[0] if row else 0) + amount > limit:
                return False
        if amount == 0:
            return True
        for key in limits:
            db.execute('INSERT INTO counters VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET used=used+excluded.used',
                       (key, amount, now+ttl))
        return True


def rate(client):
    minute = int(time.time() // 60)
    digest = hashlib.sha256(f'{minute}:{client}'.encode()).hexdigest()
    prefix = f'tsse:guide:minute:{minute}:'
    if not reserve({prefix+'total':60, prefix+digest:12}, 1, 120):
        raise APIError('The guide is busy. Try again in a minute.', 429)


def free_tokens(amount):
    day = datetime.now(timezone.utc).date().isoformat()
    maximum = integer('TSSE_CHAT_FREE_TOKENS_PER_DAY', 200000, 1, 100000000)
    if not reserve({'tsse:guide:free-tokens:'+day: maximum}, amount, 172800):
        raise APIError('Archive excerpts are available while the guide rests.', 429)


def quota_available():
    return reserve({'tsse:guide:groq-cooldown': 0}, 0, 1)


def pause_provider(seconds):
    reserve({'tsse:guide:groq-cooldown': 1}, 1, seconds)
