from modules.alpha_hunter_health import AlphaHunterHealth


def _build_records():
    return [
        {"trade_date": "2026-01-01", "volume": 100, "close_price": 100},
        {"trade_date": "2026-01-02", "volume": 110, "close_price": 101},
        {"trade_date": "2026-01-03", "volume": 90, "close_price": 100},
        {"trade_date": "2026-01-04", "volume": 95, "close_price": 100},
        {"trade_date": "2026-01-05", "volume": 105, "close_price": 101},
        {"trade_date": "2026-01-06", "volume": 400, "close_price": 104},
        {"trade_date": "2026-01-07", "volume": 220, "close_price": 103},
        {"trade_date": "2026-01-08", "volume": 180, "close_price": 102},
    ]


class _FakeAlphaRepo:
    def __init__(self, item=None):
        self._item = item

    def get_watchlist_item(self, ticker):
        return self._item


class _FakeDB:
    def __init__(self, records, watchlist_item=None):
        self._records = records
        self._repo = _FakeAlphaRepo(watchlist_item)

    def get_volume_history(self, ticker, start_date=None, end_date=None):
        return self._records

    def get_alpha_hunter_repo(self):
        return self._repo


def test_auto_detect_spike_date_detects_latest_valid_spike():
    spike_date = AlphaHunterHealth._auto_detect_spike_date(
        _build_records(),
        min_ratio=2.0,
        lookback_days=5,
    )

    assert spike_date == "2026-01-06"


def test_check_pullback_health_uses_watchlist_spike_date_when_available():
    health = AlphaHunterHealth()
    health.db = _FakeDB(_build_records(), watchlist_item={"spike_date": "2026-01-05"})

    result = health.check_pullback_health("SMGA")

    assert result["spike_date"] == "2026-01-05"
    assert result["spike_source"] == "watchlist"
    assert "health_score" in result


def test_check_pullback_health_uses_auto_detect_when_watchlist_missing():
    health = AlphaHunterHealth()
    health.db = _FakeDB(_build_records(), watchlist_item=None)

    result = health.check_pullback_health("SMGA")

    assert result["spike_date"] == "2026-01-06"
    assert result["spike_source"] == "auto_detected"
    assert "health_score" in result
