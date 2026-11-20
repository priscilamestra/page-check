# Regras e scores atuais

## Estados e cobertura

- `passed`: verificação concluída e satisfeita.
- `failed`: violação objetiva e reproduzível.
- `warning`: evidência que requer correção/revisão.
- `not_verified`: execução incompleta; nunca sucesso.
- `not_applicable`: fora do denominador.

`coverage = (passed + failed + warning) / (passed + failed + warning + not_verified)`.

## Technical SEO

O score usa somente as regras estruturais abaixo:

| Regra | Peso |
|---|---:|
| Title | 3 |
| Meta description | 2 |
| H1 | 3 |
| Ordem de headings | 1 |
| Canonical | 2 |
| Noindex, quando aplicável | 4 |
| Alt de imagens | 1 |

`passed` recebe o peso integral, `warning` metade e `failed` zero. `not_verified` não inventa pontos e reduz cobertura. O denominador contém apenas regras aplicáveis e verificáveis. O relatório preserva pontos ganhos, pontos possíveis e deduções.

O número é conformidade técnica observada, não ranking Google, qualidade semântica total ou previsão de conversão.

## Conteúdo e keywords

A análise usa somente idioma, nicho, keywords fornecidas e HTML observado. Ela verifica frases exatas com comparação case/accent-insensitive e limites de palavra em:

- title e meta description;
- H1, H2 e H3;
- conteúdo principal;
- texto de âncoras;
- alt de imagens.

Header, nav, footer, aside, forms, scripts e templates são excluídos do corpo principal. Keyword ausente em shell JavaScript parcial fica `not_verified`. Keywords presentes apenas fora de áreas proeminentes geram orientação; keywords ausentes no HTML observado geram warning. Esses checks não alteram o Technical SEO.

`Review relevance` permanece vazio quando não existe evidência determinística defensável. Termos comuns ou palavras do title/H1 não são classificados automaticamente como ruins.

## Crawl e regras multi-page

Links são descobertos pelo Scrapling e testados via GET protegido. 4xx/5xx confirmam destino quebrado; redirects ficam para revisão; fragments são comparados com `id`/`name`; limites e robots produzem `not_tested`.

As regras adaptadas do jev-seo verificam títulos e meta descriptions duplicados entre páginas HTTP 200 crawleadas. Elas acrescentam findings com URLs e valores observados, mas não mudam o score técnico da página inicial.

## Motores e visuais

axe-core e Impeccable mantêm seus próprios findings e limitações. Screenshots/Playwright mantêm evidência de viewport. Nenhum desses resultados é somado a uma nota geral. Lighthouse não é fonte ativa.
