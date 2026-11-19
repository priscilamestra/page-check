# PRD — Page Check

**Versão:** 1.2 | **Atualizado:** 19/11/2026 | **Status:** versão final validada e publicada no ambiente de produção | **Repositório:** independente do Stock.

## 1. Resumo

Aplicação local de auditoria técnica, funcional e visual de landing pages públicas para profissionais de marketing, growth e GTM. O usuário informa URL, nicho e objetivo. O sistema abre a página, analisa HTML e rede, percorre a página, executa verificações determinísticas, registra capturas desktop/mobile e apresenta **problemas localizados e ações por equipe**. Sem IA generativa e sem API paga obrigatória.

## 2. Problema e proposta de valor

Landing pages podem perder oportunidades por links quebrados, CTAs sem destino, imagens que falham durante scroll, problemas de SEO técnico, layout mobile inconsistente, ausência de rastreamento ou acessibilidade básica. O usuário não precisa ler uma auditoria textual extensa: vê a página marcada com problemas, uma tabela curta de prioridades e evidências reproduzíveis.

**Público principal:** freelancers de marketing/growth, GTM Engineers, profissionais de conteúdo/SEO, times de aquisição e QA de landing pages.

**Casos de uso:** auditoria antes de publicar uma campanha; diagnóstico de uma página pública; comparação antes/depois após correção; handoff para SEO, Design, Frontend, Growth/Tracking ou QA.

## 3. Princípios inegociáveis

1. Resultado determinístico e explicável: cada achado contém regra, evidência e recomendação. Nada de recomendações geradas por LLM.
2. Nunca atribuir 100% a testes não executados. Status permitidos: `passed`, `failed`, `warning`, `not_verified`, `not_applicable`.
3. Score próprio de conformidade **não** equivale a ranking Google, sucesso comercial ou probabilidade de conversão; Lighthouse aparece separadamente.
4. Sem ações invasivas, login, envio real de formulário, bypass de bloqueios ou crawling de área privada.
5. Componentes isolados; falha de um adapter não derruba as demais auditorias. Toda dependência de CLI externa tem timeout, versão fixada, logs e fallback `not_verified`.
6. Não coletar dados pessoais desnecessários; guardar evidências com retenção controlada.
7. Streamlit apresenta resultados, não executa lógica de negócio; FastAPI oferece API; o núcleo Python independe da UI.

## 4. Entrada e fluxos

### 4.1 Campos obrigatórios
- **URL** pública `http://` ou `https://`, validada e normalizada.
- **Nicho:** texto livre curto, contextual (ex.: nutrição, SaaS B2B). Não é usado para fabricar uma pontuação de relevância sem referência externa.
- **Objetivo:** `leads | meetings | sales | signup | organic_traffic`.

### 4.2 Fluxo principal
1. Validar URL e segurança do destino/redirects.
2. Criar auditoria com `audit_id`, data/hora, regras/versionamento, viewport e configurações.
3. Coletar HTML inicial com HTTPX + BeautifulSoup.
4. Abrir browser Playwright (desktop e mobile), observar rede, fazer scroll incremental e capturar screenshots com coordenadas.
5. Executar os módulos independentes; opcionalmente executar Lighthouse, axe-core e detector Impeccable via adapters isolados.
6. Normalizar todos os achados em um contrato único; calcular status, score e cobertura por módulo.
7. Desenhar anotações nas capturas (Pillow) e montar relatório compacto.
8. Em desenvolvimento, persistir no SQLite; em produção, permitir somente recuperação privada temporária por token opaco por até 24 horas.
9. Exportar HTML + imagens (ZIP), CSV/JSON (resultados tabulares).

### 4.3 Interface MVP
- **Auditar página:** formulário 3 campos, botão Auditar, aviso de limites.
- **Resultados:** resumo visual com status/score/cobertura, screenshot desktop/mobile anotado, lista curta de problemas por severidade, filtro por equipe e detalhes expandidos por achado.
- **Recuperação:** nenhum histórico público. Em produção, o navegador guarda somente um token opaco para restaurar a última auditoria por até 24 horas.

## 5. Requisitos funcionais

