# Page Check — STAGE40: Render Free SEM GitHub

**Escopo:** somente empacotamento e implantação. Nenhuma alteração de layout, FastAPI, Streamlit, Chromium, Neon ou auditorias. Os commits continuam LOCAIS. Nunca usar `git push`.

## Por que Docker Hub privado?

O Render aceita **Existing Image** de registries externos com credenciais, inclusive imagens privadas do Docker Hub, e permite criar Web Services no plano **Free**. O Docker Hub Personal inclui **um repositório privado**. Guardamos **as duas imagens nesse mesmo repositório**, com tags diferentes:

- `docker.io/SEU_USUARIO/pagecheck-staging:stage40-api`
- `docker.io/SEU_USUARIO/pagecheck-staging:stage40-ui`

O Docker Hub é um *registro de imagens* necessário para transferir containers ao Render. **Não é um repositório Git nem o GitHub.** As imagens contêm o programa empacotado, portanto devem permanecer **privadas** enquanto o projeto não estiver concluído. Não guardar variáveis de ambiente, senhas, tokens ou URLs privadas do Neon nos arquivos Docker.

Referências oficiais: https://render.com/docs/deploying-an-image ; https://render.com/docs/free ; https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-registry/

## 1. Construção LOCAL — sem upload

1. Inicie Docker Desktop no Windows. Abra PowerShell na raiz do Page Check.
2. Instale somente os arquivos novos da STAGE40. Execute os testes usuais: `uv run pytest -q`.
3. Rode:

```powershell
.\scripts\stage40_render_free_images.ps1 -Mode Build
```

A construção é para `linux/amd64` (exigência do Render para imagens prebuilt). O script verifica a arquitetura, roda o autoteste de bloqueio IPv4/IPv6 do Chromium e mostra `STAGE40_LOCAL_IMAGES_READY`. **Não publica nem envia nada nessa modalidade.**

## 2. Criar repositório PRIVADO gratuito no Docker Hub

1. Entre em https://hub.docker.com/ (conta Docker Personal gratuita; não é GitHub).
2. Repositories -> Create repository -> **Name: `pagecheck-staging`**, Visibility: **Private**. Confirme a privacidade antes de continuar. Use seu único repositório privado gratuito.
3. Inicie sessão no Docker Desktop com a mesma conta, ou no PowerShell use `docker login -u SEU_USUARIO` e complete a autenticação (não coloque senha em comandos ou no chat).
4. No PowerShell, ainda na raiz do Page Check, rode **somente quando quiser transmitir imagens para o repositório privado**:

```powershell
.\scripts\stage40_render_free_images.ps1 -Mode Publish -DockerHubUser SEU_USUARIO -PrivateRepositoryConfirmed
```

A opção `-PrivateRepositoryConfirmed` é obrigatória: use-a **somente depois de confirmar visualmente que o repositório está marcado como Private**. O script envia as duas tags para o mesmo repositório privado. **Não executa `git push`**. Guarde os dois nomes que aparecem como `RENDER_IMAGE_API=` e `RENDER_IMAGE_UI=`.

## 3. Criar a API no Render Free a partir da imagem PRIVADA

1. Abra https://dashboard.render.com/ -> **New** -> **Web Service** -> **Existing Image**. **Não** selecione Git Repository/Blueprint.
2. Cole a imagem `RENDER_IMAGE_API`.
3. Em **Credentials**, Add Credential, registry Docker Hub, username Docker Hub, e um **Access Token Docker Hub com permissão apenas de leitura** de imagens privadas. Para gerar: Docker Hub -> Account Settings -> Personal Access Tokens. Insira o token somente no Render, nunca no GitHub/chat.
4. **Compute plan: Free**, nome único como `pagecheck-api`, região igual à UI, health check `/health`, porta exposta `10000` (a imagem aceita `PORT` do Render). Comando padrão da imagem pode ser mantido, **mas configure o Docker Command** para `/bin/sh /app/deploy/start_api_render_free.sh`. Esse comando migra o Neon antes de iniciar a API e faz a limpeza de registros expirados na inicialização.
5. Environment -> **variáveis de produção**:

| Key | Value |
| --- | --- |
| `PAGECHECK_ENV` | `production` |
| `PAGECHECK_DATABASE_URL` | URL privada do Neon (use a área de segredos do Render) |
| `PAGECHECK_PRIVATE_API_KEY` | Chave longa gerada localmente (ver abaixo) |
| `PAGECHECK_PUBLIC_AUDITS_ENABLED` | `0` |
| `PAGECHECK_EGRESS_ISOLATED` | `0` |
| `PAGECHECK_ALLOW_LIVE_FETCH` | `0` |
| `PAGECHECK_ALLOW_LIVE_BROWSER` | `0` |
| `PAGECHECK_ALLOW_LOCAL_STATIC_ENGINES` | `0` |

