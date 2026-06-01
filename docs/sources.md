# TSSE Editorial OS Source Registry

## Purpose

This document defines the authoritative sources used by TSSE Editorial OS.

The goal is to eliminate ambiguity and ensure that all systems, developers, and AI agents reference the same sources of truth.

Whenever possible, recommendation systems should rely on the sources defined in this document rather than performing broad internet searches.

---

# Source of Truth Principles

## Principle 1

If an authoritative source exists, use it.

Example:

Use the official startup website instead of third-party articles whenever possible.

---

## Principle 2

Podcast transcripts are the authoritative source for episode analysis.

The transcript should always take precedence over summaries, show notes, or social posts.

---

## Principle 3

Editorial decisions remain human decisions.

The role of TSSE Editorial OS is to recommend, not decide.

---

# TSSE Sources

## Sure Ventures Website

Purpose:

* Firm information
* Portfolio information
* Events
* General company context

URL:

https://www.sure.ventures/

---

## The Sure Shot Entrepreneur Podcast

Purpose:

* Episode information
* Guest information
* Podcast transcripts

URL:

https://podcast.sure.ventures/

Notes:

This is the primary source of truth for episode content.

All episode analysis should originate from transcript content retrieved from this website.

---

# Editorial Sources

## Guest Ranking Database

Purpose:

Maintain editorial rankings assigned by Gopi Rangan.

Used by:

* Connected Insights Recommendation Engine

Rules:

Only guests ranked 4 are eligible for Connected Insights recommendations.

Source:

Google Sheet maintained by Gopi Rangan.

URL:

https://docs.google.com/spreadsheets/d/18kpyRiloBY5xXzCOnPNUVcMrPBvAMiiOsA32tttcmsI/

Notes:

The spreadsheet contains:

* Episode number
* Guest name
* Episode URL
* Guest ranking

Guest ranking reflects editorial quality and suitability for future newsletter references.

---

## Startup Watchlist

Purpose:

Defines the approved companies eligible for Startup Corner recommendations.

Used by:

* Startup Recommendation Engine

Source:

Google Doc maintained by Sure Ventures.

URL: https://docs.google.com/document/d/18tkUc5LTkpMWI5k1Nl7FbGkSTVGTMBydYU8o-zekqpQ/edit?pli=1&tab=t.0

Notes:

Only companies listed in the watchlist may be recommended.

The watchlist may evolve over time.

---

# Startup Sources

## Lumber

Website:

https://www.lumberfi.com/

Category:

Construction Finance

---

## TrustLayer

Website:

https://www.trustlayer.io/

Category:

Insurance Verification and Risk Management

---

## PAXAFE

Website:

https://www.paxafe.com/

Category:

Supply Chain Intelligence

---

## Coterie

Website:

https://coterieinsurance.com/

Category:

InsurTech

---

## Hi Marley

Website:

https://www.himarley.com/

Category:

Insurance Communication Platform

---

## Ava

Website:

https://meetava.com/

Category:

AI Meeting Intelligence

---

## Insurate

Website:

https://www.insurate.com/

Category:

Insurance Technology

---

## Juno

Website:

https://www.junokids.com/

Category:

Family Financial Protection

---

## FirstShift

Website:

https://firstshift.ai/

Category:

Supply Chain Decision Intelligence

---

## Balance Cash

Website:

https://www.balancecash.io/

Category:

Financial Technology

---

## Rigor AI

Website:

https://rigor.ai/

Category:

Artificial Intelligence

---

## Honeycomb

Website:

https://honeycombinsurance.com/

Category:

InsurTech

---

## Konfyd

Website:

https://www.konfyd.com/

Category:

Identity and Trust Infrastructure

---

## Weav

Website:

https://weav.ai/

Category:

Artificial Intelligence

---

# Community Organization Sources

Purpose:

Support Community Involvement section generation.

Source:

Primary organization website.

Examples:

* Riley's Way Foundation
* MedShare
* Gift of Life

Process:

1. Identify organization from episode transcript.
2. Visit official website.
3. Retrieve mission information.
4. Retrieve recent milestones.
5. Generate newsletter summary.

---

# Newsletter History Source

Purpose:

Maintain institutional memory of editorial decisions.

Used by:

* Connected Insights Recommendation Engine
* Startup Recommendation Engine

Location:

Repository-managed dataset.

Initial implementation should use a CSV file stored within TSSE Editorial OS.

Future implementations may migrate to:
- Google Sheets
- Database tables
- Other structured storage systems

Minimum Fields:

```yaml
issue_number:
publication_date:
featured_episode:
connected_insight_guest:
startup_corner_company:
community_organization:
central_theme:
```

---

# Future Sources

Future versions of TSSE Editorial OS may incorporate:

* Sure Ventures event calendars
* Guest LinkedIn profiles
* Startup blogs
* Startup press releases
* Founder interviews
* Industry publications

Any new source should be added to this document before being used in production.

---

# Guiding Principle

The quality of TSSE Editorial OS recommendations depends on the quality of its source material.

Whenever there is uncertainty, prefer authoritative sources over inferred information.
