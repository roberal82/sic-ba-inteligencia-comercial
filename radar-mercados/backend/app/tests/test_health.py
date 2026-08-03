def test_health_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "demo"
    assert "time" in body


def test_system_status_ok(client):
    response = client.get("/api/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["database_ok"] is True
    assert body["app_mode"] == "demo"