| ID | Prioridade | Requisito | Aceite mínimo |
|---|---|---|---|
| FR-01 | P0 | Validar URL e bloquear destinos perigosos | IPs privados/loopback, esquemas proibidos e redirects bloqueados não são acessados |
| FR-02 | P0 | Coletar HTML público | Title, meta description, headings, canonical, robots, links, imagens, formulários normalizados |
| FR-03 | P0 | Executar navegador real | Desktop e mobile, timeouts, screenshot antes/depois do scroll, logs de rede |
| FR-04 | P0 | Inspecionar lazy loading | Detalhar quais imagens foram carregadas durante scroll e quais permaneceram falhas/incompletas; exceções marcadas |
| FR-05 | P0 | Auditar links e CTAs sem alterar dados | HTTP/redirects e navegação GET permitida; elementos que acionam POST ficam `not_verified` |
| FR-06 | P0 | Inspecionar formulários | Identificar campos, rótulos, HTML validation, action; não submeter a produção |
| FR-07 | P0 | Auditoria técnica SEO | Checks com critérios explícitos e evidências; sem previsão SERP |
| FR-08 | P0 | Inspecionar imagens/layout | URLs, dimensões, alt, decode, viewport overflow e elementos sobrepostos em casos verificáveis |
| FR-09 | P0 | Validar UTMs e indícios de tracking | Checagem de parâmetros, redirects e presença de tags/requisições observadas; não afirmar conversão ou coleta completa |
| FR-10 | P0 | Integrar axe-core | Retornar violações e status não verificado se ferramenta falhar |
| FR-11 | P0 | Integrar Lighthouse local | Exibir scores originais separados dos próprios e informar ambiente de execução |
| FR-12 | P0 | Consolidar relatório | Achados por área/status/severidade/equipe, com evidência clicável e anotações na imagem |
| FR-13 | P0 | Recuperação e exportação | SQLite local; recuperação privada temporária em produção; PNG + JSON/CSV e relatório HTML via ZIP |
| FR-14 | P1 condicional | Adapter Impeccable detector | Usar CLI `detect --json` sem LLM, após smoke test no Windows; se indisponível, demais testes prosseguem |
| FR-15 | P1 | Histórico antes/depois | Comparar dois `audit_id` do mesmo alvo com regras compatíveis |
| FR-16 | P1 | Comparação de múltiplas URLs | Aplicar mesmo perfil de auditoria e comparar indicadores com Pandas |
| FR-17 | P1 | Revisão visual avançada | Heurísticas de inconsistência tipográfica e espaçamento, sem impor estilo subjetivo |

**Nota:** requisitos P0 são o escopo da versão 1.0 final; a implementação ocorrerá em incrementos para não bloquear entrega por dependências externas.

## 6. Regras por módulo

### SEO técnico
- Title e description presentes e não vazios; comprimento como alerta heurístico, não como fator absoluto de ranking.
- Heading H1, hierarquia H2/H3 e duplicações suspeitas (sem dizer que todo H1 duplicado é erro definitivo).
- Canonical, meta robots, idioma HTML, links internos, URL final após redirects.
- Lighthouse SEO: score original em painel separado; falha do CLI = `not_verified`.

### Performance e rede
- Requisições e status observados; falhas de recurso, console erros com contexto e contagem limitada.
- Lighthouse performance e Core Web Vitals laboratoriais: indicar teste de laboratório; não confundir com dados reais de usuários.
- Sem inferir causas completas de lentidão apenas pelo tamanho de arquivo ou tempo local.

### Imagens e scroll
- Antes/ao entrar/depois da viewport: `complete`, `naturalWidth`, `currentSrc`, falhas HTTP, espaços reservados e screenshots por seção.
- Lazy loading é avaliado pelo resultado observado, não só pelo atributo `loading=lazy`.
- Sinalizar imagem com dimensionamento problemático ou overflow apenas com medidas registradas; aspecto visual/erros em imagens de IA exigem revisão humana.

### Navegação/CTAs/formulários
- Identificar CTA por semântica verificável (`a`, `button`, role, texto, posição). Não garantir se é persuasivo.
- Verificar destino/link ou abertura segura; nenhum click capaz de criar lead, comprar, excluir ou disparar ação irreversível.
- Formulários: método/action, labels, required, validações nativas; não testar envio sem ambiente autorizado.

### Rastreamento
- Verificar sintaxe e consistência de UTMs quando URL de entrada possuir campanha ou quando houver links com UTMs.
- Verificar preservação em redirects; detectar scripts/requests observáveis de analytics sem afirmar que eventos funcionam do início ao fim.
- Ausência de UTM em acesso orgânico direto não é falha automática.

### Layout, UX e acessibilidade
- Desktop/mobile: overflow horizontal, conteúdo fora da viewport, links/botões com problemas de alvo, itens com sobreposição material verificável.
- axe-core para regras de acessibilidade automatizáveis.
- Tipografia, distâncias e diferenças de tamanho: inconsistência sinalizada como `warning`, não falha determinística universal.
- Impeccable detector pode gerar achados adicionais **somente depois** de testar CLI, licença, formato JSON e estabilidade no Windows; não requisita agente.

## 7. Saída e visualização

