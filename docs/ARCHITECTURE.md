# Arquitetura modular — Page Check

**Objetivo:** cada diretório tem uma única responsabilidade; interface, API, auditorias e bibliotecas externas não se acoplam diretamente.

## 1. Caminho dos dados

`Streamlit → FastAPI → application/orchestrator → acquisition + audits + integrations → domain/score → reporting → persistence → API → Streamlit`

O mesmo orquestrador pode ser acionado por uma API/n8n sem depender do Streamlit. A UI **não importa** código dos coletores ou verificadores. Apenas faz chamadas à API HTTP e renderiza DTOs.

## 2. Estrutura de diretórios

```text
pagecheck/
├── main.py                    # Entrypoint FastAPI -> package api/app.py
├── streamlit_app.py           # Entrypoint Streamlit -> package ui/app.py
├── pyproject.toml             # Dependências e projeto Python
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── SCORING_AND_RULES.md
│   └── API_CONTRACT.md
├── src/
│   └── pagecheck/
│       ├── api/                 # Rotas HTTP, schemas e dependências FastAPI
│       │   ├── app.py           # FastAPI e endpoint /health (bootstrap)
│       │   ├── routes/
│       │   └── schemas/
│       ├── ui/                  # Páginas, componentes e estilos Streamlit
│       │   ├── app.py           # Shell e status da API (bootstrap)
│       │   ├── pages/
│       │   ├── components/
│       │   └── styles/
│       ├── domain/              # Entidades, enum/status, regras puras e score
│       │   ├── models/
│       │   └── scoring/
│       ├── application/         # Casos de uso e orquestração de auditorias
│       │   └── use_cases/
│       ├── acquisition/         # HTTP, browser, scroll e observação de rede
│       │   ├── http/
│       │   ├── browser/
│       │   └── network/
│       ├── audits/              # Regras nossas, por domínio de inspeção
│       │   ├── seo/
│       │   ├── performance/
│       │   ├── navigation/
│       │   ├── forms/
│       │   ├── images/
│       │   ├── layout/
│       │   ├── tracking/
│       │   └── accessibility/
│       ├── integrations/        # Adapters de Lighthouse/axe/Impeccable
│       │   ├── lighthouse/
│       │   ├── axe/
│       │   └── impeccable/
│       ├── reporting/           # Anotações, visualização e exportação
│       │   ├── annotations/
│       │   ├── html/
│       │   └── exports/
│       ├── persistence/         # SQLite, repos e armazenamento de evidências
│       │   ├── sqlite/
│       │   └── artifacts/
│       └── common/              # Settings, erros, logs e segurança de URLs
│           └── security/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│       ├── pages/               # Landing page local com defeitos conhecidos
│       └── expected/            # Resultados esperados por caso
├── assets/
│   └── demo/                    # Imagens e relatórios de exemplo públicos
├── scripts/                     # Setup, dev.ps1, smoke tests futuros
├── .github/
│   └── workflows/              # CI futura
├── README.md
├── .env.example
└── .gitignore
```

A estrutura inicial contém **um bootstrap executável**, com `main.py` na raiz para a FastAPI e `streamlit_app.py` para Streamlit. Apenas `GET /health` e uma interface de status estão implementados. Os motores de auditoria, endpoints `/v1/audits`, exportação e evidências **ainda serão implementados**. As pastas reservadas conservam `.gitkeep` para serem versionadas até receberem código.

## 3. Responsabilidade e dependências permitidas

| Camada | Pode depender de | Não deve depender de |
|---|---|---|
| `domain/` | Python stdlib, tipos | Streamlit, FastAPI, Playwright, banco, CLIs |
| `application/` | domain, portas/interfaces tipadas | widgets, requests diretamente, SQL de UI |
| `acquisition/` | domain, HTTPX/Playwright | Streamlit ou regras de scoring |
| `audits/` | domain, dados normalizados de acquisition | UI, banco e adapters diretamente sem interface |
| `integrations/` | contratos domain; ferramentas externas | componentes de UI |
| `reporting/` | domain, Pandas/Pillow | chamadas HTTP ou scraping |
| `persistence/` | domain, SQLite, arquivos | UI e lógica de verificações |
| `api/` | application, DTOs Pydantic | implementação interna de UI |
| `ui/` | chamadas HTTP da API, Streamlit | Playwright, SQL, Lighthouse, regras de score |

