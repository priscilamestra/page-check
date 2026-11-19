"""Inspeciona links, âncoras e sinais de CTAs sem clicar nem consultar destinos."""
from __future__ import annotations

import re
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup
from bs4.element import Tag

CTA_TERMS = re.compile(
    r"\b(?:contato|contact|fale conosco|saiba mais|learn more|"
    r"comprar|buy|adquirir|solicitar|request|agendar|schedule|book|"
    r"começar|iniciar|start|cadastre-se|inscrever|inscreva-se|"
    r"sign up|register|demonstração|demo|orçamento|quote)\b",
    flags=re.IGNORECASE,
)


def _finding(rule: str, status: str, title: str, *, evidence: dict,
             recommendation: str = "", severity: str = "info") -> dict:
    return {
        "check_id": rule, "module": "navigation", "status": status,
        "severity": severity, "title": title, "team": "Frontend / Growth",
        "evidence": evidence, "recommendation": recommendation,
    }


def _element_selector(element: Tag) -> str:
    """Record a reproducible DOM location, not a guessed visual coordinate."""
    segments = []
    node: Tag | None = element
    while isinstance(node, Tag) and node.name != "[document]" and len(segments) < 24:
        parent = node.parent
        if not isinstance(parent, Tag):
            segments.append(node.name)
            break
        siblings = parent.find_all(node.name, recursive=False)
        index = next((i for i, sibling in enumerate(siblings, 1) if sibling is node), 1)
        segments.append(f"{node.name}:nth-of-type({index})")
        node = parent
    return " > ".join(reversed(segments))


def _fragment_exists(soup: BeautifulSoup, fragment: str) -> bool:
    target = unquote(fragment)
    return bool(soup.find(id=target) or soup.find("a", attrs={"name": target}))


def inspect_navigation(html: str, page_url: str) -> list[dict]:
    """Avalia integridade estrutural. HTTP remoto e funcionamento JS ficam não verificados."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for index, a in enumerate(soup.find_all("a"), 1):
        href = str(a.get("href") or "").strip()
        text = a.get_text(" ", strip=True) or str(a.get("aria-label") or "").strip()
        element = {"tag": "a", "index": index, "id": a.get("id"), "text": text,
                   "href": href, "selector_hint": f"#{a['id']}" if a.get("id") else None,
                   "selector": _element_selector(a), "element_html": str(a)[:1000]}
        is_cta = bool(CTA_TERMS.search(text) or a.get("data-cta"))
        prefix = "CTA" if is_cta else "LINK"
        if not href or href == "#":
            results.append(_finding(f"NAV_{prefix}_{index}", "warning",
                "Link sem destino definido", evidence=element, severity="medium",
                recommendation="Definir o destino do link ou confirmar se há tratamento JavaScript."))
            continue
        if href.startswith("#"):
            exists = _fragment_exists(soup, href[1:])
            results.append(_finding(f"NAV_{prefix}_{index}",
                "passed" if exists else "failed",
                "Âncora interna encontrada" if exists else "Âncora interna inexistente",
                evidence=element, severity="info" if exists else "medium",
                recommendation="Corrigir o identificador do destino da âncora." if not exists else ""))
            continue
        try:
            resolved = urljoin(page_url, href)
            parts = urlsplit(resolved)
            allowed = (parts.scheme.lower() in {"http", "https"} and bool(parts.hostname))
        except ValueError:
            allowed, resolved = False, ""
        element["resolved_url"] = resolved
        if not allowed:
            results.append(_finding(f"NAV_{prefix}_{index}", "warning",
                "Destino não é uma URL HTTP(S) verificável", evidence=element,
                severity="medium", recommendation="Revisar protocolo e ação do link."))
        elif parts.fragment and parts.netloc.lower() == urlsplit(page_url).netloc.lower() and (
            parts.path or "/") == (urlsplit(page_url).path or "/"):
            exists = _fragment_exists(soup, parts.fragment)
            results.append(_finding(f"NAV_{prefix}_{index}",
                "passed" if exists else "failed",
                "Âncora interna encontrada" if exists else "Âncora interna inexistente",
                evidence=element, severity="info" if exists else "medium",
                recommendation="Corrigir o identificador da âncora." if not exists else ""))
        else:
            results.append(_finding(f"NAV_{prefix}_{index}", "not_verified",
                "Destino identificado; disponibilidade não testada", evidence=element,
                recommendation="Verificar HTTP/navegação separadamente, por meio do fetcher protegido."))

    for index, button in enumerate(soup.find_all("button"), 1):
        text = button.get_text(" ", strip=True) or str(button.get("aria-label") or "").strip()
        if not (CTA_TERMS.search(text) or button.get("data-cta")):
            continue
        button_type = str(button.get("type") or "submit").lower()
        in_form = button.find_parent("form") is not None
        results.append(_finding(f"NAV_BUTTON_CTA_{index}", "not_verified",
            "CTA identificado; ação não executada", evidence={"tag": "button",
                "id": button.get("id"), "text": text, "type": button_type,
                "selector": _element_selector(button),
                "element_html": str(button)[:1000],
                "inside_form": in_form},
            recommendation="Validar a ação em teste autorizado. O Page Check não envia formulários."))
    return results
