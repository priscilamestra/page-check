# Page Check — Render Free + idle guard (STAGE39)

## Contrato de arquitetura

Mantem Streamlit, FastAPI (servico web separado), Chromium/Playwright e Neon.
Nenhum servico pago no Blueprint: dois `type: web`, `plan: free`.
Sem cron, private service, pre-deploy pago ou keep-alive.

## Economia de horas

* O Render contabiliza horas de **cada instancia ativa**, nao o tempo de CPU gasto para executar uma auditoria.
* A franquia e de 750 horas mensais **por workspace**, compartilhada. O serviço gratuito dorme apos 15 minutos sem HTTP/WebSocket recebidos.
* `PAGECHECK_UI_IDLE_GUARD=1` (somente production) adiciona JS estatico local ao navegador. Depois de 15 minutos sem interacao, a aba navega para uma pagina in-memory com botao de retorno. Essa navegacao descarrega a UI e fecha o WebSocket. Sem requests de polling ou serviços de ping externos.
* A pagina ativa nao muda. Se a pessoa deixar de interagir durante a leitura, a aba tambem pausa depois do limite. Relatorios salvos no Neon podem ser recuperados ate 24 horas; resultados nao salvos podem se perder ao pausar.
* Em abas em segundo plano, navegadores podem atrasar timers. A mitigacao reduz gasto ocioso mas NAO garante limite exato de minutos; verifique o uso real no Render Dashboard.
* `PAGECHECK_UI_IDLE_MINUTES=15` (intervalo permitido 10 a 60). O scanner pode consumir ate dois minutos antes da resposta; o tempo ocioso e maior para nao interrompe-lo.
* Nao utilizar monitores externos (UptimeRobot), chamadas agendadas a /health ou keep-alive.

## Deploy, com seguranca

1. No Windows e na raiz do repo, descompactar o ZIP da STAGE39, executar `uv run pytest -q` e `uv run python scripts/render_deploy_preflight.py`.
2. Fazer commit local. Nao executar `git push` sem autorizacao expressa.
3. O deploy precisa de GitHub; verificar os dois `plan: free` na tela do Blueprint antes de criar qualquer recurso. Nao aceitar upgrade ou adicionar cartao.
4. Blueprint `render.yaml` vincula `PAGECHECK_API_URL` da UI a URL HTTPS (`RENDER_EXTERNAL_URL`) da API; a chave de servico e gerada e referenciada automaticamente, sem ir ao frontend. Preencher `PAGECHECK_DATABASE_URL` da API usando Neon, no painel Render.
5. Como Render Free nao possui comandos de pre-deploy, a API executa a migracao SQL idempotente ao iniciar; faz limpeza oportunista de linhas expiradas. O armazenamento rejeita relatorios apos 24h em consultas. **Exclusao fisica pode atrasar** se o servidor ficar dormindo; nao prometer cron exato com plano gratuito.
6. Validar no Render UI, API, comunicacao, logs e memoria. API tem **512 MB** e deve ser avaliada com Chromium e casos reais, sem inventar sucesso.
7. Execute de qualquer terminal local, apos criar os dois servicos: `uv run python scripts/render_free_smoke.py --api https://<api>.onrender.com --ui https://<ui>.onrender.com`. Copie as URLs exatas do painel Render; nao coloque `<>` no comando final.
8. Public URL audits seguem bloqueadas (`PAGECHECK_PUBLIC_AUDITS_ENABLED=0`) ate aprovacao de protecao de rede, especialmente do processo Python. Nao ligar flags por tentativa.

## Comandos locais

```powershell
uv run pytest -q
uv run python scripts/render_deploy_preflight.py

git add -- render.yaml deploy/Dockerfile.api deploy/start_api_render_free.sh deploy/start_streamlit.sh src/pagecheck/ui/app.py src/pagecheck/ui/idle_guard.py scripts/render_deploy_preflight.py scripts/render_free_smoke.py tests/unit/test_stage32_render_deployment.py tests/unit/test_stage38_release_smoke.py tests/unit/test_stage39_render_free_idle.py docs/RENDER_FREE_DEPLOY_STAGE39.md
git diff --cached --check
git commit -m "fix(deploy): use Render Free services and idle browser pause"
git status --short
```

## Limites

O plano gratuito nao transforma FastAPI/Chromium em execucao serverless. Cold start pode levar cerca de um minuto. Auditar 5 minutos nao significa consumir 5 minutos de instancia: cada servico permanece ativo antes de dormir. O guard funciona no navegador e nao resolve o risco de recursos limitados ou o isolamento de egress do Python.

Documentacao: https://render.com/docs/free ; https://render.com/changelog/free-web-services-now-remain-active-while-receiving-websocket-messages ; https://docs.streamlit.io/develop/api-reference/text/st.html
