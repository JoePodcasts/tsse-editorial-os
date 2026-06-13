#!/usr/bin/env python3
import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

DATA_DIR = Path(__file__).parent / "data"
EPISODE_DIR = DATA_DIR / "episodes" / "rank4"
STARTUP_DIR = DATA_DIR / "startups"
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

TOKEN_ALIASES = {
    "ai": {"artificial", "intelligence"},
    "fintech": {"financial", "technology", "finance"},
    "insurtech": {"insurance", "technology"},
    "p&c": {"property", "casualty", "insurance"},
}


@dataclass
class AppearanceStats:
    appearances: int
    last_issue: Optional[int]
    issue_numbers: List[int]


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = value.lower().replace("&", " and ")
    return re.sub(r"\s+", " ", value).strip()


def tokenize(value: Any) -> Set[str]:
    normalized = normalize_text(value)
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", normalized)
        if len(token) > 1 and token not in STOPWORDS
    }
    for alias, expansions in TOKEN_ALIASES.items():
        alias_tokens = set(re.findall(r"[a-z0-9]+", alias))
        if alias in normalized or alias_tokens & tokens:
            tokens.update(expansions)
    return tokens


def parse_issue_number(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def load_episode_records(path: Path = EPISODE_DIR) -> List[Dict[str, Any]]:
    records = []
    for json_file in sorted(path.glob("episode_*.json"), key=lambda p: int(p.stem.split("_")[1])):
        records.append(json.loads(json_file.read_text(encoding="utf-8")))
    return records


def load_startup_records(path: Path = STARTUP_DIR) -> List[Dict[str, Any]]:
    return [
        json.loads(json_file.read_text(encoding="utf-8"))
        for json_file in sorted(path.glob("*.json"))
    ]


def load_newsletter_history(path: Path = HISTORY_CSV) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [dict(row) for row in csv.DictReader(f)]


def latest_issue_number(history: Iterable[Dict[str, str]]) -> Optional[int]:
    issues = [parse_issue_number(row.get("issue_number")) for row in history]
    issues = [issue for issue in issues if issue is not None]
    return max(issues) if issues else None


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
    if not current_tokens or not candidate_tokens:
        return 0
    overlap = len(current_tokens & candidate_tokens)
    if overlap >= 4:
        return strong
    if overlap == 3:
        return medium
    if overlap == 2:
        return light
    return 0


def match_items(
    current_items: List[str],
    startup_items: List[str],
    *,
    exact: int,
    strong: int,
    medium: int,
    light: int,
    max_score: Optional[int] = None,
) -> Tuple[int, List[Dict[str, Any]]]:
    matches: List[Dict[str, Any]] = []
    total = 0
    used: Set[Tuple[str, str]] = set()
    for current in current_items:
        best: Optional[Tuple[int, str]] = None
        for startup in startup_items:
            pair = (current, startup)
            if pair in used:
                continue
            score = token_overlap_score(
                current,
                startup,
                exact=exact,
                strong=strong,
                medium=medium,
                light=light,
            )
            if score and (best is None or score > best[0]):
                best = (score, startup)
        if best:
            score, startup = best
            used.add((current, startup))
            total += score
            matches.append({"episode": current, "startup": startup, "score": score})
    if max_score is not None and total > max_score:
        scale = max_score / total
        total = max_score
        for match in matches:
            match["score"] = round(match["score"] * scale, 2)
    return total, matches


def exact_or_token_industry_score(
    episode_industries: List[str],
    startup_industries: List[str],
) -> Tuple[int, List[Dict[str, Any]]]:
    matches: List[Dict[str, Any]] = []
    total = 0
    startup_by_norm = {normalize_text(ind): ind for ind in startup_industries}
    for industry in episode_industries:
        norm = normalize_text(industry)
        if norm in startup_by_norm:
            total += 7
            matches.append({"episode": industry, "startup": startup_by_norm[norm], "score": 7})
            continue
        best_score = 0
        best_industry = ""
        for startup_industry in startup_industries:
            score = token_overlap_score(industry, startup_industry, exact=7, strong=5, medium=3, light=2)
            if score > best_score:
                best_score = score
                best_industry = startup_industry
        if best_score:
            total += best_score
            matches.append({"episode": industry, "startup": best_industry, "score": best_score})
    return min(total, 18), matches


def appearance_stats(startup: Dict[str, Any]) -> AppearanceStats:
    issues = [
        parse_issue_number(item.get("issue_number"))
        for item in startup.get("previous_newsletter_appearances", [])
        if isinstance(item, dict)
    ]
    issues = sorted([issue for issue in issues if issue is not None], reverse=True)
    return AppearanceStats(
        appearances=len(issues),
        last_issue=max(issues) if issues else None,
        issue_numbers=issues,
    )


def recency_score(stats: AppearanceStats, latest_issue: Optional[int]) -> Tuple[int, str]:
    if stats.last_issue is None or latest_issue is None:
        return 5, "No normalized Startup Corner appearance found; treated as fresh."
    elapsed = latest_issue - stats.last_issue
    if elapsed <= 4:
        return -25, f"Featured {elapsed} issue(s) ago; strong recency penalty."
    if elapsed <= 8:
        return -10, f"Featured {elapsed} issue(s) ago; moderate recency penalty."
    if elapsed <= 12:
        return -3, f"Featured {elapsed} issue(s) ago; light recency penalty."
    return 4, f"Last featured {elapsed} issue(s) ago; eligible for resurfacing."


def frequency_score(stats: AppearanceStats) -> Tuple[int, str]:
    if stats.appearances == 0:
        return 0, "No normalized historical Startup Corner usage."
    if stats.appearances == 1:
        return 0, "1 normalized historical appearance."
    if stats.appearances <= 3:
        return -4, f"{stats.appearances} normalized historical appearances; mild frequency penalty."
    return -8, f"{stats.appearances} normalized historical appearances; high frequency penalty."


def milestone_score(startup: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]], str]:
    milestones = [
        item
        for item in startup.get("notable_milestones", [])
        if isinstance(item, dict)
        and item.get("review_status") in {"official_site_supported", "needs_manual_review"}
    ]
    official = [item for item in milestones if item.get("review_status") == "official_site_supported"]
    if official:
        return 8, official[:2], f"{len(official)} official-site-supported milestone(s) available."
    if milestones:
        return 3, milestones[:2], "Newsletter-history milestone(s) available but require manual review."
    return 0, [], "No notable milestone available in startup intelligence."


