# STAGE43 — Auditorias públicas com worker isolado no Render Free

Este patch mantém o Render Free, o FastAPI, o Streamlit, o Neon e a interface. Sem GitHub, sem serviço pago, sem mudança de layout.

## Alteração de segurança

1. API autenticada aceita uma única auditoria simultânea, com rate limit preexistente.
2. Worker Python separado é iniciado por `pagecheck-chromium-sandbox` (Linux seccomp) e não pode abrir sockets IPv4/IPv6; validação em tempo de execução inclusive **depois do `execve` para Python**.
3. Worker recebe um ambiente reduzido sem `PAGECHECK_DATABASE_URL`, sem chave privada e sem credenciais do Render. Playwright/Chromium permanece guardado (Stage36).
4. Todas as buscas HTTP(S) do worker passam por broker de socket Unix. Só há GET 80/443 com URL validada, DNS validado e conexão fixada em IP público, limite por recurso 2 MB e limite total por auditoria 16 MB, sem seguir redirects automaticamente.
5. A API registra relatórios e screenshots no Neon **fora do worker**, usando a implementação de persistência privada já existente.
6. API não libera auditoria sem flags explícitas; falha no teste de seccomp, no worker ou no broker resulta em 503.

**Escopo da garantia:** isolamento do processo de auditoria, e não firewall de saída de TODO o container. A API pai mantém a rede necessária para Neon e requisições HTTPS públicas validadas. Requer teste na infraestrutura Render real. `PAGECHECK_EGRESS_ISOLATED` continua **0**, pois não há prova de firewall global.

## Procedimento em ordem (PowerShell na raiz do projeto)

**A. Instalar a atualização:** extrair o ZIP STAGE43 com `Expand-Archive ... -DestinationPath . -Force`.

**B. Validar:** `uv run pytest -q`. Docker Desktop deve indicar `Engine running`. Executar `./scripts/stage43_render_free_release.ps1 -Mode Publish`. O script constrói imagens API/UI, faz uma auditoria de `https://example.com/` sob limite de 512 MB e **só publica se passar**. Se houver falha, não alterar Render.

**C. Git local:** com testes passando, `git add` somente os arquivos do ZIP, `git diff --cached --check` e `git commit`. Não criar repositório GitHub nem fazer `git push`.

**D. Render `pagecheck-api` → Settings → Image → Edit:** `docker.io/priscilamestra/pagecheck-staging:stage43-api`.

**E. Render `pagecheck-api` → Environment:** adicionar `PAGECHECK_AUDIT_WORKER_ISOLATED=1`. Manter `PAGECHECK_EGRESS_ISOLATED=0` e as flags de auditoria **0** por enquanto. Aguardar Live.

**F. Validar a segurança no Render, a partir do PowerShell local:** `uv run python scripts/stage43_render_isolation_smoke.py --api https://pagecheck-api.onrender.com`. Digitar a chave `PAGECHECK_PRIVATE_API_KEY` quando solicitada (entrada oculta). O script não grava a chave em arquivos, não faz Git push e não inicia auditoria nesse modo.

**G. Habilitar apenas na API para fazer uma auditoria privada de teste:** nas Environment Variables da API, colocar `PAGECHECK_PUBLIC_AUDITS_ENABLED=1`, `PAGECHECK_ALLOW_LIVE_FETCH=1` e `PAGECHECK_ALLOW_LIVE_BROWSER=1`; manter `PAGECHECK_AUDIT_WORKER_ISOLATED=1`, `PAGECHECK_EGRESS_ISOLATED=0`. A UI permanece desativada. Aguardar Live.

**H. Validar uma auditoria REAL autenticada no Render (UI ainda bloqueada):** `uv run python scripts/stage43_render_isolation_smoke.py --api https://pagecheck-api.onrender.com --audit`. Este teste confirma SEO, conversão, screenshots desktop e mobile. Se falhar, reverter `PAGECHECK_PUBLIC_AUDITS_ENABLED=0` na API e investigar Logs / Metrics. O teste não armazena um relatório no Neon porque não passa pela UI.

**I. Só depois de G+H aprovados, atualizar Render `pagecheck-ui`:** Settings → Image → Edit → `docker.io/priscilamestra/pagecheck-staging:stage43-ui`. Em Environment adicionar `PAGECHECK_AUDIT_WORKER_ISOLATED=1`; ajustar `PAGECHECK_PUBLIC_AUDITS_ENABLED=1`, `PAGECHECK_ALLOW_LIVE_FETCH=1`, `PAGECHECK_ALLOW_LIVE_BROWSER=1` e manter `PAGECHECK_EGRESS_ISOLATED=0`. Recarregar o site, testar uma auditoria, confirmar screenshots, salvar no Neon, fechar/reabrir no mesmo navegador em menos de 24h. Nenhum histórico público.

## Limitações e rollback

- **Não** ativar `PAGECHECK_EGRESS_ISOLATED=1`: o Render não fornece firewall global de saída verificado nesse plano.
- `PAGECHECK_AUDIT_WORKER_ISOLATED=1` não substitui a verificação em tempo de execução: sem seccomp Linux a API recusa a auditoria.
- Render Free tem 512 MB e 0.1 CPU por instância; teste local de 512MB não garante que toda página externa caiba. O teste de `example.com` é uma validação mínima.
- Como a UI e a API ficam em imagens diferentes, atualizar as **duas** imagens para que o botão seja habilitado.
- Rollback imediato: `pagecheck-ui` → Environment → `PAGECHECK_PUBLIC_AUDITS_ENABLED=0` e `pagecheck-api` → mesmo. O botão fica desativado sem excluir relatórios existentes.
