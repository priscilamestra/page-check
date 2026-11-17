# STAGE37 — Auditoria de limites de rede antes do deploy

Objetivo: validar, **sem tráfego externo**, que as URLs recebidas e os endereços retornados pelo DNS são controlados pelo transporte Python. Esta etapa **não comprova o isolamento de rede no Render**.

## O que é demonstrado

- URLs diretas para localhost, endereços IP, metadados de nuvem, portas não permitidas e esquemas não HTTP(S) são rejeitadas antes da conexão.
- O transporte faz a conexão TCP com um IP público validado, sem nova resolução DNS na hora de conectar.
- DNS misto público + privado é inteiramente rejeitado (não há conexão para nenhuma das respostas).
- As flags de habilitação pública permanecem desligadas. Nenhum segredo, conexão ao Neon ou chamada externa é necessário.

## Execução local

```powershell
uv run python scripts/stage37_public_egress_preflight.py
uv run pytest -q
```

O Docker já compilado na STAGE36 também pode executar o preflight usando um bind-mount somente leitura:

```powershell
docker run --rm `
  -e PAGECHECK_ENV=production `
  -e PAGECHECK_PUBLIC_AUDITS_ENABLED=0 `
  -e PAGECHECK_EGRESS_ISOLATED=0 `
  -v "${PWD}/scripts/stage37_public_egress_preflight.py:/app/stage37_public_egress_preflight.py:ro" `
  --entrypoint /app/.venv/bin/python `
  pagecheck-api:stage36 `
  /app/stage37_public_egress_preflight.py
```

### Os resultados NÃO provam

- Isolamento de rede de todas as saídas do processo Python ou da infraestrutura do Render.
- Teste end-to-end usando um serviço hospedado ou conexão com Neon.
- Que `PAGECHECK_EGRESS_ISOLATED=1` pode ser habilitado apenas porque a STAGE36 e a STAGE37 passaram.

## Próxima decisão de implantação

**Manter `PAGECHECK_EGRESS_ISOLATED=0` e `PAGECHECK_PUBLIC_AUDITS_ENABLED=0`.** A API pode ser implantada de forma privada e com auditorias desativadas para validar saúde e comunicação interna, mas não divulgar o site como auditor de páginas públicas funcional.

Para liberar o botão de auditoria em produção, é necessário revisar e verificar uma barreira de rede independente da aplicação, incluindo tráfego de saída dos processos Python, ou redesenhar a aquisição para um executor isolado. O Render não fornece, na configuração de private service deste repositório, prova automática dessa barreira.

Não colocar credenciais reais em arquivos versionados. Não publicar sem autorização do proprietário do repositório.
