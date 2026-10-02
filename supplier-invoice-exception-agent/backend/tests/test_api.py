from fastapi.testclient import TestClient

from app.api.main import app


def test_health_reports_database_status():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["database"] == "ok"


def test_workflow_api_persists_pause_and_resumes_after_approval():
    with TestClient(app) as client:
        started = client.post("/api/agent/run", json={"invoice_id": "INV-1002"})
        assert started.status_code == 200
        initial = started.json()
        assert initial["status"] == "awaiting_approval"
        assert initial["pending_approval"] is True
        assert not any(tool["tool"] == "place_invoice_on_hold" for tool in initial["tool_results"])

        saved = client.get(f"/api/workflows/{initial['workflow_id']}")
        assert saved.status_code == 200
        assert saved.json()["status"] == "awaiting_approval"

        completed = client.post(f"/api/approval/{initial['workflow_id']}", json={"decision": "APPROVE", "reviewer": "test-controller", "rationale": "Verified source records"})
        assert completed.status_code == 200
        result = completed.json()
        assert result["status"] == "completed"
        assert any(tool["tool"] == "place_invoice_on_hold" and tool["ok"] for tool in result["tool_results"])
        assert "Invoice hold placed after human approval" in result["final_response"]


def test_chat_requires_invoice_identifier():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "Please check this invoice"})
        assert response.status_code == 422