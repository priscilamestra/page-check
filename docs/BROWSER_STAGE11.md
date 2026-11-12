# Etapa 11 — Navegação pública conservadora

**Status:** módulo independente em teste local, não habilitado na API nem no Streamlit.

Esta etapa utiliza `BrowserContext.route()` antes de criar páginas para **interceptar as requisições HTTP(S)** do Chromium. O handler NUNCA chama `route.continue_()` ou `route.fetch()`; somente retorna `route.fulfill()` com bytes obtidos pelo transporte Python `PublicHTTPTransport` (IP público validado na abertura da conexão TCP), ou `route.abort()` quando a política rejeita a requisição. Desativa Service Workers e JavaScript; tenta fechar WebSockets. Bloqueia requisições que não sejam GET e classes que não sejam documento, CSS, imagem ou fonte. Adota limites de requisições, tráfego, redirecionamentos, tempo e altura da captura (8.000 px).

## Limites importantes

- **Não é um sandbox de rede completo:** o navegador pode ter canais não cobertos pelo roteamento da aplicação. Antes de aceitar URLs arbitrárias de usuários ou publicar o serviço, exigir isolamento de rede no sistema operacional / container, egress deny-by-default, testes de SSRF/rebinding, limites de CPU e memória e observabilidade. Não expor o script ao público.
- JavaScript desativado: SPAs, loading por JS e ações de CTA/formulário estão **não verificados**, não 'quebrados'. Esta etapa serve ao HTML inicial e recursos estáticos. Uma etapa posterior deve executar JS apenas dentro de isolamento seguro.
- Recursos bloqueados pela política são reportados como `network.blocked`, **não** devem virar conclusões de imagem quebrada ou pontuações negativas.
- Não salva cookies e não envia credenciais, POSTs ou formulários.
- Não deve ser usado para executar crawling em massa; respeitar termos, limites e políticas dos destinos.

## Testes

```powershell
uv run pytest tests/unit/test_public_navigation.py tests/integration/test_public_navigation_offline.py -v
uv run pytest -q
```

## Teste opcional em ambiente de desenvolvimento

```powershell
$env:PAGECHECK_ALLOW_LIVE_BROWSER="1"
uv run python scripts/public_browser_smoke.py
Remove-Item Env:PAGECHECK_ALLOW_LIVE_BROWSER
```

Capturas geradas em `artifacts/browser_stage11/` se a navegação for concluída. O teste é deliberadamente limitado à página pública `https://example.com`.
