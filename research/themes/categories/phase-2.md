# Phase 2 specification · public category browser

**Prerequisite.** An editor records approval, revision or rejection for each membership and public excerpt in scope. Each approval names the reviewer, date, classification version and evidence fingerprint. Theme publication also requires approval of the theme itself and its category link. Versioned definition approval alone enables planning.

## Release data

Have a build step read an immutable approved release, join on stable category and episode IDs, verify transcript and note locators against the target archive and compute unique approved episode counts. Produce one small homepage index and a detail payload per approved category slug. Publish only approved members and display-safe excerpts. Hide empty theme groups; a category can work without editorial subthemes. Flag stale evidence for re-review and retain the last valid release. Keep reviewer notes private.

## Homepage and routes

Extend the existing homepage with **Explore by theme** above the chronological archive list. Use all nine categories in approved display order. Give each card a heading, the approved description, one descriptive link and an optional count from the same release used by the category page. Retain existing search, URL parameters and chronological browsing. A category with no approved episodes can show an informative empty state.

Use `/categories/<slug>` for category detail and reserve `/themes/<slug>` for independently approved editorial themes. Extend the existing route parser and host rewrite so direct links, reload, browser back and prior search state work. Keep existing episode, transcript and show-note routes as the source destinations.

## Category page

Use one heading and the approved description. Sort strong episodes before secondary by default, then newest first within strength. Offer newest/oldest sorting. Show episode title, publication date, original source and a link to its transcript. Present approved representative passages with exact text, a source link and genuine time labels where available. An unattributed passage can display “Speaker unknown” when the editor approves its use. Render specific recurring questions under **Editorial themes**. Related categories can link via shared approved episodes. Show the basis for a connection and avoid inferring new themes from keywords.

## Delivery and acceptance

Use current TSSE typography, color, spacing and existing episode-link components. Load homepage cards eagerly and detail data on navigation. Paginate the episode list or progressively load subsequent pages. Use semantic lists and headings, visible keyboard focus, native links and a single reading column on narrow screens. Check card-name wrapping, zoom, keyboard-only navigation, screen-reader link names and the rendering of long transcript excerpts.

Exercise release approval filters, exact evidence hashes, multi-category counts, empty categories, absent speaker/timestamp, related unpublished themes, mobile layout, direct reload and browser back. Check search and chronological browsing with the existing HTTP and deployment regression suites. Implement and release only after explicit Phase 2 authorization.
