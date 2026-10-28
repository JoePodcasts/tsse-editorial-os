"""Fail before upload when Vercel's actual prebuilt artifact lacks the API."""
import json
from pathlib import Path


def check(repository):
    repository = Path(repository).resolve()
    output = repository / '.vercel/output'
    function = output / 'functions/api/archive_function.func'
    config_path = function / '.vc-config.json'
    if not config_path.is_file():
        raise ValueError('Prebuilt archive API function is missing: ' + str(config_path))
    config = json.loads(config_path.read_text())
    if config.get('runtime') != 'python3.12':
        raise ValueError('Archive API must use the Python 3.12 runtime')
    # The CLI can reference project files through filePathMap instead of copying
    # them into .func. Both are supported Build Output representations.
    mapping = config.get('filePathMap', {})
    required = [
        'api/archive_function.py',
        'vercel_runtime/archive_public.py',
        'vercel_runtime/archive/search/archive.sqlite3',
        'vercel_runtime/archive/catalogue.jsonl',
        'vercel_runtime/archive/sync-status.json',
    ]
    handler = config.get('handler', '').split('.')[0] + '.py'
    for name in [handler, *required]:
        path = repository / mapping[name] if name in mapping else function / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError('Prebuilt archive API is missing a required file: ' + name)
    routes = json.loads((output / 'config.json').read_text()).get('routes', [])
    if not any('/api/archive_function?route=' in r.get('dest', '') for r in routes):
        raise ValueError('Prebuilt API rewrite does not target archive_function')
    if not (output / 'static/index.html').is_file():
        raise ValueError('Prebuilt archive homepage is missing')
    return {'function': 'api/archive_function', 'runtime': config['runtime'],
            'required_files': len(required) + 1}


if __name__ == '__main__':
    print(json.dumps(check(Path(__file__).resolve().parents[2]), indent=2))
