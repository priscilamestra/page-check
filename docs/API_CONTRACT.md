# Contrato atual da API local

FastAPI e Streamlit são processos separados. A UI usa `PAGECHECK_API_URL` e não importa os motores.

## Endpoints ativos

| Método | Rota | Finalidade |
|---|---|---|
| GET | `/health` | saúde da API |
| POST | `/v1/audits/page` | auditoria completa local |
| POST | `/v1/audits/seo` | regras SEO sobre dados enviados |
| POST | `/v1/pages/inspect` | inspeção HTML pública |
| POST/GET | `/v1/history` | salvar/listar histórico SQLite local |
| GET | `/v1/history/{audit_id}` | restaurar relatório local |
| GET | `/v1/history/{audit_id}/export?format=json|csv|html_zip` | exportar relatório |
| DELETE | `/v1/history/{audit_id}` | remover registro local |

As rotas `/v1/temporary/*` permanecem opcionais e inativas no fluxo local normal.

## POST /v1/audits/page

```json
{
  "url": "https://example.org/",
  "niche": "Software",
  "objective": "organic_traffic",
  "language": "en",
  "keywords": ["workflow automation"]
}
```

`language` aceita `en`, `pt` e `es`. `keywords` aceita até oito frases de 2–60 caracteres, sem duplicatas.

A resposta é um `audit-report-1.0` com:

- URL solicitada/final e redirects;
- contexto de idioma e keywords;
- score técnico interno e breakdown;
- checks/findings normalizados;
- `link_audit` com limites, robots, páginas, links, evidência e resumo;
- estados de SEO, conversão, desktop/mobile, axe e Impeccable;
- caminhos de screenshots quando capturados.

Lighthouse não faz parte do contrato ativo.

## Estados

- `passed`: regra executada e satisfeita.
- `failed`: violação objetiva confirmada.
- `warning`: observação ou decisão humana necessária.
- `not_verified`: não foi possível executar/concluir.
- `not_applicable`: regra fora do contexto.

No crawler, cada destino também usa `valid`, `broken`, `needs_review` ou `not_tested`, sempre com origem e motivo.

## Erros relevantes

- `403`: destino ou chamador bloqueado pela política local.
- `404`: histórico/artefato inexistente.
- `422`: entrada inválida.
- `429`: limite de admissão quando aplicável.
- `502`: falha segura ao obter a página.
- `503`: auditoria pública local não habilitada.

Os servidores locais devem ficar em `127.0.0.1`. Não exponha as flags locais por proxy público.
