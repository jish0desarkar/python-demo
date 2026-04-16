from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:////app/data/app.db"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "phi3:mini"
    ollama_timeout_seconds: int = 120
    app_name: str = "python-demo"
    app_base_url: str = "http://web:8000"
    webhook_url: str = "https://eofu3tzjzuyrmev.m.pipedream.net"
    webhook_secret: str = "super-secret-key"


settings = Settings()