Nenhum módulo deve depender de diretórios irmãos por importação circular. A comunicação entre verificadores se faz pelo contexto de auditoria somente leitura e por resultados estruturados.

## 4. Contratos mínimos internos

- `AuditRequest`: URL, nicho, objetivo, configurações, viewports.
- `AuditContext`: audit_id, URL final, dados de HTML/DOM, dados de rede, capturas e configuração de auditoria.
- `AuditFinding`: regra, módulo, status, severidade, seletor/URL/viewport/posição, prova, texto curto, ação e equipe.
- `ModuleResult`: lista de finding e métricas, falhas e status parcial do módulo.
- `AuditReport`: metadados, coverage, scores, arquivos e URL de downloads.

Regras puras: `evaluate(context) -> list[AuditFinding]`. Adapters externos: `run(context, timeout) -> ModuleResult` e nunca executados dentro do código de apresentação.

## 5. Ordem de execução

1. Segurança URL e orçamento de requests.
2. HTTPX + BeautifulSoup para estrutura inicial.
3. Playwright uma vez por viewport, com navegação, captura, scroll e interceptação segura.
4. Auditorias independentes em objetos coletados; checks sem necessidade de browser podem rodar separadamente.
5. Integrações de CLI em processo separado com timeout, versão e normalização de erros.
6. `domain/scoring` recebe somente findings normalizados.
7. `reporting` gera PNG anotado e HTML; `persistence` salva estado/artefatos; API devolve links.

## 6. Isolamento dos motores e falhas

- `lighthouse/` conserva score Lighthouse como dado original, não transforma em nosso score de SEO.
- `axe/` normaliza violações mas mantém regra/impacto de origem.
- `impeccable/` é **P1 condicional**: confirmar runtime no Windows, JSON, licença e comportamento antes de permitir no fluxo normal; falhas não bloqueiam o restante.
- Jobs com status `queued/running/completed/partial/failed`; se uma etapa opcional falhar, marcar `partial`, não retornar relatório fabricado.
- Preferir uma fila local controlada (1 job por vez inicialmente), sem Celery/Redis.

## 7. Screenshots e coordenadas

Salvar screenshot e metadados do viewport (largura/altura, device scale, scroll inicial, altura total, URL e momento). `bounding_box` de Playwright é relativo ao viewport; ao desenhar sobre uma captura full-page, converter usando `scrollY` e `device_scale_factor`, validando contra testes com páginas fixture. Mudanças de DOM durante scroll exigem reavaliar coordenadas.

## 8. Segurança e empacotamento

Acesso a alvos públicos com política de URL centralizada em `common/security/`, incluindo a navegação principal e cada request de subrecursos do Playwright, redirecionamentos e bloqueio de IPs não públicos. Não fazer POST em formulários. Capturas e relatórios em pasta local ignorada pelo Git. Não reutilizar cookies/sessões entre auditorias.

Não instalar todas as bibliotecas na etapa zero. Versões e dependências entram em `pyproject.toml`/lock quando o código começar, depois de validar Python/Windows/Node/Chrome. Cada nova dependência vem acompanhada de teste do adapter.

## 9. Entrypoints e como manter a separação

- `main.py` (raiz): apenas importa o `app` de `pagecheck.api.app`; não contém regras de auditoria.
- `streamlit_app.py` (raiz): apenas chama `pagecheck.ui.app.render_app`.
- `api/app.py`: composição de rotas e middlewares; controllers em `api/routes/`.
- `ui/app.py`: composição visual; lógica de interface em `ui/pages/` e `ui/components/`.
- Regras em `audits/` são funções independentes com entradas normalizadas, e podem ser testadas sem interface e sem rede.
- Bibliotecas futuras (BeautifulSoup, Playwright, Lighthouse, axe-core, Impeccable) serão integradas por módulos próprios, sem importação transversal direta na UI.