def founder_background_score(current: Dict[str, Any], startup: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
    background = startup.get("founder_background", "")
    if not background:
        return 0, []
    current_items = [
        current.get("primary_theme", ""),
        *list_values(current, "secondary_themes"),
        *list_values(current, "founder_lessons"),
    ]
    score, matches = match_items(
        current_items,
        [background],
        exact=8,
        strong=6,
        medium=4,
        light=2,
        max_score=8,
    )
    return score, matches


def plain_english_rationale(
    startup: Dict[str, Any],
    matched_themes: List[Dict[str, Any]],
    matched_industries: List[Dict[str, Any]],
    recency_note: str,
    milestone_note: str,
) -> str:
    parts = []
    if matched_themes:
        parts.append(
            f"Recommended because the episode connects to {startup['company_name']}'s theme of {matched_themes[0]['startup']}."
        )
    elif matched_industries:
        parts.append(
            f"Recommended because the episode shares industry context with {startup['company_name']}, especially {matched_industries[0]['startup']}."
        )
    else:
        parts.append(
            f"{startup['company_name']} is a lower-overlap candidate from the approved Startup Corner watchlist."
        )
    if matched_industries:
        industries = ", ".join(match["startup"] for match in matched_industries[:3])
        parts.append(f"Industry alignment includes {industries}.")
    if milestone_note.startswith(("1 ", "2 ")):
        parts.append(milestone_note)
    parts.append(recency_note)
    return " ".join(parts)


def score_startup(
    current: Dict[str, Any],
    startup: Dict[str, Any],
    latest_issue: Optional[int],
) -> Dict[str, Any]:
    startup_themes = list_values(startup, "themes")
    startup_industries = list_values(startup, "industries")

    primary_score, primary_matches = match_items(
        [current.get("primary_theme", "")],
        startup_themes,
        exact=25,
        strong=18,
        medium=12,
        light=6,
        max_score=25,
    )
    secondary_score, secondary_matches = match_items(
        list_values(current, "secondary_themes"),
        startup_themes,
        exact=8,
        strong=6,
        medium=4,
        light=2,
        max_score=15,
    )
    lesson_theme_score, lesson_theme_matches = match_items(
        list_values(current, "founder_lessons"),
        startup_themes,
        exact=8,
        strong=6,
        medium=4,
        light=2,
        max_score=12,
    )
    industry_score, industry_matches = exact_or_token_industry_score(
        list_values(current, "industries"),
        startup_industries,
    )
    founder_score, founder_matches = founder_background_score(current, startup)
    milestone_points, milestone_matches, milestone_note = milestone_score(startup)
    stats = appearance_stats(startup)
    recency_points, recency_note = recency_score(stats, latest_issue)
    frequency_points, frequency_note = frequency_score(stats)

    matched_themes = primary_matches + secondary_matches + lesson_theme_matches
    episode_relevance = primary_score + secondary_score + lesson_theme_score + industry_score
    startup_intelligence = founder_score + milestone_points
    editorial_constraints = recency_points + frequency_points
    score = episode_relevance + startup_intelligence + editorial_constraints

    return {
        "startup_name": startup.get("company_name"),
        "score": score,
        "matched_themes": matched_themes,
        "matched_industries": industry_matches,
        "matched_founder_background": founder_matches,
        "notable_milestones": milestone_matches,
        "recency_status": recency_note,
        "frequency_status": frequency_note,
        "score_breakdown": {
            "primary_theme": primary_score,
            "secondary_themes": secondary_score,
            "founder_lessons": lesson_theme_score,
            "industry_overlap": industry_score,
            "founder_background_alignment": founder_score,
            "notable_milestones": milestone_points,
            "appearance_recency": recency_points,
            "appearance_frequency": frequency_points,
            "episode_relevance_total": episode_relevance,
            "startup_intelligence_total": startup_intelligence,
            "editorial_constraints_total": editorial_constraints,
        },
        "plain_english_rationale": plain_english_rationale(
            startup,
            matched_themes,
            industry_matches,
            recency_note,
            milestone_note,
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
        "episode_number": None,
        "title": args.current_title,
        "guest_name": args.current_guest,
        "primary_theme": args.primary_theme,
        "secondary_themes": args.secondary_theme,
        "founder_lessons": args.founder_lesson,
        "industries": args.industry,
    }


def recommend_startups_v1(
    current_episode: Dict[str, Any],
    startup_records: Optional[List[Dict[str, Any]]] = None,
    history_records: Optional[List[Dict[str, str]]] = None,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    startup_records = startup_records if startup_records is not None else load_startup_records()
    history_records = history_records if history_records is not None else load_newsletter_history()
    latest_issue = latest_issue_number(history_records)
    recommendations = [
        score_startup(current_episode, startup, latest_issue)
        for startup in startup_records
    ]
    recommendations.sort(
        key=lambda item: (
            item["score"],
            item["score_breakdown"]["episode_relevance_total"],
            item["score_breakdown"]["industry_overlap"],
            item["score_breakdown"]["startup_intelligence_total"],
        ),
        reverse=True,
    )
    return recommendations[:top_n]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Startup Corner recommendation engine v1")
    parser.add_argument("--current-episode", type=int, help="Use an existing Rank 4 episode record as current context.")
    parser.add_argument("--current-record", type=str, help="Path to a standalone current episode JSON record.")
    parser.add_argument("--current-title", type=str, default="", help="Manual current episode title.")
    parser.add_argument("--current-guest", type=str, default="", help="Manual current guest name.")
    parser.add_argument("--primary-theme", type=str, default="", help="Manual current primary theme.")
    parser.add_argument("--secondary-theme", action="append", default=[], help="Manual current secondary theme.")
    parser.add_argument("--founder-lesson", action="append", default=[], help="Manual current founder lesson.")
    parser.add_argument("--industry", action="append", default=[], help="Manual current industry.")
    parser.add_argument("--top-n", type=int, default=10, help="Number of recommendations to return.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    episode_records = load_episode_records()
    startup_records = load_startup_records()
    history_records = load_newsletter_history()
    current_episode = current_episode_from_args(args, episode_records)
    recommendations = recommend_startups_v1(
        current_episode,
        startup_records=startup_records,
        history_records=history_records,
        top_n=args.top_n,
    )
    print(json.dumps({"current_episode": current_episode, "recommendations": recommendations}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
