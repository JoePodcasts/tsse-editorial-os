"""Read-only localhost timing samples; launch archive_web.py first."""
import argparse
import json
import statistics
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


def measure(base, route, samples):
    durations, size = [], 0
    for _ in range(samples):
        start = time.perf_counter()
        with urlopen(base + route, timeout=15) as response:
            raw = response.read()
        durations.append((time.perf_counter() - start) * 1000)
        size = len(raw)
    ordered = sorted(durations)
    return {'samples': samples, 'median_ms': round(statistics.median(durations), 2),
            'p95_ms': round(ordered[max(0, int(len(ordered) * .95 + .999) - 1)], 2),
            'min_ms': round(ordered[0], 2), 'max_ms': round(ordered[-1], 2), 'response_bytes': size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8765')
    parser.add_argument('--samples', type=int, default=20)
    parser.add_argument('--output', type=Path, default=Path('archive/reports/frontend-performance.json'))
    args = parser.parse_args()
    if args.base != 'http://127.0.0.1:8765':
        parser.error('This benchmark is scoped to the local default server.')
    if not 1 <= args.samples <= 100:
        parser.error('Use between 1 and 100 samples.')
    routes = {'app_document': '/', 'initial_coverage': '/api/archive',
              'initial_browse_24': '/api/episodes', 'episode_metadata': '/api/episodes/191',
              'episode_transcript': '/api/episodes/191/content?source=transcript'}
    for q in ['proof of value', 'Gokul Rajaram', 'Commerce Ventures', 'relentlessly resourceful', 'choosing a partner in life', 'founder']:
        routes['search: ' + q] = '/api/search?' + urlencode({'q': q})
    data = {name: measure(args.base, route, args.samples) for name, route in routes.items()}
    report = {'scope': 'Local loopback HTTP responses; warm filesystem; includes JSON transfer, excludes browser rendering',
              'timings': data}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
