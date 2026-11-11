# Etapa 8 — Validação dos diagnósticos SEO

Duas páginas HTML controladas validam o comportamento do pipeline completo, sem depender de sites externos ou de APIs pagas.

- `tests/fixtures/pages/seo_ok.html`: title, description, H1, headings em sequência, canonical e `alt`; resultado esperado: score 100 e nenhuma falha segundo as regras atuais.
- `tests/fixtures/pages/seo_problems.html`: title/description/H1/canonical ausentes, `noindex` e imagem sem `alt`; resultado esperado: seis achados para o objetivo `organic_traffic` e pontuação inferior à página de referência.
- `tests/integration/test_seo_reference_pages.py`: executa o caso de uso com HTML integral; valida evidência, escopo do `noindex` e o retorno HTTP do endpoint com aquisição substituída por fixtures.

## Comandos

```powershell
uv run pytest tests/integration/test_seo_reference_pages.py -v
uv run pytest -q
```

**Limites:** Estes testes comprovam a coerência das regras implementadas para os exemplos escolhidos; não comprovam ranking no Google, qualidade editorial, conectividade de URLs reais, SSRF em produção, comportamento JavaScript ou conformidade SEO completa.

Não modifica nenhum arquivo de produção. Ao avançar para Playwright e páginas reais, manter testes em ambientes controlados e um conjunto de regressão para os problemas identificados.
