# Episode Ingestion Specification

## Purpose

The Episode Ingestion component is responsible for retrieving and structuring information from newly published TSSE podcast episodes.

This is the first step in the TSSE Editorial OS pipeline. All newsletter recommendations depend on accurate episode ingestion.

---

# Source of Truth

The source of truth for episode content is the TSSE podcast website:

https://podcast.sure.ventures/

Every published episode contains:

* Episode number
* Episode title
* Guest name
* Episode URL
* Full transcript

The transcript is considered the authoritative record of the conversation.

---

# Objectives

For each episode, the system should:

1. Retrieve transcript content.
2. Identify the guest.
3. Identify the primary topic of the conversation.
4. Extract supporting themes.
5. Extract founder lessons.
6. Identify industries discussed.
7. Identify community organizations mentioned.
8. Generate structured metadata for downstream recommendation systems.

---

# Required Episode Fields

```yaml
episode:
  episode_number:
  title:
  guest_name:
  publication_date:
  episode_url:
  transcript_url:
  transcript_text:
```

---

# Editorial Metadata

The system should generate:

```yaml
analysis:
  primary_theme:
  secondary_themes:
  founder_lessons:
  notable_quotes:
  industries:
  keywords:
```

---

# Theme Extraction

Every episode should have:

## Primary Theme

The single most important idea discussed in the episode.

Examples:

* Human-Centered Leadership
* Founder Resilience
* Deep Tech Investing
* AI Infrastructure
* Venture Capital Fundraising

## Secondary Themes

Supporting ideas discussed throughout the conversation.

Examples:

* Relationship Building
* Product-Market Fit
* Talent Recruitment
* Enterprise Sales
* Operational Excellence

---

# Founder Lessons

The system should identify lessons that are actionable for founders.

Examples:

* Focus on the right problem before building.
* Recruit exceptional people early.
* Build conviction before metrics exist.
* Understand your customers before scaling.

---

# Industry Detection

The system should identify industries discussed.

Examples:

* Venture Capital
* FinTech
* InsurTech
* Enterprise Software
* Healthcare
* Logistics
* Deep Tech

---

# Community Involvement Detection

The system should identify nonprofits, foundations, and community initiatives mentioned by the guest.

Examples:

* Riley's Way Foundation
* MedShare
* Gift of Life

This information will be used by the Community Involvement section of the newsletter.

---

# Output

The ingestion process should produce a structured episode record suitable for:

* Connected Insights recommendations
* Startup Corner recommendations
* Community Involvement recommendations
* Newsletter drafting

---

# Guiding Principle

The objective is not to summarize the transcript.

The objective is to extract editorial intelligence from the transcript.
