#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
TRANSCRIPT_DIR = ROOT / "data" / "transcripts"
ACTIVE_DIR = ROOT / "data" / "episodes" / "active"

HOST_SPEAKERS = {"Gopi Rangan", "Joe"}
COMMUNITY_ORG_EXCLUSIONS = {
    "On Deck",
    "SideLetter",
    "Superclusters",
    "Localize",
    "Runway Financial",
}
BOILERPLATE_PATTERNS = [
    "you are listening to the sure shot entrepreneur",
    "welcome to the sure shot entrepreneur",
    "thank you for listening",
    "please subscribe",
    "post a review",
    "i look forward to catching you",
]

THEME_KEYWORDS = [
    (
        "LP education and disciplined emerging manager evaluation",
        ["lp", "limited partner", "emerging lp", "underwrite", "diligence", "superclusters", "sideletter"],
    ),
    (
        "Emerging manager differentiation and fund construction",
        ["emerging manager", "fund one", "fund two", "gp", "fund manager", "first close", "home field advantage"],
    ),
    (
        "Consistent decision frameworks for venture investing",
        ["framework", "consistent", "inputs", "filters", "entry discipline", "exit discipline", "executional discipline"],
    ),
    (
        "Venture performance metrics and portfolio health",
        ["tvpi", "dpi", "irr", "moic", "graduation rates", "portfolio health", "markups", "marks"],
    ),
    (
        "Founder and GP storytelling for investor fit",
        ["pitch", "storytelling", "first meeting", "fit", "questions", "point of view"],
    ),
    (
        "Founder resilience and adaptability",
        ["resilience", "adaptability", "grit", "authenticity", "self-awareness"],
    ),
    (
        "Customer discovery and market learning",
        ["customer", "market", "problem", "pain", "learn", "discovery"],
    ),
    (
        "AI-enabled company building",
        ["artificial intelligence", " ai ", "machine learning", "claude", "automation"],
    ),
    (
        "Insurance and risk infrastructure",
        ["insurance", "insurtech", "risk", "claims", "underwriting"],
    ),
    (
        "FinTech infrastructure",
        ["fintech", "financial", "payments", "banking", "treasury"],
    ),
]

INDUSTRY_KEYWORDS = {
    "Venture Capital": ["venture", "vc", "gp", "fund manager", "startup"],
    "Limited Partners": [" lp ", "limited partner", "asset allocator", "asset owner"],
    "Emerging Managers": ["emerging manager", "fund one", "fund two"],
    "Fund of Funds": ["fund to funds", "fund of funds"],
    "Family Office": ["family office"],
    "Artificial Intelligence": [" ai ", "artificial intelligence", "claude", "automation"],
    "FinTech": ["fintech", "financial", "payments", "banking", "treasury"],
    "InsurTech": ["insurtech", "insurance"],
    "Education": ["educat", "student", "school", "university", "berkeley"],
    "Enterprise Software": ["saas", "enterprise", "software"],
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def remove_timestamps(value: str) -> str:
    return normalize_space(re.sub(r"\[\d{2}:\d{2}:\d{2}\]", "", value))


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


def derive_episode_url(url: str) -> str:
    return re.sub(r"/transcript/?$", "", url.rstrip("/"))


def transcript_path_for_url(url: str) -> Path:
    return TRANSCRIPT_DIR / f"{slug_from_url(url)}_transcript.txt"


def active_record_path(episode_number: int, output_dir: Path = ACTIVE_DIR) -> Path:
    return output_dir / f"episode_{episode_number}.json"


def title_from_slug(slug: str) -> str:
    words = [word for word in re.sub(r"^tsse[-_]?\d+[-_]?", "", slug).split("-") if word]
    return " ".join(word.capitalize() for word in words)


def is_boilerplate(text: str) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in BOILERPLATE_PATTERNS)


