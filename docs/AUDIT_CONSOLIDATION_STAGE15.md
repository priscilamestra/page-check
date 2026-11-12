# Etapa 15 — Consolidação de auditorias (Page Check)

## Objetivo

Converter **resultados já obtidos** pelos módulos SEO, conversão, Playwright e motores externos em um JSON uniforme para alimentar o Streamlit e as exportações nas próximas etapas. **Não** abre URL, aciona ferramentas externas, escreve em SQLite, cria endpoint nem realiza varredura completa de site nesta etapa.

## Arquitetura

- `reporting/consolidation/normalize.py`: adapta checks e achados sem apagar evidências.
- `reporting/consolidation/summary.py`: conta status, prioriza problemas, agrupa ações por equipe.
- `application/use_cases/consolidate_audit.py`: reúne os resultados de diferentes módulos sem fazer I/O.
- `scripts/consolidation_fixture_smoke.py`: demonstra a consolidação com dados de referência **offline** e salva JSON em `artifacts/consolidation_stage15/`.

Nenhum arquivo existente precisa ser substituído.

## Exemplo de uso

```python
from pagecheck.application.use_cases.consolidate_audit import consolidate_audit

report = consolidate_audit(
    requested_url="https://example.com/landing",
    final_url="https://example.com/landing",
    niche="SaaS B2B",
    objective="leads",
    seo=seo_report,                 # resposta de audit_seo(...)
    conversion=conversion_report,   # resposta de audit_conversion_html(...)
    visuals={"desktop": desktop_visual, "mobile": mobile_visual},
    external=engines_report,        # resposta de combine_engines(...)
)
```

Todos os parâmetros de relatório são opcionais: módulos ausentes aparecem em `source_states` como `not_verified`. Quando há `scroll_complete=False` ou captura truncada, o viewport aparece como `partial`.

## Campos principais

- `status`: indica se **todos os dados previstos foram recebidos e verificáveis**, não que a página tenha qualidade aprovada.
- `source_states`: estado de SEO, conversão, viewports e ferramentas externas.
- `scores.internal.seo`: score e cobertura originais das regras SEO.
- `scores.lighthouse`: notas originais independentes do Lighthouse; `null` se indisponível.
- `scores.overall`: sempre `null` nesta etapa; nenhum score geral inventado.
- `checks`: lista uniforme com `source`, `module`, `check_id`, `status`, `severity`, `team`, `evidence`, `viewport` e `target_url`.
- `findings`: apenas problemas/alertas priorizados; não inclui aprovados ou não verificados.
- `summary.counts`: distribuição por status observados.
- `summary.check_coverage`: cobertura de **checks recebidos**. Não representa cobertura de todos os módulos possíveis.
- `actions_by_team`: problemas e ações direcionados por equipe.
- `screenshots`: referências locais fornecidas pelos resultados do Playwright; nenhuma imagem nova é gerada aqui.
- `engine_limitations`/`visual_limitations`: limites e falhas conhecidos.

## Regra de confiança

Os motores externos podem retornar `completed` mesmo quando encontram falhas na página; isso significa **execução concluída**, não aprovação. Um motor ausente não recebe score zero ou nota positiva. A consolidação nunca deduz que “não há problemas” só porque uma fonte não forneceu achados.

## Testes

```powershell
uv run pytest tests/unit/test_audit_consolidation.py tests/integration/test_audit_consolidation_integration.py -v
uv run pytest -q
uv run python scripts/consolidation_fixture_smoke.py
```

O smoke é uma demonstração offline. A ausência dos resultados visuais é intencional, resultando em relatório parcial. Não use suas notas como desempenho de uma página pública real.

## Limitações e próximos passos

Esta etapa **não** cria o endpoint `/v1/audits/full` nem vincula a execução real de Playwright, Lighthouse e CLI a uma URL de usuário. Nas etapas 16–18, conectar interfaces e orquestração exigirá respeitar a política de navegação segura, controles de recursos e limitações de rede de cada motor. Não habilitar varredura arbitrária de sites públicos apenas porque a consolidação passou nos testes.
