from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "RBAC Gateway"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    DATABASE_URL: str
    REDIS_URL: str
    INVENTORY_API_BASE_URL: str

    # Pydantic v2 syntax to read from the .env file
    # extra="ignore" means if there are extra variables in .env, don't crash
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Instantiate the settings so we can import them anywhere in the app
settings = Settings()