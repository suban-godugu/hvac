"""
Domain models and schema definitions for the Closed-Loop Scheduling & Supervisory Agent.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class AgentLifecycleState(str, Enum):
    IDLE = "IDLE"
    OBSERVE = "OBSERVE"
    VALIDATE_DATA = "VALIDATE_DATA"
    BUILD_STATE = "BUILD_STATE"
    DETECT_OPPORTUNITIES = "DETECT_OPPORTUNITIES"
    GENERATE_CANDIDATES = "GENERATE_CANDIDATES"
    EVALUATE_CANDIDATES = "EVALUATE_CANDIDATES"
    SAFETY_CHECK = "SAFETY_CHECK"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    KEEP_OR_ROLLBACK = "KEEP_OR_ROLLBACK"
    LEARN = "LEARN"


class AgentMode(str, Enum):
    AUTO = "AUTO"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    ADVISORY = "ADVISORY"
    SAFE_MODE = "SAFE_MODE"


class VerificationOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    PENDING = "PENDING"


@dataclass
class CandidateAction:
    id: str
    opportunity_code: str  # O1, O2, O3, O4
    point_id: str
    equipment_id: str
    current_value: Optional[float]
    proposed_value: float
    reason: str
    confidence: float
    verification_window_minutes: int
    expected_result: str
    rollback_value: Optional[float]
    priority: int = 10
    constraints_applied: List[str] = field(default_factory=list)


@dataclass
class OpportunityEvaluationResult:
    opportunity_code: str  # O1, O2, O3, O4
    equipment: str
    current_state: Dict[str, Any]
    candidates: List[CandidateAction]
    recommended_action: Optional[CandidateAction]
    reason: str
    confidence: float
    constraints: List[str]
    expected_impact: Dict[str, Any]  # e.g. {"estimated_power_kw_impact": 4.5, "cost_impact_usd": 0.54}
    verification_plan: Dict[str, Any]  # e.g. {"target_point": "...", "tolerance": 0.5, "window_minutes": 15}


@dataclass
class SafetyCheckResult:
    passed: bool
    status: str  # PASS / REJECT
    rejection_reason: Optional[str] = None
    checks: List[str] = field(default_factory=list)
    clamped_value: Optional[float] = None


@dataclass
class ActionRecordModel:
    id: str
    opportunity_code: str
    point_id: str
    previous_value: Optional[float]
    proposed_value: float
    actual_value: Optional[float]
    reason: str
    confidence: float
    safety_result: Dict[str, Any]
    timestamp: str
    verification_window: int
    expected_result: str
    actual_result: Optional[str]
    rollback_value: Optional[float]
    final_status: str  # PENDING_APPROVAL, EXECUTED, VERIFIED_KEPT, ROLLED_BACK, REJECTED_SAFETY


@dataclass
class BMSPoint:
    point_id: str
    value: Any
    unit: str
    quality: str  # GOOD, UNRELIABLE, FAULT, OVERRIDDEN
    timestamp: str
    writable: bool = True


@dataclass
class BMSWriteCommand:
    point_id: str
    value: float
    priority: int = 10
    release: bool = False


@dataclass
class BMSWriteResult:
    point_id: str
    success: bool
    written_value: float
    priority: int
    transaction_id: str
    timestamp: str
    error_message: Optional[str] = None


@dataclass
class BMSAck:
    transaction_id: str
    status: str  # ACK, NAK, TIMEOUT
    timestamp: str

@dataclass
class ZoneState:
    id: str = "Z1"
    name: str = "Zone 1"
    temp_actual: float = 23.0
    cooling_sp: float = 22.5
    heating_sp: float = 21.0
    occupied: bool = True
    damper_pos: float = 50.0
    zone_id: Optional[str] = None
    temperature: Optional[float] = None
    setpoint: Optional[float] = None
    damper_position: Optional[float] = None
    cooling_demand: Optional[float] = None

@dataclass
class AHUState:
    id: str = "AHU-1"
    name: str = "Floor 1 AHU"
    sat_actual: float = 13.0
    sat_setpoint: float = 12.8
    supply_air_temperature: float = 12.8
    supply_air_setpoint: float = 12.8
    fan_speed_pct: float = 65.0
    duct_static_pressure: float = 1.2
    vav_zones: List[Any] = field(default_factory=list)

@dataclass
class ChillerState:
    id: str = "CH-1"
    name: str = "Centrifugal Chiller"
    status: Any = "RUNNING"
    capacity_tons: float = 120.0
    current_tons: float = 70.0
    current_load_tons: float = 76.0
    power_kw: float = 42.5
    plr_pct: float = 63.3
    kw_per_ton: float = 0.56

@dataclass
class ChillerPlantState:
    plant_id: str = "CHILLER-PLANT-01"
    total_capacity_tons: float = 240.0
    total_tons: float = 70.0
    current_load_tons: float = 76.0
    chws_temp: float = 6.8
    chwr_temp: float = 12.2
    chws_temperature: float = 6.8
    chwr_temperature: float = 12.2
    chws_setpoint: float = 6.7
    flow_rate_lps: float = 11.0
    active_chillers: int = 1
    chillers: List[Any] = field(default_factory=list)
