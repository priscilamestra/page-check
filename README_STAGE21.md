# Page Check — Stage 21 technical readiness patch

**Incremental files only.** Extract into the repository root; preserve all existing project files.

Contents:
- `src/pagecheck/integrations/impeccable/contract_probe.py`: strict, privacy-preserving schema introspection;
- `scripts/impeccable_contract_probe.py`: offline probe for locally installed Impeccable;
- `src/pagecheck/common/security/vercel_readiness.py`: explicit deployment blockers;
- `scripts/vercel_deploy_preflight.py`: read-only preflight, optional `--strict` CI gate;
- `tests/unit/`: 13 additional tests;
- `docs/STAGE21_VERCEL_TECHNICAL_CLOSURE.md`: Vercel migration design and deployment constraints.

No UI, database, router, or security defaults are overwritten. This patch does **not** turn public URL auditing on in production. Do not deploy yet.

## Windows PowerShell

```powershell
Expand-Archive -Path "$HOME\Downloads\PageCheck_Etapa21_Diagnostico_Impeccable_Preflight_Vercel.zip" -DestinationPath . -Force
uv run pytest tests/unit/test_impeccable_contract_probe_stage21.py tests/unit/test_vercel_readiness_stage21.py -v
uv run pytest -q
uv run python scripts/impeccable_contract_probe.py
uv run python scripts/vercel_deploy_preflight.py
```

If your checked-in base currently has 426 passing tests, the expected total after this patch is **439**.

No new pip package dependencies. No Git commit until the full test suite passes in the real project.
