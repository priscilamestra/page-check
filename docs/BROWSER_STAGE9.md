# Etapa 9 — Playwright offline: scroll, imagens e screenshots

Esta etapa **não modifica FastAPI, SEO, HTTPX ou Streamlit**.

## Objetivo

Validar o motor visual em uma página HTML **local e controlada**, sem acessar URLs externas:

- Captura inicial da viewport e captura completa após scroll;
- Scroll incremental e indicação se o percurso foi concluído;
- Distinguir imagens carregadas, quebradas e não verificadas;
- Detectar o atributo `loading="lazy"` (não é prova de ganho de performance);
- Registrar caixa geométrica (`box`) para marcações visuais futuras.

## Instalação e testes (PowerShell, raiz do projeto)

```powershell
uv add playwright
uv run playwright install chromium
uv run pytest tests/unit/test_visual_probe.py tests/integration/test_visual_browser_fixture.py -v
uv run pytest -q
```

Executar demonstração local:

```powershell
uv run python scripts/browser_fixture_smoke.py
```

Os arquivos PNG são gravados em `artifacts/browser_stage9/`, ignorado pelo Git.

## Limites e cuidados

- Esta versão **não recebe URL externa**, navega ou clica em CTAs. Recebe um objeto `Page` aberto pelo chamador.
- O script de demonstração usa `page.set_content()` com fixture HTML; os recursos de imagem são `data:` URLs e todas as requisições externas são bloqueadas.
- NÃO integrar diretamente a navegação pública com `page.goto(url)` antes de implementar isolamento e filtragem de rede no Chromium. A proteção existente do HTTPX não protege o navegador automaticamente (DNS/redirects, subrecursos, websockets, service workers).
- `status=broken` indica falha de decodificação de imagem após scroll; `not_verified` indica ausência de prova, e não erro confirmado.
- A posição dos elementos é coletada para uma futura camada de anotações; ainda não é um mapa de calor de usuários reais.
- `scroll_complete=false` sinaliza que o limite de passos interrompeu a varredura.
- Esta etapa não faz análises de SEO, visual design ou Lighthouse e não produz score.
