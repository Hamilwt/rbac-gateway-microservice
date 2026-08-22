from fastapi import FastAPI
from app.core.config import settings
from app.api import auth, users  # <-- Add users here

app = FastAPI(title=settings.PROJECT_NAME)

# Include our API routers
app.include_router(auth.router)
app.include_router(users.router) # <-- Add this line

@app.get("/health")
def health_check():
    """
    A simple endpoint to verify the API is running and reading config properly.
    We mask the database credentials before returning them as a security best practice.
    """
    safe_db_url = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "Not Configured"
    
    return {
        "status": "ok", 
        "project": settings.PROJECT_NAME,
        "database_host": safe_db_url
    }