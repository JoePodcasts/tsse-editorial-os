#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from connected_insights_recommender_v3 import (
    find_record_by_episode,
    load_episode_records,
    load_newsletter_history,
    recommend_connected_insights_v3,
)
from startup_recommender_v1 import (
    load_startup_records,
    recommend_startups_v1,
)


def list_values(record: Dict[str, Any], key: str) -> List[str]:
    value = record.get(key, [])
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []


def compact_connected_insight(recommendation: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "guest_name": recommendation.get("guest_name"),
        "episode_number": recommendation.get("episode_number"),
        "score": recommendation.get("score"),
        "matched_themes": recommendation.get("matched_themes", []),
        "matched_founder_lessons": recommendation.get("matched_founder_lessons", []),
        "matched_industries": recommendation.get("matched_industries", []),
        "recency_note": recommendation.get("recency_note", ""),
        "frequency_note": recommendation.get("frequency_note", ""),
        "rationale": recommendation.get("plain_english_rationale", ""),
    }


def compact_startup(recommendation: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "startup_name": recommendation.get("startup_name"),
        "score": recommendation.get("score"),
        "matched_themes": recommendation.get("matched_themes", []),
        "matched_industries": recommendation.get("matched_industries", []),
        "recency_status": recommendation.get("recency_status", ""),
        "frequency_status": recommendation.get("frequency_status", ""),
        "rationale": recommendation.get("plain_english_rationale", ""),
    }


def generate_newsletter_briefing(
    episode_number: int,
    *,
    connected_top_n: int = 3,
    startup_top_n: int = 3,
) -> Dict[str, Any]:
    episode_records = load_episode_records()
    history_records = load_newsletter_history()
    startup_records = load_startup_records()
    episode = find_record_by_episode(episode_records, episode_number)
    if episode is None:
        raise SystemExit(f"Could not find episode {episode_number} in data/episodes/rank4/.")

    connected = recommend_connected_insights_v3(
        episode,
        episode_records=episode_records,
        history_records=history_records,
        top_n=connected_top_n,
    )
    startups = recommend_startups_v1(
        episode,
        startup_records=startup_records,
        history_records=history_records,
        top_n=startup_top_n,
    )

    return {
        "episode_number": episode.get("episode_number"),
        "episode_summary": {
            "title": episode.get("title", ""),
            "guest": episode.get("guest_name", ""),
            "episode_url": episode.get("episode_url", ""),
            "primary_theme": episode.get("primary_theme", ""),
            "secondary_themes": list_values(episode, "secondary_themes"),
            "industries": list_values(episode, "industries"),
        },
        "founder_lessons": list_values(episode, "founder_lessons"),
        "notable_quotes": list_values(episode, "notable_quotes")[:3],
        "connected_insights_recommendations": [
            compact_connected_insight(item) for item in connected
        ],
        "startup_corner_recommendations": [
            compact_startup(item) for item in startups
        ],
        "community_organizations": list_values(episode, "community_organizations"),
        "generation_notes": [
            "Episode intelligence comes from data/episodes/rank4/.",
            "Connected Insights candidates come from connected_insights_recommender_v3.py.",
            "Startup Corner candidates come from startup_recommender_v1.py.",
            "Newsletter history is used only through local data/newsletter_history.csv.",
        ],
    }


def markdown_list(items: Iterable[str]) -> str:
    items = [item for item in items if item]
    if not items:
        return "- None captured."
    return "\n".join(f"- {item}" for item in items)


def render_markdown(briefing: Dict[str, Any]) -> str:
    episode = briefing["episode_summary"]
    lines = [
        f"# Newsletter Briefing: Episode {briefing['episode_number']}",
        "",
        "## Episode Summary",
        "",
        f"- Guest: {episode.get('guest', '')}",
        f"- Title: {episode.get('title', '')}",
        f"- Episode URL: {episode.get('episode_url', '')}",
        f"- Primary theme: {episode.get('primary_theme', '')}",
        "- Secondary themes:",
        markdown_list(episode.get("secondary_themes", [])),
        "",
        "## Founder Lessons",
        "",
        markdown_list(briefing.get("founder_lessons", [])),
        "",
        "## Notable Quotes",
        "",
        markdown_list(briefing.get("notable_quotes", [])),
        "",
        "## Connected Insights Recommendations",
        "",
    ]
    for index, rec in enumerate(briefing.get("connected_insights_recommendations", []), 1):
        lines.extend([
            f"### {index}. {rec.get('guest_name', '')} - Episode {rec.get('episode_number', '')}",
            "",
            f"- Score: {rec.get('score', '')}",
            f"- Recency: {rec.get('recency_note', '')}",
            f"- Frequency: {rec.get('frequency_note', '')}",
            f"- Rationale: {rec.get('rationale', '')}",
            "",
        ])
    lines.extend(["## Startup Corner Recommendations", ""])
    for index, rec in enumerate(briefing.get("startup_corner_recommendations", []), 1):
        lines.extend([
            f"### {index}. {rec.get('startup_name', '')}",
            "",
            f"- Score: {rec.get('score', '')}",
            f"- Recency: {rec.get('recency_status', '')}",
            f"- Frequency: {rec.get('frequency_status', '')}",
            f"- Rationale: {rec.get('rationale', '')}",
            "",
        ])
    lines.extend([
        "## Community Organizations",
        "",
        markdown_list(briefing.get("community_organizations", [])),
        "",
        "## Generation Notes",
        "",
        markdown_list(briefing.get("generation_notes", [])),
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a TSSE newsletter briefing package.")
    parser.add_argument("episode_number", type=int, help="Rank 4 episode number to brief.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format.")
    parser.add_argument("--connected-top-n", type=int, default=3, help="Number of Connected Insights recommendations.")
    parser.add_argument("--startup-top-n", type=int, default=3, help="Number of Startup Corner recommendations.")
    parser.add_argument("--output", type=str, help="Optional path to write the briefing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    briefing = generate_newsletter_briefing(
        args.episode_number,
        connected_top_n=args.connected_top_n,
        startup_top_n=args.startup_top_n,
    )
    if args.format == "markdown":
        output = render_markdown(briefing)
    else:
        output = json.dumps(briefing, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
