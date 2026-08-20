from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from backend.services.canonical_telemetry_service import latest_points
from backend.services.platform_bms_service import platform_snapshot
from backend.services.platform_ops_service import get_safe_mode, set_safe_mode, record_control_audit

router = APIRouter(prefix="/api/platform", tags=["Platform"])


class SafeModeRequest(BaseModel):
    enabled: bool
    reason: Optional[str] = None


@router.get("/status")
async def platform_status():
    return platform_snapshot()


@router.post("/safe-mode")
async def post_safe_mode(req: SafeModeRequest):
    set_safe_mode(req.enabled)
    record_control_audit(user=None, action="SAFE_MODE", reason=req.reason, requested_value=req.enabled)
    return {"safeMode": get_safe_mode()}


@router.get("/telemetry")
async def telemetry_latest(building_id: Optional[str] = Query(default=None)):
    return {"points": latest_points(building_id)}
