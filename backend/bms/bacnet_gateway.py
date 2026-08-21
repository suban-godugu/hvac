"""BACnet/IP adapter. Does not invent device or object IDs."""
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


class BacnetGateway(BMSGateway):
    protocol = "bacnet"

    def __init__(self) -> None:
        self._connected = False
        self.host: str | None = None
        self.port: int | None = None
        self._last_error: str | None = None
        self._last_code: str | None = None
        self._last_connected_at: str | None = None
        self._stack = None

    def _load_stack(self):
        try:
            import BAC0  # type: ignore

            return ("BAC0", BAC0)
        except Exception:
            pass
        try:
            import bacpypes3  # type: ignore

            return ("bacpypes3", bacpypes3)
        except Exception:
            pass
        try:
            import bacpypes  # type: ignore

            return ("bacpypes", bacpypes)
        except Exception:
            return None

    def connect(self, host: str, port: int = 47808, **kwargs: Any) -> BmsHealth:
        del kwargs
        self.host = host
        self.port = int(port or 47808)
        stack = self._load_stack()
        if stack is None:
            self._connected = False
            self._last_code = ADAPTER_UNAVAILABLE
            self._last_error = "BACnet stack is not installed (BAC0/bacpypes)."
            raise BmsAdapterError(ADAPTER_UNAVAILABLE, self._last_error)
        name, mod = stack
        try:
            if name == "BAC0":
                self._stack = mod.connect(ip=host)
            self._connected = True
            self._last_code = None
            self._last_error = None
            self._last_connected_at = utc_now().isoformat()
            return self.health()
        except BmsAdapterError:
            raise
        except Exception as exc:
            self._connected = False
            self._last_code = CONNECTION_FAILED
            self._last_error = str(exc) or CONNECTION_FAILED
            raise BmsAdapterError(CONNECTION_FAILED, self._last_error)

    def disconnect(self) -> BmsHealth:
        self._connected = False
        self._stack = None
        return self.health()

    def health(self) -> BmsHealth:
        return BmsHealth(
            connected=bool(self._connected and self._last_connected_at),
            protocol=self.protocol,
            code=None if self._connected else (self._last_code or CONNECTION_FAILED if self.host else None),
            message=self._last_error,
            host=self.host,
            port=self.port,
            last_connected_at=self._last_connected_at if self._connected else None,
        )

    def discover_devices(self) -> List[DiscoveredDevice]:
        if not self._connected:
            return []
        if self._stack is None:
            return []
        try:
            whois = getattr(self._stack, "whois", None)
            raw = whois() if callable(whois) else []
            out: List[DiscoveredDevice] = []
            for item in raw or []:
                ident = str(getattr(item, "deviceIdentifier", None) or getattr(item, "address", None) or item)
                if ident:
                    out.append(DiscoveredDevice(device_identifier=ident, name=ident, device_type="UNKNOWN"))
            return out
        except Exception:
            return []

    def discover_points(self, device_id: str) -> List[DiscoveredPoint]:
        del device_id
        if not self._connected:
            return []
        return []

    def read_point(self, point_id: str) -> PointReading:
        if not self._connected:
            return PointReading(point_id=point_id, value=None, unit=None, quality="MISSING", timestamp=utc_now().isoformat(), source="LIVE_BMS")
        return PointReading(point_id=point_id, value=None, unit=None, quality="MISSING", timestamp=utc_now().isoformat(), source="LIVE_BMS")

    def read_points(self, point_ids: List[str]) -> List[PointReading]:
        return [self.read_point(pid) for pid in point_ids]

    def execute_write(self, point_id: str, value: float, priority: int = 10) -> WriteOutcome:
        del priority
        if not self._connected:
            return WriteOutcome(success=False, code=CONNECTION_FAILED, message="BACnet adapter is not connected.", point_id=point_id, value=value)
        writer = getattr(self._stack, "write", None) or getattr(self._stack, "write_property", None)
        if not callable(writer):
            return WriteOutcome(success=False, code=ADAPTER_UNAVAILABLE, message="BACnet stack has no write API.", point_id=point_id, value=value)
        try:
            writer(point_id, value)
            return WriteOutcome(success=True, code="OK", message="WRITTEN", point_id=point_id, value=value)
        except Exception as exc:
            return WriteOutcome(success=False, code=CONNECTION_FAILED, message=str(exc), point_id=point_id, value=value)

    def write_point(self, point_id: str, value: float, priority: int = 10) -> WriteOutcome:
        return reject_write(point_id, value, priority)

    def write_points(self, writes: List[Dict[str, Any]]) -> List[WriteOutcome]:
        return reject_writes(writes)
