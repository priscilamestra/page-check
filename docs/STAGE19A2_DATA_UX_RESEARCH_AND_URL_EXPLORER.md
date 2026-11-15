# Stage 19A2 — Data-first UX correction

## Problem and user goal

The Page Check must support **get a practical answer and leave** (general user), while preserving **search, comparison, evidence, and export** (analyst). In Stage 19A the URL & parameters tab rendered every navigation/tracking/form check as a separate bordered card. Sites with hundreds of checks produced unreasonably long pages. The Overview's per-area bars were also misleading for low counts: one check in a category produced a full-width bar.

## Research principles

- Microsoft Power BI dashboard design tips: prioritize decision-critical facts, avoid unnecessary scroll, choose the right visualization, and preserve scales, labels, and color semantics. https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips
- Nielsen Norman Group's *Data Tables: Four Major User Tasks*: tables help finding, comparing, inspecting, and acting on records. https://www.nngroup.com/articles/data-tables/
- Nielsen Norman Group's *Progressive Disclosure*: show essential content by default and advanced detail when requested. https://www.nngroup.com/articles/progressive-disclosure/
- CDC *Stacked Bar Chart*: proportional, part-of-whole views work best on a clear 100% denominator. https://www.cdc.gov/cove/data-visualization-types/stacked-bar-chart.html
- Microsoft *Design Power BI Reports for Accessibility*: use meaningful labels, avoid color as the sole communication channel. https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-accessibility-creating-reports

## Implemented Stage 19A2 behavior

1. **URL & parameters**: URL query parameter count and UTM count; absence of UTM is presented as neutral. No analytics event-delivery claim. Values of suspicious credentials are masked in the default UI.
2. **Check summary**: three rows for Tracking, Navigation, and Forms; columns for issues, needs review, not verified, passed, not applicable. Counts are kept separate so an unverified link is not mistaken for a broken link.
3. **Explore all checks**: default view only shows issues and reviews; optional area/status/search filters. All checks remain available, within a **350-pixel-high** grid rather than hundreds of cards.
4. **Evidence by selection**: only selected check displays its recommendation; JSON is behind one advanced expander. No check data or technical evidence is deleted from the underlying report, SQLite, or exports.
5. **Findings by area**: replace full-width bars for small counts with a compact table showing exact issue/review counts. One issue should never look like 100% severity.
6. **Audit source coverage**: use **one** 100%-stacked composition bar, where all segments sum to the seven source statuses; show all status names and counts directly in the legend.
7. **Unverified checks**: show counts and fractions of the *unverified subset*, clearly separate from actionable findings; avoid visually equating 242 unverified navigation checks with 242 page defects.

## Acceptance checks

- A 250-check audit displays **no per-check cards** in the URL tab by default.
- Its default visible list contains only issues/reviews, not 242 repetitive unverified checks.
- The URL tab remains bounded by the 350 px detailed grid; filtering still exposes every original check.
- No UTM query parameters is not automatically a defect.
- Technical evidence is available for a **selected check only**.
- The report schema and audit backends remain unchanged.
- All visible UI prose remains in English.
- Existing Stage 19A tests continue to pass, along with Stage 19A2 helper tests.

## Later UX work (not in this patch)

Issue cards (19B), screenshot annotations (19C), deployment/security testing, keyboard and screen-reader UX. The static-browser and Lighthouse restrictions remain in effect.
