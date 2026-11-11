# Etapa 7 — Auditoria SEO na FastAPI

## Rota nova

`POST /v1/audits/seo`

Entrada:

```json
{"url":"https://example.com", "niche":"Tecnologia / SaaS", "objective":"leads"}
```

Objetivos permitidos: `leads`, `meetings`, `sales`, `signup`, `organic_traffic`.

Saída: `requested_url`, `final_url`, `status_code`, `redirects`, `niche`,
`module`, `ruleset_version`, `objective`, `score`, `coverage`, `partial_score`,
`checks_executed`, `checks_applicable`, `checks` e `findings`.

- O fetcher é chamado **uma única vez** e o parser fornece **HTML completo** às regras.
- `niche` é preservado como contexto para módulos futuros, mas ainda não influencia a nota SEO.
- A nota é de conformidade técnica **do Page Check**, não é ranking do Google.
- A rota anterior `/v1/pages/inspect` foi preservada.
- Requisições externas ficam desabilitadas por padrão; apenas desenvolvimento local
  pode usar `PAGECHECK_ALLOW_LIVE_FETCH=1`. Não publicar em rede aberta sem
  autenticação, limitação de uso e revisão de SSRF, redirecionamentos e DNS.
- Ainda não há navegador Playwright, auditoria visual, ou avaliação de nicho.

## Testes locais

```powershell
uv run pytest tests/unit/test_audit_seo_page.py tests/unit/test_seo_api.py -v
uv run pytest -q
```

Para testar manualmente, reinicie **somente** a FastAPI no terminal local:

```powershell
$env:PAGECHECK_ALLOW_LIVE_FETCH="1"
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000/docs`, selecione `POST /v1/audits/seo` e execute
com os dados de entrada acima. Não use URLs de redes locais ou privadas.

## Arquivos afetados

- **Alterado:** `src/pagecheck/api/app.py` (registro de rota).
- **Novos:** `src/pagecheck/api/routes/seo.py`, `src/pagecheck/api/schemas/seo.py`,
  `src/pagecheck/application/use_cases/audit_seo_page.py`, dois testes e este documento.
- Não modificar `main.py`, `streamlit_app.py`, parser, fetcher ou regras SEO.
