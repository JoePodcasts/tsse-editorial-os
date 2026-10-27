#!/usr/bin/env python3
"""Validate and expose the existing portable exports without rewriting them."""
import argparse
import csv
import io
import json
import re
import threading
import zipfile
from pathlib import Path

import archive_sync as archive


def fenced_section(document, heading):
    """Read one actual generated fenced block, including its final LF."""
    prefix = '## ' + heading + '\n\n'
    if document.count(prefix) != 1:
        raise ValueError('Missing or ambiguous Markdown section: ' + heading)
    remainder = document.split(prefix, 1)[1]
    opening = re.search(r'(?m)^(`{3,})(?:html|text)\n', remainder)
    if not opening:
        raise ValueError('Missing literal fence: ' + heading)
    end = re.search(r'(?m)^' + opening[1] + r'\n', remainder[opening.end():])
    if not end:
        raise ValueError('Unclosed literal fence: ' + heading)
    return remainder[opening.end():opening.end() + end.start()]


def with_final_lf(text):
    return text if text.endswith('\n') else text + '\n'


def export_path(root, record, entry):
    expected = 'exports/episodes/' + record['remote_id'] + '.md'
    if entry.get('markdown_path') != expected:
        raise ValueError('Episode-to-Markdown mapping does not match canonical identity')
    path = root / expected
    if not path.resolve().is_relative_to(root) or not path.resolve().is_relative_to((root / 'exports/episodes').resolve()):
        raise ValueError('Markdown path is outside the export directory')
    return path


def validate_exports(root):
    root = Path(root).resolve()
    records = [r for r in archive.load_catalogue(root / 'catalogue.jsonl') if r['public_presence'] == 'present']
    manifest = archive.read_json(root / 'manifest.json')
    csv_raw = (root / 'exports/catalogue.csv').read_bytes()
    reader = csv.DictReader(io.StringIO(csv_raw.decode('utf-8'), newline=''))
    rows = list(reader)
    fields = reader.fieldnames
    required = {'episode_id', 'remote_id', 'episode_number', 'title', 'published_at',
                'duration_seconds', 'url', 'episode_type', 'speakers_json', 'speaker_status',
                'transcript_status', 'show_notes_status', 'timestamps_available', 'markdown_path'}
    if not fields or not required.issubset(fields):
        raise ValueError('Portable catalogue is missing required fields')
    if len(rows) != len(records) or {r['episode_id'] for r in rows} != {r['episode_id'] for r in records}:
        raise ValueError('CSV does not contain one row per current published episode')
    if csv_raw != archive.csv_export(records, manifest).encode('utf-8'):
        raise ValueError('CSV does not match the current reproducible export')
    by_id = {r['episode_id']: r for r in rows}
    files, timestamped, notes_count, transcript_count = [], 0, 0, 0
    for record in records:
        entry = manifest[record['episode_id']]
        path = export_path(root, record, entry)
        raw = path.read_bytes()
        document = raw.decode('utf-8')
        # Exact exporter parity also checks all front matter and source refs.
        if document != archive.markdown(record, entry, root):
            raise ValueError('Markdown differs from current export: ' + path.name)
        if by_id[record['episode_id']]['markdown_path'] != entry['markdown_path']:
            raise ValueError('CSV/manifest file mapping differs: ' + path.name)
        if '## Episode metadata\n' not in document:
            raise ValueError('Missing episode metadata: ' + path.name)
        for kind, heading in [('show_notes', 'Published show notes — preserved source HTML'),
                              ('transcript', 'Transcript — preserved source HTML')]:
            if not archive.available(entry[kind]):
                continue
            source = (root / entry[kind]['current_version']['path']).read_bytes().decode('utf-8')
            if fenced_section(document, heading) != with_final_lf(source):
                raise ValueError('Source HTML changed in Markdown: ' + path.name)
            if kind == 'show_notes':
                notes_count += 1
            else:
                transcript_count += 1
                exported_text = fenced_section(document, 'Transcript — source-preserving text projection')
                source_text = archive.project(source)
                if re.findall(r'\S+', source_text) != re.findall(r'\S+', exported_text):
                    raise ValueError('Transcript wording changed in Markdown: ' + path.name)
                if archive.TIME_RE.findall(source_text) != archive.TIME_RE.findall(exported_text):
                    raise ValueError('Transcript timestamps changed in Markdown: ' + path.name)
                timestamped += bool(archive.TIME_RE.search(source_text))
        files.append({'episode_id': record['episode_id'], 'remote_id': record['remote_id'],
                      'filename': path.name, 'bytes': len(raw), 'sha256': archive.digest(raw)})
    actual = {p.name for p in (root / 'exports/episodes').glob('*.md')}
    if actual != {f['filename'] for f in files}:
        raise ValueError('Markdown directory and current published catalogue differ')
    return {'published_episodes': len(records), 'csv_rows': len(rows), 'csv_fields': fields,
            'csv_bytes': len(csv_raw), 'csv_sha256': archive.digest(csv_raw),
            'markdown_files': len(files), 'markdown_bytes': sum(f['bytes'] for f in files),
            'utf8_valid': True, 'metadata_documents': len(files), 'show_note_documents': notes_count,
            'transcript_documents': transcript_count, 'timestamped_transcripts': timestamped,
            'deterministic_mapping': True, 'source_html_preserved': True,
            'transcript_wording_changes': [], 'transcript_timestamp_changes': [],
            'files': sorted(files, key=lambda f: f['remote_id'])}


