"""Esquemas Pydantic para validacion y documentacion OpenAPI."""
import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DataStatus = Literal["live", "delayed", "estimated", "demo", "unavailable"]


class MarketIndicatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    country: str
    market: str
    symbol: str
    name: str
    category: str
    value: float
    unit: str = ""
    currency: str = ""
    previous_value: float | None = None
    change: float | None = None
    change_percent: float | None = None
    timestamp: dt.datetime
    source: str
    source_url: str = ""
    data_status: DataStatus = "demo"
    delayed_minutes: int = 0
    confidence: float = 0.5


class GeopoliticalEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: str
    country: str
    region: str
    latitude: float
    longitude: float
    event_type: str
    severity: Literal["low", "medium", "high"]
    probability: float
    source: str
    source_url: str = ""
    published_at: dt.datetime
    assets_affected: list[str] = Field(default_factory=list)
    sectors_affected: list[str] = Field(default_factory=list)
    expected_direction: Literal["up", "down", "neutral"] = "neutral"
    time_horizon: str = "corto plazo"
    confidence: float = 0.5


class MarketAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scope: str
    title: str
    summary: str
    positive_factors: list[str] = Field(default_factory=list)
    negative_factors: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    affected_assets: list[str] = Field(default_factory=list)
    time_horizon: str
    confidence: float
    generated_at: dt.datetime
    methodology: str
    scenario_base: str = ""
    scenario_optimistic: str = ""
    scenario_adverse: str = ""
    disclaimer: str = (
        "Este analisis es educativo e informativo. No constituye asesoramiento financiero "
        "personalizado ni garantia de rendimiento."
    )


class PortfolioScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile: Literal["conservador", "moderado", "agresivo"]
    liquidity: float
    fixed_income: float
    gold: float
    global_equities: float
    brazil: float
    paraguay: float
    argentina: float
    commodities: float
    crypto: float
    explanation: str
    risk_level: str
    disclaimer: str = (
        "Exposicion orientativa con fines educativos. No constituye asesoramiento financiero "
        "personalizado ni recomendacion de compra o venta."
    )


class SourceStatus(BaseModel):
    name: str
    country: str
    category: str
    status: Literal["operativo", "degradado", "no_disponible", "pendiente_credenciales"]
    last_success: dt.datetime | None = None
    last_error: str | None = None
    notes: str = ""


class SystemStatusOut(BaseModel):
    app_mode: str
    app_version: str
    server_time: dt.datetime
    database_ok: bool
    cache_backend: str
    scheduler_enabled: bool
    jobs: list[dict]


class DashboardOut(BaseModel):
    mode: str
    generated_at: dt.datetime
    country: str
    period_days: int
    kpis: list[MarketIndicatorOut]
    indicators: list[MarketIndicatorOut]
    events: list[GeopoliticalEventOut]
    analysis: list[MarketAnalysisOut]
    sources: list[SourceStatus]
