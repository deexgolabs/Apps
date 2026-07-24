from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 168
    cors_origins: str = "http://localhost:3000"
    debug: bool = True
    app_name: str = "Plataforma de Apps"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    platform_mercado_pago_token: str = ""
    platform_paypal_client_id: str = ""
    platform_paypal_client_secret: str = ""
    platform_pagseguro_token: str = ""

    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_claims_email: str = ""

    facebook_app_id: str = ""
    facebook_app_secret: str = ""

    sentry_dsn: str = ""

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
