# Arquitetura atual — Page Check local

## Fluxo principal

`Streamlit → FastAPI → audit_page_html → HTTP seguro + regras + crawler + motores opcionais → consolidação → SQLite/exportações → Streamlit`

A UI chama a API HTTP e apenas apresenta o relatório. Regras, rede, navegador, persistência e exportação permanecem fora dos componentes de apresentação.

## Componentes

| Camada | Responsabilidade |
|---|---|
| `api/` | valida entrada, política local e compõe os casos de uso |
| `application/use_cases/` | orquestra HTML, crawler, Playwright, motores e consolidação |
| `acquisition/http/` | valida URL, fixa transporte público, limita bytes/redirects e adapta Scrapling |
| `acquisition/browser/` | renderiza JavaScript em desktop/mobile com rotas GET guardadas |
| `audits/` | regras determinísticas de SEO, conteúdo, navegação, formulários e tracking |
| `integrations/` | axe-core e Impeccable sobre HTML sanitizado; adapter Lighthouse legado inativo |
| `reporting/` | normaliza checks, gera resumo e exporta JSON/CSV/ZIP |
| `persistence/sqlite/` | histórico local e recuperação por `audit_id` |
| `ui/` | formulário e abas Overview, URLs, Issues, Screenshots e Export |

## Aquisição e segurança

1. A URL inicial passa por `validate_public_url`.
2. `fetch_html` faz o GET inicial pelo transporte que valida IP e redirects.
3. `scrapling_adapter.discover_links` recebe somente o HTML já obtido; nenhum fetcher do Scrapling é usado.
4. `crawl_public_site` consulta `robots.txt`, percorre somente o mesmo host e usa `fetch_resource` para cada GET.
5. O crawl é sequencial e limitado por padrão a 20 páginas expandidas, profundidade 2, 200 links verificados, 90 segundos e corpos de até 2 MB. Os limites podem ser reduzidos ou ampliados localmente dentro dos tetos validados.
6. Playwright bloqueia métodos de escrita, WebSocket, downloads, service workers e acesso direto fora da política guardada.

Links externos são contabilizados como fora do escopo. Limites de páginas e profundidade impedem apenas nova descoberta: links internos já descobertos continuam elegíveis para GET. Destinos impedidos por robots, orçamento de tempo ou erro ficam `not_tested` com causa; não viram defeito confirmado.

## SEO

`audit_seo` calcula o score técnico ponderado. `content_guidance` usa idioma, nicho e keywords informadas para presença exata em áreas observáveis, sem mudar o score técnico. `site_rules` aplica às páginas crawleadas duas regras determinísticas adaptadas do jev-seo: títulos duplicados e meta descriptions duplicadas.

## Motores opcionais

- axe-core: semântica do HTML estático sanitizado; não é WCAG completa.
- Impeccable: heurísticas do HTML estático sanitizado; não é auditoria visual completa.
- Lighthouse: removido da composição ativa, cobertura, scores e UI porque seu Chrome próprio não usa o transporte protegido.

## Relatório

Todos os checks preservam `check_id`, módulo, estado, severidade, evidência e recomendação. O crawler acrescenta URL de origem/destino, selector, HTML do elemento, status, redirects, fragment e limitação. Overview agrega prioridades sem apagar os registros completos exibidos em Issues e exportados.

Screenshots preservam o fluxo aprovado de desktop/mobile, anotações, agrupamentos e downloads.
