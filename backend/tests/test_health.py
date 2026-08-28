def test_health_returns_200_with_service_and_database_status(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "ats-cv-backend"
    assert body["database"]["status"] in {"ok", "unavailable"}