# Etapa 10 — Marcações de evidências visuais

**Objetivo:** transformar os resultados do Playwright (Etapa 9) em uma captura de tela anotada, sem alterar os módulos de aquisição, endpoints ou Streamlit.

## Arquivos e responsabilidades

- `reporting/annotations/findings.py`: converte **apenas imagens renderizadas e confirmadamente quebradas** em achados estruturados; estados pendentes são ignorados.
- `reporting/annotations/overlay.py`: desenha bordas e marcadores sobre a captura de página inteira e gera manifesto JSON. O PNG original é preservado.
- `scripts/annotate_fixture_smoke.py`: reproduz a fixture HTML local, faz scroll e exporta imagens e manifesto para `artifacts/browser_stage10/`.
- Testes separados de regras, desenho e integração com Chromium.

## Verificações de segurança e precisão

- Apenas fixture local em `page.set_content`; requisições externas bloqueadas com `context.route`.
- Coordenadas **absolutas do documento**, não relativas ao viewport após scroll.
- Captura e dimensão de viewport devem corresponder à mesma escala. Caso contrário, a anotação é recusada, não desenhada em lugar incorreto.
- A imagem sem fonte ou ainda pendente **não é chamada de quebrada**.
- O marcador vermelho não é heatmap de visitantes e não mede impacto comercial.
- Não afirmar que imagens geradas por IA são visualmente coerentes ou incoerentes.

## Executar no Windows (PowerShell, raiz do Page Check)

```powershell
uv add pillow
uv run pytest tests/unit/test_annotations.py tests/integration/test_annotated_browser_fixture.py -v
uv run pytest -q
uv run python scripts/annotate_fixture_smoke.py
explorer.exe .\artifacts\browser_stage10
```

**Arquivos gerados:** `initial_viewport.png`, `after_scroll_full.png`, `after_scroll_annotated.png`, `annotations.json`.

**Importante:** esta etapa não adiciona análise de URLs públicas, mapas de calor reais, auditoria de acessibilidade ou detecção universal de problemas de design. Essas funções são etapas futuras.
