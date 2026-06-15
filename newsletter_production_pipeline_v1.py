#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from connected_insights_recommender_v3 import (
    load_episode_records,
    load_newsletter_history,
    recommend_connected_insights_v3,
)
from episode_intelligence_generator import (
    ACTIVE_DIR,
    generate_episode_intelligence_record,
    save_active_record,
)
from startup_recommender_v1 import load_startup_records, recommend_startups_v1

ROOT = Path(__file__).resolve().parent
TRANSCRIPT_DIR = ROOT / "data" / "transcripts"
OUTPUT_ROOT = ROOT / "outputs" / "newsletter_production"
RANK4_DIR = ROOT / "data" / "episodes" / "rank4"
BUNDLED_PLAYWRIGHT_MODULE = (
    Path.home()
    / ".cache"
    / "codex-runtimes"
    / "codex-primary-runtime"
    / "dependencies"
    / "node"
    / "node_modules"
    / ".pnpm"
    / "playwright@1.60.0"
    / "node_modules"
    / "playwright"
    / "index.js"
)

SHELL_MARKERS = [
    "<!DOCTYPE html>",
    '<div id="app"></div>',
    "polyfills-legacy",
    "image.simplecastcdn.com/customersites/latest/assets",
]

INDUSTRY_KEYWORDS = {
    "Artificial Intelligence": [" ai ", "artificial intelligence", "machine learning", "autonomous"],
    "Venture Capital": ["venture", "vc", "investor", "fundraising", "fund"],
    "FinTech": ["fintech", "financial", "banking", "payments", "credit", "treasury"],
    "InsurTech": ["insurtech", "insurance", "claims", "risk"],
    "Enterprise Software": ["enterprise", "saas", "software", "workflow"],
    "Healthcare": ["healthcare", "health care", "medical", "clinical"],
    "Education": ["education", "school", "university", "learning"],
    "Deep Tech": ["deep tech", "infrastructure", "semiconductor", "robotics"],
}

THEME_KEYWORDS = [
    ("Founder resilience", ["resilience", "grit", "perseverance", "survive", "persistence"]),
    ("Fundraising strategy", ["fundraising", "raise capital", "investors", "pitch"]),
    ("Customer discovery", ["customer", "customers", "market", "problem", "pain"]),
    ("Product-market fit", ["product-market fit", "product market fit", "pmf"]),
    ("Capital discipline", ["cash", "runway", "capital efficient", "burn"]),
    ("Enterprise sales", ["enterprise", "sales", "procurement", "go-to-market"]),
    ("AI infrastructure", ["artificial intelligence", " ai ", "machine learning", "autonomous"]),
    ("Insurance and risk", ["insurance", "risk", "claims", "underwriting"]),
    ("FinTech infrastructure", ["fintech", "payments", "banking", "financial infrastructure"]),
    ("Community and access", ["community", "access", "network", "mentorship"]),
    ("Emerging manager investing", ["emerging manager", "lp", "fund of funds", "allocator"]),
]


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def slug_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[-1] == "transcript":
        parts = parts[:-1]
    if "episodes" in parts:
        index = parts.index("episodes")
        if index + 1 < len(parts):
            return parts[index + 1]
    return parts[-1] if parts else "episode"


def derive_transcript_url(url: str) -> str:
    return url.rstrip("/") if url.rstrip("/").endswith("/transcript") else f"{url.rstrip('/')}/transcript"


def derive_episode_url(url: str) -> str:
    return re.sub(r"/transcript/?$", "", url.rstrip("/"))


