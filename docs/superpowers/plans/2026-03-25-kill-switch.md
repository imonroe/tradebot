# Plan: Kill Switch API Endpoint

**Date:** 2026-03-25
**Status:** Implementation

## Problem Statement

The trading bot has no emergency stop mechanism. If something goes wrong during live trading, there's no way to immediately halt all trading activity without killing the process. A kill switch provides a safe, controlled way to stop new trades while keeping the API and monitoring running.

## Design

### Behavior

When the kill switch is **activated**:
1. The bot loop continues running (market data is still fetched, WebSocket updates still broadcast)
2. The risk manager **rejects all signals** — no new orders are placed
3. Existing open positions are **not** automatically closed (that's a separate concern)
4. The dashboard shows kill switch status so the operator knows trading is halted
5. A log entry and optional reason are recorded

When the kill switch is **deactivated**:
- Normal trading resumes on the next loop iteration

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/kill-switch/activate` | Activate kill switch. Optional JSON body: `{"reason": "..."}` |
| `POST` | `/api/kill-switch/deactivate` | Deactivate kill switch |
| `GET` | `/api/kill-switch` | Get current kill switch status |

### Integration Points

1. **`AppState`** — Add `kill_switch_active: bool` and `kill_switch_reason: str | None` fields
2. **`RiskManager`** — Add a `KillSwitchCheck` that reads from AppState and rejects all signals when active
3. **`bot_loop`** — Include kill switch status in WebSocket broadcasts
4. **`/api/health`** — Include kill switch status
5. **Frontend** — Add a kill switch toggle button to the dashboard header

## Files Changed

| File | Change |
|------|--------|
| `src/tradebot/api/state.py` | Add kill switch fields |
| `src/tradebot/api/routes/kill_switch.py` | New — kill switch endpoints |
| `src/tradebot/api/app.py` | Register kill switch router, include status in health + WS |
| `src/tradebot/risk/checks.py` | Add `KillSwitchCheck` |
| `src/tradebot/main.py` | Wire `KillSwitchCheck` into risk manager, broadcast status |
| `frontend/src/components/KillSwitch.tsx` | New — kill switch toggle component |
| `frontend/src/pages/Dashboard.tsx` | Include KillSwitch component |
| `tests/unit/test_kill_switch.py` | New — tests for endpoints and risk check |
| `README.md` | Mark roadmap item complete |

## Success Criteria

1. `POST /api/kill-switch/activate` stops all new trades
2. `POST /api/kill-switch/deactivate` resumes trading
3. `GET /api/kill-switch` returns current status
4. Risk manager rejects all signals when kill switch is active
5. Dashboard shows kill switch state with toggle button
6. All existing + new tests pass
