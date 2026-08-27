"""BACnet/IP adapter. Does not invent device or object IDs."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

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

_POINT_RE = re.compile(
    r"^(?P<addr>.+?)\s+(?P<obj>analogInput|analogOutput|analogValue|binaryInput|binaryOutput|binaryValue|"
    r"multiStateInput|multiStateOutput|multiStateValue|AI|AO|AV|BI|BO|BV)\s+(?P<inst>\d+)\s*$",
    re.IGNORECASE,
)


class BacnetGateway(BMSGateway):
    protocol = "bacnet"

    def __init__(self) -> None:
        self._connected = False
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self._last_error: Optional[str] = None
        self._last_code: Optional[str] = None
        self._last_connected_at: Optional[str] = None
        self._stack = None
        self._stack_name: Optional[str] = None
        self._point_cache: Dict[str, DiscoveredPoint] = {}

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
            self._last_error = "BACnet stack is not installed (BAC0/bacpypes). pip install -r backend/requirements-bacnet.txt"
            raise BmsAdapterError(ADAPTER_UNAVAILABLE, self._last_error)
        name, mod = stack
        try:
            if name == "BAC0":
                # BAC0.connect binds local IP; remote device is addressed on read/whois.
                try:
                    self._stack = mod.connect(ip=host)
                except TypeError:
                    self._stack = mod.connect()
                self._stack_name = "BAC0"
            else:
                # bacpypes / bacpypes3: handshake presence only until a site binds a full stack.
                self._stack = mod
                self._stack_name = name
            self._connected = True
            self._last_code = None
            self._last_error = None
            self._last_connected_at = utc_now().isoformat()
            self._point_cache.clear()
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
        if self._stack is not None and self._stack_name == "BAC0":
            try:
                disconnect = getattr(self._stack, "disconnect", None)
                if callable(disconnect):
                    disconnect()
            except Exception:
                pass
        self._stack = None
        self._stack_name = None
        self._point_cache.clear()
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

    def _parse_point_id(self, point_id: str) -> Optional[Tuple[str, str, int]]:
        m = _POINT_RE.match((point_id or "").strip())
        if not m:
            return None
        obj = m.group("obj")
        aliases = {
            "AI": "analogInput",
            "AO": "analogOutput",
            "AV": "analogValue",
            "BI": "binaryInput",
            "BO": "binaryOutput",
            "BV": "binaryValue",
        }
        obj_full = aliases.get(obj.upper(), obj)
        return m.group("addr"), obj_full, int(m.group("inst"))

    def discover_points(self, device_id: str) -> List[DiscoveredPoint]:
        if not self._connected or self._stack is None:
            return []
        # Prefer cached points discovered via BAC0 device objects when present.
        cached = [p for p in self._point_cache.values() if (p.metadata or {}).get("device") == device_id]
        if cached:
            return list(cached)
        out: List[DiscoveredPoint] = []
        try:
            if self._stack_name == "BAC0":
                devices = getattr(self._stack, "devices", None) or []
                for dev in devices:
                    addr = str(getattr(dev, "properties", None) and getattr(dev.properties, "address", None) or getattr(dev, "address", None) or device_id)
                    if device_id and str(device_id) not in (addr, str(dev)):
                        # Still allow match on whois identifier equality
                        if str(device_id) != addr:
                            continue
                    points = getattr(dev, "points", None) or []
                    for pt in points:
                        name = str(getattr(pt, "properties", None) and getattr(pt.properties, "name", None) or getattr(pt, "name", None) or pt)
                        obj_type = str(getattr(pt, "properties", None) and getattr(pt.properties, "type", None) or "analogInput")
                        inst = str(getattr(pt, "properties", None) and getattr(pt.properties, "address", None) or getattr(pt, "address", None) or "")
                        ident = f"{addr} {obj_type} {inst}".strip()
                        dp = DiscoveredPoint(
                            point_identifier=ident,
                            name=name,
                            object_type=obj_type,
                            object_instance=inst,
                            unit=None,
                            readable=True,
                            writable="Output" in obj_type or "Value" in obj_type,
                            metadata={"device": device_id},
                        )
                        self._point_cache[ident] = dp
                        out.append(dp)
        except Exception:
            return out
        return out

    def read_point(self, point_id: str) -> PointReading:
        ts = utc_now().isoformat()
        if not self._connected:
            return PointReading(point_id=point_id, value=None, unit=None, quality="MISSING", timestamp=ts, source="LIVE_BMS")
        if self._stack is None or self._stack_name != "BAC0":
            return PointReading(point_id=point_id, value=None, unit=None, quality="MISSING", timestamp=ts, source="LIVE_BMS")
        parsed = self._parse_point_id(point_id)
        reader = getattr(self._stack, "read", None)
        if not callable(reader):
            return PointReading(point_id=point_id, value=None, unit=None, quality="MISSING", timestamp=ts, source="LIVE_BMS")
        try:
            if parsed:
                addr, obj_type, inst = parsed
                raw = reader(f"{addr} {obj_type} {inst} presentValue")
            else:
                raw = reader(point_id)
            if raw is None:
                return PointReading(point_id=point_id, value=None, unit=None, quality="MISSING", timestamp=ts, source="LIVE_BMS")
            try:
                value = float(raw)
            except (TypeError, ValueError):
                value = float(raw[0]) if isinstance(raw, (list, tuple)) and raw else None
            if value is None:
                return PointReading(point_id=point_id, value=None, unit=None, quality="MISSING", timestamp=ts, source="LIVE_BMS")
            return PointReading(point_id=point_id, value=value, unit=None, quality="GOOD", timestamp=ts, source="LIVE_BMS")
        except Exception:
            return PointReading(point_id=point_id, value=None, unit=None, quality="BAD", timestamp=ts, source="LIVE_BMS")

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
