#!/usr/bin/env python3
"""Additive, public Simplecast catalogue and explicitly bounded detail pilot.

Standard library only. Existing editorial files are inputs, never destinations.
"""
import argparse
import copy
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse

from episode_discovery import request_json, SITE_URL, SIMPLECAST_API

ROOT = Path(__file__).resolve().parent
PILOT = (1, 2, 75, 191, 195)
VERSION = 'archive-v1'
SEGMENT_VERSION = 'segments-v2'
META_FIELDS = ('id', 'number', 'title', 'published_at', 'duration', 'description',
               'slug', 'enclosure_url', 'season', 'type', 'status', 'is_hidden',
               'image_url', 'updated_at', 'guid')
STATES = ('metadata', 'summary', 'show_notes', 'transcript', 'structured_transcript',
          'intelligence', 'newsletter', 'social')
TIME_RE = re.compile(r'\[(\d{2}):(\d{2}):(\d{2})\]')
# Conservative syntactic labels only; no identity resolution or accuracy claim.
LABEL_RE = re.compile(r'^[ \t]*(?:\[\d{2}:\d{2}:\d{2}\]\s*)?([A-Z\u00c0-\u00de][A-Za-z .’\u00c0-\u017f\-]{0,79}):')


def now():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    data = data.encode('utf-8') if isinstance(data, str) else data
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def read_json(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def remote_uuid(value):
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise ValueError('Invalid canonical remote UUID')
    return value


def checked_url(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.netloc != 'api.simplecast.com':
        raise ValueError('Unexpected API pagination host')
    return url


def api(url, request=None, **kwargs):
    request = request or request_json
    checked_url(url)
    for attempt in range(3):
        try:
            return request(url, **kwargs)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            try:
                delay = float(exc.headers.get('Retry-After', 2 ** attempt))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(exc.headers['Retry-After'])
                    delay = (retry_at - datetime.now(timezone.utc)).total_seconds()
                except (TypeError, ValueError, KeyError):
                    delay = 2 ** attempt
            # Defer a long rate-limit pause to a later manual/weekly run. Never
            # retry earlier than the server asks merely to fit this process.
            if delay > 30:
                raise
            time.sleep(max(delay, 0))
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def discover(fetch=api):
    site = fetch(SIMPLECAST_API + '/sites/search', method='POST', payload={'url': SITE_URL})
    return remote_uuid(site['podcast']['id'])


def fetch_catalogue(podcast_id, fetch=api):
    """Same endpoint/next-link algorithm as discovery, with completeness guards."""
    remote_uuid(podcast_id)
    url = f'{SIMPLECAST_API}/podcasts/{podcast_id}/episodes?status=published&private=false&sort=latest&limit=100&offset=0'
    visited, episodes, ids = set(), [], set()
    total = None
    while url:
        checked_url(url)
        if urlparse(url).path != f'/podcasts/{podcast_id}/episodes':
            raise ValueError('Pagination changed podcast scope')
        if url in visited or len(visited) >= 1000:
            raise ValueError('Pagination loop or excessive pages')
        visited.add(url)
        page = fetch(url)
        items, pages = page.get('collection'), page.get('pages')
        if not isinstance(items, list) or not isinstance(pages, dict):
            raise ValueError('Malformed catalogue page')
        if not items:
            raise ValueError('Empty catalogue page; completeness not established')
        if type(pages.get('total')) is not int or pages['total'] < 1:
            raise ValueError('Missing/invalid total pages')
        if total is None:
            total = pages['total']
        if pages['total'] != total or pages.get('current') != len(visited):
            raise ValueError('Pagination changed during fetch')
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Malformed episode')
            rid = remote_uuid(item.get('id'))
            if rid in ids:
                raise ValueError('Duplicate remote identity across pages')
            if item.get('status') != 'published' or item.get('is_hidden') is not False:
                raise ValueError('Unexpected non-public episode in public listing')
            ids.add(rid)
            episodes.append(item)
        next_page = pages.get('next')
        if next_page is not None and (not isinstance(next_page, dict) or not next_page.get('href')):
            raise ValueError('Malformed next page')
        url = urljoin(SIMPLECAST_API, next_page['href']) if next_page else None
        if bool(url) != (len(visited) < total):
            raise ValueError('Truncated or inconsistent pagination')
    if not episodes:
        raise ValueError('Empty public catalogue quarantined')
    return episodes, {'pages': len(visited), 'complete': True}


def metadata(item):
    remote_uuid(item.get('id'))
    result = {k: item.get(k) for k in META_FIELDS}
    for key in ('title', 'published_at', 'description', 'slug', 'enclosure_url', 'type',
                'status', 'image_url', 'updated_at', 'guid'):
        if result[key] is not None and not isinstance(result[key], str):
            raise ValueError('Unexpected metadata type: ' + key)
    for key in ('number', 'duration'):
        if result[key] is not None and (type(result[key]) is not int or result[key] < 0):
            raise ValueError('Unexpected numeric metadata: ' + key)
    for key in ('published_at', 'updated_at'):
        if result[key]:
            dt = datetime.fromisoformat(result[key].replace('Z', '+00:00'))
            if dt.tzinfo is None:
                raise ValueError('Timestamp must include offset')
    season = result['season']
    if season is not None:
        if not isinstance(season, dict) or (season.get('number') is not None and type(season['number']) is not int):
            raise ValueError('Malformed season')
        # Drop mutable next-number counter and action links.
        result['season'] = {'number': season.get('number'), 'href': season.get('href')}
    slug = result['slug']
    if slug and not re.fullmatch(r'[A-Za-z0-9_-]+', slug):
        raise ValueError('Unsafe episode slug')
    return result


def normalize(item, podcast_id):
    m = metadata(item)
    return {
        'schema_version': 1, 'episode_id': 'simplecast:' + m['id'],
        'remote_id': m['id'], 'podcast_id': podcast_id, 'provider': 'simplecast',
        'episode_number': m['number'], 'number_origin': 'api:number' if m['number'] is not None else None,
        'official_title': m['title'], 'published_at': m['published_at'],
        'duration_seconds': m['duration'], 'summary': m['description'], 'slug': m['slug'],
        'episode_url': SITE_URL + '/episodes/' + m['slug'] if m['slug'] else None,
        'episode_url_origin': 'site_slug' if m['slug'] else None,
        'audio_url': m['enclosure_url'], 'episode_type': m['type'],
        'season_number': (m['season'] or {}).get('number'), 'artwork_url': m['image_url'],
        'rss_guid': m['guid'], 'remote_status': m['status'], 'is_hidden': m['is_hidden'],
        'source_updated_at': m['updated_at'], 'public_presence': 'present',
        'media_mime_type': None, 'participants': [],
        'metadata_source_id': 'simplecast:' + m['id'] + ':metadata',
    }


class TextProjection(HTMLParser):
    """Versioned structural conversion: entities decoded; block/br breaks -> LF.

    Text nodes are appended unchanged. No trim, whitespace collapse or rewriting.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'iframe'):
            raise ValueError('Unexpected active transcript markup')
        if tag == 'br':
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'blockquote', 'pre'):
            self.parts.append('\n\n')

    def handle_data(self, data):
        self.parts.append(data)


def project(html):
    parser = TextProjection()
    parser.feed(html)
    parser.close()
    text = ''.join(parser.parts)
    if not text.strip() or '<!doctype html' in html.lower() or 'id="app"' in html:
        raise ValueError('Empty transcript or application shell')
    return text


def plausible_label(label):
    """Conservative label syntax, never person/entity or audio verification.

    Ordinary prose colon-prefixes are excluded. A two-token lowercased surname
    (e.g. source spelling 'Adam draper') is retained, never silently corrected.
    """
    words = label.strip().split()
    if not 1 <= len(words) <= 6:
        return False
    prose = {'a','an','and','as','at','but','everyone','first','for','from','i',
             "i'm",'in','it','my','our','piece','so','the','this','that','to','we','you'}
    if words[0].casefold() in prose:
        return False
    particles = {'de','del','der','di','da','du','la','le','van','von','ver','dos','do'}
    return all(word[0].isupper() or word.casefold() in particles
               or (len(words) == 2 and index == 1 and word.isalpha())
               for index, word in enumerate(words))


def segments(text):
    """Lossless nonempty line spans; no inferred speaker carry-forward/end times."""
    out, labels, timed, labeled = [], [], 0, 0
    for match in re.finditer(r'[^\n]+', text):
        value = match.group()
        label = LABEL_RE.match(value)
        if label and not plausible_label(label.group(1)):
            label = None
        times = list(TIME_RE.finditer(value))
        speaker = label.group(1).strip() if label else None
        if speaker and speaker not in labels:
            labels.append(speaker)
        timed += bool(times)
        labeled += bool(label)
        out.append({'start': match.start(), 'end': match.end(), 'excerpt': value,
                    'speaker_label': speaker, 'speaker_accuracy': 'unverified',
                    'timestamps': [{'offset': match.start() + t.start(), 'raw': t.group(),
                                    'seconds': int(t[1])*3600 + int(t[2])*60 + int(t[3])} for t in times]})
    return out, {'timestamps': {'state': 'present' if timed else 'absent',
                               'coverage': 'partial' if timed else 'none'},
                 'speaker_labels': {'state': 'present' if labeled else 'unresolved',
                                    'parseability': 'partial' if labeled < len(out) else 'syntactic',
                                    'accuracy': 'unverified', 'raw_labels': labels}}


def source(stage, rid, kind, data, media, endpoint, timestamp, previous=None,
           layer='official_source', field=None, origin_path=None):
    raw = data.encode('utf-8') if isinstance(data, str) else data
    sha = digest(raw)
    ext = {'application/json': 'json', 'text/html': 'html', 'text/plain': 'txt'}[media]
    relative = f'sources/{rid}/{kind}/{sha}.{ext}'
    write(stage / relative, raw)
    old = (previous or {}).get('current_version') or {}
    acquired = old.get('retrieved_at') if old.get('sha256') == sha else timestamp
    entry = {'source_id': f'simplecast:{rid}:{kind}', 'episode_id': f'simplecast:{rid}',
             'remote_id': rid, 'kind': kind, 'layer': layer, 'source_url': endpoint,
             'source_field': field, 'availability': 'available', 'retrieval_status': 'success',
             'current_version': {'sha256': sha, 'path': relative, 'media_type': media + '; charset=utf-8',
                                 'retrieved_at': acquired, 'validation': 'accepted_source',
                                 'validation_method': VERSION}}
    history = copy.deepcopy((previous or {}).get('previous_versions', []))
    if old and old.get('sha256') != sha and not any(v['sha256'] == old['sha256'] for v in history):
        history.append(old)
    if history:
        entry['previous_versions'] = history
    if origin_path:
        entry['origin_path'] = origin_path
        entry['source_acquisition_date'] = None
    return entry


def empty(kind):
    entry = {'kind': kind, 'availability': 'not_checked'}
    if kind == 'transcript':
        entry.update(timestamps={'state': 'not_checked', 'coverage': 'unknown'},
                     speaker_labels={'state': 'not_checked', 'parseability': 'unknown',
                                     'accuracy': 'unverified', 'raw_labels': []})
    return entry


def detail_sources(stage, record, detail, timestamp, entries):
    rid = record['remote_id']
    if detail.get('id') != rid:
        raise ValueError('Detail identity mismatch')
    podcast = detail.get('podcast')
    if not isinstance(podcast, dict) or podcast.get('id') != record['podcast_id']:
        raise ValueError('Detail podcast mismatch')
    # Prevent list/detail races from silently mixing different episode revisions.
    if metadata(detail) != read_json(stage / entries['metadata']['current_version']['path']):
        raise ValueError('List/detail metadata differs; retry complete sync')
    mime = detail.get('audio_content_type')
    if mime is not None and not isinstance(mime, str):
        raise ValueError('Invalid audio MIME type')
    record['media_mime_type'] = mime
    endpoint = SIMPLECAST_API + '/episodes/' + rid
    allowlisted = {**metadata(detail), 'audio_content_type': mime,
                   'long_description': detail.get('long_description'),
                   'transcription': detail.get('transcription')}
    # Preserve supplied fields before deriving text; no operational tokens/actions.
    entries['detail'] = source(stage, rid, 'detail', encoded(allowlisted), 'application/json',
                               endpoint, timestamp, entries.get('detail'))
    for kind, field in [('show_notes', 'long_description'), ('transcript', 'transcription')]:
        value = detail.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError('Unexpected content type: ' + field)
        if not value or not value.strip():
            old_entry = entries[kind]
            history = copy.deepcopy(old_entry.get('previous_versions', []))
            old_version = old_entry.get('current_version')
            if old_version and not any(v['sha256'] == old_version['sha256'] for v in history):
                history.append(old_version)
            entries[kind] = {'kind': kind, 'availability': 'unavailable_at_source',
                             'retrieval_status': 'success', 'source_url': endpoint,
                             'source_field': '/' + field}
            if history:
                entries[kind]['previous_versions'] = history
            if kind == 'transcript':
                entries['structured_transcript'] = empty('structured_transcript')
            continue
        entry = source(stage, rid, kind, value, 'text/html', endpoint, timestamp,
                       entries.get(kind), field='/' + field)
        text = project(value)
        text_path = f'derived/text/{rid}/{entry["current_version"]["sha256"]}.txt'
        write(stage / text_path, text)
        entry['derived_text'] = {'path': text_path, 'sha256': digest(text.encode('utf-8')),
                                 'extractor_version': VERSION}
        if kind == 'transcript':
            spans, flags = segments(text)
            entry.update(flags)
            span_path = f'derived/segments/{rid}/{SEGMENT_VERSION}/{entry["current_version"]["sha256"]}.json'
            payload = {'source_sha256': entry['current_version']['sha256'],
                       'text_sha256': entry['derived_text']['sha256'], 'extractor_version': SEGMENT_VERSION,
                       'offset_unit': 'unicode_codepoints', 'end': 'exclusive', 'segments': spans}
            write(stage / span_path, encoded(payload))
            entries['structured_transcript'] = {'kind': 'structured_transcript', 'availability': 'available',
                                                'path': span_path, 'sha256': digest(encoded(payload))}
        entries[kind] = entry


def attach_legacy(stage, repository, record, entries, timestamp):
    rid, slug = record['remote_id'], record['slug']
    legacy = repository / 'data/transcripts' / (str(slug) + '_transcript.txt')
    if slug and legacy.is_file():
        raw = legacy.read_bytes()
        text = raw.decode('utf-8')
        if text.strip() and '<!DOCTYPE html>' not in text:
            entry = source(stage, rid, 'transcript_legacy', raw, 'text/plain',
                           record['episode_url'] + '/transcript', timestamp,
                           entries.get('transcript_legacy'), layer='legacy_source',
                           origin_path=str(legacy.relative_to(repository)))
            entry.update(segments(text)[1])
            entry['validation_note'] = 'Legacy text, not freshly verified against remote source; labels unverified.'
            entries['transcript_legacy'] = entry
    matches, unresolved = [], []
    for folder in ('rank4', 'active'):
        path = repository / 'data/episodes' / folder / f'episode_{record["episode_number"]}.json'
        if path.exists():
            value = read_json(path)
            if value.get('episode_number') == record['episode_number'] and value.get('episode_url') == record['episode_url']:
                matches.append({'origin_path': str(path.relative_to(repository)), 'sha256': digest(path.read_bytes()),
                                'match_evidence': 'exact_episode_url_and_number'})
            else:
                unresolved.append({'origin_path': str(path.relative_to(repository)),
                                   'reason': 'episode_url_or_number_conflict'})
    if matches:
        entries['intelligence'] = {'kind': 'intelligence', 'layer': 'editorial_intelligence',
                                  'availability': 'available', 'references': matches}
    else:
        entries['intelligence'] = {'kind': 'intelligence', 'layer': 'editorial_intelligence',
                                  'availability': 'not_found_locally'}
    if unresolved:
        entries['intelligence']['unresolved_references'] = unresolved


def available(entry):
    return entry.get('availability') == 'available'


def transcript_entry(entries):
    for kind in ('transcript', 'transcript_legacy'):
        if available(entries.get(kind, {})):
            return entries[kind]
    return entries['transcript']


def fence(text, language='text'):
    longest = max([len(m.group()) for m in re.finditer(r'`+', text)] or [0])
    marker = '`' * max(3, longest + 1)
    return marker + language + '\n' + text + ('' if text.endswith('\n') else '\n') + marker + '\n'


def markdown(record, entries, stage):
    front = {'schema_version': 1, 'episode_id': record['episode_id'], 'episode_number': record['episode_number'],
             'title': record['official_title'], 'published_at': record['published_at'],
             'duration_seconds': record['duration_seconds'], 'url': record['episode_url'],
             'episode_type': record['episode_type'], 'media_mime_type': record['media_mime_type'],
             'speakers': entries.get('transcript', {}).get('speaker_labels', {}).get('raw_labels', []),
             'speaker_status': 'source_labels_unverified',
             'show_notes_status': entries['show_notes']['availability'],
             'transcript_status': entries['transcript']['availability'],
             'metadata_revision': entries['metadata']['current_version']['sha256'], 'exporter_version': VERSION}
    for kind in ('show_notes', 'transcript'):
        front[kind + '_revision'] = entries[kind].get('current_version', {}).get('sha256')
    # JSON scalar/array values are valid YAML values; avoid custom YAML dependency.
    text = '---\n' + ''.join(k + ': ' + json.dumps(v, ensure_ascii=False) + '\n' for k, v in front.items()) + '---\n\n'
    text += '# ' + (record['official_title'] or 'Untitled episode') + '\n\n## Episode metadata\n\n'
    text += f'Canonical identity: {record["episode_id"]}\n\nOfficial page: {record["episode_url"]}\n\n'
    text += '## Published summary\n\n' + fence(record['summary'] or '') + '\n'
    for kind, title in [('show_notes', 'Published show notes — preserved source HTML'),
                        ('transcript', 'Transcript — preserved source HTML')]:
        text += '## ' + title + '\n\n'
        entry = entries[kind]
        if available(entry):
            text += fence((stage / entry['current_version']['path']).read_bytes().decode('utf-8'), 'html')
        else:
            text += 'Availability: ' + entry['availability'] + '\n'
        text += '\n'
    if available(entries['transcript']):
        text += '## Transcript — source-preserving text projection\n\n'
        text += 'HTML entities are decoded; block and line breaks become LF. Language and source labels are not corrected. Speaker accuracy is unverified.\n\n'
        text += fence((stage / entries['transcript']['derived_text']['path']).read_bytes().decode('utf-8'))
    text += '\n## Source references\n\nPaths below are relative to the archive root. This document is a reproducible export, not editable source storage.\n\n'
    for kind in ('metadata', 'summary', 'show_notes', 'transcript'):
        entry = entries[kind]
        if available(entry):
            v = entry['current_version']
            text += f'- {kind}: `{v["path"]}`; SHA-256 `{v["sha256"]}`; acquired {v["retrieved_at"]}; {entry["source_url"]}\n'
    return text


CSV_FIELDS = ('episode_id','remote_id','rss_guid','episode_number','season_number','title','published_at','date',
              'duration_seconds','duration_display','url','audio_url','episode_type','media_mime_type',
              'speakers_json','speaker_status','guest_names_json','summary','artwork_url','public_presence',
              'source_updated_at','show_notes_status','transcript_status','structured_transcript_status',
              'transcript_available','show_notes_available','timestamps_available','speaker_labels_available',
              'intelligence_available','newsletter_content_available','social_content_available','markdown_path','metadata_revision')


def csv_export(records, manifest):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=CSV_FIELDS, lineterminator='\n')
    writer.writeheader()
    for r in records:
        e = manifest[r['episode_id']]
        t = transcript_entry(e)
        seconds = r['duration_seconds']
        duration = f'{seconds//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}' if seconds is not None else ''
        row = {k:r.get(k) for k in CSV_FIELDS if k in r}
        row.update(title=r['official_title'], date=(r['published_at'] or '')[:10], url=r['episode_url'], duration_display=duration,
                   speakers_json=json.dumps(t.get('speaker_labels', {}).get('raw_labels', []), ensure_ascii=False),
                   speaker_status='source_labels_unverified' if t.get('speaker_labels', {}).get('raw_labels') else 'unresolved',
                   guest_names_json='[]', show_notes_status=e['show_notes']['availability'],
                   transcript_status=t['availability'], structured_transcript_status=e['structured_transcript']['availability'],
                   transcript_available=available(t), show_notes_available=available(e['show_notes']),
                   timestamps_available=t.get('timestamps', {}).get('state') == 'present',
                   speaker_labels_available=t.get('speaker_labels', {}).get('state') == 'present',
                   intelligence_available=available(e['intelligence']), newsletter_content_available=available(e['newsletter']),
                   social_content_available=available(e['social']), markdown_path=e.get('markdown_path', ''),
                   metadata_revision=e['metadata']['current_version']['sha256'])
        writer.writerow(row)
    return out.getvalue()


def load_catalogue(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def validate(stage):
    records = load_catalogue(stage / 'catalogue.jsonl')
    manifest = read_json(stage / 'manifest.json')
    if not records:
        raise ValueError('Empty accepted catalogue')
    ids, numbers = set(), set()
    for record in records:
        eid = record['episode_id']
        if eid in ids or eid != 'simplecast:' + remote_uuid(record['remote_id']):
            raise ValueError('Duplicate/inconsistent canonical identity')
        ids.add(eid)
        if record['public_presence'] == 'present' and record['episode_number'] is not None:
            key = (record['season_number'], record['episode_number'])
            if key in numbers:
                raise ValueError('Duplicate editorial episode number within season')
            numbers.add(key)
        entries = manifest[eid]
        if not set(STATES).issubset(entries):
            raise ValueError('Incomplete availability manifest')
        for entry in entries.values():
            if not isinstance(entry, dict):
                continue
            v = entry.get('current_version')
            assets = [v, entry.get('derived_text'), entry if 'path' in entry and 'sha256' in entry else None]
            assets.extend(entry.get('previous_versions', []))
            for asset in assets:
                if asset:
                    path = stage / asset['path']
                    if not path.resolve().is_relative_to(stage.resolve()) or digest(path.read_bytes()) != asset['sha256']:
                        raise ValueError('Source path/hash mismatch')
            if v and entry.get('episode_id') != eid:
                raise ValueError('Manifest source identity mismatch')
        raw = read_json(stage / entries['metadata']['current_version']['path'])
        expected = normalize(raw, record['podcast_id'])
        for key in expected:
            if key not in ('public_presence', 'media_mime_type') and expected[key] != record[key]:
                raise ValueError('Catalogue metadata fidelity mismatch: ' + key)
        if available(entries.get('detail', {})):
            detail = read_json(stage / entries['detail']['current_version']['path'])
            if detail['id'] != record['remote_id']:
                raise ValueError('Detail provenance identity mismatch')
            if record['media_mime_type'] != detail['audio_content_type']:
                raise ValueError('Detail MIME fidelity mismatch')
            for kind, field in [('show_notes','long_description'),('transcript','transcription')]:
                entry = entries[kind]
                if available(entry):
                    html = (stage / entry['current_version']['path']).read_bytes().decode('utf-8')
                    if html != detail[field]:
                        raise ValueError('Exact source field fidelity mismatch')
                    text = (stage / entry['derived_text']['path']).read_bytes().decode('utf-8')
                    if project(html) != text:
                        raise ValueError('Text projection fidelity mismatch')
            if available(entries['structured_transcript']):
                payload = read_json(stage / entries['structured_transcript']['path'])
                text = (stage / entries['transcript']['derived_text']['path']).read_bytes().decode('utf-8')
                expected_spans, expected_flags = segments(text)
                if (payload['segments'] != expected_spans
                        or payload['text_sha256'] != digest(text.encode('utf-8'))
                        or payload['source_sha256'] != entries['transcript']['current_version']['sha256']):
                    raise ValueError('Passage fidelity mismatch')
                for key, value in expected_flags.items():
                    if entries['transcript'][key] != value:
                        raise ValueError('Transcript parsing state mismatch')
        if entries.get('markdown_path'):
            if (stage / entries['markdown_path']).read_bytes() != markdown(record, entries, stage).encode('utf-8'):
                raise ValueError('Markdown round-trip mismatch')
    if set(manifest) != ids:
        raise ValueError('Manifest/catalogue identity mismatch')
    expected_links = {eid: {'intelligence': entries['intelligence'].get('references', []),
                            'unresolved': entries['intelligence'].get('unresolved_references', [])}
                      for eid, entries in manifest.items()}
    if read_json(stage / 'links.json') != expected_links:
        raise ValueError('Crosswalk/manifest mismatch')
    if (stage / 'exports/catalogue.csv').read_bytes() != csv_export(records, manifest).encode('utf-8'):
        raise ValueError('CSV deterministic export mismatch')
    return {'valid': True, 'records': len(records), 'source_fidelity': 'passed', 'export_round_trip': 'passed'}


def coverage(records, manifest, changes, failures, timestamp):
    active = [r for r in records if r['public_presence'] == 'present']
    counts = {k:0 for k in ('metadata','summary','show_notes','official_transcripts','legacy_transcripts',
                           'locally_preserved_transcripts','timestamped_transcripts','speaker_labelled_transcripts',
                           'intelligence','pilot_exported')}
    missing = {}
    for r in active:
        e = manifest[r['episode_id']]
        for kind in ('metadata','summary','show_notes','intelligence'):
            counts[kind] += available(e[kind])
        counts['official_transcripts'] += available(e['transcript'])
        counts['legacy_transcripts'] += available(e.get('transcript_legacy', {}))
        t = transcript_entry(e)
        counts['locally_preserved_transcripts'] += available(t)
        counts['timestamped_transcripts'] += t.get('timestamps', {}).get('state') == 'present'
        counts['speaker_labelled_transcripts'] += t.get('speaker_labels', {}).get('state') == 'present'
        counts['pilot_exported'] += bool(e.get('markdown_path'))
        for key in ('episode_number','official_title','published_at','duration_seconds','summary','slug','audio_url','artwork_url'):
            if r[key] is None or r[key] == '':
                missing.setdefault(key, []).append(r['episode_id'])
    ordered = sorted(active, key=lambda r:r['published_at'] or '')
    return {'schema_version':1,'checked_at':timestamp,'catalogue_sync_complete':True,
            'published_episodes':len(active),'catalogue_records':len(records),'coverage':counts,
            'changes':changes,'failures':failures,'retrieval_failures':sum(f['type']=='retrieval' for f in failures),
            'validation_failures':sum(f['type']=='validation' for f in failures), 'missing_metadata':missing,
            'duplicate_identities':0,'conflicting_episode_numbers':0,
            'first':{k:ordered[0][k] for k in ('episode_number','published_at')},
            'latest':{k:ordered[-1][k] for k in ('episode_number','published_at')}}


def report_markdown(report, records, manifest):
    text = '# TSSE archive coverage\n\nChecked: ' + report['checked_at'] + '\n\n'
    text += f'Published episodes: **{report["published_episodes"]}**. Catalogue records: **{report["catalogue_records"]}**.\n\n'
    text += '| Content | Episodes |\n|---|---:|\n'
    for k,v in report['coverage'].items():
        text += f'| {k.replace("_", " ")} | {v} / {report["published_episodes"]} |\n'
    text += '\nLegacy and official transcript counts overlap; locally preserved transcripts is their distinct episode union. Speaker labels are syntactically detected, never audio-verified. Newsletter/social mappings remain not checked.\n\n'
    text += '## This run\n\n' + fence(json.dumps({k:report[k] for k in ('changes','retrieval_failures','validation_failures','missing_metadata')},indent=2))
    text += '\n## Pilot\n\n| Episode | Title | Notes | Transcript | Timestamps | Speaker labels | Markdown |\n|---|---|---|---|---|---|---|\n'
    for r in sorted(records,key=lambda r:r['episode_number'] or -1):
        e=manifest[r['episode_id']]
        if e.get('markdown_path'):
            t=e['transcript']
            text += f'| {r["episode_number"]} | {r["official_title"]} | {e["show_notes"]["availability"]} | {t["availability"]} | {t.get("timestamps",{}).get("state","unknown")} | {t.get("speaker_labels",{}).get("parseability","unknown")}; unverified | `{e["markdown_path"]}` |\n'
    return text


def build(stage, repository, items, podcast_id, fetch_detail, pilot, timestamp):
    previous_records = {r['episode_id']:r for r in load_catalogue(stage / 'catalogue.jsonl')}
    previous_manifest = read_json(stage / 'manifest.json', {})
    records, manifest, failures = [], {}, []
    for item in items:
        record = normalize(item, podcast_id)
        eid, rid = record['episode_id'], record['remote_id']
        if eid in manifest:
            raise ValueError('Duplicate canonical identity')
        entries = copy.deepcopy(previous_manifest.get(eid, {k:empty(k) for k in STATES}))
        record['media_mime_type'] = previous_records.get(eid,{}).get('media_mime_type')
        endpoint = f'{SIMPLECAST_API}/podcasts/{podcast_id}/episodes'
        entries['metadata'] = source(stage,rid,'metadata',encoded(metadata(item)),'application/json',endpoint,timestamp,entries['metadata'])
        if record['summary']:
            entries['summary'] = source(stage,rid,'summary',record['summary'],'text/plain',endpoint,timestamp,entries['summary'],field='/description')
        else:
            entries['summary'] = {'kind':'summary','availability':'unavailable_at_source'}
        attach_legacy(stage, repository, record, entries, timestamp)
        if record['episode_number'] in pilot:
            try:
                detail = fetch_detail(SIMPLECAST_API + '/episodes/' + rid)
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                failures.append({'episode_id':eid,'type':'retrieval','error':type(exc).__name__})
                detail = None
            if detail is not None:
                candidate = copy.deepcopy(entries)
                candidate_record = copy.deepcopy(record)
                try:
                    detail_sources(stage,candidate_record,detail,timestamp,candidate)
                    record, entries = candidate_record, candidate
                except (ValueError, KeyError, TypeError) as exc:
                    failures.append({'episode_id':eid,'type':'validation','error':str(exc)})
            if any(f['episode_id']==eid for f in failures):
                for k in ('show_notes','transcript'):
                    if not available(entries[k]):
                        entries[k] = {'kind':k,'availability':'failed'}
            entries['markdown_path'] = f'exports/episodes/{rid}.md'
        record['record_revision'] = digest(encoded(record))
        records.append(record)
        manifest[eid]=entries
    # Never silently delete a formerly discovered episode.
    for eid, old in previous_records.items():
        if eid not in manifest:
            old = dict(old, public_presence='not_seen_in_complete_snapshot')
            old.pop('record_revision',None)
            old['record_revision']=digest(encoded(old))
            records.append(old)
            manifest[eid]=previous_manifest[eid]
    records.sort(key=lambda r:r['episode_id'])
    for r in records:
        e=manifest[r['episode_id']]
        if e.get('markdown_path'):
            write(stage/e['markdown_path'],markdown(r,e,stage))
    write(stage/'catalogue.jsonl',''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in records))
    write(stage/'manifest.json',encoded(manifest))
    links = {eid: {'intelligence': entries['intelligence'].get('references', []),
                   'unresolved': entries['intelligence'].get('unresolved_references', [])}
             for eid, entries in manifest.items()}
    write(stage/'links.json', encoded(links))
    write(stage/'exports/catalogue.csv',csv_export(records,manifest))
    validation=validate(stage)
    changes={'new':0,'changed':0,'unchanged':0,'not_seen':0}
    for r in records:
        eid=r['episode_id']
        if r['public_presence']!='present':changes['not_seen']+=1
        elif eid not in previous_records:changes['new']+=1
        elif r!=previous_records[eid] or manifest[eid]!=previous_manifest.get(eid):changes['changed']+=1
        else:changes['unchanged']+=1
    report=coverage(records,manifest,changes,failures,timestamp)
    report['validation']=validation
    write(stage/'reports/latest.json',encoded(report))
    write(stage/'reports/latest.md',report_markdown(report,records,manifest))
    return report


@contextmanager
def lock(output):
    path=output.parent/('.'+output.name+'.lock')
    fd=os.open(str(path),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        os.write(fd,str(os.getpid()).encode())
        yield
    finally:
        os.close(fd)
        path.unlink()


def sync(output, repository=ROOT, pilot=(), fetch=api):
    output=Path(output).resolve()
    repository=Path(repository).resolve()
    # Disallow accidental replacement of original sources/code directories.
    if output==repository or output in repository.parents or any(output==repository/p or (repository/p) in output.parents for p in ('data','docs','publishing','tests','.git','outputs')):
        raise ValueError('Output must be a dedicated additive archive directory')
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists() and not (output/'manifest.json').exists():
        raise ValueError('Refusing to replace non-archive output directory')
    with lock(output):
        try:
            podcast=discover(fetch)
            items,pagination=fetch_catalogue(podcast,fetch)
            existing=load_catalogue(output/'catalogue.jsonl')
            old_ids={r['remote_id'] for r in existing if r['public_presence']=='present'}
            lost=old_ids-{i['id'] for i in items}
            if old_ids and len(lost)>max(2,len(old_ids)*0.1):
                raise ValueError('Mass disappearance quarantined; review remote catalogue')
            missing=set(pilot)-{i.get('number') for i in items}
            if missing:
                raise ValueError('Pilot episodes not in public catalogue: '+str(sorted(missing)))
            with tempfile.TemporaryDirectory(prefix='.archive-stage-',dir=str(output.parent)) as tmp:
                stage=Path(tmp)/'archive'
                if output.exists():shutil.copytree(output,stage)
                else:stage.mkdir()
                report=build(stage,repository,items,podcast,fetch,set(pilot),now())
                report['pagination']=pagination
                write(stage/'reports/latest.json',encoded(report))
                # Directory-level publication under writer lock with rollback; readers must
                # retry during the brief rename gap. No mixed old/new file generations.
                backup=Path(tmp)/'previous'
                try:
                    if output.exists():
                        output.rename(backup)
                    stage.rename(output)
                except BaseException:
                    if backup.exists() and not output.exists():
                        backup.rename(output)
                    raise
                return report
        except Exception as exc:
            # Do not change accepted archive/report on fatal failure.
            write(output.parent/('.'+output.name+'-last-failure.json'),encoded({
                'checked_at':now(),'catalogue_sync_complete':False,'error_type':type(exc).__name__,
                'message':str(exc) if isinstance(exc,ValueError) else 'Remote request or filesystem failure; previous archive retained.'}))
            raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('sync','validate','export'))
    parser.add_argument('--output',type=Path,default=ROOT/'archive')
    parser.add_argument('--pilot',action='store_true',help='Fetch details ONLY for episodes 1,2,75,191,195.')
    args=parser.parse_args()
    if args.command=='sync':
        result=sync(args.output,pilot=PILOT if args.pilot else ())
    elif args.command=='validate':result=validate(args.output.resolve())
    else:
        # Regenerate only exports from preserved sources, then validate.
        records=load_catalogue(args.output/'catalogue.jsonl');manifest=read_json(args.output/'manifest.json')
        for r in records:
            e=manifest[r['episode_id']]
            if e.get('markdown_path'):write(args.output/e['markdown_path'],markdown(r,e,args.output))
        write(args.output/'exports/catalogue.csv',csv_export(records,manifest))
        result=validate(args.output.resolve())
    print(json.dumps(result,indent=2,ensure_ascii=False))
    if result.get('failures'):return 2
    return 0


if __name__=='__main__':
    sys.exit(main())
