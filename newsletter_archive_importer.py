#!/usr/bin/env python3
import csv
import re
from pathlib import Path

INPUT_PATH = Path(__file__).parent / "data" / "newsletter_archive_sample.txt"
OUTPUT_PATH = Path(__file__).parent / "data" / "newsletter_history.csv"
HEADERS = [
    "issue_number",
    "featured_episode",
    "featured_guest",
    "connected_insight_guest",
    "startup_corner_company",
    "community_organization",
    "publication_date",
    "central_theme",
]

FIELD_PATTERNS = {
    "featured_episode": [
        r"featured episode\s*[:\-]\s*#?(\d+)",
        r"episode\s*[:\-]\s*#?(\d+)",
    ],
    "featured_guest": [
        r"featured guest\s*[:\-]\s*(.+)",
        r"guest\s*[:\-]\s*(.+)",
    ],
    "connected_insight_guest": [
        r"connected insights guest\s*[:\-]\s*(.+)",
        r"connected insights\s*[:\-]\s*(.+)",
    ],
    "startup_corner_company": [
        r"startup corner company\s*[:\-]\s*(.+)",
        r"startup corner\s*[:\-]\s*(.+)",
    ],
    "community_organization": [
        r"community organization\s*[:\-]\s*(.+)",
        r"community involvement\s*[:\-]\s*(.+)",
    ],
    "publication_date": [
        r"publication date\s*[:\-]\s*(.+)",
        r"published\s*[:\-]\s*(.+)",
    ],
    "central_theme": [
        r"central theme\s*[:\-]\s*(.+)",
        r"theme\s*[:\-]\s*(.+)",
    ],
}


def clean_value(value: str) -> str:
    value = value.strip()
    if value.endswith("."):
        value = value[:-1].strip()
    return value


def first_match(block: str, patterns):
    for pattern in patterns:
        match = re.search(pattern, block, re.IGNORECASE)
        if match:
            return clean_value(match.group(1))
    return ""


def extract_issue_date(issue_line: str) -> str:
    match = re.search(r"^Issue\s+\d+\s*[-–|]\s*(.+)$", issue_line, re.IGNORECASE)
    if match:
        return clean_value(match.group(1))
    return ""


def parse_issue_block(block: str) -> dict:
    issue_match = re.search(r"^Issue\s+(\d+)\b", block, re.IGNORECASE | re.MULTILINE)
    if not issue_match:
        return {}

    issue_number = issue_match.group(1)
    publication_date = ""
    issue_line = re.search(r"^Issue\s+\d+.*$", block, re.IGNORECASE | re.MULTILINE)
    if issue_line:
        publication_date = extract_issue_date(issue_line.group(0))

    record = {
        "issue_number": issue_number,
        "featured_episode": first_match(block, FIELD_PATTERNS["featured_episode"]),
        "featured_guest": first_match(block, FIELD_PATTERNS["featured_guest"]),
        "connected_insight_guest": first_match(block, FIELD_PATTERNS["connected_insight_guest"]),
        "startup_corner_company": first_match(block, FIELD_PATTERNS["startup_corner_company"]),
        "community_organization": first_match(block, FIELD_PATTERNS["community_organization"]),
        "publication_date": publication_date or first_match(block, FIELD_PATTERNS["publication_date"]),
        "central_theme": first_match(block, FIELD_PATTERNS["central_theme"]),
    }
    return record


def load_archive_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="replace") as file:
        return file.read()


def split_issue_blocks(text: str):
    blocks = re.split(r"(?=^Issue\s+\d+\b)", text, flags=re.MULTILINE)
    return [block.strip() for block in blocks if block.strip()]


def write_csv(records):
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=HEADERS)
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def main():
    if not INPUT_PATH.exists():
        print(f"Archive sample not found: {INPUT_PATH}")
        print("Please place the newsletter archive text file at the expected path and rerun the importer.")
        return

    text = load_archive_text(INPUT_PATH)
    blocks = split_issue_blocks(text)
    records = []

    for block in blocks:
        record = parse_issue_block(block)
        if record:
            records.append(record)

    if not records:
        print("No newsletter issues were parsed from the archive. Please verify the file structure.")
        return

    write_csv(records)
    print(f"Parsed {len(records)} newsletter issue records into {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
