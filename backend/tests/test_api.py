def test_dev_login_dashboard_and_chat(client):
    login = client.post("/auth/dev-login", json={"user_type": "startup"})
    assert login.status_code == 200
    org_id = login.json()["organization_id"]
    headers = {"x-org-id": org_id}

    dashboard = client.get("/dashboard/summary", headers=headers)
    assert dashboard.status_code == 200
    data = dashboard.json()
    assert round(data["metrics"]["current_cash"]) == 2300000
    assert data["metrics"]["runway_months"] > 0

    chat = client.post("/chat", headers=headers, json={"question": "Can I hire one engineer at ₹1.8L/month?"})
    assert chat.status_code == 200
    body = chat.json()
    assert "simulate_hiring" in body["tools_used"]
    assert body["verification"]["passed"] is True
    assert body["audit_log_id"]


def test_freelancer_receivables_workflow(client):
    login = client.post("/auth/dev-login", json={"user_type": "freelancer"})
    org_id = login.json()["organization_id"]
    headers = {"x-org-id": org_id}

    response = client.post("/workflows/receivables", headers=headers)
    assert response.status_code == 200
    feed = client.get("/feed", headers=headers)
    assert feed.status_code == 200
    assert any(action["action_type"] == "email_draft" for action in feed.json()["actions"])

