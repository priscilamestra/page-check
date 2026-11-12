# Page Check — Etapa 12: imagens, layout e responsividade

## Escopo

O objetivo é **verificar evidências mensuráveis de duas larguras de viewport** e
produzir screenshots originais e anotados. Sem modelos de IA, APIs externas ou
qualquer alteração no frontend/rotas existentes.

- `acquisition/browser/layout_probe.py`: lê geometria do DOM já renderizado.
- `audits/layout/rules.py`: detecta overflow horizontal e suspeita de sobreposição de controles.
- `audits/images/visual_rules.py`: emite alertas sobre ampliação excessiva e diferenças de proporção de imagens com dimensões intrínsecas conhecidas.
- `application/use_cases/audit_visual_viewport.py`: executa inspeção visual, reutiliza o detector de imagens quebradas da Etapa 10 e gera marcações.
- `scripts/responsive_fixture_smoke.py`: executa **somente HTML local** em desktop/mobile e gera arquivos em `artifacts/browser_stage12/`.

## Limites de interpretação

- **Overflow horizontal** é uma medição objetiva (`scrollWidth > innerWidth + 2`). Um problema real pode ser causado por diferentes elementos.
- **Sobreposição** é aviso heurístico, pois pode ser intencional (badges, menus e ícones). Não entra automaticamente como falha crítica.
- **Imagem ampliada/distendida** é um alerta técnico, não análise semântica da imagem. Uma foto com `object-fit: cover` pode ser cortada intencionalmente.
- Recurso de imagem **pendente ou bloqueado pela política de rede** não vira erro confirmado.
- A inspeção DOM lê até 200 elementos visíveis. Se ultrapassar, marca `truncated=true` e a cobertura é parcial.
- Os screenshots são feitos depois de um scroll limitado. Se `scroll_complete=false`, há regiões não verificadas.
- A navegação pública da Etapa 11 continua restrita. Este pacote **não** expõe uma rota pública, não executa JS remoto e não realiza submissões de formulário.
- Inspeção de hierarquia tipográfica subjetiva, qualidade estética, palavras-chave e similaridade de imagens com IA continuam fora desta etapa.

## Instalação

Execute na raiz do repositório, no PowerShell:

```powershell
Expand-Archive -Path "$HOME\Downloads\PageCheck_Etapa12_Imagens_Layout_Responsividade.zip" -DestinationPath . -Force
uv run pytest tests/unit/test_layout_rules.py tests/unit/test_image_quality_rules.py tests/integration/test_responsive_browser_fixture.py -v
uv run pytest -q
uv run python scripts/responsive_fixture_smoke.py
explorer.exe .\artifacts\browser_stage12
```

O script gera as capturas em `desktop/` e `mobile/`, incluindo
`after_scroll_annotated.png` e `annotations.json`. Compare os alertas das duas larguras.

Os testes de Chromium exigem `uv run playwright install chromium` (executado na Etapa 9).

## Observações para a próxima etapa

A API Streamlit ainda não foi conectada ao motor visual. Antes de expor auditorias
arbitrárias no navegador, é necessário executar o motor num ambiente isolado,
com política de rede adicional. Não usar uma rota Web aberta sem esse controle.
