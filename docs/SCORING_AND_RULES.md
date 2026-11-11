# Regras e scores — proposta v1.0

## 1. Estados

- `passed`: verificação concluída e regra satisfeita.
- `failed`: violação objetiva e reproduzível da regra.
- `warning`: heurística, risco ou evidência parcial; exige revisão.
- `not_verified`: execução inviável/bloqueada/erro/sem permissão; nunca sucesso.
- `not_applicable`: regra não se aplica ao objetivo/página; fora do denominador.

## 2. Severidade ≠ score

Severidade: `critical`, `high`, `medium`, `low`, `info`. A gravidade é usada para priorizar correções. Uma heurística estética não recebe automaticamente criticidade alta.

## 3. Cobertura

`coverage = checks_executed / checks_applicable`, onde executados são `passed | failed | warning` e aplicáveis excluem `not_applicable`. `not_verified` permanece no denominador.

Exibir cobertura sempre ao lado do score, por exemplo `SEO: 80/100 — 8 de 10 regras executadas`.

## 4. Score interno por área

Cada regra possui `weight` versionado. Para regras executadas:
- `passed` = 1,0 do peso;
- `warning` = 0,5 do peso **somente se a regra definir penalização intermediária**; caso contrário, `warning` não pontua e a regra exibe alerta;
- `failed` = 0.

`module_score = 100 × soma(pontos executados) / soma(pesos executados)` com cobertura exibida separadamente. Se nenhum check verificável, **sem nota**. Regra com `not_verified` não entra no numerador nem no denominador do score, porém reduz a cobertura. Se coverage abaixo do mínimo configurado (proposta inicial: 70%), destacar `nota parcial`, nunca apresentar como avaliação abrangente.

Não somar scores do Lighthouse com scores próprios em uma nota genérica. Primeira versão apresenta scores por área, e um índice geral opcional futuro só depois de documentar pesos e cobertura agregada.

## 5. Exemplos de checks iniciais

| ID | Área | Regra | Nível típico |
|---|---|---|---|
| SEO_TITLE | SEO | Title presente e não vazio | medium |
| SEO_CANONICAL | SEO | Canonical consistente e válida, quando declarada | medium |
| SEO_NOINDEX | SEO | `noindex` presente em página que deveria captar tráfego orgânico | high ou não aplicável conforme objetivo |
| NAV_BROKEN_LINK | Navegação | GET de destino seguro retorna 404/410 | high |
| CTA_UNRESOLVED | Conversão | CTA importante não possui destino/ação navegável verificável | warning / high conforme evidência |
| IMG_BROKEN | Imagens | Recurso da imagem não carrega/decodifica após scroll | medium |
| LAYOUT_OVERFLOW | Visual | Overflow horizontal detectado na viewport | medium |
| TRACK_UTM_LOST | Tracking | URL com UTMs perde parâmetro no redirect | medium |
| AXE_RULE | Acessibilidade | Violação reportada pelo axe-core | conforme impacto da regra |

**Sem pontuação para:** estética subjetiva, número de palavras-chave do nicho como indicador de Google ranking, conversão de CRM não observada, mapa de calor comportamental e qualidade semântica de imagens de IA.

## 6. Evidência obrigatória

Cada finding com falha/alerta deve incluir pelo menos: `check_id`, `status`, `target_url`, `observed_value` ou erro registrado, `severity`, `recommendation`, `team` e `source` (motor/regra). Quando estiver associado a elemento renderizado, armazenar locator, viewport e bounding box (se disponível); adicionar screenshot marcado. Se a evidência faltar, usar `not_verified`.

## 7. Versionamento

Registrar `ruleset_version`, versões de Playwright/Chrome/Lighthouse/axe/Impeccable, viewport, timestamp, URL final e `audit_id`. Ao comparar auditorias, informar se versões/ambientes divergem.
