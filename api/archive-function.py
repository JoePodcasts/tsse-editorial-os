"""Vercel's supported BaseHTTPRequestHandler entrypoint."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vercel_runtime'))
from archive_public import PublicHandler


class handler(PublicHandler):
    pass