- Topo: URL, nicho, objetivo, horário, viewport, status geral, cobertura (`regras executadas / regras aplicáveis`) e contagem de achados por severidade.
- **Scores por módulo** 0–100 apenas quando houver regras verificadas; se não, `sem nota`. Nunca esconder cobertura reduzida.
- **Lighthouse**: scores originais Performance/SEO/Acessibilidade/Boas práticas em bloco próprio, rotulado laboratório.
- Screenshot anotado: marcadores numerados e cor por severidade; selecionar marcador abre achado com evidência e equipe sugerida.
- Achados: título curto, regra, prova (URL/selector/coordenadas/código HTTP), impacto potencial sem promessa de conversão, ação, equipe.
- Exportações: relatório HTML com assets PNG empacotados no ZIP, `findings.csv`, `audit.json` e screenshots; sem textos longos desnecessários.

## 8. O que fica fora

- IA generativa, visão computacional para entender semântica de imagens, correção automática de copy, heatmaps reais de visitantes.
- Ranking Google, volume real de palavras-chave e suposta probabilidade de conversão.
- Descoberta/teste de APIs privadas desconhecidas, login e submissão de formulários reais.
- Scan massivo de domínios, pentest, fuzzing, bypass de robots/captcha, scraping autenticado.
- CRM, integração de leads, Supabase, multi-tenancy e notificações no MVP.

## 9. Segurança e privacidade

- HTTPS/HTTP apenas; bloquear localhost, loopback, IPs privados, link-local, cloud metadata e DNS/redirects que resolvam para destinos internos, inclusive recursos do navegador, com proteção contra rebinding.
- Produção usa worker sem sockets IPv4/IPv6 diretos e broker AF_UNIX para GETs públicos validados; o `render.yaml` permanece desabilitado até os smoke tests.
- Limites configuráveis de tempo, bytes, requests, scroll, browser contexts, concorrência e profundidade; não seguir links indiscriminadamente.
- Não executar downloads, envios ou scripts fornecidos como entrada pelo usuário. Scripts pertencentes à página podem renderizar sob orçamento GET, sem WebSocket, serviço de background ou socket direto.
- Redigir dados sensíveis encontrados em URL/relatórios/logs; sanitizar HTML antes de exibir; evitar armazenar cookies e tokens.
- Respeitar restrições aplicáveis dos sites, robots quando apropriado ao modo de coleta, e documentar limitações de sites que bloqueiem automação.

## 10. Requisitos não funcionais

- Local-first no Windows, Python + `uv` (se adotado), Node/Chrome apenas para Lighthouse/Impeccable, sem API paga.
- Regras auditáveis, versões fixadas e logs por auditoria.
- Pasta temporária isolada por `audit_id`, limpeza em falhas e encerramento obrigatório do browser.
- API acessível localmente pela UI; componentes desacoplados com contratos Pydantic.
- Layout simples e legível no Streamlit, sem gráficos redundantes com amostras pequenas.
- Testes unitários para regras, integração para API/SQLite/adapters e E2E para uma landing page fictícia com defeitos conhecidos.

## 11. Definição de pronto (v1.0)

1. Auditar URL pública e renderizar desktop/mobile, incluindo caso de JS e lazy loading.
2. Detectar erros conhecidos da página fixture de teste com evidência, regra e responsável.
3. Gerar scores próprios com cobertura correta, manter scores Lighthouse separados e não pontuar `not_verified`.
4. Exportar HTML/PNG/CSV/JSON e recuperar auditoria do SQLite.
5. UI Streamlit chama API real; nenhum botão decorativo/falso.
6. `pytest` unit/integration/E2E aprovados em ambiente documentado; smoke test Windows das CLIs aplicáveis.
7. Proteções de URL, redirects, recursos de subnavegação e limites confirmadas por testes negativos.
8. README reproduz o fluxo de instalação/execução, com limitações reais e demonstração.
9. Detector Impeccable não bloqueia release se a integração ainda não estiver validada: fica P1 condicional registrada.

## 12. Encerramento da correção de interpretação (19/11/2026)

- O card **Technical SEO** mantém a fórmula ponderada existente e agora expõe a origem da nota. No teste real do Python.org, `79/100` corresponde a `9,5 de 12` pontos elegíveis, com as deduções de H1 e canonical mostradas como chips em **Missing or improve**.
- **Review relevance** usa somente termos proeminentes do title/H1 que ficaram fora do nicho e das palavras-chave informadas. Os chips são candidatos determinísticos para revisão humana, não uma afirmação automática de que o termo prejudica SEO.
- Links não visitados deixaram de produzir centenas de linhas `not_verified`. Os destinos continuam inventariados, mas aparecem como uma única limitação de cobertura. No teste real: `204` destinos, `17` registros diagnósticos e uma limitação agregada.
- O worker isolado usa timeout de `110 s` para acomodar CPU do Render gratuito, preservando o limite HTTP de `120 s`, memória de `512 MB`, broker GET validado, bloqueio de sockets diretos e concorrência unitária.
- Validação: `609` testes automatizados aprovados, smoke test Linux/Chromium em `512 MB`, revisão Impeccable sem achados e auditoria real do Python.org concluída no ambiente publicado.
