"""
Tests for the FastAPI application.
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.app import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_ready_endpoint():
    """Test readiness check endpoint."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_root_endpoint():
    """Test root endpoint returns forecast data."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "forecast_generated" in data
    assert "locations" in data
    assert "filters" in data


def test_root_with_location_filter():
    """Test root endpoint with location filter."""
    response = client.get("/?location=A")
    assert response.status_code == 200
    data = response.json()
    assert data["filters"]["location"] == "A"
    assert "A" in data["locations"]
    assert "B" not in data["locations"]
    assert "C" not in data["locations"]


def test_root_with_invalid_location():
    """Test root endpoint with invalid location."""
    response = client.get("/?location=Z")
    assert response.status_code == 400
    assert "Invalid location" in response.json()["detail"]


def test_root_with_date_filter():
    """Test root endpoint with date filter."""
    response = client.get("/?date=2026-02-15")
    assert response.status_code == 200
    data = response.json()
    assert data["filters"]["date"] == "2026-02-15"


def test_root_with_location_and_date():
    """Test root endpoint with both filters."""
    response = client.get("/?location=B&date=2026-02-15")
    assert response.status_code == 200
    data = response.json()
    assert data["filters"]["location"] == "B"
    assert data["filters"]["date"] == "2026-02-15"
