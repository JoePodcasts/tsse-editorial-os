#!/usr/bin/env python3
import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DATA_DIR = Path(__file__).parent / "data"
HISTORY_CSV = DATA_DIR / "newsletter_history.csv"
EPISODE_DIR = DATA_DIR / "episodes"


@dataclass
class CandidateStats:
    guest: str
    appearances: int = 0
    last_issue: Optional[int] = None
    issue_numbers: List[int] = field(default_factory=list)
    record: Dict[str, Any] = field(default_factory=dict)

    def add_appearance(self, issue_number: Optional[int]):
        self.appearances += 1
        if issue_number is not None:
            self.issue_numbers.append(issue_number)
            if self.last_issue is None or issue_number > self.last_issue:
                self.last_issue = issue_number


def load_newsletter_history(path: Path = HISTORY_CSV) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def parse_issue_number(value: str) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def load_episode_records(path: Path = EPISODE_DIR) -> List[Dict[str, Any]]:
    records = []
    if not path.exists():
        return records
    for json_file in path.glob("*.json"):
        try:
            record = json.loads(json_file.read_text(encoding="utf-8"))
            if record.get("episode_number"):
                records.append(record)
        except json.JSONDecodeError:
            continue
    return records


def build_candidate_stats(history: Iterable[Dict[str, str]]) -> Dict[str, CandidateStats]:
    candidates: Dict[str, CandidateStats] = {}
    for row in history:
        guest_name = row.get("connected_insight_guest", "").strip()
        if not guest_name:
            continue
        issue_num = parse_issue_number(row.get("issue_number", ""))
        stats = candidates.setdefault(guest_name, CandidateStats(guest=guest_name))
        stats.add_appearance(issue_num)
    return candidates


def get_guest_record_map(episode_records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    result = {}
    for record in episode_records:
        guest = record.get("guest_name", "").strip()
        if guest:
            result[guest] = record
    return result


def compute_theme_score(current: Dict[str, Any], candidate: Dict[str, Any]) -> int:
    score = 0
    current_primary = current.get("primary_theme", "").strip().lower()
    current_secondary = [t.strip().lower() for t in current.get("secondary_themes", []) if t and isinstance(t, str)]
    candidate_primary = candidate.get("primary_theme", "").strip().lower()
    candidate_secondary = [t.strip().lower() for t in candidate.get("secondary_themes", []) if t and isinstance(t, str)]

    if current_primary and candidate_primary:
        if current_primary == candidate_primary:
            score += 20
        elif current_primary in candidate_secondary:
            score += 10
        elif candidate_primary in current_secondary:
            score += 5

    for theme in current_secondary:
        if theme and theme == candidate_primary:
            score += 10
        if theme and theme in candidate_secondary:
            score += 5

    return score


def compute_industry_score(current: Dict[str, Any], candidate: Dict[str, Any]) -> int:
    current_industries = {i.strip().lower() for i in current.get("industries", []) if i and isinstance(i, str)}
    candidate_industries = {i.strip().lower() for i in candidate.get("industries", []) if i and isinstance(i, str)}
    return len(current_industries & candidate_industries) * 5


def score_candidate(stats: CandidateStats, current_episode: Dict[str, Any], latest_issue: Optional[int]) -> Dict[str, Any]:
    freq_score = min(stats.appearances * 8, 40)
    recency_score = 0
    issues_since_last = None
    if latest_issue is not None and stats.last_issue is not None:
        issues_since_last = latest_issue - stats.last_issue
        if issues_since_last <= 4:
            recency_score -= 20
        elif issues_since_last <= 8:
            recency_score -= 5
        elif issues_since_last <= 12:
            recency_score += 5
        else:
            recency_score += 15
    elif stats.last_issue is None:
        recency_score += 5

    metadata_score = 0
    rationale = []
    if stats.record:
        theme_score = compute_theme_score(current_episode, stats.record)
        industry_score = compute_industry_score(current_episode, stats.record)
        metadata_score = theme_score + industry_score
        if theme_score > 0:
            rationale.append(f"Theme alignment +{theme_score}")
        if industry_score > 0:
            rationale.append(f"Industry overlap +{industry_score}")

    if stats.appearances > 1:
        rationale.append(f"Appeared {stats.appearances} times historically")
    else:
        rationale.append("Single historical appearance")

    if issues_since_last is not None:
        if issues_since_last <= 4:
            rationale.append("Too recent: penalized")
        elif issues_since_last <= 8:
            rationale.append("Recent appearance: mild penalty")
        elif issues_since_last <= 12:
            rationale.append("Moderate recency")
        else:
            rationale.append("Not featured recently")

    score = freq_score + recency_score + metadata_score
    return {
        "guest": stats.guest,
        "score": score,
        "frequency": stats.appearances,
        "last_issue": stats.last_issue,
        "issues_since_last": issues_since_last,
        "history_appearances": stats.issue_numbers,
        "theme_match_score": metadata_score,
        "rationale": rationale,
    }


def summarize_connected_insights_history(history_records: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
    history_records = history_records if history_records is not None else load_newsletter_history()
    stats = build_candidate_stats(history_records)
    summary = []
    for candidate in stats.values():
        summary.append({
            "guest": candidate.guest,
            "frequency": candidate.appearances,
            "last_issue": candidate.last_issue,
            "history_appearances": sorted(candidate.issue_numbers),
        })
    summary.sort(key=lambda item: (item["frequency"], item["last_issue"] or 0), reverse=True)
    return summary


def recommend_connected_insights(
    current_episode: Dict[str, Any],
    episode_records: Optional[List[Dict[str, Any]]] = None,
    history_records: Optional[List[Dict[str, str]]] = None,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    history_records = history_records if history_records is not None else load_newsletter_history()
    episode_records = episode_records if episode_records is not None else load_episode_records()

    latest_issue = None
    issue_numbers = [parse_issue_number(r.get("issue_number", "")) for r in history_records]
    issue_numbers = [n for n in issue_numbers if n is not None]
    if issue_numbers:
        latest_issue = max(issue_numbers)

    stats = build_candidate_stats(history_records)
    guest_record_map = get_guest_record_map(episode_records)
    for candidate in stats.values():
        if candidate.guest in guest_record_map:
            candidate.record = guest_record_map[candidate.guest]

    scored = [score_candidate(candidate, current_episode, latest_issue) for candidate in stats.values()]
    scored = [item for item in scored if item["score"] is not None]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


def parse_args():
    parser = argparse.ArgumentParser(description="Connected Insights recommendation prototype")
    parser.add_argument("--primary-theme", type=str, default="", help="Current episode primary theme")
    parser.add_argument("--secondary-theme", action="append", default=[], help="Current episode secondary theme")
    parser.add_argument("--industry", action="append", default=[], help="Current episode industry")
    parser.add_argument("--top-n", type=int, default=10, help="Number of recommendations to return")
    return parser.parse_args()


def main():
    args = parse_args()
    current_episode = {
        "primary_theme": args.primary_theme,
        "secondary_themes": args.secondary_theme,
        "industries": args.industry,
    }
    recommendations = recommend_connected_insights(current_episode, top_n=args.top_n)
    output = {
        "current_episode": current_episode,
        "recommendations": recommendations,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
