# TSSE Editorial OS

TSSE Editorial OS is an editorial intelligence system designed to support content production for The Sure Shot Entrepreneur (TSSE) podcast and newsletter.

The project aims to reduce manual research and administrative work while preserving the editorial judgment of Gopi Rangan and the TSSE content team.

Rather than generating content blindly, the system is designed to help identify the most relevant stories, guests, startups, and community initiatives to feature in each newsletter issue.

## Objectives

* Reduce manual newsletter research and analysis.
* Create a structured knowledge base of TSSE episodes.
* Recommend Connected Insights guests based on episode themes.
* Recommend Startup Corner companies based on relevance and recent developments.
* Extract Community Involvement information from episode transcripts.
* Generate newsletter briefing packages for editorial review.
* Preserve consistency across newsletter issues.

## Newsletter Structure

Each newsletter issue currently contains:

1. Email Intro
2. Podcast Entries
3. Connected Insights
4. Startup Corner
5. Community Involvement

## Data Sources

### TSSE Podcast Website

Source of truth for all episode transcripts.

### Guest Ranking Database

Google Sheet maintained by Gopi Rangan containing guest rankings (1–4).

Only guests ranked 4 are eligible for Connected Insights recommendations.

### Startup Watchlist

Curated list of Sure Ventures portfolio companies eligible for Startup Corner.

### Newsletter History

Historical record of newsletter issues, featured guests, startups, and themes.

## Editorial Philosophy

The TSSE newsletter is not a podcast summary.

Each issue is built around a central theme extracted from the newest podcast episode. Every section should reinforce or expand that theme through a different lens.

The system should support editorial decision-making rather than replace it.

## Documentation

### Core Documents

- docs/workflows.md
  - Current and future newsletter production workflows.

- docs/data-model.md
  - Core entities, relationships, and metadata used throughout the system.

- docs/architecture.md
  - High-level system architecture and processing pipeline.

## Long-Term Vision

Create an editorial intelligence platform that serves as the institutional memory of TSSE content operations and supports:

* Newsletter creation
* Social content creation
* Episode research
* Historical insight discovery
* Startup portfolio storytelling
* Future content initiatives