def parse_turns(transcript_text: str) -> List[Dict[str, str]]:
    turns: List[Dict[str, str]] = []
    current_speaker = ""
    current_parts: List[str] = []

    def flush() -> None:
        if current_parts:
            text = remove_timestamps(" ".join(current_parts))
            if text:
                turns.append({"speaker": current_speaker, "text": text})

    for paragraph in re.split(r"\n{2,}", transcript_text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        match = re.match(
            r"^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?([A-Z][A-Za-z .'\u00c0-\u017f-]+):\s*(.*)$",
            paragraph,
            re.DOTALL,
        )
        if match:
            flush()
            current_speaker = normalize_space(match.group(1))
            current_parts = [match.group(2)]
        else:
            current_parts.append(paragraph)
    flush()
    return turns


def split_sentences(text: str) -> List[str]:
    sentences = []
    for item in re.split(r"(?<=[.!?])\s+", remove_timestamps(text)):
        cleaned = normalize_space(item.strip(" -"))
        if 25 <= len(cleaned) <= 280 and not is_boilerplate(cleaned):
            sentences.append(cleaned)
    return sentences


def guest_sentences(turns: List[Dict[str, str]], guest_name: str) -> List[str]:
    sentences = []
    for turn in turns:
        speaker = turn.get("speaker", "")
        if speaker in HOST_SPEAKERS:
            continue
        if guest_name and speaker and speaker.lower() != guest_name.lower():
            continue
        sentences.extend(split_sentences(turn.get("text", "")))
    if sentences:
        return sentences
    for turn in turns:
        if turn.get("speaker") not in HOST_SPEAKERS:
            sentences.extend(split_sentences(turn.get("text", "")))
    return sentences


def full_text(turns: List[Dict[str, str]]) -> str:
    return " ".join(turn["text"] for turn in turns)


def keyword_score(text: str, keywords: Iterable[str]) -> int:
    haystack = f" {text.lower()} "
    score = 0
    for keyword in keywords:
        score += haystack.count(keyword.lower())
    return score


def infer_themes(transcript_text: str, title: str) -> Tuple[str, List[str]]:
    scored = []
    combined = f"{title} {transcript_text}"
    for label, keywords in THEME_KEYWORDS:
        score = keyword_score(combined, keywords)
        if score:
            scored.append((label, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    if not scored:
        return "Founder lessons and company-building judgment", ["Founder development", "Decision-making discipline"]
    primary = scored[0][0]
    secondary = [label for label, _ in scored[1:5]]
    return primary, secondary


def infer_industries(transcript_text: str) -> List[str]:
    scored = []
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = keyword_score(transcript_text, keywords)
        if score:
            scored.append((industry, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    industries = [industry for industry, _ in scored[:6]]
    if "Venture Capital" not in industries:
        industries.insert(0, "Venture Capital")
    return industries


def lesson_from_sentence(sentence: str) -> str:
    lower = sentence.lower()
    if "talk to at least 30" in lower or "30, 40" in lower:
        return "Talk to enough managers in an asset class before investing so you understand what quality looks like."
    if "first meeting" in lower and "never pitch" in lower:
        return "Use the first LP meeting to learn fit before pitching."
    if "framework" in lower and ("stay the same" in lower or "consistent" in lower):
        return "Keep your investing framework and inputs consistent so you can learn from one decision to the next."
    if "entry discipline" in lower and "exit discipline" in lower:
        return "Build entry, exit, and executional discipline if you want to be a fund manager, not only a good investor."
    if "home field advantage" in lower:
        return "Identify where you lack home-field advantage, refine that differentiated skill, and explain your thinking to LPs."
    if "spend more time learning about the lp" in lower:
        return "Spend more time learning what motivates the LP before deciding whether the relationship is a fit."
    if "what motivates each personality" in lower:
        return "Understand what motivates each LP personality so your pitch connects to where they want to go next."
    return sentence.rstrip(".") + "."


def infer_founder_lessons(sentences: List[str]) -> List[str]:
    scored = []
    for sentence in sentences:
        lower = sentence.lower()
        score = 0
        for marker in [
            "recommend",
            "should",
            "important",
            "need",
            "have to",
            "don't",
            "figure out",
            "spend more time",
            "consistent",
            "framework",
            "discipline",
            "home field advantage",
            "first meeting",
            "pitch",
        ]:
            if marker in lower:
                score += 2
        if "founder" in lower or "gp" in lower or "lp" in lower or "manager" in lower:
            score += 1
        if is_boilerplate(sentence):
            score -= 10
        if score > 0:
            scored.append((score, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)

    lessons = []
    for _, sentence in scored:
        lesson = lesson_from_sentence(sentence)
        if lesson not in lessons:
            lessons.append(lesson)
        if len(lessons) == 4:
            break
    return lessons


def infer_notable_quotes(sentences: List[str]) -> List[str]:
    quote_markers = [
        "truth is",
        "important",
        "you should",
        "you need",
        "home field advantage",
        "framework",
        "discipline",
        "venture",
        "founder",
        "lp",
    ]
    scored = []
    for sentence in sentences:
        words = sentence.split()
        if not 8 <= len(words) <= 45:
            continue
        score = sum(1 for marker in quote_markers if marker in sentence.lower())
        if score:
            scored.append((score, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)
    quotes = []
    for _, sentence in scored:
        if sentence not in quotes:
            quotes.append(sentence)
        if len(quotes) == 3:
            break
    return quotes


def infer_community_organizations(transcript_text: str) -> List[str]:
    organizations = []
    patterns = [
        r"organization called ([A-Z][A-Za-z .'\-&]+?)(?:\.|,|\s+It's|\s+It is)",
        r"\b([A-Z][A-Za-z&.'-]+(?:\s+[A-Z][A-Za-z&.'-]+){0,5}\s+(?:Foundation|Institute|University|School|College|Association|Center|Centre|Organization|Council|Network|Fellowship))\b",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, transcript_text):
            cleaned = normalize_space(match)
            if (
                cleaned
                and cleaned not in COMMUNITY_ORG_EXCLUSIONS
                and cleaned not in organizations
                and not cleaned.startswith("The Sure Shot")
            ):
                organizations.append(cleaned)
    return organizations[:5]


def generate_episode_intelligence_record(
    *,
    transcript_url: str,
    episode_number: int,
    guest_name: str,
    title: Optional[str] = None,
    transcript_path: Optional[Path] = None,
) -> Dict[str, Any]:
    transcript_path = transcript_path or transcript_path_for_url(transcript_url)
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript file not found: {transcript_path}")
    transcript_text = transcript_path.read_text(encoding="utf-8")
    turns = parse_turns(transcript_text)
    title = title or title_from_slug(slug_from_url(transcript_url))
    sentences = guest_sentences(turns, guest_name)
    text = full_text(turns)
    primary_theme, secondary_themes = infer_themes(text, title)

    return {
        "episode_number": episode_number,
        "title": title,
        "guest_name": guest_name,
        "episode_url": derive_episode_url(transcript_url),
        "primary_theme": primary_theme,
        "secondary_themes": secondary_themes,
        "founder_lessons": infer_founder_lessons(sentences),
        "industries": infer_industries(text),
        "community_organizations": infer_community_organizations(text),
        "notable_quotes": infer_notable_quotes(sentences),
    }


def save_active_record(record: Dict[str, Any], output_dir: Path = ACTIVE_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = active_record_path(int(record["episode_number"]), output_dir)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a TSSE episode intelligence record from a rendered transcript.")
    parser.add_argument("--transcript-url", required=True, help="Episode transcript URL.")
    parser.add_argument("--episode-number", required=True, type=int, help="Episode number.")
    parser.add_argument("--guest-name", required=True, help="Guest name.")
    parser.add_argument("--title", help="Episode title. Defaults to a title derived from the episode slug.")
    parser.add_argument("--transcript-path", help="Optional rendered transcript path. Defaults to data/transcripts/<slug>_transcript.txt.")
    parser.add_argument("--output-dir", default=str(ACTIVE_DIR), help="Directory for active episode intelligence records.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    record = generate_episode_intelligence_record(
        transcript_url=args.transcript_url,
        episode_number=args.episode_number,
        guest_name=args.guest_name,
        title=args.title,
        transcript_path=Path(args.transcript_path) if args.transcript_path else None,
    )
    path = save_active_record(record, Path(args.output_dir))
    print(json.dumps({"episode_intelligence_record": str(path)}, indent=2))


if __name__ == "__main__":
    main()
