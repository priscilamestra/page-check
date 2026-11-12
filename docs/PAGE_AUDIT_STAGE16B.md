# Page Check — Etapa 16B: auditoria HTML integrada

## Objetivo

Uma única URL + nicho + objetivo aciona, em **uma única coleta HTTP**, o SEO já existente e a inspeção passiva de links, CTAs, formulários, sinais de tracking e parâmetros da URL. Os resultados são consolidados no contrato `audit-report-1.0`.

## Novos componentes

- `audits/tracking/url_journey.py`: inspeciona UTMs e identificadores de clique presentes na URL solicitada e sua preservação nos redirecionamentos observados, sem inferir se a atribuição do GA4 funcionou. Valores de identificadores não são reproduzidos nas evidências desse módulo.
- `application/use_cases/audit_page_html.py`: executa `fetch_html()` **uma única vez**, `parse_html()` completo, `audit_seo()`, `audit_conversion_html()` e a inspeção de URL. Em seguida chama `consolidate_audit()`.
- `api/routes/audit.py`: `POST /v1/audits/page`; segue o bloqueio de execução remota já existente, exigindo `PAGECHECK_ALLOW_LIVE_FETCH=1` no servidor **somente no ambiente local de desenvolvimento**.
- `ui/app.py`: o botão agora é `Auditar página` e chama o novo endpoint.
- `ui/components/report_view.py`: remove o seletor de gravidade e exibe uma aba `URLs e parâmetros` com os achados de tracking, links e formulários.

## O que este fluxo faz e não faz

**Faz:** verifica metadados SEO; UTMs preenchidas, vazias ou contraditórias; perda/mudança de parâmetros em redirecionamentos; links e âncoras declarados; CTAs e formulários no HTML recebido; presença de scripts de tracking.

**Não faz, ainda:** JavaScript em URLs externas, screenshots automáticos, execução do Lighthouse/axe/Impeccable no mesmo botão, consulta HTTP aos links e checkouts de destino, envio de formulários, evento `purchase`, conexão GA4. Esses resultados ficam como `not_verified` ou `not_applicable`; a auditoria será **parcial** até a integração segura dos motores visuais e dos testes de navegação.

> Importante: UTMs não são obrigatórias em todos os contextos e nem sempre precisam atravessar o checkout. Perda de parâmetros observada é um alerta de revisão, não prova automática de perda de conversão.

## Instalação

Na raiz do projeto `pagecheck`, antes de extrair confira `git status`. O ZIP sobrescreve exclusivamente estes três arquivos existentes: `src/pagecheck/api/app.py`, `src/pagecheck/ui/app.py` e `src/pagecheck/ui/components/report_view.py`. Os demais arquivos são novos. Não altera SEO, fetcher, parser, outras rotas ou bibliotecas.

```powershell
Expand-Archive -Path "$HOME\Downloads\PageCheck_Etapa16B_Auditoria_HTML_Integrada.zip" -DestinationPath . -Force
uv run pytest tests/unit/test_url_journey.py tests/unit/test_audit_page_html.py tests/unit/test_audit_page_api.py -v
uv run pytest -q
```

## Teste local real

**Terminal FastAPI** (Ctrl+C se o servidor já estiver rodando sem flag):

```powershell
$env:PAGECHECK_ALLOW_LIVE_FETCH="1"
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal Streamlit separado:**

```powershell
uv run streamlit run streamlit_app.py
```

Abra `http://localhost:8501`, informe URL, nicho e objetivo. Para um teste de parâmetros em domínio de referência:

`https://example.com/?utm_source=google&utm_medium=cpc&utm_campaign=teste`

Na FastAPI (`http://127.0.0.1:8000/docs`) aparece `POST /v1/audits/page`.

Em **terminal separado**, encerre a permissão de uso depois do teste com `Remove-Item Env:PAGECHECK_ALLOW_LIVE_FETCH`. A variável de um terminal não desativa a variável que já estiver ativa no processo da FastAPI; encerre o servidor de desenvolvimento para efetivamente desligar as consultas.

## Critérios de aceite

- 14 testes novos passam (sem rede externa).
- Suíte anterior de 208 testes continua passando no computador da usuária (total esperado **222**; não validado integralmente neste ambiente).
- `POST /v1/audits/page` retorna o contrato consolidado sem alterar `POST /v1/audits/seo` e `/v1/pages/inspect`.
- Resultado inclui módulos `seo`, `navigation`, `forms`, `tracking` observados e `source_states` corretos.
- UI mostra a aba `URLs e parâmetros`, gravidade como informação automática e não como filtro.
- O relatório parcial não é divulgado como auditoria de todos os motores.
