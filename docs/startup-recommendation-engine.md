# Startup Recommendation Engine

## Purpose

The Startup Recommendation Engine recommends the most appropriate company to feature in the Startup Corner section of the newsletter.

The objective is to strengthen the narrative cohesion of each newsletter issue while highlighting companies within the Sure Ventures ecosystem.

---

# Editorial Philosophy

Startup Corner is not intended to be promotional.

Its purpose is to:

* Highlight meaningful company developments.
* Connect portfolio companies to broader industry trends.
* Reinforce themes discussed in the newsletter.
* Surface useful insights for founders and operators.

The startup should contribute to the issue's story.

---

# Eligible Companies

Current approved watchlist:

* Lumber
* TrustLayer
* PAXAFE
* Coterie
* Hi Marley
* Ava
* Insurate
* Juno
* FirstShift
* Balance Cash
* Rigor AI
* Honeycomb
* Konfyd
* Weav

Only approved companies may be recommended.

---

# Inputs

The recommendation engine uses:

## Current Episode

* Primary theme
* Secondary themes
* Founder lessons
* Industries discussed

## Startup Intelligence

* Company website
* Product announcements
* Press releases
* Blog posts
* Industry recognition
* Founder updates

## Newsletter History

* Previous Startup Corner appearances
* Appearance frequency
* Most recent appearance

---

# Recommendation Process

## Step 1: Thematic Alignment

The preferred startup should reinforce the central newsletter theme.

Example:

Episode Theme:

```yaml
theme:
  Operational Decision Making
```

Strong Match:

```yaml
FirstShift:
  Supply Chain Decision Intelligence
```

Thematic alignment is the highest priority criterion.

---

## Step 2: Industry Alignment

Industry overlap strengthens recommendations.

Examples:

* InsurTech episode → Coterie
* Logistics episode → PAXAFE
* AI episode → Rigor AI

Industry alignment is valuable but secondary to theme alignment.

---

## Step 3: Strategic Relationship Signals

Additional recommendation strength may come from:

* Co-investment relationships
* Industry overlap with guest
* Shared market focus
* Shared customer profile

These signals should supplement thematic alignment.

---

## Step 4: Newsworthiness

The engine should identify meaningful developments.

Examples:

### Product Launch

New product release.

### Customer Milestone

Significant adoption milestone.

### Partnership

Strategic partnership announcement.

### Award

Industry recognition.

### Founder Insight

Noteworthy founder article, interview, or public commentary.

The goal is to find a story worth sharing.

---

## Step 5: Appearance Recency

Avoid repeatedly featuring the same companies.

Suggested rule:

| Issues Since Last Appearance | Recommendation Effect |
| ---------------------------- | --------------------- |
| 0–4                          | Exclude               |
| 5–8                          | Strong Penalty        |
| 9–12                         | Mild Penalty          |
| 13+                          | No Penalty            |

These thresholds may evolve.

---

# Recommendation Output

The system should provide multiple candidates.

Example:

```yaml
recommendations:

  - startup:
      FirstShift
    score: 95
    rationale:
      Strong thematic alignment
      Recent product launch
      Not recently featured

  - startup:
      Weav
    score: 87
    rationale:
      Relevant industry trend
      Recent company activity
```

---

# Human Review

The recommendation engine provides suggestions.

Final selection remains an editorial decision.

Editors may choose a lower-ranked recommendation if it better supports the newsletter narrative.

---

# Success Criteria

A reviewer should consistently agree that the recommended startups are relevant to the issue and provide useful content for Startup Corner.

---

# Guiding Principle

The best Startup Corner selection is not necessarily the company with the biggest news.

It is the company whose story best strengthens the theme of the newsletter issue.
