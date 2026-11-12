"""Composição da API; novas rotas entram por routers isolados."""

from fastapi import FastAPI
from pagecheck.api.routes.pages import router as pages_router
from pagecheck.api.routes.seo import router as seo_router
from pagecheck.api.routes.audit import router as audit_router

app = FastAPI(
    title="Page Check API",
    description="API local de auditoria de landing pages (em desenvolvimento).",
    version="0.1.0",
)

app.include_router(pages_router)
app.include_router(seo_router)
app.include_router(audit_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Endpoint de saúde da API."""
    return {"status": "ok", "service": "pagecheck-api"}
