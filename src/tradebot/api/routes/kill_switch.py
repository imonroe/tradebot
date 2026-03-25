"""Kill switch API routes."""
from fastapi import APIRouter, Request
from pydantic import BaseModel

import structlog

logger = structlog.get_logger()

router = APIRouter(tags=["kill-switch"])


class ActivateRequest(BaseModel):
    reason: str | None = None


@router.get("/kill-switch")
async def get_kill_switch(request: Request):
    """Get current kill switch status."""
    state = request.app.state.app_state
    return {
        "active": state.kill_switch_active,
        "reason": state.kill_switch_reason,
    }


@router.post("/kill-switch/activate")
async def activate_kill_switch(request: Request, body: ActivateRequest | None = None):
    """Activate the kill switch, halting all new trades."""
    state = request.app.state.app_state
    reason = body.reason if body else None
    state.kill_switch_active = True
    state.kill_switch_reason = reason
    logger.warning("kill_switch_activated", reason=reason)
    return {
        "active": True,
        "reason": reason,
    }


@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch(request: Request):
    """Deactivate the kill switch, resuming normal trading."""
    state = request.app.state.app_state
    state.kill_switch_active = False
    state.kill_switch_reason = None
    logger.info("kill_switch_deactivated")
    return {
        "active": False,
        "reason": None,
    }
