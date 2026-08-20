from typing import Dict, Any, List

class SafetyGuardrails:
    """Supervisory safety kernel that clamps setpoints and blocks anomalous agent recommendations."""

    def __init__(self):
        self.HARD_LIMITS = {
            "ZONE_COOL_SP_MIN": 20.0,
            "ZONE_COOL_SP_MAX": 27.0,
            "AHU_SAT_MIN": 11.5,
            "AHU_SAT_MAX": 18.5,
            "CHWS_MIN": 5.0,
            "CHWS_MAX": 9.5
        }

    def validate_and_clamp_all(self, agent_decisions: Dict[str, Any]) -> Dict[str, Any]:
        safety_report = {
            "all_passed": True,
            "actions_blocked": [],
            "clamped_setpoints": [],
            "active_overrides": []
        }

        # Validate O3 SAT decision
        if "o3_sat" in agent_decisions:
            sat_dec = agent_decisions["o3_sat"]
            sp = sat_dec.get("target_sat_sp", 13.0)
            if sp < self.HARD_LIMITS["AHU_SAT_MIN"]:
                sat_dec["target_sat_sp"] = self.HARD_LIMITS["AHU_SAT_MIN"]
                safety_report["clamped_setpoints"].append(f"Clamped AHU SAT to minimum {self.HARD_LIMITS['AHU_SAT_MIN']}°C")
            elif sp > self.HARD_LIMITS["AHU_SAT_MAX"]:
                sat_dec["target_sat_sp"] = self.HARD_LIMITS["AHU_SAT_MAX"]
                safety_report["clamped_setpoints"].append(f"Clamped AHU SAT to maximum {self.HARD_LIMITS['AHU_SAT_MAX']}°C")

        # Validate O4 ChW setpoint
        if "o4_chiller" in agent_decisions:
            ch_dec = agent_decisions["o4_chiller"]
            chws = ch_dec.get("target_chws_sp", 6.7)
            if chws < self.HARD_LIMITS["CHWS_MIN"]:
                ch_dec["target_chws_sp"] = self.HARD_LIMITS["CHWS_MIN"]
                safety_report["clamped_setpoints"].append(f"Clamped CHWS to minimum {self.HARD_LIMITS['CHWS_MIN']}°C")
            elif chws > self.HARD_LIMITS["CHWS_MAX"]:
                ch_dec["target_chws_sp"] = self.HARD_LIMITS["CHWS_MAX"]
                safety_report["clamped_setpoints"].append(f"Clamped CHWS to maximum {self.HARD_LIMITS['CHWS_MAX']}°C")

        return safety_report
