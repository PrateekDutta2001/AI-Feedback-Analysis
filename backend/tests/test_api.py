"""API integration tests."""

from __future__ import annotations


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"healthy", "degraded"}
    assert "database" in body
    assert "models" in body


def test_create_and_retrieve_feedback(client):
    payload = {
        "customer_id": "CU-TEST-1",
        "text": "Delivery was extremely late and customer support did not respond.",
        "product": "InsightPortal",
        "department": "Operations",
        "channel": "Email",
        "location": "Ahmedabad",
        "segment": "Enterprise",
        "rating": 1,
    }
    created = client.post("/api/feedback", json=payload)
    assert created.status_code == 201
    data = created.json()["data"]
    assert data["analysis"]["sentiment"]["label"] in {"negative", "positive", "neutral"}
    detail = client.get(f"/api/feedback/{data['id']}")
    assert detail.status_code == 200
    assert "extremely late" in detail.json()["data"]["text"]


def test_feedback_list_and_filters(client):
    response = client.get("/api/feedback?page=1&page_size=5")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "total" in body["meta"]


def test_analyze_endpoint(client):
    response = client.post(
        "/api/feedback/analyze",
        json={"text": "I love the new dashboard, it is fast and clean.", "rating": 5},
    )
    assert response.status_code == 200
    analysis = response.json()["data"]
    assert analysis["sentiment"]["label"] in {"positive", "neutral", "negative"}
    assert "priority" in analysis
    assert analysis["severity"]["severity"] >= 1


def test_dashboard(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "kpis" in data
    assert "charts" in data
    assert "insights" in data


def test_analytics_endpoints(client):
    for path in (
        "/api/analytics/sentiment",
        "/api/analytics/trends",
        "/api/analytics/categories",
        "/api/analytics/emotions",
        "/api/analytics/departments",
        "/api/analytics/products",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["success"] is True


def test_insights_and_alerts(client):
    insights = client.get("/api/insights")
    assert insights.status_code == 200
    alerts = client.get("/api/alerts")
    assert alerts.status_code == 200


def test_upload_preview_rejects_non_csv(client):
    response = client.post("/api/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 400


def test_csv_import_and_export(client):
    csv_bytes = (
        "feedback_id,customer_id,text,date,product,department,channel,location,segment,rating,status\n"
        "FB-CSV-1,CU-9,The delivery was late and support did not help,2026-07-01,InsightPay,Operations,Email,Surat,SMB,2,open\n"
    ).encode("utf-8")
    preview = client.post("/api/upload", files={"file": ("batch.csv", csv_bytes, "text/csv")})
    assert preview.status_code == 200
    imported = client.post("/api/import", files={"file": ("batch.csv", csv_bytes, "text/csv")})
    assert imported.status_code == 200
    assert imported.json()["data"]["imported"] >= 1
    export_csv = client.get("/api/export/csv")
    assert export_csv.status_code == 200
    assert "text" in export_csv.headers.get("content-type", "")
    export_json = client.get("/api/export/json")
    assert export_json.status_code == 200


def test_validation_error_shape(client):
    response = client.post("/api/feedback", json={"text": "x"})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
