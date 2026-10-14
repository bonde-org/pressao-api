from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "pressao-api"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40

    # Keycloak
    KEYCLOAK_URL: str
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_CLIENT_SECRET: str
    KEYCLOAK_ADMIN_URL: str | None = None

    # Providers
    SENDGRID_API_KEY: str
    SENDGRID_SANDBOX_MODE: bool = True
    SENDGRID_WEBHOOK_VERIFICATION_KEY: str = ""
    SENDGRID_WEBHOOK_URL: str = "/api/v1/webhooks/sendgrid"
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_API_KEY_SID: str = ""
    TWILIO_API_KEY_SECRET: str = ""
    TWILIO_SANDBOX_MODE: bool = True
    # Absoluta e pública (https://host/api/v1/webhooks/twilio): o Twilio assina essa URL
    TWILIO_WEBHOOK_URL: str = "/api/v1/webhooks/twilio"
    TELEFONE_TIMEOUT_TOQUE_SEG: int = 30

    # Monitoring
    METRICS_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


settings = Settings()
