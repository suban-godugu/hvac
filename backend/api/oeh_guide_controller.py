"""OEH guide catalog + read-only evaluate for official O1–O20."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.oeh_guide_catalog import catalog_item, catalog_list, normalize_oid
from backend.services.oeh_guide_service import evaluate_guide

router = APIRouter(prefix="/api/v1/oeh-guide", tags=["OEH Guide O1–O20"])


class EvaluateBody(BaseModel):
    sliders: Optional[Dict[str, Any]] = Field(default=None)


def _unknown(raw: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "UNKNOWN_OPPORTUNITY",
            "message": "Official catalog IDs are O1–O20 (O6, O7, O8 are separate). O6-O8 is not an evaluate id.",
            "opportunityId": raw,
        },
    )


@router.get("")
@router.get("/")
async def list_guide():
    return {"opportunities": catalog_list(), "source": "SIMULATION"}


@router.get("/{oid}")
async def get_guide(oid: str):
    key = normalize_oid(oid)
    item = catalog_item(key) if key else None
    if not item:
        raise _unknown(oid)
    return item


@router.post("/{oid}/evaluate")
async def post_evaluate(oid: str, body: EvaluateBody = EvaluateBody()):
    key = normalize_oid(oid)
    if not key:
        raise _unknown(oid)
    try:
        return evaluate_guide(key, body.sliders)
    except ValueError:
        raise _unknown(oid)
