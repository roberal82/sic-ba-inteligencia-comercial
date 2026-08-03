from app.services import analysis_service


def _indicator(symbol: str, change_percent: float, **extra) -> dict:
    base = {"symbol": symbol, "change_percent": change_percent, "value": 100.0}
    base.update(extra)
    return base


def test_global_energy_rule_triggers_on_severe_event_and_oil_spike():
    indicators = [_indicator("BRENT", 4.5), _indicator("DXY", 0.5)]
    events = [
        {"title": "Bloqueo en Ormuz", "region": "Golfo Persico", "severity": "high"},
    ]
    result = analysis_service.analyze_global_energy(indicators, events)
    assert result is not None
    assert result["scope"] == "global"
    assert "energetico" in result["summary"].lower() or "energia" in result["summary"].lower()


def test_global_energy_rule_does_not_trigger_without_event():
    indicators = [_indicator("BRENT", 4.5)]
    events = []
    result = analysis_service.analyze_global_energy(indicators, events)
    assert result is None


def test_argentina_tactical_rule_triggers():
    indicators = [
        _indicator("RIESGO_PAIS", -5),
        _indicator("MERV", 3),
        _indicator("RESERVAS", 2),
        _indicator("USDARS_MEP", 0.5),
    ]
    result = analysis_service.analyze_argentina_tactical(indicators, [])
    assert result is not None
    assert result["scope"] == "argentina"


def test_paraguay_import_pressure_rule_triggers():
    indicators = [
        _indicator("USDPYG", 1.5),
        _indicator("IPC", 0.8),
        _indicator("SOJA_PY", -2.0),
    ]
    result = analysis_service.analyze_paraguay_import_pressure(indicators)
    assert result is not None
    assert result["scope"] == "paraguay"


def test_run_all_always_returns_regional_summary():
    results = analysis_service.run_all([], [])
    scopes = {r["scope"] for r in results}
    assert "regional" in scopes
    for r in results:
        assert "generated_at" in r
        assert isinstance(r["positive_factors"], list)
