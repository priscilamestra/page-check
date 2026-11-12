# Page Check — Etapa 16: Dashboard Streamlit

## Escopo desta etapa

O Streamlit apresenta dados do contrato `audit-report-1.0` e oferece três entradas:

1. **Auditoria SEO real:** URL, nicho e objetivo enviados ao endpoint existente `POST /v1/audits/seo`. O resultado é adaptado pelo consolidador da Etapa 15 e fica **parcial**: outros módulos não são executados nem recebem aprovação automática.
2. **Carregamento de JSON consolidado:** permite visualizar um relatório previamente gerado. Limite de 5 MB, validação mínima do contrato e nenhum arquivo enviado é executado ou salvo no disco.
3. **Demonstração offline:** carrega `artifacts/consolidation_stage15/consolidated_audit.json`, criado pelo script de smoke anterior. É dado de referência, **não** uma auditoria de uma landing page real.

## Interface

- Três campos de entrada: **URL, nicho, objetivo**.
- KPIs: score SEO interno, problemas, alertas e verificações não realizadas.
- **Resumo:** notas Lighthouse, quando presentes, e barras por módulo.
- **Problemas:** achados ordenados, evidências e recomendações em painéis expansíveis.
- **Capturas:** screenshots somente quando vinculados ao relatório; arquivo PNG deve estar dentro de `artifacts/`.
- **Equipes:** ações atribuídas aos responsáveis, prontas para encaminhamento.
- **Dados:** exportação JSON e inspeção do relatório consolidado.

## Arquivos alterados

- **Substituído:** `src/pagecheck/ui/app.py` (antes era apenas o shell com /health).
- **Novos:** `src/pagecheck/ui/components/{__init__.py,report_data.py,report_view.py}`.
- **Novos:** `tests/unit/test_report_data.py`, `docs/UI_STAGE16.md`.
- **Preservados:** `streamlit_app.py`, FastAPI, fetcher, parser, motores de auditoria e consolidador.

## Executar

Terminal 1 (FastAPI):

```powershell
$env:PAGECHECK_ALLOW_LIVE_FETCH="1"  # APENAS desenvolvimento local
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 (Streamlit):

```powershell
uv run streamlit run streamlit_app.py
```

Abrir: `http://localhost:8501`.

Para ver a demonstração, primeiro rode:

```powershell
uv run python scripts/consolidation_fixture_smoke.py
```

Depois clique em **Carregar demonstração da Etapa 15** na interface.

## Testes

```powershell
uv run pytest tests/unit/test_report_data.py -v
uv run pytest -q
```

> **Limites:** não há ainda orquestrador que execute SEO, conversão, Playwright, Lighthouse, axe-core e Impeccable numa única chamada da interface. Isso é trabalho da integração final, não deve ser simulado por dados de referência. O histórico e as exportações avançadas ficam para a Etapa 17. O modo live segue restrito ao seu computador; não publicar com `PAGECHECK_ALLOW_LIVE_FETCH=1` sem revisão de SSRF, isolamento e cotas.
