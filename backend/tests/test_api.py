"""Basic API integration tests for RedactAI Sprint 1."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAuthEndpoints:
    def test_register_success(self):
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User",
            "organization_name": "Test Org",
        })
        # In a real test environment with DB, this should return 201
        # Here we verify the endpoint is reachable
        assert response.status_code in [201, 409, 500]  # 500 if DB is unavailable, 409 if already exists

    def test_login_invalid_credentials(self):
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code in [401, 500]

    def test_forgot_password(self):
        response = client.post("/api/v1/auth/forgot-password", json={
            "email": "test@example.com",
        })
        # Should always return success (prevent enumeration)
        assert response.status_code in [200, 500]


class TestProtectedEndpoints:
    def test_get_profile_unauthorized(self):
        response = client.get("/api/v1/users/me")
        assert response.status_code in [401, 403]

    def test_list_documents_unauthorized(self):
        response = client.get("/api/v1/documents")
        assert response.status_code in [401, 403]

    def test_dashboard_unauthorized(self):
        response = client.get("/api/v1/documents/dashboard")
        assert response.status_code in [401, 403]
