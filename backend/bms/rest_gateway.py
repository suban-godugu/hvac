"""Vendor REST BMS adapter. No invented endpoints/points."""
from __future__ import annotations

from typing import Any, Dict, List

from backend.bms.base import (
    ADAPTER_UNAVAILABLE,
    BMSGateway,
    BmsAdapterError,
    BmsHealth,
    CONNECTION_FAILED,
    DiscoveredDevice,
    DiscoveredPoint,
    PointReading,
    WriteOutcome,
    utc_now,
)
from backend.bms.command_writer import write_point as reject_write
from backend.bms.command_writer import write_points as reject_writes


class RestGateway(BMSGateway):
    protocol = "rest"

    def __init__(self) -> None:
        self._connected = False
        self.host: str | None = None
        self.port: int | None = None
        self.base_url: str | None = None
        self._last_error: str | None = None
        self._last_code: str | None = None
        self._last_connected_at: str | None = None

    def connect(self, host: str, port: int = 443, **kwargs: Any) -> BmsHealth:
        url = (kwargs.get("url") or host or "").strip()
        if url and not url.startswith("http"):
            url = f"http://{url}:{port}" if port else f"http://{url}"
        self.base_url = url
        self.host = host
        self.port = int(port or 443)
        if not url:
            self._connected = False
            self._last_code = CONNECTION_FAILED
            self._last_error = "REST BMS URL is empty."
            raise BmsAdapterError(CONNECTION_FAILED, self._last_error)
        try:
            import httpx
        except Exception:
            self._connected = False
            self._last_code = ADAPTER_UNAVAILABLE
            self._last_error = "httpx is not installed."
            raise BmsAdapterError(ADAPTER_UNAVAILABLE, self._last_error)
        try:
            health_url = kwargs.get("health_path") or url
            with httpx.Client(timeout=5.0) as client:
                res = client.get(health_url)
            if res.status_code >= 500:
                raise BmsAdapterError(CONNECTION_FAILED, f"REST BMS returned HTTP {res.status_code}")
            self._connected = True
            self._last_error = None
            self._last_code = None
            self._last_connected_at = utc_now().isoformat()
            return self.health()
        except BmsAdapterError:
            self._connected = False
            raise
        except Exception as exc:
            self._connected = False
            self._last_code = CONNECTION_FAILED
            self._last_error = str(exc)
            raise BmsAdapterError(CONNECTION_FAILED, self._last_error)

    def disconnect(self) -> BmsHealth:
        self._connected = False
        return self.health()

    def health(self) -> BmsHealth:
        return BmsHealth(
            connected=bool(self._connected and self._last_connected_at),
            protocol=self.protocol,
            code=None if self._connected else self._last_code,
            message=self._last_error,
            host=self.host,
            port=self.port,
            last_connected_at=self._last_connected_at if self._connected else None,
        )

    def discover_devices(self) -> List[DiscoveredDevice]:
        return []

    def discover_points(self, device_id: str) -> List[DiscoveredPoint]:
        del device_id
        return []

    def read_point(self, point_id: str) -> PointReading:
        return PointReading(point_id=point_id, value=None, unit=None, quality="MISSING", timestamp=utc_now().isoformat())

    def read_points(self, point_ids: List[str]) -> List[PointReading]:
        return [self.read_point(p) for p in point_ids]

    def execute_write(self, point_id: str, value: float, priority: int = 10) -> WriteOutcome:
        del priority
        if not getattr(self, "_connected", False):
            return WriteOutcome(success=False, code=CONNECTION_FAILED, message="REST adapter is not connected.", point_id=point_id, value=value)
        return WriteOutcome(success=False, code=ADAPTER_UNAVAILABLE, message="REST write requires a commissioned endpoint map.", point_id=point_id, value=value)

    def write_point(self, point_id: str, value: float, priority: int = 10) -> WriteOutcome:
        return reject_write(point_id, value, priority)

    def write_points(self, writes: List[Dict[str, Any]]) -> List[WriteOutcome]:
        return reject_writes(writes)
