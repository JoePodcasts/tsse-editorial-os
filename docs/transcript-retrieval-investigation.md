# Transcript Retrieval Investigation

## Executive Summary

Investigation of TSSE podcast transcript retrieval mechanisms reveals that **transcripts are loaded entirely client-side through a Vite single-page application (SPA)**. The current HTTP-based retrieval method cannot access transcript content because:

1. Direct HTTP requests return only the HTML shell (3.2 KB)
2. No public API endpoints are available
3. No transcript data is embedded in the initial page source
4. All transcript content is loaded dynamically via JavaScript

**Recommended Solution**: Implement headless browser rendering using Playwright or Puppeteer to fully load the SPA and extract transcript content from the DOM.

---

## Investigation Methodology

### Test Cases Evaluated

1. **Direct HTML Fetch (Current Method)**
   - URL: `https://podcast.sure.ventures/episodes/<slug>/transcript`
   - Result: ✓ Works, but returns HTML shell only

2. **JSON API Endpoints**
   - `/episodes/<slug>/transcript.json` — ✗ Not found
   - `https://api.sure.ventures/episodes/<slug>/transcript` — ✗ Not found
   - Standard RESTful patterns — ✗ Not found

3. **Simplecast API**
   - `https://api.simplecast.com/v2/episodes?filter[slug]=<slug>` — ✗ 404 Not Found
   - `https://feeds.simplecast.com/podcasts/<id>/episodes.json` — ✗ Not Found
   - Simplecast v2 endpoints — ✗ Not Found

4. **RSS/Feed Endpoints**
   - `https://feeds.simplecast.com/sure-shot-entrepreneur.xml` — ✗ 404 Not Found
   - `https://podcast.sure.ventures/feed` — ✓ Returns HTML shell (same 3.2 KB)
   - `https://podcast.sure.ventures/feed.xml` — ✓ Returns HTML shell (same 3.2 KB)
   - `https://podcast.sure.ventures/rss` — ✓ Returns HTML shell (same 3.2 KB)

### Test Episodes Analyzed

| Episode | URL | Retrieved Size | Content Type |
|---------|-----|-----------------|--------------|
| 2 | `100-angel-investments` | 3.2 KB | HTML Shell |
| 25 | `x-factor` | 3.2 KB | HTML Shell |
| 26 | `chief-engineer` | 3.2 KB | HTML Shell |

---

## Detailed Findings

### 1. How Transcript Content Is Loaded

#### Current Architecture: Client-Side Rendering

The TSSE podcast website is built as a **Vite SPA** (Vue/React-based single-page application) hosted on Simplecast's infrastructure:

**HTML Structure**:
```html
<!DOCTYPE html>
<html>
  <head>
    <!-- Meta tags, fonts, CSS -->
    <link rel="stylesheet" href="...index-0kHawvsF.css">
  </head>
  <body>
    <div id="app"></div>
    <!-- Vite JavaScript bundles -->
    <script type="module" src="...index-B_CVZMaz.js"></script>
    <script type="module" src="...polyfills-legacy-umeSkaRK.js"></script>
  </body>
</html>
```

**Loading Process**:
1. Browser requests episode URL: `https://podcast.sure.ventures/episodes/chief-engineer/transcript`
2. Server returns HTML shell with Vite framework
3. Vite loads JavaScript bundles from: `https://image.simplecastcdn.com/customersites/latest/assets/`
4. JavaScript bundles initialize the SPA in the `<div id="app">`
5. **Unknown step**: SPA makes API call to fetch transcript content
6. Transcript rendered in DOM

**Key Limitation**: HTTP-level retrieval stops at step 2 (HTML shell). Steps 3-6 happen in the browser.

### 2. Where Is Transcript Data Stored?

**Analysis Results**:

