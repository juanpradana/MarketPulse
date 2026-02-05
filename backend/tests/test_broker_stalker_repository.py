"""Unit tests for BrokerStalkerRepository."""
import pytest
import sqlite3
import os
import tempfile
from datetime import datetime, timedelta
from db import BrokerStalkerRepository, DatabaseConnection


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
def repo(temp_db):
    """Create a BrokerStalkerRepository instance with temp database."""
    return BrokerStalkerRepository(db_path=temp_db)


class TestBrokerStalkerRepository:
    """Test suite for BrokerStalkerRepository."""
    
    def test_add_broker_to_watchlist(self, repo):
        """Test adding a broker to watchlist."""
        success = repo.add_broker_to_watchlist(
            broker_code="YP",
            broker_name="Yuanta Securities",
            description="Test broker"
        )
        
        assert success is True
        
        watchlist = repo.get_watchlist()
        assert len(watchlist) == 1
        assert watchlist[0]['broker_code'] == "YP"
        assert watchlist[0]['broker_name'] == "Yuanta Securities"
    
    def test_add_duplicate_broker(self, repo):
        """Test adding duplicate broker (should update)."""
        repo.add_broker_to_watchlist("YP", "Yuanta Securities", "First")
        repo.add_broker_to_watchlist("YP", "Yuanta Updated", "Second")
        
        watchlist = repo.get_watchlist()
        assert len(watchlist) == 1
        assert watchlist[0]['broker_name'] == "Yuanta Updated"
        assert watchlist[0]['description'] == "Second"
    
    def test_remove_broker_from_watchlist(self, repo):
        """Test removing a broker from watchlist."""
        repo.add_broker_to_watchlist("YP", "Yuanta Securities")
        repo.add_broker_to_watchlist("RK", "RK Securities")
        
        success = repo.remove_broker_from_watchlist("YP")
        assert success is True
        
        watchlist = repo.get_watchlist()
        assert len(watchlist) == 1
        assert watchlist[0]['broker_code'] == "RK"
    
    def test_get_empty_watchlist(self, repo):
        """Test getting empty watchlist."""
        watchlist = repo.get_watchlist()
        assert watchlist == []
    
    def test_update_power_level(self, repo):
        """Test updating broker power level."""
        repo.add_broker_to_watchlist("YP", "Yuanta Securities")
        
        success = repo.update_power_level("YP", 75)
        assert success is True
        
        watchlist = repo.get_watchlist()
        assert watchlist[0]['power_level'] == 75
    
    def test_save_tracking_record(self, repo):
        """Test saving a tracking record."""
        success = repo.save_tracking_record(
            broker_code="YP",
            ticker="BBCA",
            trade_date="2026-02-05",
            total_buy=1000000000,
            total_sell=500000000,
            net_value=500000000,
            avg_price=9500,
            streak_days=3,
            status="ACCUMULATING"
        )
        
        assert success is True
    
    def test_get_broker_tracking(self, repo):
        """Test getting broker tracking records."""
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        repo.save_tracking_record("YP", "BBCA", today, 1000000000, 500000000, 500000000)
        repo.save_tracking_record("YP", "BBRI", yesterday, 2000000000, 1000000000, 1000000000)
        
        records = repo.get_broker_tracking("YP", days=7)
        assert len(records) == 2
        
        records_bbca = repo.get_broker_tracking("YP", ticker="BBCA", days=7)
        assert len(records_bbca) == 1
        assert records_bbca[0]['ticker'] == "BBCA"
    
    def test_calculate_streak_buying(self, repo):
        """Test calculating buying streak."""
        base_date = datetime.now()
        
        for i in range(5):
            trade_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            repo.save_tracking_record("YP", "BBCA", trade_date, 1000000000, 500000000, 500000000)
        
        streak = repo.calculate_streak("YP", "BBCA")
        assert streak == 5
    
    def test_calculate_streak_selling(self, repo):
        """Test calculating selling streak."""
        base_date = datetime.now()
        
        for i in range(3):
            trade_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            repo.save_tracking_record("YP", "BBCA", trade_date, 500000000, 1000000000, -500000000)
        
        streak = repo.calculate_streak("YP", "BBCA")
        assert streak == -3
    
    def test_calculate_streak_mixed(self, repo):
        """Test calculating streak with mixed activity."""
        base_date = datetime.now()
        
        repo.save_tracking_record("YP", "BBCA", base_date.strftime('%Y-%m-%d'), 1000000000, 500000000, 500000000)
        repo.save_tracking_record("YP", "BBCA", (base_date - timedelta(days=1)).strftime('%Y-%m-%d'), 1000000000, 500000000, 500000000)
        repo.save_tracking_record("YP", "BBCA", (base_date - timedelta(days=2)).strftime('%Y-%m-%d'), 500000000, 1000000000, -500000000)
        
        streak = repo.calculate_streak("YP", "BBCA")
        assert streak == 2
    
    def test_get_broker_portfolio(self, repo):
        """Test getting broker portfolio."""
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        repo.save_tracking_record("YP", "BBCA", today, 1000000000, 500000000, 500000000, 9500)
        repo.save_tracking_record("YP", "BBCA", yesterday, 500000000, 200000000, 300000000, 9400)
        repo.save_tracking_record("YP", "BBRI", today, 2000000000, 1000000000, 1000000000, 5200)
        
        portfolio = repo.get_broker_portfolio("YP", min_net_value=0)
        assert len(portfolio) == 2
        
        bbri_position = [p for p in portfolio if p['ticker'] == 'BBRI'][0]
        assert bbri_position['total_net_value'] == 1000000000
        assert bbri_position['trading_days'] == 1
        
        bbca_position = [p for p in portfolio if p['ticker'] == 'BBCA'][0]
        assert bbca_position['total_net_value'] == 800000000
        assert bbca_position['trading_days'] == 2
    
    def test_get_broker_portfolio_with_filter(self, repo):
        """Test getting broker portfolio with minimum net value filter."""
        today = datetime.now().strftime('%Y-%m-%d')
        
        repo.save_tracking_record("YP", "BBCA", today, 1000000000, 500000000, 500000000)
        repo.save_tracking_record("YP", "BBRI", today, 100000000, 50000000, 50000000)
        
        portfolio = repo.get_broker_portfolio("YP", min_net_value=100000000)
        assert len(portfolio) == 1
        assert portfolio[0]['ticker'] == 'BBCA'
    
    def test_get_ticker_broker_activity(self, repo):
        """Test getting all broker activity for a ticker."""
        today = datetime.now().strftime('%Y-%m-%d')
        
        repo.save_tracking_record("YP", "BBCA", today, 1000000000, 500000000, 500000000)
        repo.save_tracking_record("RK", "BBCA", today, 2000000000, 1000000000, 1000000000)
        repo.save_tracking_record("YP", "BBRI", today, 500000000, 200000000, 300000000)
        
        activity = repo.get_ticker_broker_activity("BBCA", days=7)
        assert len(activity) == 2
        
        broker_codes = [a['broker_code'] for a in activity]
        assert "YP" in broker_codes
        assert "RK" in broker_codes
    
    def test_case_insensitive_broker_code(self, repo):
        """Test that broker codes are case insensitive."""
        repo.add_broker_to_watchlist("yp", "Yuanta Securities")
        
        watchlist = repo.get_watchlist()
        assert watchlist[0]['broker_code'] == "YP"
        
        repo.save_tracking_record("yp", "bbca", "2026-02-05", 1000000000, 500000000, 500000000)
        
        records = repo.get_broker_tracking("YP", ticker="BBCA")
        assert len(records) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
