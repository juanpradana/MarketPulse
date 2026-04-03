# Bandarmology Broker Summary Deferred Retry Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement deferred broker-summary retry in Bandarmology deep analysis with 120-second intervals, max 10 attempts, background async behavior, and non-retryable skip handling.

**Architecture:** Add a centralized retry helper in the deep-analysis pipeline (`_run_deep_analysis`) and extend deep-status payload for observability. Keep scheduler and manual trigger behavior aligned by reusing the same deep-analysis execution path. Preserve current semaphore throttling while adding deterministic stop conditions.

**Tech Stack:** FastAPI, asyncio, SQLite repositories, Python pytest, TypeScript interfaces.

---

### Task 1: Extend deep-status contract for retry observability

**Files:**
- Modify: `backend/routes/bandarmology.py:15-31`
- Modify: `backend/routes/bandarmology.py:35-61`
- Modify: `frontend/src/services/api/bandarmology.ts:536-554`

**Step 1: Write the failing test (backend status payload shape)**

Create a new test file:
- Create: `backend/tests/test_bandarmology_deep_status_retry_fields.py`

Test code:

```python
import sys
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from routes import bandarmology as band_route


def test_deep_status_includes_retry_fields_when_idle():
    client = TestClient(app)

    # Reset status to known baseline
    band_route._deep_analysis_status.clear()
    band_route._deep_analysis_status.update(
        band_route._build_deep_analysis_status(
            total=0,
            requested=0,
            qualified=0,
            analysis_date="2026-04-03",
            concurrency=1,
            profile="balanced",
        )
    )
    band_route._deep_analysis_status["running"] = False

    response = client.get("/api/bandarmology/deep-status")
    assert response.status_code == 200
    data = response.json()

    assert "retry_policy" in data
    assert data["retry_policy"]["delay_seconds"] == 120
    assert data["retry_policy"]["max_attempts"] == 10
    assert "retrying_items" in data
    assert "retry_waiting_count" in data
    assert "non_retryable_skips" in data
    assert "retry_exhausted" in data
    assert "broksum_fetch_stats" in data
```

**Step 2: Run test to verify it fails**

Run:
`pytest -q backend/tests/test_bandarmology_deep_status_retry_fields.py -v`

Expected: FAIL because fields are not present yet.

**Step 3: Write minimal implementation**

In `backend/routes/bandarmology.py`:
- Add new keys to global `_deep_analysis_status` default map:
  - `retry_policy`, `retrying_items`, `retry_waiting_count`, `non_retryable_skips`, `retry_exhausted`, `broksum_fetch_stats`
- Add same keys in `_build_deep_analysis_status(...)` return dict with defaults:
  - `retry_policy = {"delay_seconds": 120, "max_attempts": 10}`
  - arrays empty, counters 0, stats counters 0

In `frontend/src/services/api/bandarmology.ts`:
- Extend `DeepAnalysisStatus` interface with optional fields:
  - `retry_policy?: { delay_seconds: number; max_attempts: number }`
  - `retrying_items?: Array<{ ticker: string; date: string; attempt: number; next_retry_at?: string }>`
  - `retry_waiting_count?: number`
  - `non_retryable_skips?: Array<{ ticker: string; date: string; reason: string }>`
  - `retry_exhausted?: Array<{ ticker: string; date: string; attempts: number }>`
  - `broksum_fetch_stats?: { success: number; retried_success: number; non_retryable: number; exhausted: number }`

**Step 4: Run test to verify it passes**

Run:
`pytest -q backend/tests/test_bandarmology_deep_status_retry_fields.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/routes/bandarmology.py backend/tests/test_bandarmology_deep_status_retry_fields.py frontend/src/services/api/bandarmology.ts
git commit -m "feat: add deep status retry observability fields"
```

---

### Task 2: Add broker-summary outcome classification helper

**Files:**
- Modify: `backend/routes/bandarmology.py` (new internal helper near `_run_deep_analysis`)
- Modify: `backend/modules/neobdm_api_client.py` (optional lightweight signal if needed)
- Test: `backend/tests/test_bandarmology_broksum_retry_classification.py`

**Step 1: Write the failing test**

Create:
- `backend/tests/test_bandarmology_broksum_retry_classification.py`

Test code:

```python
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from routes import bandarmology as band_route


def test_classify_broksum_outcome_non_retryable_no_data():
    outcome = band_route._classify_broksum_outcome(
        raw_result=None,
        error=None,
        context={"ticker": "BBCA", "date": "2026-04-03", "source": "explicit_no_data"},
    )
    assert outcome == "non_retryable"


def test_classify_broksum_outcome_retryable_rate_limit():
    outcome = band_route._classify_broksum_outcome(
        raw_result=None,
        error="429 Too Many Requests",
        context={"ticker": "BBCA", "date": "2026-04-03"},
    )
    assert outcome == "retryable"
```

