"""Configuracion centralizada de la aplicacion, leida desde variables de entorno."""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Radar Regional de Mercados"
    app_version: str = "1.0.0"
    app_mode: Literal["demo", "production"] = Field(default="demo", validation_alias="APP_MODE")

    database_url: str = Field(
        default="sqlite:///./radar_mercados.db", validation_alias="DATABASE_URL"
    )
    redis_url: str | None = Field(default=None, validation_alias="REDIS_URL")

    cors_origins: str = Field(default="*", validation_alias="CORS_ORIGINS")

    # Claves de proveedores externos (opcionales). Sin clave, el servicio cae a fallback.
    alpha_vantage_api_key: str | None = Field(default=None, validation_alias="ALPHA_VANTAGE_API_KEY")
    twelve_data_api_key: str | None = Field(default=None, validation_alias="TWELVE_DATA_API_KEY")
    polygon_api_key: str | None = Field(default=None, validation_alias="POLYGON_API_KEY")
    news_api_key: str | None = Field(default=None, validation_alias="NEWS_API_KEY")
    fred_api_key: str | None = Field(default=None, validation_alias="FRED_API_KEY")

    admin_token: str = Field(default="", validation_alias="ADMIN_TOKEN")

    http_timeout_seconds: float = Field(default=8.0, validation_alias="HTTP_TIMEOUT_SECONDS")
    http_max_retries: int = Field(default=2, validation_alias="HTTP_MAX_RETRIES")
    cache_ttl_seconds: int = Field(default=300, validation_alias="CACHE_TTL_SECONDS")

    refresh_minutes_markets: int = Field(default=15, validation_alias="REFRESH_MINUTES_MARKETS")
    refresh_minutes_macro: int = Field(default=1440, validation_alias="REFRESH_MINUTES_MACRO")
    refresh_minutes_news: int = Field(default=15, validation_alias="REFRESH_MINUTES_NEWS")
    refresh_minutes_events: int = Field(default=15, validation_alias="REFRESH_MINUTES_EVENTS")

    rate_limit_per_minute: int = Field(default=120, validation_alias="RATE_LIMIT_PER_MINUTE")

    enable_scheduler: bool = Field(default=True, validation_alias="ENABLE_SCHEDULER")

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_demo(self) -> bool:
        return self.app_mode == "demo"


@lru_cache
def get_settings() -> Settings:
    return Settings()
