from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

@app.get("/health")
def health_check():
    """
    A simple endpoint to verify the API is running and reading config properly.
    We mask the database credentials before returning them as a security best practice.
    """
    # Split splits the string at the '@' symbol. We only return the host/port part.
    safe_db_url = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "Not Configured"
    
    return {
        "status": "ok", 
        "project": settings.PROJECT_NAME,
        "database_host": safe_db_url
    }