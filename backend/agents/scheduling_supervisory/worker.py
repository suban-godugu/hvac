"""
Persistent Background Control Worker for Scheduling & Supervisory Agent.
Executes the closed-loop optimization, safety validation, BMS dispatching,
and verification cycle continuously in AUTO mode without requiring manual triggers.
"""
import os
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime

from backend.agents.scheduling_supervisory.agent import SchedulingSupervisoryAgent
from backend.agents.scheduling_supervisory.state import AgentMode, AgentLifecycleState
from backend.services.simulation_service import sim_service
from backend.services.logging_service import log_event


class SchedulingControlWorker:
    def __init__(self, interval_seconds: int = 10):
        self.interval_seconds = interval_seconds
        self.agent = SchedulingSupervisoryAgent()
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.cycle_count = 0
        self.last_cycle_timestamp: Optional[datetime] = None
        self.last_cycle_summary: str = "Worker initialized"
        self.last_response: Dict[str, Any] = {}

    def start(self):
        """Starts the background worker thread."""
        if self.is_running:
            return
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.worker_thread.start()
        log_event("INFO", "control_worker", "STARTED", extra={"interval_seconds": self.interval_seconds})

    def stop(self):
        """Stops the background worker thread."""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        log_event("INFO", "control_worker", "STOPPED")

    def _run_loop(self):
        while self.is_running:
            try:
                self.execute_cycle()
            except Exception as e:
                log_event("ERROR", "control_worker", "CYCLE_FAILED", extra={"error": str(e)})
                self.last_cycle_summary = f"Cycle Error: {str(e)}"
            
            time.sleep(self.interval_seconds)

    def execute_cycle(self) -> Dict[str, Any]:
        """Executes a single end-to-end closed loop control cycle."""
        self.cycle_count += 1
        self.last_cycle_timestamp = datetime.utcnow()
        
        # 0. Fetch live weather every 6 cycles (approx 60s)
        if self.cycle_count % 6 == 1:
            try:
                from backend.services.weather_service import weather_service
                weather_service.fetch_live_weather_sync()
            except Exception as e:
                log_event("WARN", "control_worker", "WEATHER_FETCH_FAILED", extra={"error": type(e).__name__})

        from backend.workers.watchdog import beat, allow_autonomous_writes
        from backend.services.hvac_safety_contract import is_safe_mode

        beat(f"cycle-{self.cycle_count}")
        if is_safe_mode() or not allow_autonomous_writes():
            self.last_cycle_summary = f"Cycle #{self.cycle_count} held (SAFE_MODE or watchdog)"
            return {"held": True, "candidate_actions": []}

        if os.getenv("HVAC_USE_SIMULATION", "0") in ("1", "true", "TRUE"):
            sim_state = sim_service.step(minutes=5)
            raw_telemetry = self.agent.generate_simulated_telemetry()
        else:
            raw_telemetry = {"source": "MISSING", "quality": "MISSING"}

        response = self.agent.run_cycle(raw_telemetry)
        self.last_response = response

        from backend.bms.command_writer import simulated_writes_allowed

        if self.agent.mode == AgentMode.AUTO and simulated_writes_allowed():
            candidate_actions = response.get("candidate_actions", [])
            for act in candidate_actions:
                # Apply setpoint changes to physical simulator
                point_id = getattr(act, "point_id", "")
                prop_val = getattr(act, "proposed_value", None)
                if "SAT-SP" in point_id and prop_val:
                    # Update AHU SAT in simulator
                    for ahu in sim_service.simulator.state.ahus:
                        ahu.sat_setpoint = float(prop_val)
                elif "CLG-SP" in point_id and prop_val:
                    # Update zone setpoints in simulator
                    for ahu in sim_service.simulator.state.ahus:
                        for z in ahu.vav_zones:
                            if z.id in point_id:
                                z.temp_setpoint = float(prop_val)
                                z.cooling_sp = float(prop_val)
                elif "CHWS-SP" in point_id and prop_val:
                    sim_service.simulator.state.chiller_plant.chws_setpoint = float(prop_val)

        self.last_cycle_summary = f"Cycle #{self.cycle_count} executed ({len(response.get('candidate_actions', []))} actions dispatched)"
        return response

    def get_status(self) -> Dict[str, Any]:
        return {
            "worker_running": self.is_running,
            "interval_seconds": self.interval_seconds,
            "cycle_count": self.cycle_count,
            "agent_mode": self.agent.mode,
            "lifecycle_state": self.agent.lifecycle_state,
            "last_cycle_time": self.last_cycle_timestamp.isoformat() if self.last_cycle_timestamp else None,
            "last_summary": self.last_cycle_summary
        }


# Global Worker Instance
control_worker = SchedulingControlWorker(interval_seconds=10)
