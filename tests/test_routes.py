"""Route smoke tests."""


def test_dashboard_loads(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "TradeEdge" in resp.text or "Performance" in resp.text


def test_major_routes(client):
    for path in [
        "/trades",
        "/trades/new",
        "/trades/import",
        "/journal",
        "/journal/new",
        "/analytics",
        "/risk-management",
        "/calendar",
        "/settings",
        "/health",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} returned {resp.status_code}"


def test_api_open(client):
    resp = client.get("/api/analytics/distribution?period=all")
    assert resp.status_code == 200
    data = resp.json()
    assert "labels" in data


def test_calendar_loads_with_aware_dates(client):
    resp = client.get("/calendar")
    assert resp.status_code == 200
    assert "Profitable" in resp.text or "Month" in resp.text or "calendar" in resp.text.lower()
