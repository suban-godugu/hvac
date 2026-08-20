"""Shared BMS adapter types. Phase 1 is read-only."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


WRITE_DISABLED = "WRITE_DISABLED"
ADAPTER_UNAVAILABLE = "BMS_ADAPTER_UNAVAILABLE"
CONNECTION_FAILED = "BMS_CONNECTION_FAILED"


@dataclass
class BmsHealth:
    connected: bool
    protocol: str
    code: Optional[str] = None
    message: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    last_connected_at: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "protocol": self.protocol,
            "code": self.code,
            "message": self.message,
            "host": self.host,
            "port": self.port,
            "last_connected_at": self.last_connected_at,
        }


@dataclass
class DiscoveredDevice:
    device_identifier: str
    name: Optional[str] = None
    device_type: Optional[str] = None
    status: str = "ONLINE"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveredPoint:
    point_identifier: str
    name: Optional[str] = None
    object_type: Optional[str] = None
    object_instance: Optional[str] = None
    register: Optional[str] = None
    unit: Optional[str] = None
    data_type: Optional[str] = None
    readable: bool = True
    writable: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PointReading:
    point_id: str
    value: Optional[float]
    unit: Optional[str]
    quality: str
    timestamp: str
    source: str = "LIVE_BMS"


@dataclass
class WriteOutcome:
    success: bool
    code: str
    message: str
    point_id: Optional[str] = None
    value: Optional[float] = None
    timestamp: str = field(default_factory=lambda: utc_now().isoformat())

    def as_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "code": self.code,
            "message": self.message,
            "point_id": self.point_id,
            "value": self.value,
            "timestamp": self.timestamp,
        }


class BmsAdapterError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class BMSGateway(ABC):
    protocol: str = "unknown"

    @abstractmethod
    def connect(self, host: str, port: int, **kwargs: Any) -> BmsHealth:
        pass

    @abstractmethod
    def disconnect(self) -> BmsHealth:
        pass

    @abstractmethod
    def health(self) -> BmsHealth:
        pass

    @abstractmethod
    def discover_devices(self) -> List[DiscoveredDevice]:
        pass

    @abstractmethod
    def discover_points(self, device_id: str) -> List[DiscoveredPoint]:
        pass

    @abstractmethod
    def read_point(self, point_id: str) -> PointReading:
        pass

    @abstractmethod
    def read_points(self, point_ids: List[str]) -> List[PointReading]:
        pass

    @abstractmethod
    def write_point(self, point_id: str, value: float, priority: int = 10) -> WriteOutcome:
        pass

    @abstractmethod
    def write_points(self, writes: List[Dict[str, Any]]) -> List[WriteOutcome]:
        pass
