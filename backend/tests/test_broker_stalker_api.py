"""Integration tests for Broker Stalker API endpoints."""
import pytest
from fastapi.testclient import TestClient
import tempfile
import os
from main import app
from db import DatabaseConnection, BrokerStalkerRepository


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    DatabaseConnection(db_path=path)
    
    yield path
    
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestBrokerStalkerAPI:
    """Test suite for Broker Stalker API endpoints."""
    
    def test_health_check_includes_broker_stalker(self, client):
        """Test that health check includes broker_stalker feature."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "broker_stalker" in data["features"]
    
    def test_get_empty_watchlist(self, client):
        """Test getting empty watchlist."""
        response = client.get("/api/broker-stalker/watchlist")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 0
        assert data["brokers"] == []
    
    def test_add_broker_to_watchlist(self, client):
        """Test adding a broker to watchlist."""
        payload = {
            "broker_code": "YP",
            "broker_name": "Yuanta Securities",
            "description": "Test broker"
        }
        
        response = client.post("/api/broker-stalker/watchlist", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["broker_code"] == "YP"
        assert "power_level" in data
    
    def test_add_broker_without_optional_fields(self, client):
        """Test adding broker with only required fields."""
        payload = {"broker_code": "RK"}
        
        response = client.post("/api/broker-stalker/watchlist", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
    
    def test_get_watchlist_after_adding(self, client):
        """Test getting watchlist after adding brokers."""
        client.post("/api/broker-stalker/watchlist", json={"broker_code": "YP"})
        client.post("/api/broker-stalker/watchlist", json={"broker_code": "RK"})
        
        response = client.get("/api/broker-stalker/watchlist")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 2
        assert len(data["brokers"]) == 2
    
    def test_remove_broker_from_watchlist(self, client):
        """Test removing a broker from watchlist."""
        client.post("/api/broker-stalker/watchlist", json={"broker_code": "YP"})
        
        response = client.delete("/api/broker-stalker/watchlist/YP")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        watchlist_response = client.get("/api/broker-stalker/watchlist")
        assert watchlist_response.json()["count"] == 0
    
    def test_get_broker_portfolio_empty(self, client):
        """Test getting empty broker portfolio."""
        response = client.get("/api/broker-stalker/portfolio/YP")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["total_positions"] == 0
        assert data["portfolio"] == []
    
    def test_get_broker_portfolio_with_min_value(self, client):
        """Test getting broker portfolio with minimum value filter."""
        response = client.get("/api/broker-stalker/portfolio/YP?min_net_value=1000000000")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
    
    def test_get_broker_analysis(self, client):
        """Test getting broker analysis."""
        response = client.get("/api/broker-stalker/analysis/YP/BBCA")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "analysis" in data
    
    def test_get_broker_analysis_with_lookback(self, client):
        """Test getting broker analysis with custom lookback."""
        response = client.get("/api/broker-stalker/analysis/YP/BBCA?lookback_days=60")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
    
    def test_get_chart_data(self, client):
        """Test getting chart data."""
        response = client.get("/api/broker-stalker/chart/YP/BBCA")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["broker_code"] == "YP"
        assert data["ticker"] == "BBCA"
        assert "data" in data
    
    def test_get_chart_data_with_days(self, client):
        """Test getting chart data with custom days."""
        response = client.get("/api/broker-stalker/chart/YP/BBCA?days=14")
        assert response.status_code == 200
        
        data = response.json()
        assert data["days"] == 14
    
    def test_get_execution_ledger(self, client):
        """Test getting execution ledger."""
        response = client.get("/api/broker-stalker/ledger/YP/BBCA")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "ledger" in data
    
    def test_get_execution_ledger_with_limit(self, client):
        """Test getting execution ledger with custom limit."""
        response = client.get("/api/broker-stalker/ledger/YP/BBCA?limit=20")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
    
    def test_sync_broker_data(self, client):
        """Test syncing broker data."""
        payload = {"days": 7}
        
        response = client.post("/api/broker-stalker/sync/YP", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "sync_result" in data
    
    def test_sync_broker_data_with_ticker(self, client):
        """Test syncing broker data for specific ticker."""
        payload = {"ticker": "BBCA", "days": 7}
        
        response = client.post("/api/broker-stalker/sync/YP", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
    
    def test_get_ticker_broker_activity(self, client):
        """Test getting ticker broker activity."""
        response = client.get("/api/broker-stalker/ticker/BBCA/activity")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["ticker"] == "BBCA"
        assert "activity" in data
    
    def test_get_ticker_broker_activity_with_days(self, client):
        """Test getting ticker broker activity with custom days."""
        response = client.get("/api/broker-stalker/ticker/BBCA/activity?days=14")
        assert response.status_code == 200
        
        data = response.json()
        assert data["days"] == 14
    
    def test_calculate_power_level(self, client):
        """Test calculating power level."""
        response = client.get("/api/broker-stalker/power-level/YP")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["broker_code"] == "YP"
        assert "power_level" in data
    
    def test_calculate_power_level_with_lookback(self, client):
        """Test calculating power level with custom lookback."""
        response = client.get("/api/broker-stalker/power-level/YP?lookback_days=60")
        assert response.status_code == 200
        
        data = response.json()
        assert data["lookback_days"] == 60
    
    def test_invalid_broker_code_format(self, client):
        """Test API handles invalid broker code gracefully."""
        response = client.get("/api/broker-stalker/portfolio/")
        assert response.status_code == 404
    
    def test_invalid_query_parameters(self, client):
        """Test API handles invalid query parameters."""
        response = client.get("/api/broker-stalker/chart/YP/BBCA?days=invalid")
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """Test API handles missing required fields."""
        response = client.post("/api/broker-stalker/watchlist", json={})
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
