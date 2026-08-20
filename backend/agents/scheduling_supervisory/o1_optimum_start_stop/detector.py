from typing import Dict, Any
from datetime import datetime

class StartStopDetector:
    """Detects building schedule transitions, pre-conditioning windows, and coast-down opportunities."""

    def detect_schedule_phase(self, current_time_str: str, occ_start: str = "08:00", occ_end: str = "18:00") -> Dict[str, Any]:
        curr_h, curr_m = map(int, current_time_str.split(":"))
        start_h, start_m = map(int, occ_start.split(":"))
        end_h, end_m = map(int, occ_end.split(":"))

        curr_min = curr_h * 60 + curr_m
        start_min = start_h * 60 + start_m
        end_min = end_h * 60 + end_m

        minutes_to_start = start_min - curr_min
        minutes_to_end = end_min - curr_min

        phase = "UNOCCUPIED_NIGHT"
        if -120 <= minutes_to_start <= 0:
            phase = "PRE_CONDITIONING_WINDOW"
        elif 0 < minutes_to_end and minutes_to_start < 0:
            if 0 < minutes_to_end <= 60:
                phase = "COAST_DOWN_WINDOW"
            else:
                phase = "OCCUPIED_STEADY"
        elif minutes_to_end <= 0:
            phase = "UNOCCUPIED_EVENING"

        return {
            "phase": phase,
            "minutes_to_occupancy_start": minutes_to_start,
            "minutes_to_occupancy_end": minutes_to_end,
            "is_preconditioning": phase == "PRE_CONDITIONING_WINDOW",
            "is_coasting": phase == "COAST_DOWN_WINDOW"
        }
