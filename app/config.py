from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # database
    DATABASE_URL: str 

    # redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # WhatsApp / Meta
    WHATSAPP_API_URL: str | None = None
    WHATSAPP_ACCESS_TOKEN: str | None = None
    WHATSAPP_VERIFY_TOKEN: str = ""  # used for webhook security/verification
    APP_ID: str | None = None
    APP_SECRET: str | None = None

    # LLM
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o"
    OLLAMA_URL: str = 'http://localhost:11434/v1'
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_KEY: str = 'ollama_key'  # Only needed if Ollama is configured to require authentication

    # twilio
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None

    # optional ngrok
    NGROK_AUTHTOKEN: str | None = None

    # general
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file= BASE_DIR/".env", env_file_encoding="utf-8")


def get_settings() -> Settings:
    return Settings()

