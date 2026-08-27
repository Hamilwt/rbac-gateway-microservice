from fastapi import FastAPI

from app.api import auth, proxy, users  # <-- Add proxy here
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# Include our API routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(proxy.router)  # <-- Add this line


@app.get("/health")
def health_check():
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
