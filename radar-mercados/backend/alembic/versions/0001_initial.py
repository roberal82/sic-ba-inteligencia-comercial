"""esquema inicial: indicadores, eventos, analisis, escenarios

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_indicators",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("country", sa.String(32), index=True),
        sa.Column("market", sa.String(64)),
        sa.Column("symbol", sa.String(32), index=True),
        sa.Column("name", sa.String(128)),
        sa.Column("category", sa.String(32), index=True),
        sa.Column("value", sa.Float),
        sa.Column("unit", sa.String(32)),
        sa.Column("currency", sa.String(8)),
        sa.Column("previous_value", sa.Float, nullable=True),
        sa.Column("change", sa.Float, nullable=True),
        sa.Column("change_percent", sa.Float, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), index=True),
        sa.Column("source", sa.String(128)),
        sa.Column("source_url", sa.String(512)),
        sa.Column("data_status", sa.String(16)),
        sa.Column("delayed_minutes", sa.Integer),
        sa.Column("confidence", sa.Float),
    )
    op.create_table(
        "geopolitical_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(256)),
        sa.Column("summary", sa.Text),
        sa.Column("country", sa.String(64)),
        sa.Column("region", sa.String(64)),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column("event_type", sa.String(32), index=True),
        sa.Column("severity", sa.String(16), index=True),
        sa.Column("probability", sa.Float),
        sa.Column("source", sa.String(128)),
        sa.Column("source_url", sa.String(512)),
        sa.Column("published_at", sa.DateTime(timezone=True), index=True),
        sa.Column("assets_affected", sa.JSON),
        sa.Column("sectors_affected", sa.JSON),
        sa.Column("expected_direction", sa.String(16)),
        sa.Column("time_horizon", sa.String(32)),
        sa.Column("confidence", sa.Float),
    )
    op.create_table(
        "market_analysis",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scope", sa.String(32), index=True),
        sa.Column("title", sa.String(256)),
        sa.Column("summary", sa.Text),
        sa.Column("positive_factors", sa.JSON),
        sa.Column("negative_factors", sa.JSON),
        sa.Column("risks", sa.JSON),
        sa.Column("opportunities", sa.JSON),
        sa.Column("affected_assets", sa.JSON),
        sa.Column("time_horizon", sa.String(32)),
        sa.Column("confidence", sa.Float),
        sa.Column("generated_at", sa.DateTime(timezone=True)),
        sa.Column("methodology", sa.Text),
    )
    op.create_table(
        "portfolio_scenarios",
        sa.Column("profile", sa.String(16), primary_key=True),
        sa.Column("liquidity", sa.Float),
        sa.Column("fixed_income", sa.Float),
        sa.Column("gold", sa.Float),
        sa.Column("global_equities", sa.Float),
        sa.Column("brazil", sa.Float),
        sa.Column("paraguay", sa.Float),
        sa.Column("argentina", sa.Float),
        sa.Column("commodities", sa.Float),
        sa.Column("crypto", sa.Float),
        sa.Column("explanation", sa.Text),
        sa.Column("risk_level", sa.String(16)),
    )


def downgrade() -> None:
    op.drop_table("portfolio_scenarios")
    op.drop_table("market_analysis")
    op.drop_table("geopolitical_events")
    op.drop_table("market_indicators")
