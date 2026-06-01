#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path
from urllib.parse import urlparse, urlunparse
import urllib.request
import urllib.error

GUEST_RANKINGS_PATH = Path('data/guest_rankings.csv')
TRANSCRIPTS_DIR = Path('data/transcripts')
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


def derive_transcript_url(episode_url: str) -> str:
    parsed = urlparse(episode_url)
    path = parsed.path.rstrip('/')
    if path.endswith('/transcript'):
        return episode_url
    path = f'{path}/transcript'
    return urlunparse((parsed.scheme, parsed.netloc, path, '', '', ''))


def episode_slug(episode_url: str) -> str:
    parsed = urlparse(episode_url)
    path = parsed.path.strip('/')
    if path.startswith('episodes/'):
        path = path[len('episodes/'):]
    return path.replace('/', '_') or 'episode'


def transcript_filename(episode_url: str) -> Path:
    slug = episode_slug(episode_url)
    return TRANSCRIPTS_DIR / f'{slug}_transcript.html'


def fetch_transcript(transcript_url: str) -> str:
    request = urllib.request.Request(
        transcript_url,
        headers={'User-Agent': 'Mozilla/5.0 (compatible; TSSE-Transcript-Ingestion/1.0)'}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            if status != 200:
                raise ValueError(f'Unexpected HTTP status: {status}')
            raw = response.read()
            charset = response.headers.get_content_charset('utf-8')
            return raw.decode(charset, errors='replace')
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'HTTP error fetching transcript URL: {exc.code} {exc.reason}')
    except urllib.error.URLError as exc:
        raise RuntimeError(f'URL error fetching transcript URL: {exc.reason}')


def save_transcript(content: str, path: Path) -> Path:
    path.write_text(content, encoding='utf-8')
    return path


def first_rank4_episode_url() -> str:
    if not GUEST_RANKINGS_PATH.exists():
        raise FileNotFoundError(f'Missing guest rankings file: {GUEST_RANKINGS_PATH}')
    with GUEST_RANKINGS_PATH.open(newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            if row.get('GUEST RANK', '').strip() == '4':
                url = row.get('URL', '').strip()
                if url:
                    return url
    raise ValueError('No Rank 4 episode URL found in guest rankings')


def validate_saved_transcript(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding='utf-8', errors='replace')
    return len(text) > 100 and '<html' in text.lower()


def main() -> None:
    parser = argparse.ArgumentParser(description='Transcript ingestion prototype for TSSE episodes.')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--episode-url', help='The TSSE episode URL to ingest.')
    group.add_argument('--sample-rank4', action='store_true', help='Use the first Rank 4 episode from data/guest_rankings.csv.')
    parser.add_argument('--output-dir', default=str(TRANSCRIPTS_DIR), help='Directory to save transcripts.')
    args = parser.parse_args()

    if not args.episode_url and not args.sample_rank4:
        parser.error('Either --episode-url or --sample-rank4 must be provided.')

    episode_url = args.episode_url
    if args.sample_rank4:
        episode_url = first_rank4_episode_url()
        print(f'Using first Rank 4 episode URL from guest_rankings.csv: {episode_url}')

    transcript_url = derive_transcript_url(episode_url)
    print(f'Derived transcript URL: {transcript_url}')

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / transcript_filename(episode_url).name

    try:
        transcript_text = fetch_transcript(transcript_url)
        save_transcript(transcript_text, output_path)
        print(f'Transcript saved to: {output_path}')
        if validate_saved_transcript(output_path):
            print('Validation passed: transcript file looks valid.')
        else:
            print('Validation warning: transcript file may be incomplete or invalid.')
    except Exception as exc:
        print(f'Error: {exc}')
        raise


if __name__ == '__main__':
    main()
