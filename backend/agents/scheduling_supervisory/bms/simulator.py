import math
import random
from typing import Dict, Any, List
from ..state import SupervisoryState, WeatherState, OccupancySchedule, AHUState, ZoneState, ChillerState, ChillerPlantState

class BMSSimulator:
    """Physics-based building thermal and HVAC mechanical plant simulator."""

    def __init__(self, scenario_id: str = "scenario_summer_peak"):
        self.scenario_id = scenario_id
        self.sim_minute = 480 # Starts at 08:00 AM (480 mins from midnight)
        self.state = self._initialize_state()

    def _initialize_state(self) -> SupervisoryState:
        # 2 AHUs, each serving 6 VAV zones (total 12 zones)
        ahus = []
        for a_idx in [1, 2]:
            zones = []
            for z_idx in range(1, 7):
                zone_num = (a_idx - 1) * 6 + z_idx
                floor = 1 if zone_num <= 6 else 2
                zones.append(ZoneState(
                    id=f"VAV-{floor}0{z_idx}",
                    name=f"Floor {floor} Zone {z_idx} ({'North' if z_idx%2==1 else 'South'})",
                    temp_actual=22.8 + (z_idx * 0.1),
                    temp_setpoint=22.5,
                    cooling_sp=23.0,
                    heating_sp=21.0,
                    deadband=2.0,
                    damper_pos=45.0 + (z_idx * 4.0),
                    cooling_request=False,
                    heating_request=False,
                    occupied=True,
                    co2_ppm=480.0 + (z_idx * 20.0),
                    airflow_cfm=480.0
                ))
            ahus.append(AHUState(
                id=f"AHU-{a_idx}",
                name=f"Central AHU {a_idx} (Floor {a_idx})",
                fan_status=True,
                fan_speed_pct=65.0,
                fan_power_kw=12.0 if a_idx == 1 else 9.5,
                sat_actual=13.2,
                sat_setpoint=13.0,
                cooling_valve_pct=52.0,
                vav_zones=zones
            ))

        ch1 = ChillerState(id="CH-1", name="Centrifugal Chiller 1", status=True, capacity_tons=120.0, current_tons=76.0, pct_load=63.3, power_kw=42.5, cop=6.2, run_minutes=180)
        ch2 = ChillerState(id="CH-2", name="Centrifugal Chiller 2", status=False, capacity_tons=120.0, current_tons=0.0, pct_load=0.0, power_kw=0.0, cop=0.0, run_minutes=0)

        plant = ChillerPlantState(
            chillers=[ch1, ch2],
            total_tons=76.0,
            total_power_kw=42.5,
            plant_efficiency_kw_per_ton=0.56,
            chws_temp=6.8,
            chws_setpoint=6.7,
            chwr_temp=12.2,
            flow_rate_lps=28.5
        )

        return SupervisoryState(
            simulation_time="08:00",
            scenario_id=self.scenario_id,
            weather=WeatherState(oat=22.5, oah=55.0, wet_bulb=18.0, solar_irradiance=420.0),
            schedule=OccupancySchedule(occupied_start="08:00", occupied_end="18:00", current_occupancy_pct=80.0, is_occupied_window=True),
            ahus=ahus,
            chiller_plant=plant
        )

    def step(self, elapsed_minutes: int = 5, manual_overrides: Dict[str, Any] = None) -> SupervisoryState:
        self.sim_minute = (self.sim_minute + elapsed_minutes) % 1440
        h = self.sim_minute // 60
        m = self.sim_minute % 60
        time_str = f"{h:02d}:{m:02d}"
        self.state.simulation_time = time_str

        # 1. Update Weather based on diurnal sinusoidal curve
        # Peak OAT at 15:00 (900 min)
        rad = (self.sim_minute - 360) / 1440.0 * 2.0 * math.pi
        if self.scenario_id == "scenario_summer_peak":
            base_oat = 21.0
            peak_amp = 13.0
        elif self.scenario_id == "scenario_shoulder_mild":
            base_oat = 13.0
            peak_amp = 8.0
        else:
            base_oat = 18.0
            peak_amp = 10.0

        oat = base_oat + peak_amp * (0.5 * (1.0 - math.cos(rad))) + random.uniform(-0.1, 0.1)
        solar = max(0.0, math.sin((self.sim_minute - 360) / 720.0 * math.pi) * 850.0) if 360 <= self.sim_minute <= 1080 else 0.0

        self.state.weather.oat = round(oat, 1)
        self.state.weather.solar_irradiance = round(solar, 1)
        self.state.weather.wet_bulb = round(oat * 0.7 + 2.0, 1)

        # 2. Update Occupancy
        is_occ = 480 <= self.sim_minute <= 1080
        self.state.schedule.is_occupied_window = is_occ
        occ_pct = 85.0 if is_occ else 5.0
        self.state.schedule.current_occupancy_pct = occ_pct

        # 3. Simulate Zones & AHUs
        total_cooling_tons = 0.0
        for ahu in self.state.ahus:
            # Check manual override for SAT
            if manual_overrides and f"{ahu.id}_SAT_SP" in manual_overrides:
                ahu.sat_setpoint = float(manual_overrides[f"{ahu.id}_SAT_SP"])

            # Dynamics of SAT tracking setpoint
            sat_error = ahu.sat_setpoint - ahu.sat_actual
            ahu.sat_actual = round(ahu.sat_actual + sat_error * 0.35, 1)

            # Zone thermal model
            for zone in ahu.vav_zones:
                zone.occupied = is_occ
                # Heat gain: envelope + internal + solar
                internal_q = (0.35 if is_occ else 0.05)
                solar_q = (solar / 1000.0) * 0.4
                env_q = (oat - zone.temp_actual) * 0.08
                total_gain = internal_q + solar_q + env_q

                # Cooling delivered by VAV
                # Q_cool = CFM * 1.08 * (T_zone - T_sat)
                cooling_delta = max(0.0, zone.temp_actual - ahu.sat_actual)
                damper_factor = zone.damper_pos / 100.0
                q_cool_delivered = damper_factor * cooling_delta * 0.45

                # Update zone temp
                dt_temp = (total_gain - q_cool_delivered) * (elapsed_minutes / 15.0)
                zone.temp_actual = round(zone.temp_actual + dt_temp, 2)

                # VAV Local PI controller (adjusts damper position to track cooling SP)
                temp_error = zone.temp_actual - zone.cooling_sp
                new_damper = max(15.0, min(100.0, zone.damper_pos + (temp_error * 12.0)))
                zone.damper_pos = round(new_damper, 1)
                zone.cooling_request = zone.damper_pos >= 85.0 and temp_error > 0.3

            # Fan Affinity Law: Fan Power kW proportional to (speed/100)^3
            avg_damper = sum(z.damper_pos for z in ahu.vav_zones) / len(ahu.vav_zones)
            ahu.fan_speed_pct = round(max(35.0, avg_damper * 0.95), 1)
            # 15 kW design fan motor
            base_kw = 14.0 if ahu.id == "AHU-1" else 10.0
            ahu.fan_power_kw = round(base_kw * ((ahu.fan_speed_pct / 100.0) ** 2.7), 2)
            total_cooling_tons += avg_damper * 0.65

        # 4. Simulate Chiller Plant
        plant = self.state.chiller_plant
        plant.total_tons = round(total_cooling_tons * 1.25, 1)
        
        # Calculate ChW Return Temp: Q = m * Cp * dT
        plant.flow_rate_lps = round(max(15.0, plant.total_tons * 0.38), 1)
        plant.chws_temp = round(plant.chws_setpoint + random.uniform(-0.1, 0.1), 1)
        # Delta T = Q / (flow * 4.184)
        calculated_dt = (plant.total_tons * 3.51685) / (plant.flow_rate_lps * 4.184)
        plant.chwr_temp = round(plant.chws_temp + calculated_dt, 1)

        # Chiller status & electrical power
        active_chillers = [c for c in plant.chillers if c.status]
        if active_chillers:
            tons_per_ch = plant.total_tons / len(active_chillers)
            total_ch_kw = 0.0
            for c in plant.chillers:
                if c.status:
                    c.current_tons = round(tons_per_ch, 1)
                    c.pct_load = round((tons_per_ch / c.capacity_tons) * 100.0, 1)
                    c.run_minutes += elapsed_minutes
                    # Empirical Centrifugal Chiller kW/ton curve
                    plr = c.pct_load / 100.0
                    kw_per_ton = 0.52 + 0.35 * ((plr - 0.72) ** 2)
                    # Lift penalty: +2% per °C lower CHWS
                    lift_factor = 1.0 + (6.7 - plant.chws_temp) * 0.025
                    c.power_kw = round(c.current_tons * kw_per_ton * lift_factor, 1)
                    c.cop = round(3.51685 / max(0.2, c.power_kw / max(1.0, c.current_tons)), 2)
                    total_ch_kw += c.power_kw
                else:
                    c.current_tons = 0.0
                    c.pct_load = 0.0
                    c.power_kw = 0.0
                    c.cop = 0.0
            plant.total_power_kw = round(total_ch_kw, 1)
            plant.plant_efficiency_kw_per_ton = round(plant.total_power_kw / max(1.0, plant.total_tons), 3)

        return self.state
