import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.canonical_telemetry_service import latest_points
from backend.services.hvac_safety_contract import is_demo_source
from backend.services.logging_service import log_event
from backend.services.platform_bms_service import platform_snapshot

ws_router = APIRouter()


@ws_router.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            snap = platform_snapshot()
            points = latest_points(limit=40)
            events = []
            for p in points:
                src = p.get("source")
                pid = str(p.get("point_id") or "")
                equipment = p.get("equipment_id") or p.get("asset_id")
                point_name = pid.split(".", 1)[1] if "." in pid else pid
                live = (
                    snap.get("bmsConnected")
                    and (not is_demo_source(src))
                    and p.get("quality") == "GOOD"
                    and p.get("classified") == "LIVE"
                )
                events.append(
                    {
                        "equipment_id": equipment,
                        "point": point_name,
                        "point_id": pid,
                        "value": p.get("value"),
                        "unit": p.get("unit"),
                        "timestamp": p.get("timestamp"),
                        "quality": p.get("quality"),
                        "source": src,
                        "building_id": p.get("building_id"),
                        "live": live,
                    }
                )
            bms = dict(snap.get("bms") or {})
            if "lastError" not in bms:
                bms["lastError"] = bms.get("last_error")
            await websocket.send_json(
                {
                    "bms": bms,
                    "telemetry": snap.get("telemetry"),
                    "safeMode": snap.get("safeMode"),
                    "controlEnabled": False,
                    "events": events,
                    "count": len(events),
                }
            )
            await asyncio.sleep(5.0)
    except WebSocketDisconnect:
        return
    except Exception as e:
        log_event("ERROR", "websocket", "TELEMETRY_STREAM", extra={"error": type(e).__name__})
        try:
            await websocket.close()
        except Exception:
            pass
        return
