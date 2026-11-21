from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_NAME: str = "smartbaku"
    DB_USER: str = "smartbaku"
    DB_PASSWORD: str = "smartbaku2026"
    CBAR_URL: str = "https://www.cbar.az/currencies/{date}.xml"
    CBAR_TIMEOUT: int = 5
    EDV_RATE: float = 18.0

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
