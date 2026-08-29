from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from scalar_fastapi import get_scalar_api_reference

from app.core.config import settings
from app.api import auth, users, gateway, roles

# Disable default Swagger (docs_url=None) so Scalar can take over the /docs route
app = FastAPI(title=settings.PROJECT_NAME, docs_url=None, redoc_url=None)

@app.get("/", include_in_schema=False)
async def root():
    """Redirects the bare root URL to the interactive API docs."""
    return RedirectResponse(url="/docs")

# Include our API routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(gateway.router)
app.include_router(roles.router)

@app.get("/docs", include_in_schema=False)
async def scalar_html():
    """
    Renders the Scalar UI API documentation.
    """
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=f"{settings.PROJECT_NAME} - API Reference",
    )

@app.get("/health", tags=["default"])
def health_check():
    """
    Health check endpoint to verify the API is running and database is configured.
    """
    safe_db_url = (
        settings.DATABASE_URL.split("@")[-1]
        if "@" in settings.DATABASE_URL
        else "Not Configured"
    )
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "database_host": safe_db_url,
    }