def episode_number_from_url(url: str) -> Optional[int]:
    match = re.search(r"(?:tsse[-_]?|episode[-_]?)(\d+)", url, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def transcript_path_for_url(url: str) -> Path:
    return TRANSCRIPT_DIR / f"{slug_from_url(url)}_transcript.txt"


def output_dir_for_url(url: str, output_dir: Optional[str]) -> Path:
    if output_dir:
        return Path(output_dir)
    return OUTPUT_ROOT / slug_from_url(url)


def extract_json_from_stdout(stdout: str) -> Dict[str, Any]:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise RuntimeError(f"Retrieval command did not emit JSON metadata:\n{stdout}")
    return json.loads(stdout[start : end + 1])


def retrieve_transcript(
    transcript_url: str,
    *,
    force_retrieve: bool,
    episode_number: Optional[int],
    guest_name: str,
) -> Dict[str, Any]:
    output_path = transcript_path_for_url(transcript_url)
    if output_path.exists() and not force_retrieve:
        text = output_path.read_text(encoding="utf-8")
        return {
            "source": "cached_rendered_transcript",
            "transcript_url": derive_transcript_url(transcript_url),
            "output_path": str(output_path),
            "validation": validate_transcript(text),
        }

    if episode_number is None:
        raise RuntimeError("A TSSE episode number is required for Playwright transcript retrieval.")

    command = [
        "node",
        "phase3_transcript_retrieval.mjs",
        "--episode-number",
        str(episode_number),
        "--episode-url",
        derive_episode_url(transcript_url),
    ]
    if guest_name:
        command.extend(["--guest-name", guest_name])

    env = os.environ.copy()
    if not env.get("PLAYWRIGHT_MODULE_PATH") and BUNDLED_PLAYWRIGHT_MODULE.exists():
        env["PLAYWRIGHT_MODULE_PATH"] = str(BUNDLED_PLAYWRIGHT_MODULE)

    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Playwright transcript retrieval failed.\n"
            f"Command: {' '.join(command)}\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    metadata = extract_json_from_stdout(completed.stdout)
    if not metadata.get("results"):
        raise RuntimeError(f"Playwright retrieval completed without a transcript result: {metadata}")
    result = metadata["results"][0]
    return {
        "source": "playwright_rendered_transcript",
        "transcript_url": result.get("transcriptUrl", derive_transcript_url(transcript_url)),
        "output_path": result.get("outputPath", str(output_path)),
        "validation": result.get("validation", {}),
        "attempts": result.get("attempts"),
    }


def validate_transcript(text: str) -> Dict[str, Any]:
    speakers = sorted(set(re.findall(r"^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?([A-Z][A-Za-z .'\u00c0-\u017f-]+):", text, re.MULTILINE)))
    has_shell = any(marker in text for marker in SHELL_MARKERS)
    byte_length = len(text.encode("utf-8"))
    return {
        "byte_length": byte_length,
        "character_length": len(text),
        "paragraph_count": len([item for item in re.split(r"\n{2,}", text) if item.strip()]),
        "speakers": speakers,
        "has_html_shell": has_shell,
        "valid": byte_length > 10000 and len(speakers) >= 2 and not has_shell,
    }


def list_values(record: Dict[str, Any], key: str) -> List[str]:
    value = record.get(key, [])
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []


def load_active_episode_records(path: Path = ACTIVE_DIR) -> List[Dict[str, Any]]:
    records = []
    if not path.exists():
        return records
    for json_file in sorted(path.glob("episode_*.json"), key=lambda p: int(p.stem.split("_")[1])):
        records.append(json.loads(json_file.read_text(encoding="utf-8")))
    return records


def find_existing_episode_record(transcript_url: str, records: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    episode_url = derive_episode_url(transcript_url)
    episode_number = episode_number_from_url(transcript_url)
    for record in records:
        if record.get("episode_url", "").rstrip("/") == episode_url.rstrip("/"):
            return record
        if episode_number and record.get("episode_number") == episode_number:
            return record
    return None


def clean_sentence(sentence: str) -> str:
    sentence = re.sub(r"^\[\d{2}:\d{2}:\d{2}\]\s*", "", sentence)
    sentence = re.sub(r"^[A-Z][A-Za-z .'\u00c0-\u017f-]+:\s*", "", sentence)
    return normalize_space(sentence)


def transcript_sentences(text: str) -> List[str]:
    normalized = re.sub(r"\n+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    return [clean_sentence(part) for part in parts if 20 <= len(clean_sentence(part)) <= 260]


def infer_guest_name(text: str, fallback: str = "") -> str:
    patterns = [
        r"my guest today is ([A-Z][A-Za-z .'-]+)",
        r"my guest is ([A-Z][A-Za-z .'-]+)",
        r"welcome to the Sure Shot Entrepreneur\.?\s+([A-Z][A-Za-z .'-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_space(match.group(1)).rstrip(".")
    speakers = re.findall(r"^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?([A-Z][A-Za-z .'\u00c0-\u017f-]+):", text, re.MULTILINE)
    non_host = [speaker for speaker in speakers if speaker not in {"Gopi Rangan", "Joe"}]
    if non_host:
        return Counter(non_host).most_common(1)[0][0]
    return fallback


def title_from_slug(slug: str) -> str:
    words = [word for word in re.sub(r"^tsse[-_]?\d+[-_]?", "", slug).split("-") if word]
    return " ".join(word.capitalize() for word in words)


def score_keyword_groups(text: str, groups: Iterable[Tuple[str, List[str]]]) -> List[Tuple[str, int]]:
    haystack = f" {text.lower()} "
    scored = []
    for label, keywords in groups:
        score = sum(haystack.count(keyword.lower()) for keyword in keywords)
        if score:
            scored.append((label, score))
    return sorted(scored, key=lambda item: item[1], reverse=True)


def infer_industries(text: str) -> List[str]:
    scored = score_keyword_groups(text, INDUSTRY_KEYWORDS.items())
    industries = [label for label, _ in scored[:5]]
    if "Venture Capital" not in industries:
        industries.append("Venture Capital")
    return industries


def infer_themes(text: str) -> Tuple[str, List[str]]:
    scored = score_keyword_groups(text, THEME_KEYWORDS)
    if not scored:
        return "Founder lessons and company-building judgment", ["Founder development", "Decision-making discipline"]
    primary = scored[0][0]
    secondary = [label for label, _ in scored[1:5]]
    return primary, secondary


def infer_founder_lessons(text: str) -> List[str]:
    lessons = []
    markers = [
        "founder",
        "founders",
        "you need to",
        "you have to",
        "you should",
        "important to",
        "focus on",
        "customers",
        "investors",
    ]
    for sentence in transcript_sentences(text):
        lower = sentence.lower()
        if any(marker in lower for marker in markers) and sentence not in lessons:
            lessons.append(sentence)
        if len(lessons) == 4:
            break
    return lessons


def infer_quotes(text: str) -> List[str]:
    quotes = []
    for paragraph in re.split(r"\n{2,}", text):
        if re.match(r"^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?Gopi Rangan:", paragraph):
            continue
        sentence_candidates = transcript_sentences(paragraph)
        for sentence in sentence_candidates:
            words = sentence.split()
            if 10 <= len(words) <= 38 and any(token in sentence.lower() for token in ["i think", "we ", "you ", "founder", "market"]):
                if sentence not in quotes:
                    quotes.append(sentence)
            if len(quotes) == 3:
                return quotes
    return quotes


def infer_organizations(text: str) -> List[str]:
    pattern = r"\b([A-Z][A-Za-z&.'-]+(?:\s+[A-Z][A-Za-z&.'-]+){0,5}\s+(?:Foundation|Institute|University|School|College|Association|Center|Centre|Organization|Council|Network|Fellowship))\b"
    organizations = []
    for match in re.findall(pattern, text):
        cleaned = normalize_space(match)
        if cleaned not in organizations and not cleaned.startswith("The Sure Shot"):
            organizations.append(cleaned)
    return organizations[:5]


def generate_episode_intelligence(
    transcript_url: str,
    transcript_text: str,
    existing_record: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if existing_record:
        return {
            "episode_number": existing_record.get("episode_number"),
            "title": existing_record.get("title", ""),
            "guest_name": existing_record.get("guest_name", ""),
            "episode_url": existing_record.get("episode_url", derive_episode_url(transcript_url)),
            "primary_theme": existing_record.get("primary_theme", ""),
            "secondary_themes": list_values(existing_record, "secondary_themes"),
            "founder_lessons": list_values(existing_record, "founder_lessons"),
            "industries": list_values(existing_record, "industries"),
            "community_organizations": list_values(existing_record, "community_organizations"),
            "notable_quotes": list_values(existing_record, "notable_quotes")[:3],
            "extraction_method": "existing_transcript_derived_rank4_record",
            "extraction_confidence": "high",
        }

    primary_theme, secondary_themes = infer_themes(transcript_text)
    return {
        "episode_number": episode_number_from_url(transcript_url),
        "title": title_from_slug(slug_from_url(transcript_url)),
        "guest_name": infer_guest_name(transcript_text),
        "episode_url": derive_episode_url(transcript_url),
        "primary_theme": primary_theme,
        "secondary_themes": secondary_themes,
        "founder_lessons": infer_founder_lessons(transcript_text),
        "industries": infer_industries(transcript_text),
        "community_organizations": infer_organizations(transcript_text),
        "notable_quotes": infer_quotes(transcript_text),
        "extraction_method": "local_heuristic_transcript_extraction",
        "extraction_confidence": "draft_requires_editorial_review",
    }


def connected_metadata(recommendation: Dict[str, Any], rank: int) -> Dict[str, Any]:
    return {
        "rank": rank,
        "guest_name": recommendation.get("guest_name"),
        "episode_number": recommendation.get("episode_number"),
        "score": recommendation.get("score"),
        "score_breakdown": recommendation.get("score_breakdown", {}),
        "matched_themes": recommendation.get("matched_themes", []),
        "matched_founder_lessons": recommendation.get("matched_founder_lessons", []),
        "matched_industries": recommendation.get("matched_industries", []),
        "matched_community_organizations": recommendation.get("matched_community_organizations", []),
        "recency_note": recommendation.get("recency_note", ""),
        "frequency_note": recommendation.get("frequency_note", ""),
        "rationale": recommendation.get("plain_english_rationale", ""),
        "selection_note": "Selected by Connected Insights v3 ranking for this episode context.",
    }


def startup_metadata(recommendation: Dict[str, Any], rank: int) -> Dict[str, Any]:
    return {
        "rank": rank,
        "startup_name": recommendation.get("startup_name"),
        "score": recommendation.get("score"),
        "score_breakdown": recommendation.get("score_breakdown", {}),
        "matched_themes": recommendation.get("matched_themes", []),
        "matched_industries": recommendation.get("matched_industries", []),
        "matched_founder_background": recommendation.get("matched_founder_background", []),
        "notable_milestones": recommendation.get("notable_milestones", []),
        "recency_status": recommendation.get("recency_status", ""),
        "frequency_status": recommendation.get("frequency_status", ""),
        "rationale": recommendation.get("plain_english_rationale", ""),
        "selection_note": "Selected by Startup Recommender v1 ranking for this episode context.",
    }


def generate_briefing(
    transcript_url: str,
    retrieval: Dict[str, Any],
    episode: Dict[str, Any],
    connected: List[Dict[str, Any]],
    startups: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "pipeline_version": "newsletter_production_pipeline_v1",
        "input": {"transcript_url": derive_transcript_url(transcript_url)},
        "transcript_retrieval": retrieval,
        "episode_summary": {
            "episode_number": episode.get("episode_number"),
            "guest": episode.get("guest_name", ""),
            "title": episode.get("title", ""),
            "episode_url": episode.get("episode_url", derive_episode_url(transcript_url)),
            "primary_theme": episode.get("primary_theme", ""),
            "secondary_themes": list_values(episode, "secondary_themes"),
            "industries": list_values(episode, "industries"),
            "extraction_method": episode.get("extraction_method", ""),
            "extraction_confidence": episode.get("extraction_confidence", ""),
        },
        "founder_lessons": list_values(episode, "founder_lessons"),
        "notable_quotes": list_values(episode, "notable_quotes")[:3],
        "connected_insights_recommendations": [
            connected_metadata(item, index) for index, item in enumerate(connected[:3], 1)
        ],
        "startup_corner_recommendations": [
            startup_metadata(item, index) for index, item in enumerate(startups[:3], 1)
        ],
        "community_organizations": list_values(episode, "community_organizations"),
        "recommendation_metadata": {
            "connected_insights_source": "connected_insights_recommender_v3.py",
            "startup_corner_source": "startup_recommender_v1.py",
            "newsletter_history_source": "data/newsletter_history.csv",
            "note": "Scores and rationale are copied from the recommender systems without modifying their logic.",
        },
    }


def markdown_list(items: Iterable[str], empty: str = "None captured.") -> str:
    values = [item for item in items if item]
    if not values:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in values)


def render_briefing_markdown(briefing: Dict[str, Any]) -> str:
    episode = briefing["episode_summary"]
    lines = [
        f"# Newsletter Production Briefing: Episode {episode.get('episode_number') or 'Draft'}",
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
    for rec in briefing.get("connected_insights_recommendations", []):
        lines.extend(
            [
                f"### {rec.get('rank')}. {rec.get('guest_name', '')} - Episode {rec.get('episode_number', '')}",
                "",
                f"- Score: {rec.get('score', '')}",
                f"- Recency: {rec.get('recency_note', '')}",
                f"- Frequency: {rec.get('frequency_note', '')}",
                f"- Rationale: {rec.get('rationale', '')}",
                "",
            ]
        )
    lines.extend(["## Startup Corner Recommendations", ""])
    for rec in briefing.get("startup_corner_recommendations", []):
        lines.extend(
            [
                f"### {rec.get('rank')}. {rec.get('startup_name', '')}",
                "",
                f"- Score: {rec.get('score', '')}",
                f"- Recency: {rec.get('recency_status', '')}",
                f"- Frequency: {rec.get('frequency_status', '')}",
                f"- Rationale: {rec.get('rationale', '')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Community Organizations",
            "",
            markdown_list(briefing.get("community_organizations", [])),
            "",
            "## Recommendation Metadata",
            "",
            f"- Connected Insights source: {briefing['recommendation_metadata']['connected_insights_source']}",
            f"- Startup Corner source: {briefing['recommendation_metadata']['startup_corner_source']}",
            f"- Newsletter history source: {briefing['recommendation_metadata']['newsletter_history_source']}",
            f"- Transcript validation: {briefing['transcript_retrieval'].get('validation', {})}",
        ]
    )
    return "\n".join(lines) + "\n"


def first_item(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    return items[0] if items else {}


def render_newsletter_draft(briefing: Dict[str, Any]) -> str:
    episode = briefing["episode_summary"]
    connected = first_item(briefing.get("connected_insights_recommendations", []))
    startup = first_item(briefing.get("startup_corner_recommendations", []))
    orgs = briefing.get("community_organizations", [])

    founder_lessons = briefing.get("founder_lessons", [])
    quotes = briefing.get("notable_quotes", [])

    community_text = (
        "This episode also surfaces community involvement connected to "
        + ", ".join(orgs)
        + ". [Joe edit: add current context, donation link, or involvement detail before publishing.]"
        if orgs
        else "[Joe edit: add Community Involvement organization, mission summary, and link if available.]"
    )

    lines = [
        "# Intro",
        "",
        f"This week, Gopi sits down with {episode.get('guest', '[guest]')} for a conversation about {episode.get('primary_theme', '[primary theme]').lower()}. The episode matters because it gives founders a practical way to think about the decisions, tradeoffs, and relationships behind company building.",
        "",
        "# Podcast Entries",
        "",
        f"## {episode.get('title', '[episode title]')}",
        "",
        f"Guest: {episode.get('guest', '[guest]')}",
        "",
        "Episode URL: [Insert episode URL]",
        "",
        f"Episode summary: {episode.get('primary_theme', '')}.",
        "",
        "Founder lessons:",
        markdown_list(founder_lessons),
        "",
        "Key takeaways:",
        markdown_list(episode.get("secondary_themes", [])),
        "",
        "Transcript-derived quote options:",
        markdown_list(quotes),
        "",
        "# Connected Insights",
        "",
    ]

    if connected:
        lines.extend(
            [
                f"Recommended guest: {connected.get('guest_name')} (Episode {connected.get('episode_number')})",
                "",
                "Episode URL: [Insert Connected Insights episode URL]",
                "",
                connected.get("rationale", ""),
                "",
                "Why this connects:",
                f"{connected.get('guest_name')} was selected because the recommendation engine found overlapping themes, founder lessons, industries, and newsletter-history signals. Use this section as a starting point for Joe's editorial framing.",
                "",
            ]
        )
    else:
        lines.extend(["[Joe edit: select a Connected Insights guest and add rationale.]", ""])

    lines.extend(["# Startup Corner", ""])
    if startup:
        lines.extend(
            [
                f"Recommended company: {startup.get('startup_name')}",
                "",
                "Company URL: [Insert company URL]",
                "",
                startup.get("rationale", ""),
                "",
                "Why this connects:",
                f"{startup.get('startup_name')} was selected because the Startup Recommender found overlap with the episode's themes, industries, or founder lessons while accounting for newsletter recency and frequency.",
                "",
            ]
        )
    else:
        lines.extend(["[Joe edit: select a Startup Corner company and add rationale.]", ""])

    lines.extend(
        [
            "# Community Involvement",
            "",
            community_text,
            "",
            "# Editorial Notes",
            "",
            "- Replace all placeholders before publication.",
            "- Confirm episode and company URLs.",
            "- Treat recommendation rationale as planning support, not final copy.",
            "- Verify any current facts manually before adding them.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(briefing: Dict[str, Any], output_dir: Path) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    briefing_json = output_dir / "briefing.json"
    briefing_md = output_dir / "briefing.md"
    draft_md = output_dir / "newsletter_draft.md"

    briefing_json.write_text(json.dumps(briefing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    briefing_md.write_text(render_briefing_markdown(briefing), encoding="utf-8")
    draft_md.write_text(render_newsletter_draft(briefing), encoding="utf-8")
    return {
        "briefing_json": str(briefing_json),
        "briefing_md": str(briefing_md),
        "newsletter_draft": str(draft_md),
    }


def run_pipeline(args: argparse.Namespace) -> Dict[str, Any]:
    discovery_report = None
    if args.latest:
        from episode_discovery import discover_latest_unpublished_episode

        discovery_report = discover_latest_unpublished_episode()
        recommended = discovery_report.get("recommended_next_episode_for_newsletter_generation")
        if not recommended:
            newest = discovery_report.get("newest_episode", {})
            raise RuntimeError(
                "No unpublished TSSE episode was discovered. "
                f"Newest episode {newest.get('episode_number')} is already represented in newsletter history."
            )
        args.transcript_url = recommended["transcript_url"]
        args.episode_number = recommended.get("episode_number")
        args.guest_name = args.guest_name or recommended.get("guest_name", "")

    if not args.transcript_url:
        raise RuntimeError("Provide a transcript URL or pass --latest.")

    transcript_url = derive_transcript_url(args.transcript_url)
    episode_number = args.episode_number or episode_number_from_url(transcript_url)
    retrieval = retrieve_transcript(
        transcript_url,
        force_retrieve=args.force_retrieve,
        episode_number=episode_number,
        guest_name=args.guest_name,
    )
    transcript_path = Path(retrieval["output_path"])
    transcript_text = transcript_path.read_text(encoding="utf-8")
    validation = validate_transcript(transcript_text)
    if not validation["valid"]:
        raise RuntimeError(f"Transcript validation failed: {validation}")
    retrieval["validation"] = validation

    rank4_records = load_episode_records(RANK4_DIR)
    active_records = load_active_episode_records()
    existing_record = (
        find_existing_episode_record(transcript_url, active_records)
        or find_existing_episode_record(transcript_url, rank4_records)
    )
    episode = generate_episode_intelligence(transcript_url, transcript_text, existing_record)
    if discovery_report and not existing_record:
        recommended = discovery_report.get("recommended_next_episode_for_newsletter_generation") or {}
        episode["episode_number"] = recommended.get("episode_number") or episode.get("episode_number")
        episode["title"] = recommended.get("episode_title") or episode.get("title", "")
        episode["guest_name"] = recommended.get("guest_name") or episode.get("guest_name", "")
        episode["episode_url"] = recommended.get("episode_url") or episode.get("episode_url", "")

    active_record_output = None
    if not existing_record:
        generated_title = episode.get("title") or title_from_slug(slug_from_url(transcript_url))
        generated_guest = args.guest_name or episode.get("guest_name", "")
        if not episode_number:
            raise RuntimeError("Episode number is required to generate a new episode intelligence record.")
        generated_record = generate_episode_intelligence_record(
            transcript_url=transcript_url,
            episode_number=episode_number,
            guest_name=generated_guest,
            title=generated_title,
            transcript_path=transcript_path,
        )
        active_record_output = save_active_record(generated_record, ACTIVE_DIR)
        episode = {
            **generated_record,
            "extraction_method": "active_episode_intelligence_v1",
            "extraction_confidence": "draft_requires_editorial_review",
        }
    elif find_existing_episode_record(transcript_url, active_records):
        episode["extraction_method"] = "active_episode_intelligence_record"
        episode["extraction_confidence"] = "draft_requires_editorial_review"

    history_records = load_newsletter_history()
    startup_records = load_startup_records()
    connected = recommend_connected_insights_v3(
        episode,
        episode_records=rank4_records,
        history_records=history_records,
        top_n=3,
    )
    startups = recommend_startups_v1(
        episode,
        startup_records=startup_records,
        history_records=history_records,
        top_n=3,
    )

    briefing = generate_briefing(transcript_url, retrieval, episode, connected, startups)
    if active_record_output:
        briefing["episode_intelligence_record"] = {
            "source": "episode_intelligence_generator.py",
            "path": str(active_record_output),
            "status": "active",
        }
    elif find_existing_episode_record(transcript_url, active_records):
        briefing["episode_intelligence_record"] = {
            "source": "data/episodes/active",
            "path": str(ACTIVE_DIR / f"episode_{episode_number}.json"),
            "status": "active",
        }
    if discovery_report:
        briefing["automatic_episode_discovery"] = {
            "newest_episode": discovery_report.get("newest_episode"),
            "newsletter_coverage_status": discovery_report.get("newsletter_coverage_status"),
            "recommended_next_episode_for_newsletter_generation": discovery_report.get(
                "recommended_next_episode_for_newsletter_generation"
            ),
        }
    paths = write_outputs(briefing, output_dir_for_url(transcript_url, args.output_dir))
    if discovery_report:
        discovery_path = Path(paths["briefing_json"]).parent / "discovery_report.json"
        discovery_path.write_text(json.dumps(discovery_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths["discovery_report"] = str(discovery_path)
    return {"outputs": paths, "briefing": briefing}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate TSSE newsletter production artifacts from a transcript URL.")
    parser.add_argument("transcript_url", nargs="?", help="Episode transcript URL.")
    parser.add_argument("--latest", action="store_true", help="Discover the newest episode missing newsletter coverage and generate materials for it.")
    parser.add_argument("--episode-number", type=int, help="Episode number, required for fresh retrieval if it cannot be parsed from URL.")
    parser.add_argument("--guest-name", default="", help="Optional guest name for retrieval metadata.")
    parser.add_argument("--output-dir", help="Directory for briefing.json, briefing.md, and newsletter_draft.md.")
    parser.add_argument("--force-retrieve", action="store_true", help="Force Playwright retrieval even if a cached rendered transcript exists.")
    return parser.parse_args()


def main() -> None:
    result = run_pipeline(parse_args())
    print(json.dumps(result["outputs"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