class ExportLibrary:
    """A revision-aware cache of verified generated bytes; never another export."""
    def __init__(self, root):
        self.root = Path(root).resolve()
        self._lock = threading.RLock()
        self._revision = None
        self._report = None
        self._zip = None

    def inventory(self):
        with self._lock:
            paths = [self.root / name for name in ('catalogue.jsonl', 'manifest.json', 'exports/catalogue.csv')]
            paths += sorted((self.root / 'exports/episodes').glob('*.md'))
            revision = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size, p.stat().st_ctime_ns) for p in paths)
            if revision != self._revision:
                report = validate_exports(self.root)
                self._report, self._revision, self._zip = report, revision, None
            return self._report

    def csv_bytes(self):
        report = self.inventory()
        raw = (self.root / 'exports/catalogue.csv').read_bytes()
        if archive.digest(raw) != report['csv_sha256']:
            raise ValueError('CSV changed during reading; retry after export publication')
        return raw

    def markdown(self, remote_id):
        report = self.inventory()
        info = next((f for f in report['files'] if f['remote_id'] == remote_id), None)
        if not info:
            raise ValueError('Unknown exported episode')
        return info, self._markdown_bytes(info)

    def _markdown_bytes(self, info):
        path = self.root / 'exports/episodes' / info['filename']
        if not path.resolve().is_relative_to(self.root) or not path.resolve().is_relative_to((self.root / 'exports/episodes').resolve()):
            raise ValueError('Markdown path is outside the export directory')
        raw = path.read_bytes()
        if archive.digest(raw) != info['sha256']:
            raise ValueError('Markdown changed during reading; retry after export publication')
        return raw

    def zip_bytes(self):
        with self._lock:
            report = self.inventory()
            if self._zip is None:
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
                    for info in report['files']:
                        raw = self._markdown_bytes(info)
                        item = zipfile.ZipInfo('episodes/' + info['filename'], date_time=(1980, 1, 1, 0, 0, 0))
                        item.create_system = 3
                        item.external_attr = 0o100644 << 16
                        item.compress_type = zipfile.ZIP_DEFLATED
                        bundle.writestr(item, raw, compresslevel=6)
                self._zip = buffer.getvalue()
            return self._zip


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=Path(__file__).resolve().parent / 'archive')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    library = ExportLibrary(args.archive)
    report = library.inventory()
    # Do not calculate a ZIP until after validating the original deliverables.
    bundle = library.zip_bytes()
    report = {**report, 'zip_bytes': len(bundle), 'zip_sha256': archive.digest(bundle),
              'zip_entries': report['markdown_files'], 'zip_scope': 'Existing Markdown files only; their embedded source references are retained'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}, indent=2))


if __name__ == '__main__':
    main()
