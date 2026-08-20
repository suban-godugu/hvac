from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class BuildingLimits(BaseModel):
    min_space_temp_c: float = 20.0
    max_space_temp_c: float = 26.5
    min_cooling_setpoint_c: float = 20.0
    max_cooling_setpoint_c: float = 26.5
    min_comfort_deadband_c: float = 1.0
    max_comfort_deadband_c: float = 5.0
    max_zone_setpoint_step_c: float = 0.5 # Max step per cycle (Rate-of-change)
    max_co2_ppm: float = 900.0

class AHULimits(BaseModel):
    min_sat_c: float = 12.0               # Freeze-stat low limit
    max_sat_c: float = 17.5               # De-humidification high limit
    max_sat_step_c: float = 0.5           # Max SAT delta per cycle
    min_fan_speed_pct: float = 35.0
    max_fan_speed_pct: float = 100.0
    min_static_pressure_pa: float = 150.0
    max_static_pressure_pa: float = 450.0

class ChillerPlantLimits(BaseModel):
    min_chws_temp_c: float = 5.5          # Low freeze limit
    max_chws_temp_c: float = 9.0          # High cooling capacity limit
    max_chws_step_c: float = 0.5          # Max ChW setpoint step per cycle
    min_evap_flow_lps: float = 12.0       # Minimum evaporator flow to prevent freezing
    chiller_min_run_minutes: int = 15     # Anti-short-cycling min run timer
    chiller_min_off_minutes: int = 15     # Anti-short-cycling min off timer
    min_runtime_minutes: int = 15
    min_off_time_minutes: int = 15
    max_chiller_stages: int = 2
    compressors_per_chiller: int = 2

class EngineeringLimitsConfig(BaseModel):
    building_id: str = "bldg-corp-hq-01"
    building: BuildingLimits = Field(default_factory=BuildingLimits)
    ahu: AHULimits = Field(default_factory=AHULimits)
    chiller_plant: ChillerPlantLimits = Field(default_factory=ChillerPlantLimits)

    @property
    def chiller(self) -> ChillerPlantLimits:
        return self.chiller_plant

DEFAULT_ENGINEERING_LIMITS = EngineeringLimitsConfig()

def get_limits_config() -> EngineeringLimitsConfig:
    return DEFAULT_ENGINEERING_LIMITS