**Step 2: Run test to verify it fails**

Run:
`pytest -q backend/tests/test_bandarmology_broksum_retry_classification.py -v`

Expected: FAIL because helper does not exist.

**Step 3: Write minimal implementation**

In `backend/routes/bandarmology.py` add helper:

```python
def _classify_broksum_outcome(raw_result, error, context) -> str:
    # returns: "success" | "retryable" | "non_retryable"
```

Rules:
- `success`: dict with non-empty buy/sell
- `non_retryable`: explicit no-data/invalid ticker/date context
- `retryable`: 429, cooldown active, timeout/network/transient failures

Optional: if needed, add lightweight signal in `neobdm_api_client.py` so caller can pass context reason without changing global API behavior.

**Step 4: Run test to verify it passes**

Run:
`pytest -q backend/tests/test_bandarmology_broksum_retry_classification.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/routes/bandarmology.py backend/tests/test_bandarmology_broksum_retry_classification.py backend/modules/neobdm_api_client.py
git commit -m "feat: classify broker summary outcomes for retry policy"
```

---

### Task 3: Implement deferred retry helper (120s, max 10)

**Files:**
- Modify: `backend/routes/bandarmology.py` (new async helper)
- Test: `backend/tests/test_bandarmology_broksum_retry_helper.py`

**Step 1: Write the failing test**

Create:
- `backend/tests/test_bandarmology_broksum_retry_helper.py`

Test code (use monkeypatch to avoid real sleeping/network):

```python
import sys
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from routes import bandarmology as band_route


@pytest.mark.asyncio
async def test_retry_helper_retries_until_success(monkeypatch):
    calls = {"n": 0}

    async def fake_fetch(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            return None, "429"
        return {"buy": [{"broker": "PD", "nlot": "10"}], "sell": []}, None

    async def fake_sleep(_):
        return None

    monkeypatch.setattr(band_route.asyncio, "sleep", fake_sleep)

    result = await band_route._fetch_broksum_with_deferred_retry(
        fetch_fn=fake_fetch,
        ticker="BBCA",
        date_str="2026-04-03",
        status=band_route._build_deep_analysis_status(1, 1, 1, "2026-04-03", 1, "balanced"),
    )

    assert result is not None
    assert calls["n"] == 3
```

**Step 2: Run test to verify it fails**

Run:
`pytest -q backend/tests/test_bandarmology_broksum_retry_helper.py -v`

Expected: FAIL because helper not implemented.

**Step 3: Write minimal implementation**

In `backend/routes/bandarmology.py`, add:

```python
async def _fetch_broksum_with_deferred_retry(fetch_fn, ticker, date_str, status, status_lock=None):
    # fixed policy: delay 120s, max_attempts 10
    # update status retrying_items / counters
    # stop on success/non_retryable/exhausted
```

Requirements:
- Use fixed constants: `delay_seconds=120`, `max_attempts=10`
- Avoid infinite loop
- Update status fields consistently

**Step 4: Run test to verify it passes**

Run:
`pytest -q backend/tests/test_bandarmology_broksum_retry_helper.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/routes/bandarmology.py backend/tests/test_bandarmology_broksum_retry_helper.py
git commit -m "feat: add deferred broker summary retry helper"
```

---

### Task 4: Integrate retry helper into deep-analysis broker-summary fetch points

**Files:**
- Modify: `backend/routes/bandarmology.py:647-813`
- Test: `backend/tests/test_bandarmology_deep_retry_integration.py`

**Step 1: Write the failing test**

Create:
- `backend/tests/test_bandarmology_deep_retry_integration.py`

Test should simulate one ticker where initial broksum fetch is retryable then success, and assert:
- deep flow continues,
- broksum saved,
- status stats updated (`retried_success`).

Use monkeypatch to stub:
- `NeoBDMApiClient.get_broker_summary`
- repo save/get calls
- `asyncio.sleep` (no real 120s wait)

**Step 2: Run test to verify it fails**

Run:
`pytest -q backend/tests/test_bandarmology_deep_retry_integration.py -v`

Expected: FAIL before integration.

**Step 3: Write minimal implementation**

Refactor all broker-summary fetch blocks in `_run_deep_analysis` to call `_fetch_broksum_with_deferred_retry`.

Scope:
- latest forward-date lookup
- analysis-date fetch
- recent dates
- important dates

Preserve:
- existing semaphore usage (`broksum_rate_limiter`)
- existing DB write lock behavior

**Step 4: Run test to verify it passes**

Run:
`pytest -q backend/tests/test_bandarmology_deep_retry_integration.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/routes/bandarmology.py backend/tests/test_bandarmology_deep_retry_integration.py
git commit -m "feat: wire deferred broksum retry into deep analysis flow"
```

