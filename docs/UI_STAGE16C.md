# Page Check — Stage 16C: English UI and multilingual content targeting

## What changed

- **English-only controls and primary reports.** All main Streamlit labels, actions,
  explanations, statuses, and severity badges are in English.
- **Content language:** English (`en`), Portuguese (`pt`), or Spanish (`es`).
  This chooses the language against which `html[lang]` is checked. It does **not**
  translate the inspected page or change the application's interface language.
- **Industry or niche:** free text, neutral placeholder, no preset examples.
- **Target keywords:** type and press **Enter** to create removable tags, up to eight.
  At least one keyword is required by the Streamlit form. Older API clients remain
  compatible because the HTTP endpoint accepts an empty keyword list.
- **Additional deterministic guidance:** review `html[lang]`, find user-supplied
  phrases in the page title, description, H1, and visible body copy, and observe the
  broad niche phrase when present. Missing niche text is `not_verified`, not a failure.
- **Original SEO technical score is unchanged.** Keyword guidance is an advisory SEO
  check, not a prediction of Google rankings or search volume. No paid API, generative
  AI, SERP query, or external keyword-research service is used.
- **Issue priority badges:** visible immediately, sorted by the existing backend
  priority; detailed evidence is available only by expanding the issue.
- **Clearer disabled-fetch message** when the API's live-network opt-in is not enabled.

## File structure (only these files are included)

- `src/pagecheck/ui/app.py` (updated)
- `src/pagecheck/ui/components/report_data.py` (updated; UI labels)
- `src/pagecheck/ui/components/report_view.py` (updated)
- `src/pagecheck/reporting/english_copy.py` (new)
- `src/pagecheck/api/schemas/audit.py` (updated)
- `src/pagecheck/api/routes/audit.py` (updated)
- `src/pagecheck/application/use_cases/audit_page_html.py` (updated)
- `src/pagecheck/audits/seo/content_guidance.py` (new)
- `tests/unit/test_content_guidance.py` (new, 13 tests)
- `docs/UI_STAGE16C.md` (this file)

Existing network guards, browser safety, and all previous routes remain intact.
Stage 16C **does not** add screenshot collection to the combined HTML audit.

## Apply in Windows PowerShell (repository root)

```powershell
# First, commit Stage 16B if its files are still pending.
Expand-Archive -Path "$HOME\Downloads\PageCheck_Etapa16C_English_Keywords.zip" -DestinationPath . -Force
uv add "streamlit>=1.45,<2"
uv run pytest tests/unit/test_content_guidance.py -v
uv run pytest -q
```

Expected on the full local 222-test repository: **235 passed** (13 new).
The smaller reference copy used for package validation passed **202 tests**.

`st.multiselect(accept_new_options=True)` requires Streamlit 1.45 or newer.

## Restart the backend for a live local test

In the terminal running Uvicorn, press `Ctrl+C` to stop it. Then run **in that
same PowerShell terminal**:

```powershell
$env:PAGECHECK_ALLOW_LIVE_FETCH="1"
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
uv run streamlit run streamlit_app.py
```

Open <http://localhost:8501>. You can inspect a page whose content language and
keywords match what you enter. If an older Uvicorn process is still running,
setting an environment variable in a different terminal will not enable it.

**Do not enable live fetching in a public deployment.** A public URL auditing
service still requires additional browser/network isolation, rate limits, and
operational controls.

## Limits / next step

- No external keyword popularity, organic ranking, or topic search is performed.
- Contextual SEO checks use **accent-insensitive word and phrase matching**.
  The user-provided niche can be expressed differently than the site's wording;
  nonmatches cannot be classified conclusively without semantic analysis.
- The combined HTML API translates the known audit rule messages to English,
  while preserving technical identifiers and unmodified evidence. Older imported
  reports can retain their original raw source messages.
- Current audit still checks only HTML; subsequent work will connect the already
  built browser/visual engines and safely test applicable navigation targets.
