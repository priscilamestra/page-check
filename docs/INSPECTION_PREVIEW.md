# Inspeção de HTML — Etapa 5 (endpoint experimental)

- Nova rota: `POST /v1/pages/inspect`.
- Entrada: `{ "url": "https://example.com" }`.
- Saída: fatos extraídos do HTML, contagens, até 30 headings, 25 links e 25 imagens.
- Não implementa scores, auditorias de SEO, screenshots, Playwright ou persistência.
- Não altera o contrato planejado de `POST /v1/audits`; esta rota é um diagnóstico técnico temporário.
- **Uso local:** a rota retorna 503 a menos que `PAGECHECK_ALLOW_LIVE_FETCH=1` esteja definido no processo FastAPI.
- **Não publicar como serviço aberto:** a segurança e os limites de requisições ainda precisam de testes de integração, cotas, autenticação e política de rede/egress.
- Em testes automatizados, o fetcher é substituído por funções simuladas, sem usar internet.

## Como testar no Windows (PowerShell)

No terminal do servidor FastAPI, interrompa com Ctrl+C e inicie:

```powershell
$env:PAGECHECK_ALLOW_LIVE_FETCH="1"
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000/docs` e execute `POST /v1/pages/inspect` com `https://example.com`.

Para desligar o modo de teste posteriormente:

```powershell
Remove-Item Env:PAGECHECK_ALLOW_LIVE_FETCH
```
