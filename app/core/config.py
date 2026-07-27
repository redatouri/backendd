from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://moviecam:moviecam@moviecam_database:5432/moviecam"
    )
    jwt_secret: str = "development-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    cors_origins: list[str] = ["http://localhost:3000"]
    media_root: str = "/app/media"
    media_url_prefix: str = "/media"
    admin_email: str = "admin@moviecam.ma"
    admin_password: str = "changeme"
    order_number_prefix: str = "MC"
    shipping_flat_rate: Decimal = Decimal("49.00")
    free_shipping_threshold: Decimal = Decimal("2000.00")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
