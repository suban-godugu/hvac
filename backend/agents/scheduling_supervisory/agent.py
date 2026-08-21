"""
SchedulingSupervisoryAgent: Top-level agent encapsulating all closed-loop submodules:
StateBuilder, OpportunityDetector, O1-O4 Engines, SupervisoryDecisionEngine,
SafetyEngine, BMSGateway, VerificationEngine, RollbackEngine, and AuditLogger.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.agents.scheduling_supervisory.state import (
    AgentLifecycleState,
    AgentMode,
    CandidateAction,
    OpportunityEvaluationResult,
    ActionRecordModel,
    SafetyCheckResult
)
from backend.agents.scheduling_supervisory.state_builder import StateBuilder
from backend.agents.scheduling_supervisory.opportunity_detector import OpportunityDetector
from backend.agents.scheduling_supervisory.o1_engine import OptimumStartStopEngine
from backend.agents.scheduling_supervisory.o2_engine import SpaceTemperatureOptimizationEngine
from backend.agents.scheduling_supervisory.o3_engine import MasterAHUSATOptimizationEngine
from backend.agents.scheduling_supervisory.o4_engine import ChillerCompressorStagingEngine
from backend.agents.scheduling_supervisory.supervisory_decision_engine import SupervisoryDecisionEngine
from backend.agents.scheduling_supervisory.safety_engine import SafetyEngine
from backend.agents.scheduling_supervisory.gateway import BMSGatewayBase, get_bms_gateway
from backend.agents.scheduling_supervisory.verification_engine import VerificationEngine
from backend.agents.scheduling_supervisory.rollback_engine import RollbackEngine
from backend.agents.scheduling_supervisory.audit_logger import AuditLogger
from backend.agents.scheduling_supervisory.metrics_service import MetricsService
from backend.agents.scheduling_supervisory.llm_explainer import SupervisoryExplainer


class SchedulingSupervisoryAgent:
    def __init__(self, gateway: Optional[BMSGatewayBase] = None):
        # 1. Core Submodules
        self.state_builder = StateBuilder()
        self.opportunity_detector = OpportunityDetector()
        
        # 2. Opportunity Engines (Common Interface)
        self.o1_engine = OptimumStartStopEngine()
        self.o2_engine = SpaceTemperatureOptimizationEngine()
        self.o3_engine = MasterAHUSATOptimizationEngine()
        self.o4_engine = ChillerCompressorStagingEngine()

        # 3. Decision & Safety Kernels
        self.decision_engine = SupervisoryDecisionEngine()
        self.safety_engine = SafetyEngine()

        # 4. BMS Gateway & Execution
        self.gateway = gateway if gateway is not None else get_bms_gateway()

        # 5. Verification, Rollback & Audit
        self.verification_engine = VerificationEngine()
        self.rollback_engine = RollbackEngine(self.gateway)
        self.audit_logger = AuditLogger()
        self.metrics_service = MetricsService()
        self.explainer = SupervisoryExplainer()

        # Simulation state
        self.simulation_minutes_elapsed = 0
        self.current_scenario_id = "scenario_summer_peak"

        # Agent state
        self.lifecycle_state = AgentLifecycleState.IDLE
        self.mode = AgentMode.AUTO
        self.pending_approvals: List[CandidateAction] = []
        self.latest_state: Dict[str, Any] = {}
        self.latest_actions: List[ActionRecordModel] = []
        self.latest_evaluation_results: List[OpportunityEvaluationResult] = []

    def set_scenario(self, scenario_id: str):
        self.current_scenario_id = scenario_id

    def generate_simulated_telemetry(self) -> Dict[str, Any]:
        """Generates realistic building telemetry based on simulated time-of-day and weather."""
        hour = 8 + (self.simulation_minutes_elapsed // 60)
        minute = self.simulation_minutes_elapsed % 60
        sim_time_str = f"{hour:02d}:{minute:02d}"

        # Ambient weather from live weather service (OpenWeatherMap / Open-Meteo)
        from backend.services.weather_service import weather_service
        live_w = weather_service.cached_weather
        oat = float(live_w.get("oat") if live_w.get("oat") is not None else 28.5)
        oah = float(live_w.get("humidity") if live_w.get("humidity") is not None else 55.0)
        solar = 450.0 if 8 <= hour <= 17 else 50.0

        # Building zone thermal state
        ahus = [
            {
                "id": "AHU-1",
                "fan_status": True,
                "fan_speed_pct": 65.0,
                "fan_power_kw": 10.4,
                "sat_actual": 13.2,
                "sat_setpoint": 13.0,
                "cooling_valve_pct": 48.0,
                "vav_zones": [
                    {
                        "id": f"VAV-{100 + i}",
                        "temp_actual": 22.4 + (0.2 * (i % 3)),
                        "cooling_sp": 23.0,
                        "heating_sp": 20.0,
                        "deadband": 1.5,
                        "damper_pos": 35.0 + (5.0 * (i % 4)),
                        "occupied": i != 3 and i != 7
                    }
                    for i in range(1, 13)
                ]
            }
        ]

        # Chiller plant thermal state
        plant = {
            "total_tons": 76.0,
            "total_power_kw": 42.5,
            "plant_efficiency_kw_per_ton": 0.56,
            "chws_temp": 6.8,
            "chws_setpoint": 6.7,
            "chwr_temp": 12.2,
            "flow_rate_lps": 28.5,
            "chillers": [
                {
                    "id": "CH-1",
                    "status": True,
                    "tons": 76.0,
                    "power_kw": 42.5,
                    "chws_temp": 6.8,
                    "chwr_temp": 12.2,
                    "flow_lps": 28.5,
                    "compressor_stages": {"1A": 100, "1B": 26},
                    "maintenance_lock": False
                },
                {
                    "id": "CH-2",
                    "status": False,
                    "tons": 0.0,
                    "power_kw": 0.0,
                    "chws_temp": 6.8,
                    "chwr_temp": 12.2,
                    "flow_lps": 0.0,
                    "compressor_stages": {"2A": 0, "2B": 0},
                    "maintenance_lock": False
                }
            ]
        }

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "simulation_time": sim_time_str,
            "scenario_id": self.current_scenario_id,
            "weather": {
                "oat": oat,
                "oah": oah,
                "humidity": oah,
                "wet_bulb": 18.2,
                "solar_irradiance": solar,
                "source": live_w.get("source", "OpenWeatherMap Live API")
            },
            "ahus": ahus,
            "plant": plant,
            "building_occupancy": {
                "scheduled_start": "06:00",
                "occupancy_start": "08:00",
                "scheduled_stop": "18:00",
                "occupancy_stop": "18:00",
                "is_occupied_now": 8 <= hour < 18
            },
            "stale_age_seconds": 1.5
        }

    def run_supervisory_cycle(self, elapsed_minutes: int = 5) -> Dict[str, Any]:
        """Advances simulation clock and runs complete supervisory control cycle."""
        self.simulation_minutes_elapsed += elapsed_minutes
        telemetry = self.generate_simulated_telemetry()
        return self.run_cycle(telemetry)

    def set_mode(self, new_mode: AgentMode):
        self.mode = new_mode
        return {"success": True, "mode": str(self.mode)}

    def switch_mode(self, new_mode: AgentMode):
        return self.set_mode(new_mode)

    def approve_action(self, action_id: str) -> Dict[str, Any]:
        match = next((act for act in self.pending_approvals if act.id == action_id), None)
        if match:
            self.pending_approvals.remove(match)
            return {"success": True, "action_id": action_id, "status": "APPROVED"}
        return {"success": False, "message": f"Action {action_id} not found in pending queue"}

    def reject_action(self, action_id: str, reason: str = "Operator rejected") -> Dict[str, Any]:
        match = next((act for act in self.pending_approvals if act.id == action_id), None)
        if match:
            self.pending_approvals.remove(match)
            return {"success": True, "action_id": action_id, "status": "REJECTED", "reason": reason}
        return {"success": False, "message": f"Action {action_id} not found in pending queue"}

    def run_cycle(self, raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes full closed-loop supervisory control cycle:
        OBSERVE -> VALIDATE_DATA -> BUILD_STATE -> DETECT -> EVALUATE -> SAFETY -> EXECUTE -> VERIFY -> AUDIT -> IDLE
        """
        # Step 1: Observe & Validate Data Quality -> Build State
        self.lifecycle_state = AgentLifecycleState.OBSERVE
        self.lifecycle_state = AgentLifecycleState.VALIDATE_DATA
        state = self.state_builder.validate_and_build_state(raw_telemetry)
        self.latest_state = state
        self.lifecycle_state = AgentLifecycleState.BUILD_STATE

        # Safety Interlock: If sensor data invalid, force SAFE_MODE
        if not state["data_quality_valid"]:
            self.mode = AgentMode.SAFE_MODE
            self.lifecycle_state = AgentLifecycleState.IDLE
            return self._build_cycle_response(
                actions=[],
                cycle_summary=f"SAFE MODE LOCKDOWN: {'; '.join(state['sensor_faults'])}"
            )

        # Step 2: Detect Opportunities
        self.lifecycle_state = AgentLifecycleState.DETECT_OPPORTUNITIES
        detected = self.opportunity_detector.detect_opportunities(state)

        # Step 3: Evaluate Opportunities through Common Interface
        self.lifecycle_state = AgentLifecycleState.GENERATE_CANDIDATES
        self.lifecycle_state = AgentLifecycleState.EVALUATE_CANDIDATES

        eval_results: List[OpportunityEvaluationResult] = [
            self.o1_engine.evaluate(state),
            self.o2_engine.evaluate(state),
            self.o3_engine.evaluate(state),
            self.o4_engine.evaluate(state)
        ]
        self.latest_evaluation_results = eval_results

        # Step 4: Supervisory Decision Engine (Conflict Resolution & Ranking)
        coordinated_candidates = self.decision_engine.produce_coordinated_action_set(eval_results)

        # Step 5: Safety Validation Kernel (11 Safety Gates)
        self.lifecycle_state = AgentLifecycleState.SAFETY_CHECK
        approved_actions: List[CandidateAction] = []
        rejected_actions: List[CandidateAction] = []
        action_records: List[ActionRecordModel] = []
        dispatched_batch: List[CandidateAction] = []

        for candidate in coordinated_candidates:
            safety_res = self.safety_engine.validate_action(
                candidate,
                state,
                dispatched_this_cycle=dispatched_batch
            )
            
            if safety_res.passed:
                approved_actions.append(candidate)
                dispatched_batch.append(candidate)
            else:
                rejected_actions.append(candidate)
                # Create rejected audit record
                rec = ActionRecordModel(
                    id=candidate.id,
                    opportunity_code=candidate.opportunity_code,
                    point_id=candidate.point_id,
                    previous_value=candidate.current_value,
                    proposed_value=candidate.proposed_value,
                    actual_value=candidate.current_value,
                    reason=f"REJECTED BY SAFETY: {safety_res.rejection_reason}",
                    confidence=candidate.confidence,
                    safety_result={"status": "REJECT", "reason": safety_res.rejection_reason, "checks": safety_res.checks},
                    timestamp=datetime.utcnow().isoformat(),
                    verification_window=candidate.verification_window_minutes,
                    expected_result=candidate.expected_result,
                    actual_result="Action blocked by Safety Kernel",
                    rollback_value=candidate.rollback_value,
                    final_status="REJECTED_SAFETY"
                )
                action_records.append(rec)
                self.audit_logger.log_action(rec)

        # Step 6: Execution via BMS Gateway (Gated by Operating Mode)
        self.lifecycle_state = AgentLifecycleState.EXECUTE

        if self.mode == AgentMode.APPROVAL_REQUIRED:
            self.pending_approvals = approved_actions
            for act in approved_actions:
                rec = ActionRecordModel(
                    id=act.id,
                    opportunity_code=act.opportunity_code,
                    point_id=act.point_id,
                    previous_value=act.current_value,
                    proposed_value=act.proposed_value,
                    actual_value=None,
                    reason=act.reason,
                    confidence=act.confidence,
                    safety_result={"status": "PASS", "checks": act.constraints_applied},
                    timestamp=datetime.utcnow().isoformat(),
                    verification_window=act.verification_window_minutes,
                    expected_result=act.expected_result,
                    actual_result="Awaiting operator confirmation in APPROVAL_REQUIRED mode",
                    rollback_value=act.rollback_value,
                    final_status="PENDING_APPROVAL"
                )
                action_records.append(rec)

        elif self.mode == AgentMode.AUTO:
            self.pending_approvals = []
            for act in approved_actions:
                # Write through BMS Gateway (Strict Gateway Rule)
                write_res = self.gateway.write_point(
                    point_id=act.point_id,
                    value=act.proposed_value,
                    priority=act.priority
                )

                # Track for Verification
                self.verification_engine.track_action(act, write_res.written_value)

                # Step 7: Verify Response
                self.lifecycle_state = AgentLifecycleState.VERIFY
                verif_res = self.verification_engine.verify_action(act, state)

                final_status = "VERIFIED_KEPT"
                actual_result_str = verif_res["actual_result"]

                # Step 8: Keep or Rollback
                self.lifecycle_state = AgentLifecycleState.KEEP_OR_ROLLBACK
                if verif_res["requires_rollback"]:
                    self.rollback_engine.execute_rollback(act, reason="Verification error threshold breached")
                    final_status = "ROLLED_BACK"
                    actual_result_str += " [Automated Rollback to Safe Baseline Executed]"

                rec = ActionRecordModel(
                    id=act.id,
                    opportunity_code=act.opportunity_code,
                    point_id=act.point_id,
                    previous_value=act.current_value,
                    proposed_value=act.proposed_value,
                    actual_value=write_res.written_value,
                    reason=act.reason,
                    confidence=act.confidence,
                    safety_result={"status": "PASS", "checks": act.constraints_applied},
                    timestamp=datetime.utcnow().isoformat(),
                    verification_window=act.verification_window_minutes,
                    expected_result=act.expected_result,
                    actual_result=actual_result_str,
                    rollback_value=act.rollback_value,
                    final_status=final_status
                )
                action_records.append(rec)
                self.audit_logger.log_action(rec)

        elif self.mode == AgentMode.ADVISORY:
            for act in approved_actions:
                rec = ActionRecordModel(
                    id=act.id,
                    opportunity_code=act.opportunity_code,
                    point_id=act.point_id,
                    previous_value=act.current_value,
                    proposed_value=act.proposed_value,
                    actual_value=None,
                    reason=act.reason,
                    confidence=act.confidence,
                    safety_result={"status": "PASS", "checks": act.constraints_applied},
                    timestamp=datetime.utcnow().isoformat(),
                    verification_window=act.verification_window_minutes,
                    expected_result=act.expected_result,
                    actual_result="Advisory recommendation only (BMS write suppressed)",
                    rollback_value=act.rollback_value,
                    final_status="ADVISORY_ONLY"
                )
                action_records.append(rec)

        # Step 9: Learn & Idle
        self.lifecycle_state = AgentLifecycleState.LEARN
        self.latest_actions = action_records
        self.lifecycle_state = AgentLifecycleState.IDLE

        # Generate natural language summary
        summary = self.explainer.generate_cycle_summary(
            mode=self.mode.value,
            actions=[a.__dict__ for a in action_records],
            state=state
        )

        return self._build_cycle_response(action_records, summary)

    def approve_action(self, action_id: str) -> Optional[ActionRecordModel]:
        """Operator manual approval handler in APPROVAL_REQUIRED mode."""
        act = next((a for a in self.pending_approvals if a.id == action_id), None)
        if not act:
            return None

        write_res = self.gateway.write_point(point_id=act.point_id, value=act.proposed_value, priority=act.priority)
        verif_res = self.verification_engine.verify_action(act, self.latest_state)

        final_status = "VERIFIED_KEPT"
        if verif_res["requires_rollback"]:
            self.rollback_engine.execute_rollback(act)
            final_status = "ROLLED_BACK"

        rec = ActionRecordModel(
            id=act.id,
            opportunity_code=act.opportunity_code,
            point_id=act.point_id,
            previous_value=act.current_value,
            proposed_value=act.proposed_value,
            actual_value=write_res.written_value,
            reason=f"OPERATOR APPROVED: {act.reason}",
            confidence=act.confidence,
            safety_result={"status": "PASS", "checks": act.constraints_applied},
            timestamp=datetime.utcnow().isoformat(),
            verification_window=act.verification_window_minutes,
            expected_result=act.expected_result,
            actual_result=verif_res["actual_result"],
            rollback_value=act.rollback_value,
            final_status=final_status
        )
        self.audit_logger.log_action(rec)
        self.pending_approvals = [a for a in self.pending_approvals if a.id != action_id]
        return rec

    def reject_action(self, action_id: str, reason: str = "Rejected by building operator"):
        """Operator manual rejection handler in APPROVAL_REQUIRED mode."""
        act = next((a for a in self.pending_approvals if a.id == action_id), None)
        if not act:
            return
        rec = ActionRecordModel(
            id=act.id,
            opportunity_code=act.opportunity_code,
            point_id=act.point_id,
            previous_value=act.current_value,
            proposed_value=act.proposed_value,
            actual_value=act.current_value,
            reason=f"OPERATOR REJECTED: {reason}",
            confidence=act.confidence,
            safety_result={"status": "REJECT", "reason": reason},
            timestamp=datetime.utcnow().isoformat(),
            verification_window=act.verification_window_minutes,
            expected_result=act.expected_result,
            actual_result="Action rejected by operator",
            rollback_value=act.rollback_value,
            final_status="REJECTED_OPERATOR"
        )
        self.audit_logger.log_action(rec)
        self.pending_approvals = [a for a in self.pending_approvals if a.id != action_id]

    def _build_cycle_response(self, actions: List[ActionRecordModel], cycle_summary: str) -> Dict[str, Any]:
        savings = self.metrics_service.calculate_tiered_savings(
            self.latest_state,
            [a.__dict__ for a in actions]
        )
        detected = self.opportunity_detector.detect_opportunities(self.latest_state)

        return {
            "lifecycle_state": self.lifecycle_state.value,
            "mode": self.mode.value,
            "timestamp": datetime.utcnow().isoformat(),
            "simulation_time": self.latest_state.get("simulation_time", "08:00"),
            "data_quality_valid": self.latest_state.get("data_quality_valid", True),
            "sensor_faults": self.latest_state.get("sensor_faults", []),
            "weather": self.latest_state.get("weather", {}),
            "ahus": self.latest_state.get("ahus", []),
            "plant": self.latest_state.get("plant", {}),
            "detected_opportunities": detected,
            "candidate_actions": [a.__dict__ for a in actions],
            "pending_approvals": [a.__dict__ for a in self.pending_approvals],
            "completed_actions": [a.__dict__ for a in actions if a.final_status in ("VERIFIED_KEPT", "ROLLED_BACK")],
            "savings_summary": savings,
            "cycle_summary": cycle_summary,
            "opportunity_results": [
                {
                    "opportunity_code": r.opportunity_code,
                    "equipment": r.equipment,
                    "reason": r.reason,
                    "confidence": r.confidence,
                    "constraints": r.constraints,
                    "expected_impact": r.expected_impact,
                    "verification_plan": r.verification_plan,
                    "candidates_count": len(r.candidates)
                }
                for r in self.latest_evaluation_results
            ]
        }
