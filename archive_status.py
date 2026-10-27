"""Small public success records, independent of content commits/deployments."""
import json
import io
import os
import re
import threading
import time
from datetime import datetime, timezone
import zipfile
from urllib.request import Request, HTTPRedirectHandler, build_opener

REPOSITORY = 'JoePodcasts/tsse-editorial-os'
FIELDS = ('schema_version', 'status', 'last_successful_sync_at', 'published_episodes',
          'changes_detected', 'changes', 'archive_fingerprint')


def checked(value, fingerprint, count):
    if not isinstance(value, dict):
        raise ValueError('Invalid synchronization record')
    stamp = datetime.fromisoformat(value['last_successful_sync_at'])
    if (value.get('schema_version') != 1 or value.get('status') != 'success'
            or stamp.tzinfo is None or stamp > datetime.now(timezone.utc)
            or value.get('archive_fingerprint') != fingerprint
            or value.get('published_episodes') != count
            or not isinstance(value.get('changes_detected'), bool)
            or not isinstance(value.get('changes'), dict)
            or not set(value['changes']).issubset({'new', 'changed', 'unchanged', 'not_seen'})
            or any(type(n) is not int or n < 0 for n in value['changes'].values())):
        raise ValueError('Synchronization record does not match this archive')
    return {key: value[key] for key in FIELDS}


def artifact_name(fingerprint):
    if not re.fullmatch('[0-9a-f]{64}', fingerprint):
        raise ValueError('Invalid archive fingerprint')
    return 'archive-status-' + fingerprint


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        from urllib.parse import urlsplit
        if urlsplit(newurl).scheme != 'https':
            raise ValueError('Unsafe artifact redirect')
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if urlsplit(newurl).hostname != 'api.github.com':
            redirected.remove_header('Authorization')
        return redirected


def retrieve(fingerprint):
    # A private repo needs a server-only fine-grained token with Actions: read.
    # Build jobs may use their scoped GITHUB_TOKEN via this environment variable.
    token = os.environ.get('ARCHIVE_STATUS_TOKEN')
    if not token:
        raise OSError('Archive status credential is not configured')
    opener = build_opener(SafeRedirect())
    def get(url, maximum):
        request = Request(url, headers={'Authorization': 'Bearer ' + token,
                          'Accept': 'application/vnd.github+json', 'Cache-Control': 'no-cache',
                          'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'TSSE-Public-Archive/1.0'})
        with opener.open(request, timeout=3) as response:
            raw = response.read(maximum + 1)
        if len(raw) > maximum:
            raise ValueError('Synchronization response exceeds size limit')
        return raw
    endpoint = f'https://api.github.com/repos/{REPOSITORY}/actions/artifacts'
    records = json.loads(get(endpoint + '?per_page=20&name=' + artifact_name(fingerprint), 131072))['artifacts']
    records = [r for r in records if not r['expired'] and r['name'] == artifact_name(fingerprint)
               and r.get('workflow_run', {}).get('head_branch') == 'main']
    if not records:
        raise ValueError('No matching successful archive artifact')
    artifact = max(records, key=lambda r: int(r['id']))
    raw = get(endpoint + '/' + str(int(artifact['id'])) + '/zip', 65536)
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        if bundle.namelist() != ['sync-status.json'] or bundle.getinfo('sync-status.json').file_size > 16384:
            raise ValueError('Unexpected status artifact contents')
        return json.loads(bundle.read('sync-status.json'))


class PublicStatus:
    """A matching, monotonic success; no credentials or archive writes at runtime."""
    def __init__(self, baseline, fetch=retrieve, ttl=60):
        self.fingerprint = baseline['archive_fingerprint']
        self.count = baseline['published_episodes']
        self.value = checked(baseline, self.fingerprint, self.count)
        self.fetch, self.ttl, self.next_check = fetch, ttl, 0
        self.lock = threading.Lock()

    def get(self):
        with self.lock:
            if time.monotonic() >= self.next_check:
                self.next_check = time.monotonic() + self.ttl
                try:
                    value = checked(self.fetch(self.fingerprint), self.fingerprint, self.count)
                    if datetime.fromisoformat(value['last_successful_sync_at']) > datetime.fromisoformat(self.value['last_successful_sync_at']):
                        self.value = value
                except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
                    pass  # Bundled/last matching success remains truthful during outages.
            return dict(self.value)