Para criar a chave em PowerShell sem exibi-la no chat:

```powershell
$chaveServico = ([guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N'))
```

Para copiar a chave sem mostrá-la no terminal, rode `Set-Clipboard -Value $chaveServico` e cole nas configurações de **ambos os serviços**. Não grave em arquivo nem execute `Write-Host $chaveServico`. Não envie essa chave por mensagem.

6. Crie o Web Service apenas se o plano estiver **Free/US$0**. Anote a URL HTTPS exata que o Render atribuiu à API (por exemplo `https://pagecheck-api-xxxx.onrender.com`). Não configure monitor externo, UptimeRobot nem keep-alive.

## 4. Criar a interface Streamlit no Render Free

1. Render -> **New** -> **Web Service** -> **Existing Image**.
2. Cole `RENDER_IMAGE_UI`. Reutilize a **mesma credencial** Docker Hub já registrada no Render.
3. **Compute: Free**, mesmo datacenter/região, health check `/_stcore/health`, comando padrão da imagem (`CMD` do Dockerfile UI) — **não** substitua pelo comando de API.
4. Environment:

| Key | Value |
| --- | --- |
| `PAGECHECK_ENV` | `production` |
| `PAGECHECK_STORAGE_BACKEND` | `postgres_temporary` |
| `PAGECHECK_API_URL` | URL HTTPS exata da API, sem `/` no final |
| `PAGECHECK_PRIVATE_API_KEY` | **Mesma** chave da API |
| `PAGECHECK_PUBLIC_AUDITS_ENABLED` | `0` |
| `PAGECHECK_EGRESS_ISOLATED` | `0` |
| `PAGECHECK_ALLOW_LIVE_FETCH` | `0` |
| `PAGECHECK_ALLOW_LIVE_BROWSER` | `0` |
| `PAGECHECK_UI_IDLE_GUARD` | `1` |
| `PAGECHECK_UI_IDLE_MINUTES` | `15` |

5. Confirme apenas **Free/US$0**. Anote URL HTTPS da UI.

## 5. Conferir com comando do Windows, SEM shell pago

A partir do seu Windows, na raiz do projeto:

```powershell
uv run python scripts/render_free_smoke.py --api 'https://URL_EXATA_DA_API.onrender.com' --ui 'https://URL_EXATA_DA_UI.onrender.com'
```

Sucesso esperado: `RENDER_FREE_HOSTED_STAGING_SMOKE_PASSED`. Depois abra a URL da UI no navegador para inspecionar a aparência; **o botão de novas auditorias permanece intencionalmente bloqueado**, por segurança. Não habilite as flags só para testar. Verifique os logs no Render se a migração Neon falhar ou API retornar 503.

## Limites e decisão de liberação

O teste acima comprova inicialização, saúde e bloqueio básico de endpoint sem autenticação. **Não comprova** execução de auditorias reais, memória do Chromium nos 512 MB, isolamento de egress do processo Python, recuperação de relatórios nem resolução de problemas de deploy. Esses pontos continuam sendo critérios de liberação, não devem ser presumidos aprovados.

Plano Free tem 750 horas por workspace compartilhadas entre as instâncias, e 512 MB por serviço; cada instância dorme após cerca de 15 minutos sem tráfego HTTP/WebSocket. Abas do Streamlit são mitigadas pelo idle guard da STAGE39, mas a suspensão não é imediata. Monitorar Billing -> Monthly Included Usage. **Sem cartão** para evitar cobranças por excesso de banda/build, de acordo com as regras atuais do Render.

**O arquivo `render.yaml` é para deploy de repositório Git, não para esse fluxo. Não usar Blueprint agora.**

## O que não fazer

- NÃO publicar GitHub nem criar Git remoto.
- NÃO criar segundo repositório privado no Docker Hub: o mesmo repositório com duas tags basta.
- NÃO usar imagens públicas, credenciais no código ou URLs privadas em `docker build`.
- NÃO escolher Starter/Standard/Private Service/Cron/Pre-deploy pagos.
- NÃO mudar `PAGECHECK_PUBLIC_AUDITS_ENABLED` ou `PAGECHECK_EGRESS_ISOLATED` para `1` sem cumprir o teste de segurança e memória.
