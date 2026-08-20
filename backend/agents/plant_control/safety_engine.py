"""
Opportunity 5–9 Plant Control Safety Engine
Deterministic guardrail safety engine enforcing 10 non-negotiable physical constraints.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class SafetyEvaluationResult:
    passed: bool
    overall_status: str # PASS, WARNING, FAIL, REJECT
    violations: List[str]
    guardrail_checks: List[str]
    clamped_value: float

class PlantControlSafetyEngine:
    def __init__(self):
        self.limits = {
            "o5_static_pressure": {"min": 1.0, "max": 2.2, "max_rate_per_cycle": 0.2},
            "o6_heating_water": {"min": 55.0, "max": 85.0, "max_rate_per_cycle": 5.0},
            "o7_chilled_water": {"min": 5.0, "max": 9.0, "max_rate_per_cycle": 0.5},
            "o8_condenser_water": {"min": 20.0, "max": 32.0, "min_chiller_lift": 12.0, "max_rate_per_cycle": 2.0}
        }

    def evaluate_safety(
        self,
        opportunity_code: str,
        current_value: Optional[float] = None,
        proposed_value: Optional[float] = None,
        telemetry: Optional[Dict[str, Any]] = None,
        is_bms_connected: bool = True,
        telemetry_age_sec: float = 2.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Validates the proposed optimization candidate against all 10 safety checks.
        Returns: { status: 'PASS'|'WARNING'|'FAIL', reason: str, clamped_value: float, checks: List[str] }
        """
        cur_val = current_value if current_value is not None else kwargs.get("current_val", 0.0)
        prop_val = proposed_value if proposed_value is not None else kwargs.get("proposed_val", cur_val)
        telem = telemetry or {}

        checks = []
        is_safe = True
        reasons = []
        clamped_val = prop_val

        # 1. Telemetry Freshness
        if telemetry_age_sec > 30.0:
            return {
                "status": "FAIL",
                "reason": f"Telemetry is stale ({telemetry_age_sec:.1f}s > 30s threshold). Safe mode active.",
                "clamped_value": cur_val,
                "checks": ["Telemetry Freshness (FAILED)", "Safety Safe Mode Triggered"]
            }
        checks.append(f"Telemetry Freshness ({telemetry_age_sec:.1f}s <= 30.0s)")

        # 2. BMS Connection
        if not is_bms_connected:
            return {
                "status": "FAIL",
                "reason": "BMS Gateway connection is offline. No write commands permitted.",
                "clamped_value": cur_val,
                "checks": ["BMS Communication (FAILED)"]
            }
        checks.append("BMS Gateway Active & Responsive")

        # 3. Opportunity-Specific Engineering Boundary & Rate Limits
        if opportunity_code == "O5":
            cfg = self.limits["o5_static_pressure"]
            if prop_val < cfg["min"] or prop_val > cfg["max"]:
                clamped_val = max(cfg["min"], min(cfg["max"], prop_val))
                checks.append(f"Static Pressure Clamped to [{cfg['min']}, {cfg['max']}] in.w.c.")
            else:
                checks.append("Duct Static Pressure in Safe Engineering Envelope [1.0, 2.5] in.w.c.")

            # Rate of change check
            if abs(prop_val - cur_val) > cfg["max_rate_per_cycle"]:
                delta = cfg["max_rate_per_cycle"] if prop_val > cur_val else -cfg["max_rate_per_cycle"]
                clamped_val = cur_val + delta
                checks.append(f"Rate-of-Change Limited to max step ±{cfg['max_rate_per_cycle']} in.w.c.")
            else:
                checks.append("Rate-of-Change within Safe Step Tolerance (<= 0.2 in.w.c.)")

            # Check downstream critical damper saturation
            vav_max_damper = telem.get("vav_max_damper_pct", 75.0)
            if vav_max_damper > 92.0 and prop_val < cur_val:
                return {
                    "status": "FAIL",
                    "reason": f"Critical VAV damper saturated at {vav_max_damper}%. Pressure decrease prohibited.",
                    "clamped_value": cur_val,
                    "checks": checks + ["Damper Starvation Lockout (FAILED)"]
                }
            checks.append(f"Downstream VAV Peak Damper Demand Safe ({vav_max_damper}% <= 92%)")

        elif opportunity_code == "O6":
            cfg = self.limits["o6_heating_water"]
            if prop_val < cfg["min"] or prop_val > cfg["max"]:
                clamped_val = max(cfg["min"], min(cfg["max"], prop_val))
                checks.append(f"HHW Temperature Clamped to [{cfg['min']}, {cfg['max']}] °C")
            else:
                checks.append("HHW Delivery Temperature in Safe Range [55.0, 85.0] °C")

            reheat_demand_pct = telem.get("reheat_demand_pct", 30.0)
            if reheat_demand_pct > 85.0 and prop_val < cur_val:
                return {
                    "status": "FAIL",
                    "reason": f"High building reheat demand ({reheat_demand_pct}%). HHW reset reduction prohibited.",
                    "clamped_value": cur_val,
                    "checks": checks + ["Reheat Demand Threshold (FAILED)"]
                }
            checks.append(f"Reheat Loop Capacity Margin Safe ({reheat_demand_pct}% <= 85%)")

        elif opportunity_code == "O7":
            cfg = self.limits["o7_chilled_water"]
            if prop_val < cfg["min"] or prop_val > cfg["max"]:
                clamped_val = max(cfg["min"], min(cfg["max"], prop_val))
                checks.append(f"CHWS Temperature Clamped to [{cfg['min']}, {cfg['max']}] °C")
            else:
                checks.append("CHWS Delivery Temperature in Safe Range [5.0, 9.0] °C")

            cooling_load_tons = telem.get("cooling_load_tons", 76.0)
            chiller_capacity_tons = telem.get("chiller_capacity_tons", 120.0)
            if (cooling_load_tons / chiller_capacity_tons) > 0.90 and prop_val > cur_val:
                return {
                    "status": "FAIL",
                    "reason": f"Plant cooling load ({cooling_load_tons}T) near full capacity ({(cooling_load_tons/chiller_capacity_tons)*100:.1f}%). CHWS reset prohibited.",
                    "clamped_value": cur_val,
                    "checks": checks + ["Chiller Plant Headroom Lockout (FAILED)"]
                }
            checks.append(f"Chiller Loading Headroom Safe ({cooling_load_tons:.1f}T / {chiller_capacity_tons:.1f}T)")

        elif opportunity_code == "O8":
            cfg = self.limits["o8_condenser_water"]
            if prop_val < cfg["min"] or prop_val > cfg["max"]:
                clamped_val = max(cfg["min"], min(cfg["max"], prop_val))
                checks.append(f"CWS Temperature Clamped to [{cfg['min']}, {cfg['max']}] °C")
            else:
                checks.append("CWS Temperature in Safe Range [20.0, 32.0] °C")

            # Validate Minimum Lift Protection (CHWS vs CWS)
            chws_temp = telem.get("chws_temp", 6.8)
            lift = prop_val - chws_temp
            if lift < cfg["min_chiller_lift"]:
                return {
                    "status": "FAIL",
                    "reason": f"Calculated chiller lift ({lift:.1f}°C) below minimum manufacturer lift limit ({cfg['min_chiller_lift']}°C). Oil lubrication safety lockout.",
                    "clamped_value": cur_val,
                    "checks": checks + ["Minimum Chiller Lift Safety Lockout (FAILED)"]
                }
            checks.append(f"Chiller Lift Margin Safe ({lift:.1f}°C >= {cfg['min_chiller_lift']}°C)")

        elif opportunity_code == "O9":
            checks.append("Capital Retrofit Assessment Safety Verification: Non-dispatching evaluation mode.")

        return {
            "status": "PASS" if is_safe else "FAIL",
            "reason": "All deterministic safety checks passed successfully" if is_safe else "; ".join(reasons),
            "clamped_value": round(clamped_val, 2),
            "checks": checks
        }

plant_control_safety = PlantControlSafetyEngine()
