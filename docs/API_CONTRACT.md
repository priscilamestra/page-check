# Contrato da API — Page Check (bootstrap + proposta)

**Implementado agora:** `GET /health`. **Planejado:** endpoints de auditoria com prefixo `/v1`. FastAPI e Streamlit são processos separados. A UI chama apenas endpoints HTTP; os motores não são importados pela UI.

## Endpoints

| Método | Rota | Finalidade |
|---|---|---|
| `GET` | `/health` | **Implementado** — saúde da API |
| `POST` | `/v1/audits` | Validar entrada, criar audit_id e agendar job |
| `GET` | `/v1/audits/{audit_id}` | Estado, metadados, cobertura, scores e findings |
| `GET` | `/v1/audits` | Histórico paginado |
| `GET` | `/v1/audits/{audit_id}/artifacts/{name}` | Screenshot/relatório autorizado do audit_id |
| `GET` | `/v1/audits/{audit_id}/export?format=json|csv|html_zip` | Exportação final |

As rotas `/v1/audits` ainda NÃO estão implementadas nesta entrega. Em desenvolvimento local, API bind em `127.0.0.1` por padrão. Não expor endpoints públicos de auditoria arbitrária sem autenticação e proteção adicional.

## Entrada exemplo de POST /v1/audits

```json
{
  "url": "https://example.org/landing-page",
  "niche": "SaaS B2B",
  "objective": "leads",
  "viewports": ["desktop", "mobile"]
}
```

Resposta inicial `202 Accepted` (proposta):

```json
{
  "audit_id": "uuid-gerado-pelo-servidor",
  "status": "queued",
  "status_url": "/v1/audits/uuid-gerado-pelo-servidor"
}
```

Resposta final resumida:

```json
{
  "audit_id": "uuid-gerado-pelo-servidor",
  "status": "completed",
  "requested_url": "https://example.org/landing-page",
  "final_url": "https://example.org/landing-page",
  "niche": "SaaS B2B",
  "objective": "leads",
  "ruleset_version": "1.0.0",
  "modules": [
    {
      "name": "seo",
      "score": 80.0,
      "coverage": 1.0,
      "checks_executed": 5,
      "checks_applicable": 5
    }
  ],
  "findings": [
    {
      "finding_id": "finding-001",
      "check_id": "SEO_TITLE",
      "module": "seo",
      "status": "failed",
      "severity": "medium",
      "title": "Title ausente",
      "team": "SEO / Conteúdo",
      "evidence": {"source": "beautifulsoup", "observed_value": null},
      "recommendation": "Adicionar um título descritivo na página."
    }
  ],
  "artifacts": {"desktop_screenshot": null, "mobile_screenshot": null}
}
```

Esses valores são exemplos de schema, **não resultados de auditoria real**.

## Falhas

- `400`: dados malformados / objetivo inválido.
- `403`: destino bloqueado pela política de rede.
- `404`: auditoria ou artefato inexistente.
- `409`: auditoria ainda não finalizada para exportação.
- `422`: validação Pydantic (FastAPI).
- `429`: limite de jobs/uso.
- `500`: falha controlada do serviço; mensagens internas não expostas.

Jobs parciais retornam `status=partial`, e cada módulo indica `not_verified`/erro apropriado. Não esconder falha de Lighthouse, axe ou Impeccable.

## Modelo lógico de persistência

- `audits`: id, input, timestamps, state, version, scores/cobertura resumidos.
- `findings`: id, audit_id, module, check_id, status, severity, evidence_json, recommendation, team, viewport.
- `artifacts`: id, audit_id, type, relative_path, mime, size, checksum.
- `engine_runs`: audit_id, engine, version, started_at, finished_at, status, log limitado.

Imagens e HTML em diretório local ignorado por Git; no banco apenas metadados e caminhos relativos controlados.
