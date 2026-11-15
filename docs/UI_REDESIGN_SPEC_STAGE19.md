# Stage 19 — Final visual redesign specification (after technical stabilization)

## Product goal
A non-technical Growth/Marketing user should understand: what is wrong, why it matters, what to fix first, what was actually inspected, and which visual evidence exists. English-only UI. Preserve deterministic analysis and honest statuses.

## Layout & navigation
- **No permanent left sidebar.** Upper-right in-app **Connection & tools** icon/popover, near but not embedded in Streamlit's native toolbar.
- The popover houses API connection and Developer tools (local only). Preserve `Load sample report` in local mode. In production, the top control is `Connection` and Developer tools are hidden via `PAGECHECK_ENV=production`; guard backend dev-only functionality independently. Do not add an account, sign-in, or login interface.
- Wide responsive content with legible card density; on mobile, collapse to one column.
- History list: `MM/DD/YYYY · h:mm AM/PM (browser timezone) · domain/path · status`. Retain F5 persistence and show date/time timezone, not server UTC.

## Overview ordered by decision value
1. **Audit summary**: audited URL + goal, measured SEO score with scored-rule coverage and explicit exclusions. Separate main findings count from checks that could not run.
2. **Top actions**: highest priority problems first, without a severity picker. Each card shows title, affected area, reason, business implication, recommended action, verification/source, and link to underlying evidence.
3. **Visual evidence**: real desktop/mobile image(s), viewport-only images visibly labelled **Partial visual evidence** when full-page capture blocked. Annotate *only* directly observed issues; never invent red boxes.
4. **Meaningful charts** (not mixed-category hover-dependent stacks):
   - **Actionable findings by area**: separate single-purpose horizontal bars with visible count and type (critical issue vs needs review), predictable scale, and link to corresponding Issues cards.
   - **Audit source coverage**: source cards Completed / Limited / Not verified, with readable explanation and measured scope; show summary `3 completed / 2 limited / 2 not run` for the specific report when true.
   - **Not verified**: secondary chart/table grouped by area (e.g. 242 navigation checks), separate from defects; deduplicate/aggregate repeated elements rather than visually showing 242 independent page failures.
   - Avoid any chart that requires hover to understand its axes, units, legend or actual numbers.
5. **Technical evidence**: JSON, selectors, HTTP traces, and scanner limitations in closed expanders or Data tab for developers.

## Issues & exports
- Default Issues view: actionable summary first, source and raw JSON collapsed. Label `Needs review` distinctly from confirmed failure; `Not applicable` does not count as failure.
- Plain-English calls to action: what, why, fix, confidence/evidence and owners, no fabricated severity when tool has only static evidence.
- Exports must keep accurate status and original evidence references.

## Acceptance tests
- Users understand 100/100 SEO vs 246 Not verified without being told 246 errors.
- 3 primary charts answer distinct questions at a glance; labels and counts visible without hover.
- Lighthouse and Impeccable statuses visible without JSON access; tool failures never converted into Passed.
- History dates change with browser timezone and preserve the same underlying instant.
- Do not imply that sign-in or account access exists. No login interface in this release.
- Audit same saved report on mobile and desktop; F5 restores selection/report; no duplicate history entries.
- No unsafe navigation/remote resources enabled to make charts or screenshots look complete.
