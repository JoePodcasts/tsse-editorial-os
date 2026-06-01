# Connected Insights Recommendation Engine

## Purpose

The Connected Insights Recommendation Engine identifies the most relevant historical TSSE guest to feature alongside the newest podcast episode.

The objective is to expand the newsletter theme by introducing a complementary perspective from a previously featured guest.

Connected Insights should reinforce the central idea of the issue rather than introduce a completely different topic.

---

# Editorial Philosophy

The TSSE newsletter is built around ideas, not individuals.

The Connected Insights section exists to:

* Reinforce the central theme.
* Provide an additional perspective.
* Surface valuable historical TSSE content.
* Encourage readers to explore previous episodes.

The best Connected Insights selections feel like a continuation of the conversation.

---

# Eligibility Rules

Only guests ranked 4 by Gopi Rangan are eligible.

Guest ranking is maintained in the Guest Ranking Database.

```yaml
eligible_guest:
  guest_rank: 4
```

Guests with rankings below 4 should never be recommended.

---

# Inputs

The recommendation engine uses:

## Current Episode

* Primary theme
* Secondary themes
* Founder lessons
* Industries discussed

## Guest Database

* Rank 4 guests only
* Historical episode metadata
* Guest themes

## Newsletter History

* Previous Connected Insights appearances
* Appearance frequency
* Most recent appearance

---

# Recommendation Process

## Step 1: Theme Matching

Identify guests whose historical episode themes align with the current episode.

Examples:

Current Episode Theme:

```yaml
primary_theme:
  Human-Centered Leadership
```

Potential Matches:

```yaml
Guy Kawasaki:
  Leadership
  Authenticity
  Influence

Lo Toney:
  Leadership
  Talent Development

Ian Rountree:
  Building Through Relationships
```

Theme alignment should be the most important factor.

---

## Step 2: Founder Lesson Matching

Compare practical lessons.

Example:

Current Episode:

```yaml
lesson:
  Great organizations are built around people.
```

Historical Guest:

```yaml
lesson:
  Great leaders inspire rather than control.
```

These lessons are complementary and should increase recommendation strength.

---

## Step 3: Industry Context

Industry alignment is helpful but not required.

Examples:

Strong Match:

* Deep Tech → Deep Tech

Moderate Match:

* Venture Capital → Entrepreneurship

Weak Match:

* Deep Tech → Healthcare Policy

Industry should support recommendations but should not dominate them.

---

## Step 4: Appearance Recency

The system should avoid repeatedly featuring the same guests.

Suggested rule:

| Issues Since Last Appearance | Recommendation Effect |
| ---------------------------- | --------------------- |
| 0–4                          | Exclude               |
| 5–8                          | Strong Penalty        |
| 9–12                         | Mild Penalty          |
| 13+                          | No Penalty            |

These thresholds may evolve over time.

---

# Recommendation Output

The system should return multiple candidates.

Example:

```yaml
recommendations:

  - guest:
      Guy Kawasaki
    score: 94
    rationale:
      Strong leadership alignment
      Human-centered perspective
      Not featured recently

  - guest:
      Lo Toney
    score: 89
    rationale:
      Similar people-first leadership themes
```

---

# Human Review

The recommendation engine does not make final editorial decisions.

It provides ranked candidates.

The editor selects the final Connected Insights guest.

---

# Success Criteria

A human reviewer should consistently agree that the top recommendations are reasonable candidates for the newsletter issue.

Perfect recommendations are not required.

Useful recommendations are required.

---

# Guiding Principle

Connected Insights should deepen the newsletter theme rather than simply reference another popular guest.
