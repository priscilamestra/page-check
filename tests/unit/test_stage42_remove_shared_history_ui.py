"""Stage42: no history-list UI, production recovery is browser-token scoped."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src/pagecheck/ui/app.py"
HISTORY = ROOT / "src/pagecheck/api/routes/history.py"
TEMP = ROOT / "src/pagecheck/api/routes/temporary.py"
BROWSER = ROOT / "src/pagecheck/ui/browser_recovery.py"


def test_saved_history_control_is_removed_in_every_environment():
    source = UI.read_text(encoding="utf-8")
    ast.parse(source)
    assert "Saved audits · local history" not in source
    assert "Open saved audit" not in source
    assert "Choose a saved audit" not in source
    assert "Delete saved audit" not in source
    assert "_history_items(" not in source
    assert "st.expander(\"Saved audits" not in source


def test_production_always_uses_browser_private_recovery_even_without_storage_variable():
    tree = ast.parse(UI.read_text(encoding="utf-8"))
    render = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "render_app")
    assignment = next(node for node in ast.walk(render) if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "use_postgres" for t in node.targets))
    assert ast.unparse(assignment.value) == "is_production or storage_backend == 'postgres_temporary'"
    source = UI.read_text(encoding="utf-8")
    assert "save_temporary(" in source
    assert "restore_temporary(" in source
    assert "browser_recovery(" in source
    assert "pagecheck_browser_set" in source


def test_local_history_api_is_disabled_outside_local_development():
    source = HISTORY.read_text(encoding="utf-8")
    assert 'if not is_local_development():' in source
    assert 'raise HTTPException(503, "Local history is disabled outside development.")' in source
    assert source.count("dependencies=[Depends(_local_only)]") >= 5


def test_hosted_recovery_is_private_and_has_no_global_listing():
    source = TEMP.read_text(encoding="utf-8")
    assert "Depends(require_private_service)" in source
    assert 'prefix="/v1/temporary"' in source
    assert '@router.get(' not in source
    browser = BROWSER.read_text(encoding="utf-8")
    assert "localStorage" in browser
    assert "?audit=" in browser  # Only referenced as a design warning, not generated URL.
    ui = UI.read_text(encoding="utf-8")
    assert 'del st.query_params["audit"]' in ui