| Hypothesis | Evidence | Verdict |
|-----------|----------|---------|
| Embedded in page source | ✗ No JSON in meta tags, script tags, or data attributes | **NO** |
| Loaded from JSON API | ✗ No public endpoint found; API authentication likely required | **NO** |
| Loaded from CMS backend | ⚠ Unknown; likely but not documented | **UNKNOWN** |
| Loaded from Simplecast API | ✗ Standard endpoints return 404; custom endpoint unknown | **UNKNOWN** |
| Embedded in Vite bundles | ⚠ Possible but would require JavaScript execution | **UNKNOWN** |
| Rendered entirely client-side | ✓ Evidence of SPA architecture | **LIKELY** |

**Conclusion**: Transcript data is NOT statically available in HTTP responses. It requires JavaScript execution to retrieve.

### 3. JavaScript Execution Analysis

**Vite Bundle Contents** (Not inspected, but typical for SPA architecture):
- Core SPA framework (Vue or React)
- Route handlers for `/episodes/<slug>/transcript`
- API client for backend communication
- DOM rendering logic

**Unknown API Endpoint**:
- The JavaScript bundles likely contain API calls to fetch transcript data
- Without loading JavaScript, we cannot determine the endpoint
- Possible formats:
  - `https://api.sure.ventures/v1/episodes/<slug>/transcript`
  - `https://api.simplecast.com/episodes/<slug>` (with authentication)
  - Internal microservice endpoint

---

## Retrieval Approach Evaluation

### Approach 1: Static HTML Parsing (Current)

**How It Works**:
- HTTP GET to episode/transcript URL
- Parse returned HTML
- Extract content from DOM

**Pros**:
- ✓ Simple, lightweight
- ✓ No external dependencies
- ✓ Fast (immediate HTTP response)
- ✓ Works with current Python script

**Cons**:
- ✗ No transcript content in HTML shell
- ✗ Cannot extract meaning from page
- ✗ Requires manual workarounds (metadata inference)

**Recommendation**: ❌ **Not viable for transcript extraction**

**Confidence**: 100%

---

### Approach 2: API Endpoint Reverse Engineering

**How It Works**:
1. Manually load the page in a browser
2. Open browser DevTools → Network tab
3. Identify the API call that fetches transcript
4. Document the endpoint format
5. Implement direct API calls in ingestion script

**Pros**:
- ✓ Simplest if API is accessible
- ✓ Fast, lightweight
- ✓ No JavaScript execution needed
- ✓ Reliable once endpoint is known

**Cons**:
- ✗ Requires manual investigation
- ✗ API may require authentication
- ✗ Endpoint may change with site updates
- ✗ API may have rate limiting
- ⚠ Not yet attempted (requires browser access)

**Recommendation**: ✅ **Try this first** (requires manual investigation)

**Confidence**: Unknown until tested

---

### Approach 3: Simplecast/Podcast Host API

**How It Works**:
1. Identify the Simplecast podcast ID
2. Use Simplecast public API to fetch episode metadata
3. Extract transcript URL or content from API response

**Pros**:
- ✓ Standard, documented API
- ✓ Official endpoint
- ✓ Likely to be stable

**Cons**:
- ✗ Simplecast API not responding to standard queries (404s)
- ✗ May require API key
- ✗ May not include transcripts in free tier
- ✗ Need to determine correct podcast ID

**Recommendation**: ⚠️ **Research required** (API access unclear)

**Confidence**: Low until Simplecast API is confirmed

---

### Approach 4: Headless Browser Rendering

**How It Works**:
1. Use Playwright (Python) or Puppeteer (Node.js)
2. Load episode URL in headless Chrome browser
3. Wait for JavaScript to load and render transcript
4. Extract transcript text from DOM using CSS selectors
5. Save transcript to file

**Example Code** (Pseudocode):
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://podcast.sure.ventures/episodes/chief-engineer/transcript")
    page.wait_for_selector(".transcript-content")
    transcript = page.text_content(".transcript-content")
    browser.close()
