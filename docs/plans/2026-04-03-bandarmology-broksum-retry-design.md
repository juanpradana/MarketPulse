# Bandarmology Broker Summary Deferred Retry Design

**Date:** 2026-04-03
**Author:** Claude + User
**Status:** Approved for implementation planning

## 1) Context and Problem

Bandarmology deep analysis (scheduled and manual trigger) currently uses fast-fail behavior for NeoBDM broker summary calls in several paths. When upstream is rate-limited (429) or temporarily unstable, the pipeline may skip broker summary data too early.

User requirement:
- If broker summary fetch fails in deep analyze flow, retry with **2-minute delay**.
- Retry until success, but with hard cap **10 attempts**.
- Keep manual deep analyze as **background async** (non-blocking request).
- Do **not** force retries for clearly non-retryable cases (no data for date/ticker, invalid ticker).

## 2) Goals

1. Add robust deferred retry behavior for broker summary fetch in deep analysis flow.
2. Keep both scheduler and manual deep analyze using the same retry policy.
3. Expose clear status observability for retrying / skipped / exhausted states.
4. Prevent infinite loops and avoid hammering NeoBDM when rate limited.

## 3) Non-Goals

- No redesign of overall Bandarmology scoring logic.
- No broad rewrite of all NeoBDM consumers outside deep analysis flow.
- No queue-table persistence redesign in this phase (in-memory run status remains).

## 4) Functional Requirements

### Retry policy
- Retry interval: **120 seconds**.
- Max attempts per `(ticker, date)`: **10**.
- Applied to broker summary fetch points in `_run_deep_analysis`:
  - latest/forward-date lookup
  - analysis-date fetch
  - recent dates fetch
  - important dates fetch

### Async behavior
- Manual endpoints (`/api/bandarmology/deep-analyze`, `/api/bandarmology/deep-analyze-tickers`) remain background tasks.
- API returns immediately with started message; progress observed via `/api/bandarmology/deep-status`.

### Retry classification
- **Retryable:** 429, cooldown active, timeout/network/transient upstream issues.
- **Non-retryable:** explicit no-data for date+ticker, invalid ticker/date signal.

### Stop conditions
- Success → stop retry and continue pipeline.
- Non-retryable → stop retry immediately, record skip reason.
- Attempt 10 exhausted → mark exhausted, continue pipeline without blocking others.

## 5) Design Overview

### 5.1 Backend status model extension (`backend/routes/bandarmology.py`)

Extend `_deep_analysis_status` and `_build_deep_analysis_status` with:

- `retry_policy`: `{ "delay_seconds": 120, "max_attempts": 10 }`
- `retrying_items`: list of active waiting retries
- `retry_waiting_count`: number of items waiting for next retry window
- `non_retryable_skips`: list of `{ticker,date,reason}`
- `retry_exhausted`: list of `{ticker,date,attempts}`
- `broksum_fetch_stats`: `{ success, retried_success, non_retryable, exhausted }`

This allows UI and scheduler monitoring to understand whether deep analysis is progressing, waiting, or skipping for valid reasons.

### 5.2 Centralized deferred-retry helper in deep-analysis flow

Create internal helper in `routes/bandarmology.py` (used only by deep-analysis run):

- Inputs: `ticker`, `date`, shared `NeoBDMApiClient`, repo handles, status lock.
- Steps:
  1. Try DB first (if valid rows exist, use them).
  2. Try API fetch.
  3. Classify outcome: success / retryable / non-retryable.
  4. Retryable: register status + sleep 120s + retry, up to 10 attempts.
  5. Non-retryable: record skip and return no data.
  6. Exhausted: record exhausted and return no data.

The helper will be used in all broker-summary fetch points inside `_run_deep_analysis`.

### 5.3 NeoBDM client classification signals (`backend/modules/neobdm_api_client.py`)

Keep existing return compatibility while enabling better classification:
- Reuse detectable signals already present in client logic:
  - 429/cooldown path
  - explicit `Data tidak tersedia` no-data path
  - known invalid input indicators when available
- Add lightweight metadata or helper classification logic at call-site without breaking existing callers.

### 5.4 Frontend contract update (`frontend/src/services/api/bandarmology.ts`)

Extend `DeepAnalysisStatus` interface to include new retry fields.

### 5.5 Optional UI observability (`frontend/src/app/bandarmology/page.tsx`)

Display concise runtime indicators from deep-status:
- `Retrying: N`
- `Non-retryable skips: N`
- `Retry exhausted: N`

No trigger-flow changes required.

## 6) Detailed Behavior Matrix

For each `(ticker, date)` fetch task:

1. **Success at first attempt**
   - Save/use data, increment success counters.
2. **Retryable then success**
   - Track attempt count and waiting status.
   - On success, increment `retried_success`.
3. **Non-retryable**
   - No further retries.
   - Add entry to `non_retryable_skips` with reason.
4. **Retry exhausted (10 attempts)**
   - Add entry to `retry_exhausted`.
   - Continue deep-analysis pipeline without blocking other tickers.

## 7) Concurrency and Safety

- Keep global broker-summary semaphore (single active broker-summary API call) to avoid 429 amplification.
- Retry waiting happens per item while other ticker work can continue where possible.
- Status updates remain lock-protected via `_deep_analysis_status_lock`.
- Hard stop at 10 attempts prevents runaway loops.

## 8) Testing Strategy (TDD)

### Backend tests
1. Retryable→Success sequence
   - Simulate transient failures then success.
   - Assert status counters and final success path.
2. Retry exhausted
   - Simulate repeated retryable failures.
   - Assert exhausted list and no infinite loop.
3. Non-retryable no-data
   - Simulate explicit no-data response.
   - Assert immediate skip, no retries.
4. Non-retryable invalid ticker
   - Simulate invalid ticker signal.
   - Assert immediate skip.
5. Manual trigger remains async
   - Start endpoint responds quickly and deep-status shows running/retrying states.

### Contract checks
- Validate deep-status JSON includes newly added fields.
- Validate frontend type compatibility for new fields.

## 9) Rollout Plan

1. Implement backend status schema extension.
2. Implement deferred-retry helper and integrate in `_run_deep_analysis` broksum fetch points.
3. Update DeepAnalysisStatus TypeScript interface.
4. (Optional) show retry indicators in Bandarmology page.
5. Run targeted backend tests + syntax checks.
6. Validate manual and scheduled paths in dev environment.

## 10) Acceptance Criteria

- Deep analyze broker summary fetch uses 2-minute deferred retry with max 10 attempts.
- Manual trigger remains background async.
- Non-retryable cases are skipped immediately and recorded.
- Retry state visible in deep-status payload.
- No infinite retry loops; pipeline completes with deterministic status.

## 11) Risks and Mitigations

- **Longer runtime** due to deferred retries
  - Accepted by requirement; visible via status fields.
- **Over-retrying non-retryable cases**
  - Mitigated by explicit classification and immediate skip.
- **Rate-limit cascades**
  - Mitigated by existing semaphore and deferred spacing.

---

This design is approved by user and ready for implementation planning.