---

### Task 5: Add non-retryable skip and retry-exhausted regression tests

**Files:**
- Modify: `backend/tests/test_bandarmology_broksum_retry_helper.py`

**Step 1: Write failing tests**

Add two tests:
1. Non-retryable no-data stops immediately (attempt=1).
2. Retryable repeated failure stops at 10 attempts and marks exhausted.

**Step 2: Run tests to verify failure**

Run:
`pytest -q backend/tests/test_bandarmology_broksum_retry_helper.py -v`

Expected: FAIL for new tests.

**Step 3: Write minimal implementation updates**

Adjust helper logic/status updates to satisfy both edge cases.

**Step 4: Run tests to verify pass**

Run:
`pytest -q backend/tests/test_bandarmology_broksum_retry_helper.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_bandarmology_broksum_retry_helper.py backend/routes/bandarmology.py
git commit -m "test: cover non-retryable and exhausted broker-summary retry cases"
```

---

### Task 6: Ensure scheduler and manual paths remain compatible

**Files:**
- Modify: `backend/tests/test_scheduler_bandarmology_refresh.py`
- Modify: `backend/tests/test_bandarmology_deep_status_retry_fields.py`

**Step 1: Write failing test updates**

Add assertions that scheduler-triggered deep analyze can still call `_run_deep_analysis` with unchanged signature and that status includes retry fields during run lifecycle.

**Step 2: Run tests to verify failure**

Run:
`pytest -q backend/tests/test_scheduler_bandarmology_refresh.py -v`

Expected: FAIL if behavior changed unexpectedly.

**Step 3: Write minimal implementation updates**

If needed, only adjust adapter/wrapper code so scheduler keeps working with new internals (no API signature break).

**Step 4: Run tests to verify pass**

Run:
`pytest -q backend/tests/test_scheduler_bandarmology_refresh.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_scheduler_bandarmology_refresh.py backend/routes/bandarmology.py
git commit -m "test: keep scheduler deep analyze compatibility with retry policy"
```

---

### Task 7: (Optional UI) Display retry indicators on Bandarmology page

**Files:**
- Modify: `frontend/src/app/bandarmology/page.tsx`
- Modify: `frontend/src/services/api/bandarmology.ts`

**Step 1: Write failing UI/contract check**

If no FE test framework exists for this page, create a minimal type-level check by running `tsc`/build and ensuring new status fields are consumed safely.

**Step 2: Run check to verify fail (if applicable)**

Run:
`npm -C frontend run build`

Expected: type mismatch before UI changes if using new fields unsafely.

**Step 3: Write minimal implementation**

Render compact status lines when values exist:
- `Retrying: {retry_waiting_count}`
- `Non-retryable skips: {non_retryable_skips.length}`
- `Retry exhausted: {retry_exhausted.length}`

No behavior changes to trigger buttons.

**Step 4: Run check to verify pass**

Run:
`npm -C frontend run build`

Expected: build passes for modified files (or report pre-existing unrelated failures separately).

**Step 5: Commit**

```bash
git add frontend/src/app/bandarmology/page.tsx frontend/src/services/api/bandarmology.ts
git commit -m "feat(ui): show deep analysis retry and skip indicators"
```

---

### Task 8: Final verification and integration commit

**Files:**
- Verify all changed files

**Step 1: Run targeted backend suite**

Run:
`pytest -q backend/tests/test_bandarmology_deep_status_retry_fields.py backend/tests/test_bandarmology_broksum_retry_classification.py backend/tests/test_bandarmology_broksum_retry_helper.py backend/tests/test_bandarmology_deep_retry_integration.py backend/tests/test_scheduler_bandarmology_refresh.py`

Expected: all pass.

**Step 2: Run backend syntax check**

Run:
`python -m py_compile backend/routes/bandarmology.py backend/modules/neobdm_api_client.py`

Expected: no syntax errors.

**Step 3: Run frontend type/lint checks for touched files**

Run:
`npm -C frontend run lint -- "src/services/api/bandarmology.ts" "src/app/bandarmology/page.tsx"`

Expected: no new errors introduced by this feature (document unrelated pre-existing errors if any).

**Step 4: Commit final integration**

```bash
git add backend/routes/bandarmology.py backend/modules/neobdm_api_client.py backend/tests/*.py frontend/src/services/api/bandarmology.ts frontend/src/app/bandarmology/page.tsx
git commit -m "feat: add deferred broker-summary retry policy for deep analysis"
```

---

## Notes for Execution

- Use strict TDD cycle for each task (@superpowers:test-driven-development).
- Keep changes minimal and local; no unrelated refactors.
- Preserve current endpoint contracts unless explicitly updated in this plan.
- If build/lint fails due to unrelated existing issues, report them clearly and proceed with targeted verification evidence.
