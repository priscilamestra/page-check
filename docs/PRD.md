# Page Check — PRD v1.5 local finalizado

**Atualizado:** 20/11/2026
**Status:** implementação local concluída e validada no Windows
**Base:** commit local `3d66b6b`; alterações posteriores ainda sem commit/push
**Escopo:** aplicação local de portfólio; sem Docker, Render, Neon ou deploy

## 1. Objetivo

O Page Check recebe URL pública, nicho, objetivo, idioma e keywords e produz uma auditoria determinística de SEO on-page, conteúdo, links, navegação, acessibilidade estática, design heurístico e evidências desktop/mobile.

Não usa IA generativa, pesquisa de keywords paga ou serviços hospedados obrigatórios. Não promete ranking Google, volume de busca, conversão real, Core Web Vitals de campo, pentest ou WCAG completa.

## 2. Funcionalidades entregues

### 2.1 SEO técnico e conteúdo

- Score **Technical SEO** preservado e independente, com pesos e breakdown rastreáveis.
- Title, description, H1, ordem de headings, canonical, noindex e alt continuam sendo regras técnicas.
- Idioma, nicho e keywords informadas participam dos checks de conteúdo.
- Expressões compostas são verificadas em title, meta description, H1/H2/H3, conteúdo principal, âncoras e alt.
- Nav, header, footer, aside, forms, scripts e templates não contam como conteúdo principal.
- HTML que parece um shell JavaScript parcial não comprova ausência; o resultado fica `not_verified`.
- Keywords presentes, pouco proeminentes ou ausentes têm regra, localização, exemplos observados e recomendação.
- Termos comuns e palavras do title/H1 não viram automaticamente “irrelevantes”.
- Trocar keywords altera somente os checks de conteúdo, sem manipular o score técnico.

### 2.2 Crawler e links

- Scrapling participa de forma real por `scrapling.Selector` na descoberta de links e preserva selector/HTML do elemento.
- BeautifulSoup continua responsável pelo parsing estrutural e pela verificação de fragments.
- Toda rede usa o transporte protegido do Page Check; nenhum fetcher/spider do Scrapling acessa a rede.
- Crawl sequencial, GET-only, limitado ao mesmo host, robots-aware e com tetos explícitos:
  - 20 páginas;
  - profundidade 2;
  - 200 links;
  - 90 segundos por padrão, configurável localmente até 600;
  - 2 MB por recurso;
  - concorrência 1.
- Registra origem, href, URL resolvida/final, texto, selector, HTML, status HTTP, redirects, fragment, ocorrências e limitação.
- Distingue `discovered`, `tested`, `valid`, `broken`, `needs_review`, `not_tested` e `out_of_scope`.
- 4xx/5xx confirma link quebrado; redirect vira revisão; fragment ausente é falha; limite/robots/erro fica não testado com causa.
- Links externos não são acessados.
- Limites de páginas e profundidade controlam somente a expansão do crawl; não impedem a verificação de destinos internos já descobertos.
- Formulários, contas, compras, POST e demais ações de escrita nunca são executados.

### 2.3 Regras adaptadas do jev-seo

Duas regras determinísticas ausentes foram adaptadas ao contrato Page Check:

1. títulos duplicados entre páginas crawleadas;
2. meta descriptions duplicadas entre páginas crawleadas.

Elas usam somente páginas HTTP 200 observadas, agrupam valor e URLs, têm severidade/recomendação e não usam Jev, TypeSafe, DataForSEO, modelo ou score do projeto externo. Não alteram o score técnico da página inicial.

### 2.4 Motores e capturas

- Playwright renderiza desktop/mobile com JavaScript e interceptação GET guardada.
- POST, WebSocket, downloads, service workers e sockets diretos permanecem bloqueados.
- axe-core executa sobre HTML estático sanitizado e declara esse limite.
- Impeccable executa sobre HTML estático sanitizado e declara esse limite.
- Screenshots, marcadores, categorias, detalhes e downloads foram preservados.

### 2.5 Decisão Lighthouse

Foi aplicada a opção **C: remoção do produto ativo**.

Causa: o Lighthouse abre Chrome próprio e suas requisições não passam pelo transporte protegido do Page Check. Permiti-lo em URLs públicas exigiria afrouxar a garantia de rede ou criar outra camada de isolamento fora do escopo local.

Consequência aplicada:

- não aparece na UI;
- não entra em `Sources completed`;
- não entra em scores, cobertura ou exportações;
- README/API/arquitetura não o apresentam como motor disponível;
- adapter e fixture históricos podem permanecer no código apenas como legado inativo.

### 2.6 Relatório e interface

- Overview, URLs & parameters, Issues e Export consomem os resultados reais.
- URLs mostra descobertos, testados, quebrados, redirects para revisão e não testados.
- Issues preserva problema, estado, severidade, evidência, selector/HTML/localização e recomendação.
- Duplicatas são agregadas no resumo sem apagar os checks completos.
- **Missing or improve** e **Review relevance** contêm somente chips; ficam vazios sem evidência defensável.
- Checks técnicos nunca viram chips de keyword.
- **Fix these first** mostra apenas `High`, `Medium` ou `Low`.
- A mensagem visual `Audit saved to local history (<id>)` foi removida; persistência e erros reais foram mantidos.
- Persistência local SQLite e restauração por `audit_id` continuam ativas.
- Exportações JSON, CSV e ZIP com HTML/screenshots continuam ativas.

