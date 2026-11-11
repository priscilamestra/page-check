# Plano incremental — implementação sem agente de IA

**Contexto:** projeto novo, separado do Stock. A desenvolvedora implementará manualmente no VS Code, com entregas pequenas e testes a cada incremento.

## Sequência com gates de validação

### Etapa 0 — Repo e ambiente
- Extrair `pagecheck/` como projeto novo; `git init -b main` e commit inicial.
- **Já incluídos no scaffold:** `pyproject.toml`, `main.py`, `streamlit_app.py`, `src/pagecheck/api/app.py`, `src/pagecheck/ui/app.py` e teste de saúde.
- Confirmar Python 3.11+ e `uv`; `uv sync` instala somente o bootstrap. Node e navegadores de testes serão configurados nas etapas respectivas.
- Iniciar API e UI em **dois terminais**, verificar `/health` e a mensagem de conexão na interface.
- **Gate:** `uv run pytest tests/unit/test_health.py` passa. Nenhum auditor está implementado ainda.

### Etapa 1 — Núcleo e contrato
- Modelos e enum em `domain/`; Pydantic em `api/schemas`.
- `common/security/` validar URLs/redirects/DNS/bloqueios.
- API `POST /v1/audits`, `GET /v1/audits/{audit_id}`, status persistido em SQLite.
- **Gate:** testes unitários do contrato e negativos SSRF/timeout; endpoint responde sem Streamlit.

### Etapa 2 — HTTP e SEO básico
- HTTPX/BeautifulSoup extrair title/meta/headings/canonical/links/formulários/imagens.
- Regras SEO com evidência e status/coverage.
- **Gate:** fixture HTML com erros conhecidos; API devolve findings reproduzíveis.

### Etapa 3 — Browser e layout
- Playwright desktop/mobile, escrolagem progressiva, rede, screenshots e coordenadas.
- Verificar imagens, overflow e CTA GET seguro; separar ações inseguras como `not_verified`.
- **Gate:** página fixture com imagens atrasadas, botão quebrado e overflow; capturas correspondem às coordenadas marcadas.

### Etapa 4 — Integrações técnicas
- axe-core executado em contexto isolado; Lighthouse CLI local com JSON e limites.
- Inspeção visual e scoring próprios; Lighthouse separado.
- Smoke test Impeccable CLI no Windows, com `detect --json` contra fixture **antes** de integrar; se incompatível, permanecer opcional.
- **Gate:** falha em qualquer CLI externa retorna `partial`/`not_verified`, sem derrubar auditoria.

### Etapa 5 — Relatório Streamlit
- UI Auditar página, Resultados e Histórico.
- PDF não é requisito; HTML visual + PNG, CSV/JSON e ZIP de evidências.
- SQLite guarda metadados e paths, não grandes binários.
- **Gate:** nenhum controle sem ação real; abrir e exportar relatório, teste de navegação manual no Windows.

### Etapa 6 — Qualidade final e portfólio
- E2E com fixture de erros predefinidos; comparar auditoria boa/ruim.
- Teste com 2 landing pages públicas autorizadas; registrar bloqueios ou limitações observadas.
- CI para unitários sem navegador; testes browser em job separado quando possível.
- Revisar `.gitignore`, proteção de URLs, licenças, documentação e imagens sem dados pessoais.
- **Gate:** critérios de pronto do PRD atendidos; commit + tags de release.

## Ordem recomendada de arquivo ao programar

1. `domain/models/`: tipos/enum/resultado
2. `common/security/`: validação URL
3. `application/use_cases/`: criar/consultar auditoria
4. `api/schemas/` + `api/routes/`: contratos HTTP
5. `acquisition/http/` + `audits/seo/`
6. `acquisition/browser/` + `audits/images/` + `audits/layout/`
7. `integrations/axe/`, depois `integrations/lighthouse/`, Impeccable condicional
8. `reporting/` e `persistence/`
9. `ui/pages/` e `ui/components/`

Evitar implementar todas as telas primeiro. Cada tela só aparece após sua operação backend ter teste.

## Política de commits

- `docs: define product requirements and modular architecture`
- `feat(core): add audit contracts and URL validation`
- `feat(seo): extract and validate public landing page metadata`
- `feat(browser): capture desktop mobile and scroll evidence`
- `feat(reporting): add visual findings report`

Nunca remover a branch/repositório original `stock`; nenhum código do Stock deve ser copiado automaticamente sem auditoria de licença e dependências.
