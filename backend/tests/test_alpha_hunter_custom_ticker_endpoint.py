import asyncio

import pytest
from fastapi import HTTPException

from routes.alpha_hunter import stage1_custom_ticker


def test_stage1_custom_ticker_success(monkeypatch):
    def _fake_get_signals_for_ticker(self, ticker):
        return {
            "ticker": ticker,
            "signal_score": 82,
            "signal_strength": "VERY_STRONG",
            "conviction": "HIGH",
            "flow": 120,
            "change": 1.2,
            "price": 150,
            "patterns": ["UNUSUAL_ACTIVITY"],
            "momentum_status": "UP",
            "warning_status": "NONE",
        }

    monkeypatch.setattr(
        "modules.database.DatabaseManager.get_signals_for_ticker",
        _fake_get_signals_for_ticker,
    )

    result = asyncio.run(stage1_custom_ticker("SMGA"))

    assert result["ticker"] == "SMGA"
    signal = result["signal"]
    assert signal["symbol"] == "SMGA"
    assert signal["signal_score"] == 82
    assert signal["entry_zone"] in {"SWEET_SPOT", "ACCEPTABLE", "RISKY"}
    assert signal["unusual"] == "v"


def test_stage1_custom_ticker_not_found(monkeypatch):
    def _fake_get_signals_for_ticker(self, ticker):
        return {}

    monkeypatch.setattr(
        "modules.database.DatabaseManager.get_signals_for_ticker",
        _fake_get_signals_for_ticker,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(stage1_custom_ticker("XXXX"))

    assert exc.value.status_code == 404
