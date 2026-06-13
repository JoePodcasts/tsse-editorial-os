#!/usr/bin/env python3
import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
NEWSLETTER_HISTORY = ROOT / "data" / "newsletter_history.csv"
DEFAULT_REPORT = ROOT / "discovery_report.json"

SITE_URL = "https://podcast.sure.ventures"
SIMPLECAST_API = "https://api.simplecast.com"
EPISODE_PAGE_BASE = "https://podcast.sure.ventures/episodes/"


def parse_issue_number(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def request_json(url: str, *, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "TSSE-Editorial-OS/1.0",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def discover_podcast_id(site_url: str = SITE_URL) -> str:
    site = request_json(f"{SIMPLECAST_API}/sites/search", method="POST", payload={"url": site_url})
    podcast = site.get("podcast") or {}
    podcast_id = podcast.get("id")
    if not podcast_id:
        raise RuntimeError(f"Could not discover Simplecast podcast id from {site_url}.")
    return podcast_id


def fetch_podcast_episodes(podcast_id: str, *, limit: int = 100) -> List[Dict[str, Any]]:
    episodes: List[Dict[str, Any]] = []
    next_url: Optional[str] = (
        f"{SIMPLECAST_API}/podcasts/{podcast_id}/episodes"
        f"?status=published&private=false&sort=latest&limit={limit}&offset=0"
    )

    while next_url:
        page = request_json(next_url)
        episodes.extend(page.get("collection", []))
        next_href = ((page.get("pages") or {}).get("next") or {}).get("href")
        next_url = urljoin(SIMPLECAST_API, next_href) if next_href else None

    return episodes


def episode_number_from_item(item: Dict[str, Any]) -> Optional[int]:
    number = parse_issue_number(item.get("number"))
    if number is not None:
        return number
    slug = item.get("slug", "")
    match = re.search(r"tsse[-_]?(\d+)", slug, re.IGNORECASE)
    return int(match.group(1)) if match else None


def infer_guest_name(item: Dict[str, Any]) -> str:
    description = re.sub(r"\s+", " ", item.get("description") or "").strip()
    title = item.get("title") or ""

    patterns = [
        r"^([A-Z][A-Za-z .'\-]+?),\s+(?:co-founder|founder|general partner|partner|managing partner|ceo|chief|cofounder|host|investor|principal|president|coo)\b",
        r"^([A-Z][A-Za-z .'\-]+?)\s+(?:shares|explains|discusses|joins|reflects)\b",
        r"with\s+([A-Z][A-Za-z .'\-]+?)(?:\s+-|,|\s+on\b|\s+about\b)",
    ]
    for source in [description, title]:
        for pattern in patterns:
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip()
    return ""


def normalize_episode(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    episode_number = episode_number_from_item(item)
    slug = item.get("slug")
    if episode_number is None or not slug:
        return None
    episode_url = f"{EPISODE_PAGE_BASE}{slug}"
    return {
        "episode_number": episode_number,
        "episode_title": item.get("title", ""),
        "guest_name": infer_guest_name(item),
        "episode_url": episode_url,
        "transcript_url": f"{episode_url}/transcript",
        "published_at": item.get("published_at", ""),
        "slug": slug,
        "simplecast_id": item.get("id", ""),
    }


def load_newsletter_history(path: Path = NEWSLETTER_HISTORY) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def represented_episode_numbers(history: Iterable[Dict[str, str]]) -> List[int]:
    numbers = []
    for row in history:
        number = parse_issue_number(row.get("featured_episode"))
        if number is not None:
            numbers.append(number)
    return sorted(set(numbers))


def build_discovery_report(
    episodes: List[Dict[str, Any]],
    history: List[Dict[str, str]],
) -> Dict[str, Any]:
    normalized = [
        episode
        for episode in (normalize_episode(item) for item in episodes)
        if episode is not None
    ]
    normalized.sort(key=lambda item: item["episode_number"], reverse=True)

    if not normalized:
        raise RuntimeError("No published TSSE episodes were discovered.")

    represented = represented_episode_numbers(history)
    represented_set = set(represented)
    latest_represented = max(represented) if represented else None

    missing_after_latest = [
        episode
        for episode in normalized
        if latest_represented is None or episode["episode_number"] > latest_represented
    ]
    missing_after_latest.sort(key=lambda item: item["episode_number"], reverse=True)

    newest_episode = normalized[0]
    newest_is_represented = newest_episode["episode_number"] in represented_set
    recommended = missing_after_latest[0] if missing_after_latest else None

    return {
        "source": {
            "site_url": SITE_URL,
            "episode_source": "official Simplecast API used by the TSSE podcast website",
            "newsletter_history": str(NEWSLETTER_HISTORY),
        },
        "newest_episode": newest_episode,
        "newsletter_coverage_status": {
            "latest_episode_already_represented": latest_represented,
            "newest_episode_already_represented": newest_is_represented,
            "episodes_missing_newsletter_coverage_count": len(missing_after_latest),
            "episodes_missing_newsletter_coverage": missing_after_latest,
        },
        "recommended_next_episode_for_newsletter_generation": recommended,
    }


def discover_latest_unpublished_episode() -> Dict[str, Any]:
    podcast_id = discover_podcast_id()
    episodes = fetch_podcast_episodes(podcast_id)
    history = load_newsletter_history()
    return build_discovery_report(episodes, history)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover TSSE episodes needing newsletter production.")
    parser.add_argument("--output", default=str(DEFAULT_REPORT), help="Path to write discovery_report.json.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = discover_latest_unpublished_episode()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"discovery_report": str(output)}, indent=2))


if __name__ == "__main__":
    main()
