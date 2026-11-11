# Page Check

**Status:** estrutura inicial e conexão API/UI prontas. **Os motores de auditoria ainda NÃO foram implementados.**

Page Check é um projeto local-first de auditoria técnica e visual de landing pages para marketing e GTM, com relatórios verificáveis e sem IA generativa ou APIs pagas obrigatórias.

## Convenção de nomes

- **Page Check**: nome exibido do produto.
- **`pagecheck/`**: nome da pasta raiz e do repositório sugerido.
- **`src/pagecheck/`**: nome do pacote Python (sem espaços).
- **`main.py`**: entrada da FastAPI.
- **`streamlit_app.py`**: entrada da interface Streamlit.

## Pré-requisitos

- Python 3.11+ e `uv` instalado.
- Node.js e Playwright/Chrome serão necessários em etapas futuras para alguns motores de auditoria; **não** são pré-requisitos do bootstrap.

## Instalação (PowerShell / terminal do VS Code)

Abra **dois terminais na pasta raiz `pagecheck`**. Instale as dependências uma vez:

```powershell
uv sync
```

**Terminal 1 — API:**

```powershell
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- Saúde: http://127.0.0.1:8000/health
- Documentação da API: http://127.0.0.1:8000/docs

**Terminal 2 — Streamlit:**

```powershell
uv run streamlit run streamlit_app.py --server.port 8501
```

- Interface: http://localhost:8501
- A interface mostra se a API respondeu. **Ainda não audita URLs.**

Para testes rápidos:

```powershell
uv run pytest tests/unit/test_health.py
```

## Onde trabalhar em cada etapa

| Objetivo | Pasta responsável |
|---|---|
| Endpoints HTTP e validação de payload | `src/pagecheck/api/` |
| Interface visual e componentes | `src/pagecheck/ui/` |
| Fluxo da auditoria | `src/pagecheck/application/` |
| Modelos e pontuação pura | `src/pagecheck/domain/` |
| HTTP, HTML, Playwright, rede | `src/pagecheck/acquisition/` |
| Regras por área (SEO, layout etc.) | `src/pagecheck/audits/` |
| Integrações CLI externas | `src/pagecheck/integrations/` |
| Relatórios, marcações, exportação | `src/pagecheck/reporting/` |
| Histórico e artefatos | `src/pagecheck/persistence/` |
| Segurança, erros e configurações | `src/pagecheck/common/` |
| Testes independentes | `tests/` |

Pastas reservadas para módulos futuros contêm `.gitkeep`: isso permite versioná-las enquanto estiverem vazias. Não importe regras de auditoria diretamente da interface Streamlit.

## Documentação

- [PRD](docs/PRD.md)
- [Arquitetura e estrutura](docs/ARCHITECTURE.md)
- [Plano de implementação](docs/IMPLEMENTATION_PLAN.md)
- [Pontuação e regras](docs/SCORING_AND_RULES.md)
- [Contrato da API](docs/API_CONTRACT.md)

## Limites importantes

Não são realizados: rastreamento de usuários, heatmap comportamental, envio real de formulários, pentest, verificação de endpoints privados ou análise semântica de imagens de IA. A auditoria futura será baseada em verificações públicas e seguras.

O projeto **Stock** permanece separado e inalterado.
