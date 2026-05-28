from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    smtp_server: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    redis_url: str
    debug: bool = True

    class Config:
        env_file = ".env"

settings = Settings()