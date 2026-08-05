"""Authentication removed — dashboard is open for personal use."""


def test_dashboard_open_without_login(client):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 200
    assert "Performance" in resp.text or "TradeEdge" in resp.text


def test_login_route_gone(client):
    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code == 404


def test_logout_route_gone(client):
    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code == 404
