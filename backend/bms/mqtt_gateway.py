"""MQTT adapter. No invented topics."""
from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlparse

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


class MqttGateway(BMSGateway):
    protocol = "mqtt"

    def __init__(self) -> None:
        self._connected = False
        self.host: str | None = None
        self.port: int | None = None
        self._last_error: str | None = None
        self._last_code: str | None = None
        self._last_connected_at: str | None = None

    def connect(self, host: str, port: int = 1883, **kwargs: Any) -> BmsHealth:
        url = kwargs.get("url") or host
        parsed = urlparse(url if "://" in str(url) else f"mqtt://{host}:{port}")
        self.host = parsed.hostname or host
        self.port = parsed.port or int(port or 1883)
        try:
            import paho.mqtt.client as mqtt  # type: ignore
        except Exception:
            self._connected = False
            self._last_code = ADAPTER_UNAVAILABLE
            self._last_error = "paho-mqtt is not installed."
            raise BmsAdapterError(ADAPTER_UNAVAILABLE, self._last_error)
        try:
            client = mqtt.Client()
            client.connect(self.host, self.port, keepalive=5)
            client.disconnect()
            self._connected = True
            self._last_error = None
            self._last_code = None
            self._last_connected_at = utc_now().isoformat()
            return self.health()
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
            return WriteOutcome(success=False, code=CONNECTION_FAILED, message="MQTT adapter is not connected.", point_id=point_id, value=value)
        return WriteOutcome(success=False, code=ADAPTER_UNAVAILABLE, message="MQTT write requires a commissioned topic map.", point_id=point_id, value=value)

    def write_point(self, point_id: str, value: float, priority: int = 10) -> WriteOutcome:
        return reject_write(point_id, value, priority)

    def write_points(self, writes: List[Dict[str, Any]]) -> List[WriteOutcome]:
        return reject_writes(writes)
