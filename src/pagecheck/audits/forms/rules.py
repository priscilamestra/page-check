"""Verificações de estrutura e rótulos de formulários; nunca os envia."""
from __future__ import annotations

from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


def _finding(rule: str, status: str, title: str, *, evidence: dict,
             severity: str = "info", recommendation: str = "") -> dict:
    return {
        "check_id": rule, "module": "forms", "status": status,
        "severity": severity, "title": title, "team": "Frontend / Growth",
        "evidence": evidence, "recommendation": recommendation,
    }


def _has_label(soup: BeautifulSoup, field) -> bool:
    if field.get("aria-label") or field.get("title"):
        return True
    ids = str(field.get("aria-labelledby") or "").split()
    if ids and all(soup.find(id=i) for i in ids):
        return True
    if field.find_parent("label"):
        return True
    field_id = field.get("id")
    return bool(field_id and soup.find("label", attrs={"for": field_id}))


def inspect_forms(html: str, page_url: str, *, objective: str = "leads") -> list[dict]:
    """Ausência de form não prova falha de conversão (pode existir CTA externo)."""
    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")
    if not forms:
        return [_finding("FORM_PRESENCE", "warning" if objective in
            {"leads", "meetings", "signup"} else "not_applicable",
            "Nenhum formulário encontrado no HTML analisado", evidence={"count": 0},
            severity="low", recommendation="Verificar se a captação ocorre em outra página ou widget.")]
    results = []
    for index, form in enumerate(forms, 1):
        method = str(form.get("method") or "get").lower()
        action = str(form.get("action") or "").strip()
        resolved = urljoin(page_url, action) if action else page_url
        fields = [field for field in form.find_all(["input", "select", "textarea"])
                  if str(field.get("type") or "").lower() not in {"hidden", "submit", "button", "reset"}]
        unlabeled = [field.get("name") or field.get("id") or field.name
                     for field in fields if not _has_label(soup, field)]
        form_evidence = {"form_index": index, "id": form.get("id"), "method": method,
                         "action": action or None, "resolved_action": resolved,
                         "field_count": len(fields)}
        results.append(_finding(f"FORM_FIELDS_{index}",
            "passed" if not unlabeled else "warning",
            "Campos com rótulos detectáveis" if not unlabeled else "Campos sem rótulo detectável",
            evidence={**form_evidence, "unlabeled_fields": unlabeled},
            severity="info" if not unlabeled else "medium",
            recommendation="Associar labels, aria-label ou aria-labelledby aos campos." if unlabeled else ""))
        if method == "get" and any(str(f.get("type") or "").lower() == "password"
                                   for f in fields):
            results.append(_finding(f"FORM_PASSWORD_GET_{index}", "failed",
                "Formulário com senha configurado para GET", severity="high",
                evidence=form_evidence,
                recommendation="Evitar transmitir senhas em parâmetros de URL; revisar o fluxo no backend."))
        else:
            results.append(_finding(f"FORM_METHOD_{index}", "not_verified",
                "Envio de formulário não executado", evidence=form_evidence,
                recommendation="Testar persistência e integração com CRM somente em ambiente autorizado."))
        try:
            parts = urlsplit(resolved)
            valid_target = parts.scheme.lower() in {"http", "https"} and bool(parts.hostname)
        except ValueError:
            valid_target = False
        if not valid_target:
            results.append(_finding(f"FORM_ACTION_{index}", "warning",
                "Destino do formulário não é HTTP(S)", evidence=form_evidence,
                severity="medium", recommendation="Revisar o atributo action."))
    return results
