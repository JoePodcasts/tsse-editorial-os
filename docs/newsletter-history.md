# Newsletter History Specification

## Purpose

The Newsletter History dataset serves as the institutional memory of TSSE Editorial OS.

Its purpose is to record previous editorial decisions so the system can avoid repetitive recommendations and maintain variety across newsletter issues.

---

# Why Newsletter History Matters

Newsletter production involves editorial judgment.

When selecting:

* Connected Insights guests
* Startup Corner companies
* Community organizations

it is important to know what has already been featured recently.

Without this information, recommendations may become repetitive.

---

# Core Record Structure

Each newsletter issue should have a single record.

```yaml
newsletter_issue:
  issue_number:
  publication_date:
```

---

# Content Fields

```yaml
content:
  featured_episode:
  featured_guest:
  connected_insight_guest:
  startup_corner_company:
  community_organization:
```

---

# Editorial Fields

```yaml
editorial:
  central_theme:
  supporting_themes:
```

---

# Example Record

```yaml
newsletter_issue:
  issue_number: 75
  publication_date: 2026-06-01

content:
  featured_episode: 188
  featured_guest: Ian Sandler
  connected_insight_guest: Guy Kawasaki
  startup_corner_company: FirstShift
  community_organization: Riley's Way Foundation

editorial:
  central_theme: Human-Centered Leadership
```

---

# Recommendation Constraints

## Connected Insights

When recommending guests:

The system should check:

* Has this guest appeared recently?
* How many issues ago was the guest featured?

Recent appearances should reduce recommendation priority.

---

## Startup Corner

When recommending startups:

The system should check:

* Has the startup appeared recently?
* How many issues ago was the startup featured?

Recent appearances should reduce recommendation priority.

---

# Historical Seed Data

The initial dataset should include previous newsletter issues where available.

Examples:

| Issue | Episode        | Connected Insight | Startup    |
| ----- | -------------- | ----------------- | ---------- |
| 73    | Debjit Mukerji | Karthee Madasamy  | PAXAFE     |
| 74    | Gilad Shai     | Matt Harris       | Juno       |
| 75    | Ian Sandler    | Guy Kawasaki      | FirstShift |

Additional historical issues can be added over time.

---

# Future Use Cases

The Newsletter History dataset may later support:

* Recommendation penalties
* Theme diversity analysis
* Startup appearance tracking
* Guest appearance tracking
* Editorial analytics

---

# Guiding Principle

Newsletter History records editorial decisions, not just published content.

This dataset exists to help preserve variety, context, and institutional memory across future issues.
