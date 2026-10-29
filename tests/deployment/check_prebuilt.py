"""Fail before upload when Vercel's actual prebuilt artifact lacks the API."""
import json
import subprocess
import tempfile
from pathlib import Path


def check_upload_paths(repository, mapping):
    # Vercel uses gitignore-style rules for project files referenced by its
    # filePathMap. The pinned CLI exempts dependency virtual environments from
    # user ignore rules; our Python builder puts its dependencies in this one.
    paths = sorted(set(p for p in mapping.values()
                       if not p.startswith('.vercel/python/.venv/')))
    if not paths:
        return
    with tempfile.TemporaryDirectory(prefix='archive-upload-check-') as tmp:
        root = Path(tmp)
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        (root / '.gitignore').write_bytes((repository / '.vercelignore').read_bytes())
        result = subprocess.run(
            ['git', '-c', 'core.excludesFile=/dev/null', 'check-ignore',
             '--no-index', '-z', '--stdin'], cwd=root,
            input='\0'.join(paths) + '\0', text=True, capture_output=True)
        if result.returncode not in (0, 1):
            raise ValueError('Could not verify prebuilt upload filtering')
        ignored = result.stdout.strip('\0').split('\0') if result.stdout else []
        if ignored:
            raise ValueError('Prebuilt files excluded by .vercelignore: ' + ', '.join(ignored[:5]))


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
    for name, source in mapping.items():
        if not (repository / source).is_file():
            raise ValueError('Prebuilt mapped file is missing: ' + name)
    check_upload_paths(repository, mapping)
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
