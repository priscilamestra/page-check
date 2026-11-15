# Page Check — Stage 19A: Executive Overview and chart redesign

This is a **UI-only incremental update**, intended to overlay the tested Stage 18B files. No audit rule, score formula, HTTP access policy, SQLite schema, export contract, or deployment control is changed.

## What changes

- The heading metrics show **Technical SEO scored rules**, **Issues found**, **Needs review**, and **Sources completed**. The count of unverified checks is explained separately instead of being presented next to actual defects as though it were another quality score.
- **Fix these first** highlights up to three priority findings; each shows classification, affected area, general (qualified) impact, recommendation and responsible team. All findings remain accessible in **Issues**, preserving their raw evidence. No severity filter.
- **Visual evidence** previews existing desktop/mobile screenshots when available. First-viewport-only captures are explicitly labelled partial; unavailable images are **not** treated as passing checks. The full Screenshots tab is unchanged.
- **Actionable findings by area** is a single-measure horizontal bar chart. Every bar has its area and visible numeric breakdown (`1 issue · 2 reviews`). Nothing requires a hover, and Passed/Not verified are excluded.
- **Source coverage** shows seven existing source cards with completed/limited/not-verified states, plus a separate three-bar status graphic. Explanatory details are collapsed within each card. Failed engine output does **not** become Passed.
- **Checks without enough evidence** is a different chart that displays not-verified check counts by area, without misrepresenting them as page defects. A high count (e.g. 242 navigation checks) cannot inflate the actionable chart.
- **Technical coverage JSON** remains available in a closed expander and raw results remain in Data.
- The upper-right **Tools** popover is narrower; it still contains FastAPI connection state and the local-only Developer tools, including **Load sample report**. No sidebar, login, user account, or new authentication.

## Existing functionality intentionally unchanged

- User/browser timezone in Saved audits (`MM/DD/YYYY · local time`) and F5 restoration.
- History save/open/delete, export JSON/CSV/ZIP and screenshot paths.
- SEO scoring rules, status semantics, target keywords and language selection.
- Browsing remains conservative: no JavaScript is enabled in public static audit runs; Lighthouse is not activated for arbitrary public URLs.
- `PAGECHECK_ENV=production` continues to hide the local Developer tools in the UI. This is **not** a security boundary: backend development endpoints and network isolation still require security verification prior to deployment.

## Installation (PowerShell from Page Check repository root)

```powershell
Expand-Archive -Path "$HOME\Downloads\PageCheck_Etapa19A_Overview_Graficos.zip" -DestinationPath . -Force
uv run pytest tests/unit/test_overview_insights_stage19a.py -v
uv run pytest -q
```

Do **not** commit before checking the complete suite on the user's local repository. If the Stage 18B baseline was 321 passing tests, the expected total after 23 new tests is **344**.

Restart the Streamlit server after changing code. The FastAPI server does not need changed flags for this UI-only patch.

## Visual acceptance checklist

1. Open the existing saved **HubSpot** audit without re-running it. The metrics should show `100/100` for scored SEO, 1 issue, 3 reviews, and 3/7 completed sources for that saved report.
2. The first priority should be the *Buttons must have discernible text* finding. The Overview should explain that the result comes from static evidence, not measured behavior.
3. **Actionable findings by area** should show `SEO: 2 reviews`, `Accessibility: 1 issue`, `Navigation: 1 review`, with visible text labels without hover.
4. **Source coverage** should show `3 Completed / 2 Limited / 2 Not verified` for the later HubSpot audit. If another report is opened, counts should change accordingly.
5. **Checks without enough evidence** should display `Navigation: 242` separately from the four actionable findings and explain that this does not represent 242 confirmed defects.
6. Existing partial first-viewport desktop/mobile screenshots should remain labelled partial; if the saved image is missing, the UI should say unavailable, not completed.
7. The compact Tools popover should not obscure the form while closed. The local Developer tools should still provide **Load sample report** and never show login.
8. Reopen another saved audit and press F5. Verify saved selection, local-time history labels, report, exports and original source status values remain intact.

## Planned next steps

- **19B:** Simplify Issues cards, explanations and actions, with clearer confidence/source and only-on-demand technical evidence.
- **19C:** Screenshot evidence and annotation navigation; only annotate objectively detected issues.
- **19D:** End-to-end responsive visual verification, regression tests, security and deployment readiness assessment.

Stage 19A does not claim to fix the existing Impeccable `EngineOutputError` on the HubSpot audit or to add public-site Lighthouse execution. Those remain separately verifiable technical tasks.