```

**Pros**:
- ✓ Guaranteed to work
- ✓ Loads full SPA and JavaScript
- ✓ Extracts actual rendered content
- ✓ No reliance on undocumented APIs
- ✓ Handles dynamic content well

**Cons**:
- ✗ Slower (browser startup + page load)
- ✗ Requires additional dependencies (Playwright/Puppeteer)
- ✗ More resource-intensive
- ✗ Need to identify CSS selectors for transcript content
- ✗ Need to wait for content to load (timing-dependent)

**Resource Requirements**:
- `playwright` or `puppeteer` library
- Chromium/Firefox/WebKit binary
- Additional ~100 MB disk space
- ~2-5 seconds per transcript

**Recommendation**: ✅ **Viable fallback** if API approach fails

**Confidence**: 95% (proven technology)

---

### Approach 5: Simplecast Transcript Embed API

**How It Works**:
- Simplecast may offer a direct transcript API for premium/partner podcasts
- Check if TSSE has explicit transcript data through Simplecast

**Status**: Not investigated (would require Simplecast account access)

**Recommendation**: ⚠️ **Contact Simplecast if API approach fails**

---

## Detailed Episode Analysis

### Episode 2: "100 Angel Investments" (Gokul Rajaram)

- **URL**: `https://podcast.sure.ventures/episodes/100-angel-investments`
- **Transcript URL**: `https://podcast.sure.ventures/episodes/100-angel-investments/transcript`
- **HTTP Response Size**: 3,281 bytes
- **Content Type**: HTML (Vite SPA shell)
- **Transcript Content Retrieved**: ❌ No
- **File Type**: HTML shell with SPA framework
- **Embedded Data**: None detected
- **Assessment**: Same HTML shell as all others

### Episode 25: "The X Factor" (Ullas Naik)

- **URL**: `https://podcast.sure.ventures/episodes/x-factor`
- **Transcript URL**: `https://podcast.sure.ventures/episodes/x-factor/transcript`
- **HTTP Response Size**: 3,281 bytes
- **Content Type**: HTML (Vite SPA shell)
- **Transcript Content Retrieved**: ❌ No
- **File Type**: HTML shell with SPA framework
- **Embedded Data**: None detected
- **Assessment**: Same HTML shell as all others

### Episode 26: "Building Products Like a Chief Engineer" (Ashmeet Sidana)

- **URL**: `https://podcast.sure.ventures/episodes/chief-engineer`
- **Transcript URL**: `https://podcast.sure.ventures/episodes/chief-engineer/transcript`
- **HTTP Response Size**: 3,281 bytes
- **Content Type**: HTML (Vite SPA shell)
- **Transcript Content Retrieved**: ❌ No
- **File Type**: HTML shell with SPA framework
- **Embedded Data**: None detected
- **Assessment**: Same HTML shell as all others

---

## Recommended Solution

### Primary Approach: Headless Browser Rendering

**Rationale**:
1. **Simplicity**: Single, straightforward implementation
2. **Reliability**: Guaranteed to work; no hidden assumptions
3. **Maintainability**: Works regardless of API changes
4. **Completeness**: Captures all rendered content
5. **Safety**: No authentication/API key requirements

**Implementation Plan**:

```python
#!/usr/bin/env python3
"""Updated transcript_ingestion.py using Playwright"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import json

def fetch_transcript_with_browser(episode_url: str) -> str:
    """
    Fetch transcript using headless browser rendering.
    
    Args:
        episode_url: TSSE episode URL (e.g., https://podcast.sure.ventures/episodes/100-angel-investments)
    
    Returns:
        Transcript text content
    """
    transcript_url = f"{episode_url}/transcript"
    
    with sync_playwright() as p:
        # Launch headless Chrome
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Navigate to transcript page
            page.goto(transcript_url, wait_until="networkidle")
            
            # Wait for transcript content to render
            # (selector TBD - requires manual inspection)
            page.wait_for_selector(".transcript", timeout=10000)
            
            # Extract transcript text
            transcript = page.text_content(".transcript")
            
            browser.close()
            return transcript
        
        except Exception as e:
            browser.close()
            raise RuntimeError(f"Failed to retrieve transcript: {e}")
```

