# Episode Analysis Framework

This framework defines how TSSE episode transcripts should be analyzed and converted into structured episode intelligence records.

The goal is to make episode data usable for recommendation engines, newsletter drafting, and historical analysis.

## Episode Record Structure

A structured episode record should contain the following fields:

- `episode_number`
- `title`
- `guest_name`
- `episode_url`
- `primary_theme`
- `secondary_themes`
- `founder_lessons`
- `industries`
- `community_organizations`
- `notable_quotes`

The template is stored in `data/episodes/episode_template.json`.

## 1. Primary Theme Identification

### Definition
The primary theme is the single most important idea or editorial focus of the episode.

### How to identify it
1. Read the episode introduction and host framing.
2. Identify the main question or problem the guest is addressing.
3. Locate the recurring concept that appears across the episode summary, quotes, and guest insights.

### Examples
- Human-Centered Leadership
- Founder Resilience
- Deep Tech Investing
- AI Infrastructure
- Venture Capital Fundraising

### Guiding rule
Choose the theme that best captures the episode’s overriding narrative, even if the episode touches on several related topics.

## 2. Secondary Theme Identification

### Definition
Secondary themes are supporting ideas that are important to the episode but not its main focus.

### How to identify them
1. Extract additional concepts mentioned repeatedly in the transcript.
2. Look for supporting topics that help explain or extend the primary theme.
3. Capture themes that are useful for recommendation matching but not the episode’s central idea.

### Examples
- Relationship Building
- Product-Market Fit
- Talent Recruitment
- Enterprise Sales
- Operational Excellence

### Structure
Store secondary themes as an array of short expressions. Prefer 2–4 supporting themes per episode.

## 3. Founder Lesson Extraction

### Definition
Founder lessons are actionable insights or advice for startup founders that emerge from the conversation.

### How to extract them
1. Identify statements that begin with or imply guidance, tradeoffs, or rules of thumb.
2. Prefer lessons rooted in the guest’s experience, not generic aphorisms.
3. Keep each lesson concise and specific.

### Examples
- Focus on the right problem before building.
- Recruit exceptional people early.
- Build conviction before metrics exist.
- Understand your customers before scaling.

### Best practice
Translate narrative insights into short, founder-oriented lessons. Each lesson should stand alone and be useful outside the original transcript.

## 4. Industry Classification

### Definition
Industries are the business domains discussed in the episode.

### How to classify them
1. Identify the verticals, sectors, or market categories the guest references.
2. Use broad industry labels that align with the TSSE editorial model.
3. Include both the guest’s sector and related domains that matter for recommendations.

### Example industries
- Venture Capital
- FinTech
- InsurTech
- Enterprise Software
- Healthcare
- Logistics
- Deep Tech

### Structure
Store industries as an array of normalized sector labels. Include multiple industries when the episode spans different domains.

## 5. Community Organization Identification

### Definition
Community organizations are nonprofits, foundations, or social impact entities mentioned by the guest.

### How to identify them
1. Search the transcript for named organizations connected to the guest’s personal or professional story.
2. Capture organizations that are explicitly referenced as part of community involvement.
3. Exclude generic categories; record actual organization names.

### Examples
- Riley’s Way Foundation
- MedShare
- Gift of Life

### Use case
This field supports Community Involvement recommendations and helps the newsletter highlight mission-driven work.

## 6. Notable Quotes

### Definition
Notable quotes are short, memorable passages from the transcript that illustrate the episode’s themes.

### How to select them
1. Choose quotes that are insightful, distinct, and representative of the episode.
2. Prefer statements that connect to the primary or secondary themes.
3. Keep quotes concise and suitable for reuse in recommendations or newsletter summaries.

### Structure
Store quotes as an array of strings.

## Provenance and Source Rules

- The transcript is the authoritative source for all episode analysis.
- Do not infer episode facts from summaries, show notes, or external articles.
- Whenever possible, derive theme labels from the guest’s own language and the host’s framing.

## Implementation Notes

- The episode record format is intentionally lightweight and designed for downstream consumption.
- Recommendation engines should treat `primary_theme` as the episode’s core signal and `secondary_themes` as supporting context.
- `founder_lessons`, `industries`, and `community_organizations` are the main structured outputs that connect episodes to newsletter sections.
- `notable_quotes` provide narrative detail and should remain faithful to the transcript.

## Next step

Future ingestion processes should populate this structure from transcript text using the rules described here. For now, this document defines the editorial intelligence model without relying on external APIs or website scraping.
