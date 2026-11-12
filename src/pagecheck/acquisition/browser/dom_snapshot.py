"""Obtém DOM já renderizado em uma página controlada pelo chamador."""
from __future__ import annotations

from playwright.sync_api import Page


def snapshot_dom(page: Page) -> dict[str, str]:
    """Não navega, não clica, não habilita JS nem configura rede."""
    return {"html": page.content(), "url": page.url}
