# TSSE Editorial OS Architecture

## Overview

TSSE Editorial OS is designed as an editorial intelligence system.

Its purpose is to analyze new TSSE podcast episodes and generate recommendations that assist in newsletter creation.

The system is intended to support editorial decisions rather than automate them entirely.

---

## Inputs

### 1. Podcast Episode Transcript

Source:
https://podcast.sure.ventures/

Purpose:

* Theme extraction
* Founder lesson identification
* Community involvement detection

---

### 2. Guest Ranking Database

Source:
Google Sheets

Purpose:

* Filter eligible guests for Connected Insights
* Maintain editorial quality standards

Rule:
Only guests with Rank = 4 are eligible.

---

### 3. Startup Watchlist

Source:
Google Doc

Current Watchlist:

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

Purpose:

* Generate Startup Corner recommendations

---

### 4. Newsletter History

Purpose:

* Track previous Connected Insights guests
* Track previous Startup Corner selections
* Avoid repetitive recommendations

---

## Processing Pipeline

### Step 1: Episode Analysis

Input:
Podcast transcript

Output:

* Primary theme
* Secondary themes
* Key founder lessons
* Notable quotes
* Industry focus

---

### Step 2: Connected Insights Recommendation

Input:

* Episode themes
* Rank 4 guest database
* Newsletter history

Output:

* Ranked Connected Insights candidates
* Similarity scores
* Recommendation rationale

---

### Step 3: Startup Corner Recommendation

Input:

* Episode themes
* Startup watchlist
* Recent startup news
* Newsletter history

Output:

* Ranked startup candidates
* Recommendation rationale

---

### Step 4: Community Involvement Detection

Input:
Podcast transcript

Output:

* Organization name
* Mission summary
* Relevant milestones
* Draft newsletter content

---

### Step 5: Intro Generation

Input:

* Episode themes
* Connected Insights theme
* Startup Corner theme
* Community involvement theme

Output:
Three intro alternatives:

1. Big-Idea Intro
2. Founder/Investor Commentary Intro
3. Personal Reflection Intro

---

## Outputs

### Newsletter Briefing Package

Contains:

* Episode analysis
* Connected Insights recommendations
* Startup recommendations
* Community involvement draft
* Intro alternatives

This package is reviewed before newsletter drafting begins.

---

## Human Review Layer

Editorial judgment remains essential.

The system recommends.

The editor decides.

Final approval remains with Gopi Rangan.
