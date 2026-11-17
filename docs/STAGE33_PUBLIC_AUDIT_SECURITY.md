# STAGE33 — Preparação segura do scanner para produção

**Estado:** proteções no código implementadas; publicação com auditorias de URLs arbitrárias **ainda bloqueada** até validar o isolamento da rede do navegador. Esta etapa não altera o design nem desativa a segurança existente.

## Mudanças

- Endpoint `/v1/audits/page`: exige chave interna em produção antes de gastar capacidade ou fazer acesso à rede. Streamlit envia a chave somente de servidor para servidor. A chave nunca é transmitida ao navegador do usuário.
- Admissão global do scanner: no máximo **1 auditoria simultânea** e **6 inícios de auditoria por minuto** por processo. Excedentes recebem HTTP 429 e `Retry-After`. Não é cota por usuário e não substitui proteção de entrada contra abuso.
- Regras de produção: auditoria só é habilitada quando **todas** as flags necessárias estão presentes e a chave tem pelo menos 32 caracteres. O Blueprint mantém todas desabilitadas.
- Navegação guardada: permanece sem JavaScript, com subrecursos limitados a GET e HTTP(S) e transporte intermediado pelo backend de IP validado. Foi adicionado limite de tempo para as requisições interceptadas.
- Motors locais experimentais (`Lighthouse`, `axe-core`, `Impeccable`) não foram habilitados em produção.

## Flags de habilitação futura

`PAGECHECK_PUBLIC_AUDITS_ENABLED=1`, `PAGECHECK_EGRESS_ISOLATED=1`, `PAGECHECK_ALLOW_LIVE_FETCH=1`, `PAGECHECK_ALLOW_LIVE_BROWSER=1` e `PAGECHECK_PRIVATE_API_KEY` de 32+ caracteres são condições **necessárias, mas não suficientes**. Não as configure como `1` sem comprovar *externamente* que o Chromium não consegue alcançar serviços internos, metadados da nuvem, redes privadas ou interfaces de gerenciamento, mesmo com redirecionamentos e DNS adversarial. **Uma variável de ambiente não cria isolamento**. O modo `PAGECHECK_ENV=development` nunca deve ser usado em produção.

O Render Private Service restringe o tráfego de entrada, não garante sozinho a política de saída da rede do Chromium. A implantação para usuários públicos requer uma solução de isolamento de saída apropriada ao serviço de hospedagem, com teste negativo controlado e revisão independente. Por isso, este pacote não altera as flags do Blueprint para `1`.

## Limites restantes

- Limites de taxa são locais a **um processo**. Não execute workers ou instâncias adicionais sem um rate limiter distribuído.
- Ainda falta demonstrar um orçamento rígido de tempo total de cada processo de auditoria, limites de custo, defesa contra execução concorrente em múltiplas instâncias e isolamento real da rede.
- Builds Docker, disponibilidade do Chromium no Render, custos, comunicação entre serviços e limpeza agendada no Neon ainda requerem um ensaio no ambiente de implantação.
- A versão antiga do Streamlit pode recuperar os relatórios enquanto o scanner está desabilitado. Isto é intencional e não é uma falha da interface.

## Validação local no VS Code

```powershell
uv run python scripts/stage33_security_preflight.py
uv run pytest -q

git status --short
git diff --check
```

Se a suíte e o preflight passarem, faça **commit local** dos arquivos desta etapa. Não faça push automaticamente. Antes do deploy, revisite a configuração de rede e os custos estimados do Render e execute os testes integrados da API, browser e banco. Nunca compartilhe a URL do Neon nem a chave interna em prints ou ZIPs.
