import pytest

from app.services import (
    argentina_service,
    brazil_service,
    crypto_service,
    fallback_service,
    paraguay_service,
)


def test_demo_indicators_shape():
    items = fallback_service.demo_indicators()
    assert len(items) > 20
    for item in items:
        assert item["data_status"] == "demo"
        assert item["value"] is not None
        assert item["source"]


def test_demo_events_have_geolocation():
    events = fallback_service.demo_events()
    assert len(events) > 0
    for event in events:
        assert -90 <= event["latitude"] <= 90
        assert -180 <= event["longitude"] <= 180
        assert event["severity"] in ("low", "medium", "high")


@pytest.mark.asyncio
async def test_paraguay_service_always_demo():
    """Paraguay no tiene API publica documentada: siempre debe marcarse como demo."""
    items = await paraguay_service.get_indicators()
    assert len(items) > 0
    assert all(item["data_status"] == "demo" for item in items)


@pytest.mark.asyncio
async def test_brazil_service_demo_mode(monkeypatch):
    from app.core import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("APP_MODE", "demo")
    config.get_settings.cache_clear()
    from app.services import brazil_service as bs

    bs.settings = config.get_settings()
    items = await bs.get_indicators()
    assert all(item["country"] == "brasil" for item in items)


@pytest.mark.asyncio
async def test_argentina_service_demo_mode():
    items = await argentina_service.get_indicators()
    assert all(item["country"] == "argentina" for item in items)


@pytest.mark.asyncio
async def test_crypto_service_demo_mode():
    items = await crypto_service.get_indicators()
    symbols = {item["symbol"] for item in items}
    assert symbols == {"BTC", "ETH"}
