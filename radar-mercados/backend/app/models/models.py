"""Modelos SQLAlchemy del dominio de mercados, eventos, analisis y escenarios."""
import datetime as dt
import uuid

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class MarketIndicator(Base):
    """Un valor puntual de un indicador de mercado (indice, FX, tasa, commodity, cripto, etc.)."""

    __tablename__ = "market_indicators"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    country: Mapped[str] = mapped_column(String(32), index=True)
    market: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32), default="")
    currency: Mapped[str] = mapped_column(String(8), default="")
    previous_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    change: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    source: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str] = mapped_column(String(512), default="")
    data_status: Mapped[str] = mapped_column(String(16), default="demo")  # live|delayed|estimated|demo|unavailable
    delayed_minutes: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)


class GeopoliticalEvent(Base):
    __tablename__ = "geopolitical_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(256))
    summary: Mapped[str] = mapped_column(Text)
    country: Mapped[str] = mapped_column(String(64))
    region: Mapped[str] = mapped_column(String(64))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)  # low|medium|high
    probability: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str] = mapped_column(String(512), default="")
    published_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    assets_affected: Mapped[list] = mapped_column(JSON, default=list)
    sectors_affected: Mapped[list] = mapped_column(JSON, default=list)
    expected_direction: Mapped[str] = mapped_column(String(16), default="neutral")  # up|down|neutral
    time_horizon: Mapped[str] = mapped_column(String(32), default="corto plazo")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)


class MarketAnalysis(Base):
    __tablename__ = "market_analysis"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    scope: Mapped[str] = mapped_column(String(32), index=True)  # regional|brasil|paraguay|argentina|global
    title: Mapped[str] = mapped_column(String(256))
    summary: Mapped[str] = mapped_column(Text)
    positive_factors: Mapped[list] = mapped_column(JSON, default=list)
    negative_factors: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    opportunities: Mapped[list] = mapped_column(JSON, default=list)
    affected_assets: Mapped[list] = mapped_column(JSON, default=list)
    time_horizon: Mapped[str] = mapped_column(String(32), default="medio plazo")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    generated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    methodology: Mapped[str] = mapped_column(Text, default="")


class PortfolioScenario(Base):
    __tablename__ = "portfolio_scenarios"

    profile: Mapped[str] = mapped_column(String(16), primary_key=True)  # conservador|moderado|agresivo
    liquidity: Mapped[float] = mapped_column(Float)
    fixed_income: Mapped[float] = mapped_column(Float)
    gold: Mapped[float] = mapped_column(Float)
    global_equities: Mapped[float] = mapped_column(Float)
    brazil: Mapped[float] = mapped_column(Float)
    paraguay: Mapped[float] = mapped_column(Float)
    argentina: Mapped[float] = mapped_column(Float)
    commodities: Mapped[float] = mapped_column(Float)
    crypto: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String(16))
