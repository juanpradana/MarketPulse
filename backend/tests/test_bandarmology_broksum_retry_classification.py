import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from routes.bandarmology import _classify_broksum_outcome


def test_classify_broksum_outcome_non_retryable_no_data():
    result = _classify_broksum_outcome(
        raw_result={"buy": [], "sell": []},
        error=None,
        context={"reason": "no_data", "ticker": "ABCD", "date": "2026-04-01"},
    )

    assert result == "non_retryable"


def test_classify_broksum_outcome_retryable_rate_limit_429():
    result = _classify_broksum_outcome(
        raw_result=None,
        error=Exception("429 Too Many Requests: cooldown active"),
        context={"ticker": "BBCA", "date": "2026-04-01"},
    )

    assert result == "retryable"
