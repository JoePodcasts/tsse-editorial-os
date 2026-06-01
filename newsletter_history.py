#!/usr/bin/env python3
import csv
from pathlib import Path

CSV_PATH = Path(__file__).parent / "data" / "newsletter_history.csv"


def load_newsletter_history(path):
    with path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)


def sorted_records(records):
    def sort_key(record):
        try:
            return int(record.get("issue_number", ""))
        except ValueError:
            return float("inf")

    return sorted(records, key=sort_key)


def print_summary(records):
    sorted_list = sorted_records(records)
    total_issues = len(sorted_list)
    connected_guests = sorted({r.get("connected_insight_guest", "").strip() for r in sorted_list if r.get("connected_insight_guest", "").strip()})
    startup_companies = sorted({r.get("startup_corner_company", "").strip() for r in sorted_list if r.get("startup_corner_company", "").strip()})

    most_recent_connected = next((r["connected_insight_guest"] for r in reversed(sorted_list) if r.get("connected_insight_guest", "").strip()), "")
    most_recent_startup = next((r["startup_corner_company"] for r in reversed(sorted_list) if r.get("startup_corner_company", "").strip()), "")

    print("Newsletter history summary:")
    print(f"- total newsletter issues: {total_issues}")
    print(f"- unique Connected Insights guests: {len(connected_guests)}")
    print(f"- unique Startup Corner companies: {len(startup_companies)}")
    print(f"- most recently featured Connected Insights guest: {most_recent_connected}")
    print(f"- most recently featured Startup Corner company: {most_recent_startup}")


def print_issues(records):
    print("\nNewsletter issues:")
    for record in sorted_records(records):
        print(f"- Issue {record.get('issue_number', '')}: Episode {record.get('featured_episode', '')}")


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")

    records = load_newsletter_history(CSV_PATH)
    print_summary(records)
    print_issues(records)


if __name__ == "__main__":
    main()
