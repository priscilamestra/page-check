"""Entrypoint local da API FastAPI do Page Check.

Execução: uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
"""
from pagecheck.api.app import app
