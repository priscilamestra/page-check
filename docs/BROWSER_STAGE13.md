# Page Check — Etapa 13: links, CTAs, formulários e tracking

## Objetivo

Analisar **dados observáveis** de landing pages sem cliques, sem POSTs, sem simular conversões e sem APIs pagas/de IA. O módulo recebe HTML já adquirido pelo pipeline existente. Não faz rede nem tenta descobrir endpoints privados.

## Diretórios e responsabilidades

- `audits/navigation/rules.py`: href, âncoras internas e presença de CTAs.
- `audits/forms/rules.py`: rótulos, action, method e risco de formulário GET com senha.
- `audits/tracking/rules.py`: presença estrutural de UTMs e indícios de tags no HTML.
- `application/use_cases/audit_conversion_page.py`: agregação dos checks e contagens, sem pontuação.
- `acquisition/browser/dom_snapshot.py`: lê o DOM de uma página já aberta por navegador controlado. Não navega nem ativa JavaScript.

## Estados

- `passed`: condição estrutural realmente observada, **não** teste de conversão.
- `failed`: problema comprovado na evidência (p.ex. href fragmentado aponta para ID inexistente).
- `warning`: indício que merece revisão; não é prova de falha funcional.
- `not_verified`: necessidade de teste externo/ação de usuário/recebimento no backend.
- `not_applicable`: regra não se aplica aos dados fornecidos.

Nesta etapa **não calculamos score** para não misturar estrutura, performance e conversões. A consolidação de pesos fica para a Etapa 15.

## Limitações importantes

1. Um link HTTP(S) com href válido pode retornar 404: o módulo **não faz requests** para verificar destinos. Em momento apropriado, usaremos somente o fetcher existente e sua política de segurança.
2. Um formulário com method POST e um botão submit **não prova** integração com CRM: nenhum envio é realizado.
3. A presença de script de analytics **não prova** disparo ou recebimento de eventos.
4. JavaScript desabilitado no modo público conservador da Etapa 11 impede validar handlers dinâmicos; resultados dependentes de JS ficam não verificados.
5. Um site pode não conter formulário porque direciona a agendamento externo. Nesse caso, ausência é aviso, não falha.
6. O HTML e a URL usados nas verificações precisam pertencer à mesma versão da página. Não usar JSON de prévia com campos truncados.

## Testes

```powershell
uv run pytest tests/unit/test_navigation_rules.py tests/unit/test_form_rules.py tests/unit/test_tracking_rules.py tests/integration/test_conversion_browser_fixture.py -v
uv run pytest -q
uv run python scripts/conversion_fixture_smoke.py
```

Relatório demonstrativo (não versionado): `artifacts/browser_stage13/conversion_audit.json`.

Nenhum arquivo de produção anterior é substituído; tudo é novo. Para testar em sites públicos no futuro, integrar com a aquisição protegida existente e revisar as limitações de segurança antes de colocar numa instância aberta à internet.
