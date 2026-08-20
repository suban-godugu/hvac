"""
BMS Gateway interface and implementations (Simulator & Production).
Provides read_point, read_state, write_point, write_batch, and get_acknowledgement.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import uuid

from backend.agents.scheduling_supervisory.state import (
    BMSPoint,
    BMSWriteCommand,
    BMSWriteResult,
    BMSAck
)


class BMSGatewayBase(ABC):
    """Abstract Base Class defining the standard BMS Gateway interface."""

    @abstractmethod
    def read_point(self, point_id: str) -> BMSPoint:
        pass

    @abstractmethod
    def read_state(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def write_point(self, point_id: str, value: float, priority: int = 10) -> BMSWriteResult:
        pass

    @abstractmethod
    def write_batch(self, writes: List[BMSWriteCommand]) -> List[BMSWriteResult]:
        pass

    @abstractmethod
    def get_acknowledgement(self, transaction_id: str) -> BMSAck:
        pass


class SimulatorBMSGateway(BMSGatewayBase):
    """
    In-memory simulation gateway modeling BACnet Commandable Priority Arrays:
    Priority 8  = Manual Operator Override
    Priority 10 = Supervisory Agent Automated Control
    Priority 16 = Default Baseline Schedule
    """

    def __init__(self):
        # Priority array per point: { point_id: { priority: value } }
        self.priority_arrays: Dict[str, Dict[int, float]] = {}
        self.transactions: Dict[str, BMSWriteResult] = {}
        self.points_db: Dict[str, BMSPoint] = {}
        self.connected = False

    def is_production_connected(self) -> bool:
        return False

    def _get_effective_value(self, point_id: str, default: float = 0.0) -> float:
        if point_id not in self.priority_arrays:
            return default
        array = self.priority_arrays[point_id]
        for pri in sorted(array.keys()):
            val = array[pri]
            if val is not None:
                return val
        return default

    def read_point(self, point_id: str) -> BMSPoint:
        val = self._get_effective_value(point_id)
        return BMSPoint(
            point_id=point_id,
            value=val,
            unit="°C" if "TEMP" in point_id or "SP" in point_id or "SAT" in point_id else "status",
            quality="GOOD",
            timestamp=datetime.utcnow().isoformat(),
            writable=True
        )

    def read_state(self) -> Dict[str, Any]:
        # Return live simulated state representation
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "points": {p: self._get_effective_value(p) for p in self.priority_arrays}
        }

    def write_point(self, point_id: str, value: float, priority: int = 10) -> BMSWriteResult:
        from backend.bms.command_writer import write_point as reject_write

        blocked = reject_write(point_id, value, priority)
        tx_id = f"tx-{uuid.uuid4().hex[:8]}"
        if not blocked.success:
            return BMSWriteResult(
                point_id=point_id,
                success=False,
                written_value=value,
                priority=priority,
                transaction_id=tx_id,
                timestamp=datetime.utcnow().isoformat(),
                error_message=blocked.code,
            )
        from backend.services.hvac_safety_contract import is_demo_source, is_safe_mode

        if is_safe_mode():
            return BMSWriteResult(point_id=point_id, success=False, written_value=value, priority=priority, transaction_id=tx_id, timestamp=datetime.utcnow().isoformat())
        if os.getenv("HVAC_ALLOW_SIM_WRITES", "0") not in ("1", "true", "TRUE"):
            return BMSWriteResult(point_id=point_id, success=False, written_value=value, priority=priority, transaction_id=tx_id, timestamp=datetime.utcnow().isoformat())
        if point_id not in self.priority_arrays:
            self.priority_arrays[point_id] = {}

        self.priority_arrays[point_id][priority] = value

        res = BMSWriteResult(
            point_id=point_id,
            success=True,
            written_value=value,
            priority=priority,
            transaction_id=tx_id,
            timestamp=datetime.utcnow().isoformat()
        )
        self.transactions[tx_id] = res
        return res

    def write_batch(self, writes: List[BMSWriteCommand]) -> List[BMSWriteResult]:
        results: List[BMSWriteResult] = []
        for cmd in writes:
            res = self.write_point(cmd.point_id, cmd.value, cmd.priority)
            results.append(res)
        return results

    def get_acknowledgement(self, transaction_id: str) -> BMSAck:
        if transaction_id in self.transactions:
            return BMSAck(
                transaction_id=transaction_id,
                status="ACK",
                timestamp=datetime.utcnow().isoformat()
            )
        return BMSAck(
            transaction_id=transaction_id,
            status="NAK",
            timestamp=datetime.utcnow().isoformat()
        )


class ProductionBMSGateway(BMSGatewayBase):
    """Production adapter bound to backend/bms. Connectivity is handshake-only, never HVAC_BMS_CONNECTED."""

    def __init__(self, bacnet_ip_host: str = "127.0.0.1", bacnet_port: int = 47808, protocol: str = "bacnet"):
        self.host = bacnet_ip_host
        self.port = bacnet_port
        self.protocol = protocol
        self.connected = False

    def is_production_connected(self) -> bool:
        from backend.bms.connection_manager import get_connection_manager

        return bool(get_connection_manager().is_production_connected())

    def read_point(self, point_id: str) -> BMSPoint:
        from backend.bms.connection_manager import get_connection_manager

        mgr = get_connection_manager()
        adapter = mgr.adapter()
        if adapter is None or not mgr.is_production_connected():
            return BMSPoint(point_id=point_id, value=None, unit="", quality="MISSING", timestamp=datetime.utcnow().isoformat(), writable=False)
        reading = adapter.read_point(point_id)
        return BMSPoint(
            point_id=point_id,
            value=reading.value,
            unit=reading.unit or "",
            quality=reading.quality,
            timestamp=reading.timestamp,
            writable=False,
        )

    def read_state(self) -> Dict[str, Any]:
        from backend.bms.connection_manager import get_connection_manager

        h = get_connection_manager().health()
        return {"timestamp": datetime.utcnow().isoformat(), "connected": h.connected, "protocol": h.protocol, "points": {}}

    def write_point(self, point_id: str, value: float, priority: int = 10) -> BMSWriteResult:
        from backend.bms.command_writer import write_point as reject_write

        blocked = reject_write(point_id, value, priority)
        tx_id = f"tx-{uuid.uuid4().hex[:8]}"
        return BMSWriteResult(
            point_id=point_id,
            success=False,
            written_value=value,
            priority=priority,
            transaction_id=tx_id,
            timestamp=datetime.utcnow().isoformat(),
            error_message=blocked.code,
        )

    def write_batch(self, writes: List[BMSWriteCommand]) -> List[BMSWriteResult]:
        return [self.write_point(cmd.point_id, cmd.value, cmd.priority) for cmd in writes]

    def get_acknowledgement(self, transaction_id: str) -> BMSAck:
        return BMSAck(transaction_id=transaction_id, status="NAK", timestamp=datetime.utcnow().isoformat())


class MqttBMSGateway(ProductionBMSGateway):
    def __init__(self):
        super().__init__(protocol="mqtt")


class OpcUaBMSGateway(ProductionBMSGateway):
    def __init__(self):
        super().__init__(protocol="opcua")


_GATEWAY = None


class RestBMSGateway(ProductionBMSGateway):
    def __init__(self):
        super().__init__(protocol="rest")
        self.host = os.getenv("HVAC_BMS_REST_URL", "")


def get_bms_gateway() -> BMSGatewayBase:
    """Factory. Simulation is never live. Production never falls back to simulator. HVAC_BMS_CONNECTED is ignored."""
    global _GATEWAY
    if _GATEWAY is not None:
        return _GATEWAY
    mode = (os.getenv("HVAC_BMS_MODE", "simulation") or "simulation").lower()
    protocol = (os.getenv("HVAC_BMS_PROTOCOL") or "bacnet").lower()
    if mode in ("simulation", "simulator", "sim"):
        gw = SimulatorBMSGateway()
        gw.connected = False
        _GATEWAY = gw
        return _GATEWAY
    if protocol in ("mqtt",):
        _GATEWAY = MqttBMSGateway()
    elif protocol in ("opcua", "opc-ua"):
        _GATEWAY = OpcUaBMSGateway()
    elif protocol in ("rest", "http"):
        _GATEWAY = RestBMSGateway()
    elif protocol in ("modbus", "modbus-tcp"):
        _GATEWAY = ProductionBMSGateway(protocol="modbus")
    else:
        _GATEWAY = ProductionBMSGateway(
            bacnet_ip_host=os.getenv("HVAC_BACNET_HOST", "127.0.0.1"),
            bacnet_port=int(os.getenv("HVAC_BACNET_PORT", "47808")),
            protocol="bacnet",
        )
    return _GATEWAY


def reset_bms_gateway() -> None:
    global _GATEWAY
    _GATEWAY = None

