def test_dashboard_default(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "demo"
    assert len(body["kpis"]) > 0
    assert len(body["indicators"]) > 0
    assert len(body["events"]) > 0
    assert len(body["analysis"]) > 0
    assert all(i["data_status"] == "demo" for i in body["indicators"])


def test_dashboard_country_filter(client):
    response = client.get("/api/dashboard", params={"country": "brasil"})
    body = response.json()
    assert all(i["country"] == "brasil" for i in body["indicators"])


def test_markets_by_country(client):
    response = client.get("/api/markets/paraguay")
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(i["country"] == "paraguay" for i in body)


def test_markets_invalid_country(client):
    response = client.get("/api/markets/atlantida")
    assert response.status_code == 404


def test_events_endpoint(client):
    response = client.get("/api/events", params={"severity": "high"})
    assert response.status_code == 200
    body = response.json()
    assert all(e["severity"] == "high" for e in body)


def test_events_map_shape(client):
    response = client.get("/api/events/map")
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    for event in body:
        assert "latitude" in event and "longitude" in event


def test_scenarios_endpoint(client):
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    body = response.json()
    profiles = {s["profile"] for s in body}
    assert profiles == {"conservador", "moderado", "agresivo"}


def test_sources_endpoint(client):
    response = client.get("/api/sources")
    assert response.status_code == 200
    body = response.json()
    assert any(s["status"] == "pendiente_credenciales" for s in body)
