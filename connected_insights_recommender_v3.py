#!/usr/bin/env python3
import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

DATA_DIR = Path(__file__).parent / "data"
EPISODE_DIR = DATA_DIR / "episodes" / "rank4"
HISTORY_CSV = DATA_DIR / "newsletter_history.csv"

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "not",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "through",
    "to",
    "with",
    "without",
    "you",
    "your",
}


@dataclass
class HistoryStats:
    guest: str
    appearances: int = 0
    last_issue: Optional[int] = None
    issue_numbers: List[int] = field(default_factory=list)
    matched_labels: List[str] = field(default_factory=list)

    def add(self, issue_number: Optional[int], label: str) -> None:
        self.appearances += 1
        self.matched_labels.append(label)
        if issue_number is not None:
            self.issue_numbers.append(issue_number)
            if self.last_issue is None or issue_number > self.last_issue:
                self.last_issue = issue_number


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip().lower()
    text = re.sub(r"[\s\u00a0]+", " ", text)
    return text


def tokenize(value: Any) -> Set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", normalize_text(value))
        if token not in STOPWORDS and len(token) > 1
    }


def parse_issue_number(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def load_episode_records(path: Path = EPISODE_DIR) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for json_file in sorted(path.glob("episode_*.json"), key=lambda p: int(p.stem.split("_")[1])):
        record = json.loads(json_file.read_text(encoding="utf-8"))
        records.append(record)
    return records


def load_newsletter_history(path: Path = HISTORY_CSV) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
      return [dict(row) for row in csv.DictReader(f)]


def latest_issue_number(history: Iterable[Dict[str, str]]) -> Optional[int]:
    issue_numbers = [parse_issue_number(row.get("issue_number")) for row in history]
    issue_numbers = [issue for issue in issue_numbers if issue is not None]
    return max(issue_numbers) if issue_numbers else None


def label_matches_guest(label: str, guest_name: str) -> bool:
    normalized_label = normalize_text(label)
    normalized_guest = normalize_text(guest_name)
    if not normalized_label or not normalized_guest:
        return False
    guest_tokens = tokenize(normalized_guest)
    label_tokens = tokenize(normalized_label)
    return normalized_guest == normalized_label or guest_tokens.issubset(label_tokens)


def build_history_stats(
    episode_records: Iterable[Dict[str, Any]],
    history_records: Iterable[Dict[str, str]],
) -> Dict[str, HistoryStats]:
    stats = {
        normalize_text(record.get("guest_name")): HistoryStats(record.get("guest_name", ""))
        for record in episode_records
        if record.get("guest_name")
    }
    for row in history_records:
        label = row.get("connected_insight_guest", "").strip()
        issue = parse_issue_number(row.get("issue_number"))
        if not label:
            continue
        for record in episode_records:
            guest = record.get("guest_name", "")
            guest_key = normalize_text(guest)
            if label_matches_guest(label, guest):
                stats[guest_key].add(issue, label)
    return stats


def list_values(record: Dict[str, Any], key: str) -> List[str]:
    value = record.get(key, [])
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []


def token_overlap_score(current: str, candidate: str, *, exact: int, strong: int, medium: int, light: int) -> int:
    current_norm = normalize_text(current)
    candidate_norm = normalize_text(candidate)
    if not current_norm or not candidate_norm:
        return 0
    if current_norm == candidate_norm:
        return exact
    current_tokens = tokenize(current_norm)
    candidate_tokens = tokenize(candidate_norm)
    overlap = len(current_tokens & candidate_tokens)
    if overlap >= 4:
        return strong
    if overlap == 3:
        return medium
    if overlap == 2:
        return light
    return 0


def match_list_items(
    current_items: List[str],
    candidate_items: List[str],
    *,
    exact: int,
    strong: int,
    medium: int,
    light: int,
) -> Tuple[int, List[Dict[str, str]]]:
    score = 0
    matches: List[Dict[str, str]] = []
    used: Set[Tuple[str, str]] = set()
    for current in current_items:
        for candidate in candidate_items:
            pair = (current, candidate)
            if pair in used:
                continue
            item_score = token_overlap_score(
                current,
                candidate,
                exact=exact,
                strong=strong,
                medium=medium,
                light=light,
            )
            if item_score:
                used.add(pair)
                score += item_score
                matches.append({
                    "current": current,
                    "candidate": candidate,
                    "score": item_score,
                })
    return score, matches


def compute_primary_theme_score(current: Dict[str, Any], candidate: Dict[str, Any]) -> Tuple[int, List[Dict[str, str]]]:
    current_primary = current.get("primary_theme", "")
    candidate_primary = candidate.get("primary_theme", "")
    score = token_overlap_score(current_primary, candidate_primary, exact=40, strong=24, medium=16, light=8)
    matches: List[Dict[str, str]] = []
    if score:
        matches.append({"current": current_primary, "candidate": candidate_primary, "score": score})
    secondary_score, secondary_matches = match_list_items(
        [current_primary],
        list_values(candidate, "secondary_themes"),
        exact=24,
        strong=14,
        medium=10,
        light=5,
    )
    candidate_primary_score, candidate_primary_matches = match_list_items(
        list_values(current, "secondary_themes"),
        [candidate_primary],
        exact=20,
        strong=12,
        medium=8,
        light=4,
    )
    return score + secondary_score + candidate_primary_score, matches + secondary_matches + candidate_primary_matches


def exact_case_map(values: List[str]) -> Dict[str, str]:
    return {normalize_text(value): value for value in values if normalize_text(value)}


def exact_overlap(current_items: List[str], candidate_items: List[str], points: int) -> Tuple[int, List[str]]:
    current_map = exact_case_map(current_items)
    candidate_map = exact_case_map(candidate_items)
    overlap = sorted(set(current_map) & set(candidate_map))
    return len(overlap) * points, [candidate_map[item] for item in overlap]


def compute_recency(stats: HistoryStats, latest_issue: Optional[int]) -> Tuple[int, str]:
    if stats.appearances == 0 or stats.last_issue is None or latest_issue is None:
        return 8, "No normalized Connected Insights appearance found; treated as fresh."
    elapsed = latest_issue - stats.last_issue
    if elapsed <= 4:
        return -20, f"Featured {elapsed} issues ago; strong recency penalty."
    if elapsed <= 8:
        return -10, f"Featured {elapsed} issues ago; moderate recency penalty."
    if elapsed <= 12:
        return -3, f"Featured {elapsed} issues ago; light recency penalty."
    return 8, f"Last normalized appearance was {elapsed} issues ago; eligible for resurfacing."


def compute_frequency(stats: HistoryStats) -> Tuple[int, str]:
    if stats.appearances == 0:
        return 0, "No normalized historical usage."
    score = min(stats.appearances * 4, 16)
    return score, f"{stats.appearances} normalized historical appearance(s)."


def plain_english_rationale(
    candidate: Dict[str, Any],
    matched_themes: List[Dict[str, str]],
    matched_lessons: List[Dict[str, str]],
    matched_industries: List[str],
    matched_orgs: List[str],
    recency_note: str,
) -> str:
    parts = []
    if matched_themes:
        theme = matched_themes[0]["candidate"]
        parts.append(f"{candidate['guest_name']} is relevant because Episode {candidate['episode_number']} shares the theme of {theme}.")
    else:
        parts.append(f"{candidate['guest_name']} is a lower-theme-overlap candidate from Episode {candidate['episode_number']}.")
    if matched_lessons:
        parts.append("The founder lessons also connect, especially around " + matched_lessons[0]["candidate"].rstrip(".") + ".")
    if matched_industries:
        parts.append("Industry overlap: " + ", ".join(matched_industries) + ".")
    if matched_orgs:
        parts.append("Community overlap: " + ", ".join(matched_orgs) + ".")
    parts.append(recency_note)
    return " ".join(parts)


def score_candidate(
    current: Dict[str, Any],
    candidate: Dict[str, Any],
    stats: HistoryStats,
    latest_issue: Optional[int],
) -> Dict[str, Any]:
    primary_score, primary_matches = compute_primary_theme_score(current, candidate)
    secondary_score, secondary_matches = match_list_items(
        list_values(current, "secondary_themes"),
        list_values(candidate, "secondary_themes"),
        exact=14,
        strong=8,
        medium=5,
        light=2,
    )
    lesson_score, lesson_matches = match_list_items(
        list_values(current, "founder_lessons"),
        list_values(candidate, "founder_lessons"),
        exact=10,
        strong=6,
        medium=4,
        light=2,
    )
    industry_score, matched_industries = exact_overlap(
        list_values(current, "industries"),
        list_values(candidate, "industries"),
        7,
    )
    org_score, matched_orgs = exact_overlap(
        list_values(current, "community_organizations"),
        list_values(candidate, "community_organizations"),
        5,
    )
    recency_score, recency_note = compute_recency(stats, latest_issue)
    frequency_score, frequency_note = compute_frequency(stats)

    matched_themes = primary_matches + secondary_matches
    score = primary_score + secondary_score + lesson_score + industry_score + org_score + recency_score + frequency_score

    return {
        "guest_name": candidate.get("guest_name"),
        "episode_number": candidate.get("episode_number"),
        "score": score,
        "matched_themes": matched_themes,
        "matched_founder_lessons": lesson_matches,
        "matched_industries": matched_industries,
        "matched_community_organizations": matched_orgs,
        "recency_note": recency_note,
        "frequency_note": frequency_note,
        "score_breakdown": {
            "primary_theme": primary_score,
            "secondary_themes": secondary_score,
            "founder_lessons": lesson_score,
            "industries": industry_score,
            "community_organizations": org_score,
            "recency": recency_score,
            "frequency": frequency_score,
        },
        "plain_english_rationale": plain_english_rationale(
            candidate,
            matched_themes,
            lesson_matches,
            matched_industries,
            matched_orgs,
            recency_note,
        ),
    }


def find_record_by_episode(records: Iterable[Dict[str, Any]], episode_number: int) -> Optional[Dict[str, Any]]:
    for record in records:
        if record.get("episode_number") == episode_number:
            return record
    return None


def current_episode_from_args(args: argparse.Namespace, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if args.current_episode is not None:
        record = find_record_by_episode(records, args.current_episode)
        if record is None:
            raise SystemExit(f"Could not find episode {args.current_episode} in {EPISODE_DIR}.")
        return record
    if args.current_record:
        return json.loads(Path(args.current_record).read_text(encoding="utf-8"))
    return {
        "guest_name": args.current_guest,
        "primary_theme": args.primary_theme,
        "secondary_themes": args.secondary_theme,
        "founder_lessons": args.founder_lesson,
        "industries": args.industry,
        "community_organizations": args.community_organization,
    }


def recommend_connected_insights_v3(
    current_episode: Dict[str, Any],
    episode_records: Optional[List[Dict[str, Any]]] = None,
    history_records: Optional[List[Dict[str, str]]] = None,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    episode_records = episode_records if episode_records is not None else load_episode_records()
    history_records = history_records if history_records is not None else load_newsletter_history()
    history = build_history_stats(episode_records, history_records)
    latest_issue = latest_issue_number(history_records)
    current_guest = normalize_text(current_episode.get("guest_name"))
    current_episode_number = current_episode.get("episode_number")

    recommendations = []
    for candidate in episode_records:
        if current_episode_number and candidate.get("episode_number") == current_episode_number:
            continue
        if current_guest and normalize_text(candidate.get("guest_name")) == current_guest:
            continue
        stats = history.get(normalize_text(candidate.get("guest_name")), HistoryStats(candidate.get("guest_name", "")))
        recommendations.append(score_candidate(current_episode, candidate, stats, latest_issue))

    recommendations.sort(
        key=lambda item: (
            item["score"],
            item["score_breakdown"]["primary_theme"] + item["score_breakdown"]["secondary_themes"],
            item["score_breakdown"]["founder_lessons"],
            item["score_breakdown"]["industries"],
        ),
        reverse=True,
    )
    return recommendations[:top_n]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Connected Insights recommendation engine v3")
    parser.add_argument("--current-episode", type=int, help="Use an existing Rank 4 episode record as the current episode.")
    parser.add_argument("--current-record", type=str, help="Path to a JSON current episode record.")
    parser.add_argument("--current-guest", type=str, default="", help="Current episode guest name.")
    parser.add_argument("--primary-theme", type=str, default="", help="Current episode primary theme.")
    parser.add_argument("--secondary-theme", action="append", default=[], help="Current episode secondary theme.")
    parser.add_argument("--founder-lesson", action="append", default=[], help="Current episode founder lesson.")
    parser.add_argument("--industry", action="append", default=[], help="Current episode industry.")
    parser.add_argument("--community-organization", action="append", default=[], help="Current episode community organization.")
    parser.add_argument("--top-n", type=int, default=10, help="Number of recommendations to return.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_episode_records()
    history = load_newsletter_history()
    current_episode = current_episode_from_args(args, records)
    recommendations = recommend_connected_insights_v3(current_episode, records, history, top_n=args.top_n)
    print(json.dumps({"current_episode": current_episode, "recommendations": recommendations}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