## 3. Segurança

- URL inicial e cada redirect passam pela política de destino público.
- Localhost, redes privadas, link-local, metadata, credenciais em URL e destinos não públicos são bloqueados.
- Transporte fixa o destino validado e limita redirects, tempo e bytes.
- Crawler e browser são somente leitura; nenhum método de escrita é enviado a terceiros.
- Serviços locais devem permanecer em `127.0.0.1`.
- Relatórios podem conter URLs e trechos de HTML; `data/local/` e `artifacts/` ficam fora do Git.

## 4. Estados e interpretação

- `passed`: regra executada e satisfeita.
- `failed`: falha objetiva confirmada.
- `warning`: evidência que requer correção/revisão.
- `not_verified`/`not_tested`: cobertura indisponível ou limitada; não é defeito.
- `not_applicable`: regra fora do caso.

O score Technical SEO mede somente regras técnicas elegíveis. Findings de conteúdo, crawler, axe, Impeccable e Playwright não são somados em uma nota geral arbitrária.

## 5. Aceite validado

| Requisito | Evidência executada | Status |
|---|---|---|
| Keywords presente/ausente/composta e HTML parcial | testes de `content_guidance` | concluído |
| Termos comuns e score técnico separados | testes de conteúdo/Overview | concluído |
| Scrapling real sem rede própria | testes do adapter + crawl real | concluído |
| Link 200, 404, redirect, fragment, robots e limite | testes de `crawl_public_site` e `fetch_resource` | concluído |
| Bloqueio de redirect privado e GET-only | testes de transporte/segurança | concluído |
| Duas regras jev-seo | testes de `site_rules` | concluído |
| Overview/URLs/Issues/Evidence/Screenshots | inspeção visual Streamlit em auditoria real | concluído |
| Chips, prioridades e salvamento silencioso | testes unitários + inspeção visual | concluído |
| Lighthouse com desfecho A/B/C | opção C aplicada e testada | concluído |
| axe/Impeccable com escopo fiel | execução real sobre snapshot sanitizado | concluído |
| Persistência e exportação | SQLite + JSON/CSV/ZIP 200 | concluído |
| Regressão | `594 passed, 1 warning` | concluído |

## 6. Auditoria pública de validação

Alvo autorizado: `https://www.python.org/`
Entrada: nicho `Software development`, idioma `en`, keywords `python programming` e `python documentation`.

Resultado observado na API:

- HTTP 200;
- Technical SEO 79 no fluxo completo com as duas keywords;
- 200 links internos descobertos;
- 200 testados;
- 181 válidos;
- 2 quebrados;
- 17 redirects/destinos para revisão;
- 0 não testados;
- 132 destinos externos fora do escopo;
- título único aprovado e meta descriptions duplicadas sinalizadas;
- axe e Impeccable concluídos no modo estático sanitizado;
- capturas desktop e mobile produzidas;
- Lighthouse ausente de scores/fontes.

No fluxo completo pela UI com `python programming` e `python documentation`, o Overview exibiu Technical SEO 79, chip de melhoria real, Review relevance vazio sem placeholder, prioridades High/Medium/Low e nenhuma mensagem visual de salvamento. A aba URLs confirmou 200 descobertos, 200 testados e 0 não testados.

Exportação da mesma auditoria:

- ZIP HTTP 200 com `report.html`, `report.json`, `findings.csv`, `screenshots/desktop.png` e `screenshots/mobile.png`;
- JSON HTTP 200;
- CSV HTTP 200.

## 7. Limitações efetivas

- O crawl não é infinito e pode deixar links como não testados ao atingir tempo/páginas/profundidade/quantidade ou robots.
- Links externos não são verificados.
- Navegação dinâmica por cliques não é exercitada; somente renderização e subrecursos GET seguros.
- Conteúdo atrás de login, API privada, CAPTCHA ou ações de escrita está fora do escopo.
- axe/Impeccable estáticos e screenshots não substituem teste humano completo.
- Relevância semântica, termos “ruins”, volume de busca e ranking não são inferidos.

## 8. Execução local

```powershell
# Terminal 1
$env:PAGECHECK_ENV="local"
$env:PAGECHECK_ALLOW_LIVE_FETCH="1"
$env:PAGECHECK_ALLOW_LIVE_BROWSER="1"
$env:PAGECHECK_ALLOW_LOCAL_STATIC_ENGINES="1"
uv run uvicorn main:app --host 127.0.0.1 --port 8765
```

```powershell
# Terminal 2
$env:PAGECHECK_API_URL="http://127.0.0.1:8765"
uv run streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

## 9. Restrições de entrega preservadas

- nenhum deploy executado;
- Docker/Render/Neon não foram restaurados ou usados;
- `docs/STAGE43_WINDOWS_BROKER_TEST_FIX.md` permanece não rastreado e não modificado.
- a publicação Git inclui somente código, documentação e mídias públicas validadas; dados locais e relatórios operacionais continuam ignorados.