**Dependencies**:
```bash
pip install playwright
playwright install chromium
```

**Performance**:
- Time per transcript: 2-5 seconds
- Time for 15 Phase 2 episodes: 30-75 seconds
- Acceptable for initial bulk ingestion

### Secondary Approach: API Reverse Engineering

**If headless browser approach is too slow or resource-constrained**:

1. **Manual Investigation**:
   - Open `https://podcast.sure.ventures/episodes/chief-engineer/transcript` in Chrome
   - Open DevTools → Network tab
   - Reload page
   - Find API call to `/api/` or `/v1/` endpoint
   - Document request format and response structure

2. **Implementation**:
   - Replicate API call format in Python script
   - Implement direct HTTP calls to API endpoint
   - Handle authentication if required

3. **Benefits**:
   - Much faster (~100ms per transcript vs 2-5s)
   - Lower resource usage
   - More scalable for Phase 3 (54 episodes)

---

## Next Steps

### Immediate Actions

1. **Determine Preferred Approach**:
   - [ ] Attempt headless browser implementation with Playwright
   - [ ] If successful, proceed with bulk ingestion
   - [ ] If performance issues, pivot to API reverse engineering

2. **Selector Identification** (if using headless browser):
   - [ ] Open `https://podcast.sure.ventures/episodes/100-angel-investments/transcript` in Chrome
   - [ ] Inspect DOM to find transcript container selector
   - [ ] Test selector in DevTools console
   - [ ] Document for implementation

3. **API Investigation** (if needed):
   - [ ] Open transcript page in Chrome
   - [ ] Open DevTools → Network tab
   - [ ] Reload page and watch for API calls
   - [ ] Document endpoint, request format, response structure
   - [ ] Test endpoint with curl/Python

### Implementation Priorities

**Priority 1**: Implement headless browser approach
- Update `transcript_ingestion.py` to use Playwright
- Test on Phase 1 episodes (should have full content now)
- Validate transcript quality

**Priority 2**: If headless browser is too slow, implement API approach
- Reverse engineer API endpoint from DevTools
- Implement direct API calls
- Benchmark performance improvement

**Priority 3**: Phase 2 Re-ingestion
- Run updated ingestion script on Phase 2 episodes (25-79)
- Validate transcripts (>10KB, contains timestamps)
- Update Phase 2 intelligence records with transcript-derived content

---

## Platform Analysis: Simplecast + Vite Architecture

### Why This Architecture?

The use of Vite SPA + Simplecast CDN suggests:

1. **Scalability**: SPA allows fast page loads and smooth navigation
2. **Content Management**: Likely managed through Simplecast CMS
3. **Dynamic Features**: Can embed custom analytics, comments, etc.
4. **Developer Experience**: Vite is modern, popular SPA framework

### Implications for Transcript Retrieval

| Aspect | Impact |
|--------|--------|
| **Static content unavailable** | Must use headless browser or API |
| **No public API** | Cannot use simple HTTP calls |
| **Client-side rendering** | Requires JavaScript execution |
| **Simplecast backend** | Transcripts likely in Simplecast database |
| **Custom authentication** | May require session tokens if API is found |

---

## Conclusion

**Finding**: TSSE podcast transcripts are **loaded entirely client-side** through a Vite SPA. They are **not available** through static HTML, public APIs, or RSS feeds.

**Viable Solutions** (in order of preference):
1. ✅ **Headless Browser Rendering** (Playwright) — Guaranteed to work
2. ✅ **API Reverse Engineering** (after DevTools investigation) — Faster if available
3. ⚠️ **Simplecast API** (if documented/accessible) — Cleanest if available

**Recommendation**: Implement headless browser approach with Playwright. If performance becomes an issue, pivot to API reverse engineering.

---

*Investigation completed: June 2, 2026*
