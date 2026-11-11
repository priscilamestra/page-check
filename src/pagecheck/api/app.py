"""Composição da API; as rotas de auditoria serão integradas por módulos."""
from fastapi import FastAPI

app = FastAPI(
    title="Page Check API",
    description="API local de auditoria de landing pages (em desenvolvimento).",
    version="0.1.0",
)

@app.get('/health', tags=['system'])
def health() -> dict[str, str]:
    """Endpoint inicial real, usado para validar a conexão com a interface."""
    return {'status': 'ok', 'service': 'pagecheck-api'}
