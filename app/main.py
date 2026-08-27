from fastapi import FastAPI
from app.core.config import settings
from app.api import auth, users, gateway, roles

app = FastAPI(title=settings.PROJECT_NAME)

# Include our API routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(gateway.router)
app.include_router(roles.router)

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