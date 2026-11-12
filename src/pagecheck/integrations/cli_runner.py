"""Executa apenas comandos locais fixos; sem download automático via npx."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Callable

from pagecheck.integrations.engine_result import EngineOutputError, unavailable


def local_binary(project_root: Path, package: str) -> Path | None:
    """Aceita somente binário local instalado em node_modules/.bin."""
    if package not in {"lighthouse", "impeccable"}:
        raise ValueError("Ferramenta não permitida.")
    suffix = ".cmd" if os.name == "nt" else ""
    candidate = project_root.resolve() / "node_modules" / ".bin" / (package + suffix)
    return candidate if candidate.is_file() else None


def run_local_json_command(engine: str, command: list[str], *, root: Path,
                           timeout: int = 90,
                           run: Callable = subprocess.run) -> dict:
    """Resultado de execução, sem interpretar stdout como sucesso quando há falha."""
    if engine not in {"lighthouse", "impeccable"}:
        raise ValueError("Motor não permitido.")
    if timeout < 1 or timeout > 120:
        raise ValueError("Timeout fora do limite.")
    try:
        completed = run(command, cwd=str(root.resolve()), capture_output=True,
                        text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return unavailable(engine, f"Execução indisponível: {type(exc).__name__}")
    valid_codes = {0, 2} if engine == "impeccable" else {0}
    if completed.returncode not in valid_codes:
        return unavailable(engine, f"Falha na ferramenta (exit {completed.returncode}).")
    try:
        payload = json.loads(completed.stdout)
    except (ValueError, TypeError) as exc:
        return unavailable(engine, f"Saída não era JSON válido ({type(exc).__name__}).")
    from pagecheck.integrations.impeccable.adapter import normalize_impeccable
    from pagecheck.integrations.lighthouse.adapter import normalize_lighthouse
    try:
        return (normalize_impeccable(payload) if engine == "impeccable"
                else normalize_lighthouse(payload))
    except EngineOutputError as exc:
        return unavailable(engine, f"Formato inesperado: {exc}")
