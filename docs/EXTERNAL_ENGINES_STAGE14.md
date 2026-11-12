# Page Check — Etapa 14: motores externos

## Propósito

Adaptadores independentes para **Lighthouse** (notas originais), **axe-core** (violação automatizada de acessibilidade) e **Impeccable Detector** (alertas de design, sem LLM). Não altera os endpoints existentes nem a interface Streamlit.

Os resultados são `completed` ou `not_verified`; nenhum erro de instalação, timeout ou formato vira aprovação. A consolidação (`partial`) é apenas de disponibilidade e **não calcula a nota final** (Etapa 15).

## Instalação

`npm` deve estar disponível com **Node.js 22 LTS ou superior** para o Lighthouse atual. Execute na raiz:

```powershell
npm init -y
npm install --save-dev lighthouse axe-core impeccable
```

O diretório `node_modules/` permanece ignorado pelo Git; `package.json` e `package-lock.json` podem ser versionados após a validação.

O Playwright Python e Chromium já foram instalados na Etapa 9.

## Testes e validação

```powershell
uv run pytest tests/unit/test_external_engine_adapters.py tests/unit/test_external_engine_runner.py -v
uv run pytest -q
uv run python scripts/external_engines_fixture_smoke.py
```

O último comando **não executa ferramentas externas**: interpreta amostras JSON e grava `artifacts/external_stage14/reference_engines.json`. É adequado para confirmar normalização offline.

Para executar motores locais no HTML de demonstração:

```powershell
uv run python scripts/external_engines_fixture_smoke.py --live-local
```

Este smoke usa **somente** `tests/fixtures/pages/visual_scroll.html` e um servidor HTTP temporário em `127.0.0.1`. Não aceita URL do usuário nem usa serviços pagos. O axe é injetado na página aberta pelo Python Playwright; o Impeccable analisa o arquivo local; o Lighthouse analisa a página servida localmente. Se alguma ferramenta não puder ser executada, aparecerá `not_verified` no JSON — abra `artifacts/external_stage14/local_engines.json`.

Não exponha essas ferramentas em endpoints públicos nesta etapa: o Lighthouse e o detector abrem navegadores com rede própria, sem passar pela política de SSRF do Page Check. Testes contra páginas reais só podem ser liberados após isolamento de rede apropriado.

### Leituras

- Lighthouse: https://github.com/GoogleChrome/lighthouse
- Axe: https://www.deque.com/axe/core-documentation/api-documentation/
- Impeccable: https://impeccable.style/docs/detector/

### Notas de qualidade

- Score Lighthouse é score de laboratório próprio (0–100) e não deve ser misturado com o score das regras SEO do Page Check.
- axe detecta problemas automatizáveis, não garante conformidade WCAG total.
- Impeccable é um detector de heurísticas e pode produzir alertas intencionais. O JSON real pode evoluir: se vier em formato não suportado, a integração deve retornar `not_verified` e guardar diagnóstico, não fabricar achados.
- Sem agentes, IA generativa ou API paga.
