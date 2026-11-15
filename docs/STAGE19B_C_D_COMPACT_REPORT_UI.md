# Page Check — Stage 19B/19C/19D: compact report experience

## Product contract

The Page Check dashboard is a **rapid, visual decision aid**, not a raw dump of all audit records. People who need technical depth can inspect an individual item or export all data. This patch does **not** change the meaning of source checks, SEO scores, HTML analysis, the SQLite schema, or browser restrictions.

The three information levels are:

1. **Summary** — top findings, counts and honest coverage statuses in Overview.
2. **Explore** — bounded, filterable tables and side-by-side screenshot panes in the relevant tabs.
3. **Verify** — technical source/evidence only after selecting an item, plus original JSON, CSV, ZIP exports.

## Included

- **Stage 19A2 included for convenience:** compact `URLs & parameters` and clearer quantitative Overview. Its previous 17 tests are included in this ZIP so it can be applied over Stage 19A even if 19A2 was not installed separately.
- **Stage 19B — Issues:** issue vs review vs unverified kept distinct, four metrics, filters (area, result, priority), search, table max 400px, one selected detail panel; raw evidence behind an expander. No loop that produces one card for each finding.
- **Stage 19C — Screenshots:** desktop and mobile previews are side by side, each limited to 360px height. The original screenshot files remain unchanged. A first-viewport capture is labeled partial evidence, not a passing full visual audit. No marker is invented for an image without annotations. The original screenshots are still present in audit export/history.
- **Stage 19D — Teams:** count actions from actual records, show a compact summary per team, filters, table max 380px, and one selectable detail. Never expand hundreds of task cards automatically.
- **Data:** raw consolidated JSON remains behind an advanced expander, exports remain unchanged.

## Install (from project root; do not copy the parent folder)

In VS Code PowerShell, stop Streamlit (`Ctrl+C`) before extraction:

```powershell
Expand-Archive -Path "$HOME\Downloads\PageCheck_Etapa19_Abas_Compactas_Entrega_UI.zip" -DestinationPath . -Force
uv run pytest tests/unit/test_url_explorer_stage19a2.py tests/unit/test_issues_explorer_stage19b.py tests/unit/test_visual_explorer_stage19c.py tests/unit/test_teams_explorer_stage19d.py -q
uv run pytest -q
```

**Expected total:** If the project contained 344 tests at the end of Stage 19A, it should now have **394** tests (17 Stage 19A2 + 18 Stage 19B + 7 Stage 19C + 8 Stage 19D). This assumes the baseline was unchanged and all 50 new tests were not already installed. If Stage 19A2 was previously installed, only 33 tests are new and 361 → 394. Verify the actual total in the user's repository.

Reopen the saved HubSpot audit; no new web audit is necessary. Confirm:

- Overview counts are consistent with the source report; the three top findings remain prioritized.
- URLs & parameters renders a short summary and a **bounded table**, not hundreds of open JSON cards. All checks remain filterable and exportable.
- Issues uses filters and a single selected detail; selecting a `Needs review` item does not turn it into a confirmed defect.
- Screenshots shows desktop/mobile in panes and explains partial captures.
- Teams uses a compact action table and does not expand all tasks at once.
- Data still offers full JSON, CSV and ZIP exports.

Do **not** commit without local validation. Inspect `git diff --stat`, `git diff --check`, and `git status --short` first.

## Validation and deployment boundary

Pure transformations and local UI-data regressions were tested in the reconstructed copy. The reconstructed copy lacks some early modules in the user's original repository, so full-suite and interactive Windows Streamlit testing remain required. No production deployment is included here. **Production browser/network isolation, authentication policy if needed, and the Impeccable format issue are separate unresolved tasks.** UI concealment of Developer Tools is not a security boundary.
