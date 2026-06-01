#!/usr/bin/env python3
import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

DATA_DIR = Path(__file__).parent / "data"
HISTORY_CSV = DATA_DIR / "newsletter_history.csv"
EPISODE_DIR = DATA_DIR / "episodes" / "rank4"


@dataclass
class CandidateStats:
    guest: str
    appearances: int = 0
    last_issue: Optional[int] = None
    issue_numbers: List[int] = field(default_factory=list)

    def add_appearance(self, issue_number: Optional[int]) -> None:
        self.appearances += 1
        if issue_number is not None:
            self.issue_numbers.append(issue_number)
            if self.last_issue is None or issue_number > self.last_issue:
                self.last_issue = issue_number


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip().lower()
    text = re.sub(r"[\s\u00A0]+", " ", text)
    return text


def tokenize(value: str) -> Set[str]:
    return set(re.findall(r"\w+", normalize_text(value)))


def load_newsletter_history(path: Path = HISTORY_CSV) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def parse_issue_number(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def load_episode_records(path: Path = EPISODE_DIR) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not path.exists():
        return records
    for json_file in sorted(path.glob("*.json"), key=lambda p: p.name):
        try:
            record = json.loads(json_file.read_text(encoding="utf-8"))
            if record.get("guest_name"):
                records.append(record)
        except json.JSONDecodeError:
            continue
    return records


def build_history_stats(history: Iterable[Dict[str, str]]) -> Dict[str, CandidateStats]:
    stats: Dict[str, CandidateStats] = {}
    for row in history:
        guest_name = normalize_text(row.get("connected_insight_guest", ""))
        if not guest_name:
            continue
        stats.setdefault(guest_name, CandidateStats(guest=row.get("connected_insight_guest", "").strip()))
        stats[guest_name].add_appearance(parse_issue_number(row.get("issue_number", "")))
    return stats


def get_guest_record_map(episode_records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for record in episode_records:
        guest = record.get("guest_name", "").strip()
        if guest:
            result[normalize_text(guest)] = record
    return result


def current_episode_from_issue(row: Dict[str, str], guest_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    episode_number = parse_issue_number(row.get("featured_episode", ""))
    if episode_number is not None:
        for record in guest_map.values():
            if record.get("episode_number") == episode_number:
                return record
    featured_guest = normalize_text(row.get("featured_guest", ""))
    if featured_guest in guest_map:
        return guest_map[featured_guest]
    return {
        "primary_theme": normalize_text(row.get("primary_theme", "")),
        "secondary_themes": [],
        "founder_lessons": [],
        "industries": [],
        "guest_name": None,
    }


def build_candidate_pool(episode_records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return get_guest_record_map(episode_records)


def compute_primary_score(current: Dict[str, Any], candidate: Dict[str, Any]) -> int:
    current_primary = normalize_text(current.get("primary_theme", ""))
    candidate_primary = normalize_text(candidate.get("primary_theme", ""))
    current_secondary = {normalize_text(v) for v in current.get("secondary_themes", []) if v}
    candidate_secondary = {normalize_text(v) for v in candidate.get("secondary_themes", []) if v}
    if not current_primary or not candidate_primary:
        return 0
    if current_primary == candidate_primary:
        return 40
    if candidate_primary in current_secondary or current_primary in candidate_secondary:
        return 25
    if current_primary in candidate_primary or candidate_primary in current_primary:
        return 15
    if len(tokenize(current_primary) & tokenize(candidate_primary)) >= 3:
        return 10
    return 0


def compute_secondary_score(current: Dict[str, Any], candidate: Dict[str, Any]) -> int:
    current_secondary = [normalize_text(v) for v in current.get("secondary_themes", []) if v]
    candidate_secondary = [normalize_text(v) for v in candidate.get("secondary_themes", []) if v]
    exact_overlap = len(set(current_secondary) & set(candidate_secondary))
    score = exact_overlap * 6
    for current_theme in current_secondary:
        current_tokens = tokenize(current_theme)
        for candidate_theme in candidate_secondary:
            overlap = len(current_tokens & tokenize(candidate_theme))
            if overlap >= 4:
                score += 4
            elif overlap == 3:
                score += 2
            elif overlap == 2:
                score += 1
    return score


def compute_lesson_score(current: Dict[str, Any], candidate: Dict[str, Any]) -> int:
    current_lessons = [normalize_text(v) for v in current.get("founder_lessons", []) if v]
    candidate_lessons = [normalize_text(v) for v in candidate.get("founder_lessons", []) if v]
    exact_overlap = len(set(current_lessons) & set(candidate_lessons))
    score = exact_overlap * 3
    for current_lesson in current_lessons:
        current_tokens = tokenize(current_lesson)
        for candidate_lesson in candidate_lessons:
            overlap = len(current_tokens & tokenize(candidate_lesson))
            if overlap >= 8:
                score += 3
            elif overlap >= 5:
                score += 2
            elif overlap >= 3:
                score += 1
    return score


def compute_industry_score(current: Dict[str, Any], candidate: Dict[str, Any]) -> int:
    current_industries = {normalize_text(v) for v in current.get("industries", []) if v}
    candidate_industries = {normalize_text(v) for v in candidate.get("industries", []) if v}
    return len(current_industries & candidate_industries) * 5


def compute_recency_score(stats: CandidateStats, latest_issue: Optional[int]) -> int:
    if stats.last_issue is None or latest_issue is None:
        return 8
    elapsed = latest_issue - stats.last_issue
    if elapsed <= 4:
        return -20
    if elapsed <= 8:
        return -8
    if elapsed <= 12:
        return 0
    return 10


def compute_frequency_score(stats: CandidateStats) -> int:
    if stats.appearances == 0:
        return 0
    return min(stats.appearances * 5, 25)


def score_candidate(
    guest_name: str,
    candidate: Dict[str, Any],
    current_episode: Dict[str, Any],
    stats: CandidateStats,
    latest_issue: Optional[int],
) -> Dict[str, Any]:
    theme_score = compute_primary_score(current_episode, candidate)
    theme_score += compute_secondary_score(current_episode, candidate)
    theme_score += compute_lesson_score(current_episode, candidate)
    industry_score = compute_industry_score(current_episode, candidate)
    recency_score = compute_recency_score(stats, latest_issue)
    frequency_score = compute_frequency_score(stats)

    rationale: List[str] = []
    if theme_score > 0:
        rationale.append(f"Theme score +{theme_score}")
    if industry_score > 0:
        rationale.append(f"Industry overlap +{industry_score}")
    if stats.appearances > 0:
        rationale.append(f"Historical Connected Insights frequency {stats.appearances}")
    else:
        rationale.append("No historical Connected Insights appearances")
    if latest_issue is not None and stats.last_issue is not None:
        issues_since_last = latest_issue - stats.last_issue
        rationale.append(f"Last featured {issues_since_last} issues ago")
    elif stats.last_issue is None:
        rationale.append("Fresh candidate by history")

    score = theme_score + industry_score + recency_score + frequency_score
    return {
        "guest": candidate.get("guest_name", guest_name),
        "score": score,
        "theme_score": theme_score,
        "industry_score": industry_score,
        "recency_score": recency_score,
        "frequency_score": frequency_score,
        "rationale": rationale,
        "candidate_episode": candidate.get("episode_number"),
        "candidate_primary_theme": candidate.get("primary_theme"),
    }


def recommend_connected_insights_v2(
    current_episode: Dict[str, Any],
    episode_records: Optional[List[Dict[str, Any]]] = None,
    history_records: Optional[List[Dict[str, str]]] = None,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    episode_records = episode_records if episode_records is not None else load_episode_records()
    history_records = history_records if history_records is not None else load_newsletter_history()

    guest_map = build_candidate_pool(episode_records)
    history_stats = build_history_stats(history_records)

    latest_issue = None
    issue_numbers = [parse_issue_number(r.get("issue_number", "")) for r in history_records]
    issue_numbers = [n for n in issue_numbers if n is not None]
    if issue_numbers:
        latest_issue = max(issue_numbers)

    current_guest = normalize_text(current_episode.get("guest_name", ""))
    scored: List[Dict[str, Any]] = []
    for guest_key, candidate in guest_map.items():
        if guest_key and current_guest and guest_key == current_guest:
            continue
        stats = history_stats.get(guest_key, CandidateStats(guest=candidate.get("guest_name", "")))
        scored.append(score_candidate(candidate.get("guest_name", guest_key), candidate, current_episode, stats, latest_issue))

    scored.sort(key=lambda item: (item["score"], item["theme_score"], item["industry_score"]), reverse=True)
    return scored[:top_n]


def validate_historical_issues(
    issue_numbers: List[int],
    episode_records: Optional[List[Dict[str, Any]]] = None,
    history_records: Optional[List[Dict[str, str]]] = None,
    top_n: int = 3,
) -> Dict[str, Any]:
    episode_records = episode_records if episode_records is not None else load_episode_records()
    history_records = history_records if history_records is not None else load_newsletter_history()
    guest_map = build_candidate_pool(episode_records)
    issue_map = {parse_issue_number(row.get("issue_number", "")): row for row in history_records if parse_issue_number(row.get("issue_number", "")) is not None}
    latest_issue = max((parse_issue_number(row.get("issue_number", "")) for row in history_records if parse_issue_number(row.get("issue_number", "")) is not None), default=None)

    results: List[Dict[str, Any]] = []
    hits = 0
    for issue in issue_numbers:
        row = issue_map.get(issue)
        if not row:
            continue
        current_episode = current_episode_from_issue(row, guest_map)
        recommendations = recommend_connected_insights_v2(current_episode, episode_records, history_records, top_n=top_n)
        top_recommendation = recommendations[0]["guest"] if recommendations else None
        top3 = [item["guest"] for item in recommendations]
        actual_label = row.get("connected_insight_guest", "")
        exact_match = actual_label.strip() in top3
        if exact_match:
            hits += 1
        results.append({
            "issue": issue,
            "actual_connected_insight_label": actual_label,
            "top_recommendation": top_recommendation,
            "top_3": top3,
            "exact_match": exact_match,
            "used_featured_episode": current_episode.get("episode_number"),
            "current_guest": current_episode.get("guest_name"),
        })

    hit_rate = 0.0
    if results:
        hit_rate = hits / len(results) * 100
    return {
        "results": results,
        "hit_rate": hit_rate,
        "total_issues": len(results),
        "matches": hits,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Connected Insights recommendation prototype v2")
    parser.add_argument("--primary-theme", type=str, default="", help="Current episode primary theme")
    parser.add_argument("--secondary-theme", action="append", default=[], help="Current episode secondary theme")
    parser.add_argument("--founder-lesson", action="append", default=[], help="Current episode founder lesson")
    parser.add_argument("--industry", action="append", default=[], help="Current episode industry")
    parser.add_argument("--current-guest", type=str, default="", help="Current episode guest name")
    parser.add_argument("--issue-number", type=int, help="Newsletter issue number to use for current episode metadata")
    parser.add_argument("--top-n", type=int, default=10, help="Number of recommendations to return")
    parser.add_argument("--validate-historical", action="store_true", help="Run the original historical validation issues 66-75")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    episode_records = load_episode_records()
    history_records = load_newsletter_history()
    if args.validate_historical:
        validation = validate_historical_issues([66, 67, 68, 69, 70, 71, 72, 73, 74, 75], episode_records, history_records, top_n=3)
        print(json.dumps(validation, indent=2, ensure_ascii=False))
        return

    current_episode = {
        "primary_theme": args.primary_theme,
        "secondary_themes": args.secondary_theme,
        "founder_lessons": args.founder_lesson,
        "industries": args.industry,
        "guest_name": args.current_guest,
    }
    if args.issue_number is not None:
        issue_map = {parse_issue_number(row.get("issue_number", "")): row for row in history_records if parse_issue_number(row.get("issue_number", "")) is not None}
        row = issue_map.get(args.issue_number)
        if row:
            current_episode = current_episode_from_issue(row, get_guest_record_map(episode_records))

    recommendations = recommend_connected_insights_v2(current_episode, episode_records, history_records, top_n=args.top_n)
    print(json.dumps({"current_episode": current_episode, "recommendations": recommendations}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
