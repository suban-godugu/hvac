"""OEH guide copy + slider schema keyed to official catalog IDs O1–O20."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.services.official_catalog import CATALOG, catalog_entry

ROUTES: Dict[str, str] = {
    "O1": "/agents/scheduling/optimum-start-stop",
    "O2": "/agents/scheduling/space-temperature",
    "O3": "/agents/scheduling/master-ahu-sat",
    "O4": "/agents/scheduling/chiller-staging",
    "O5": "/agents/plant-control/duct-static-pressure",
    "O6": "/agents/plant-control/temperature-reset?mode=HHW",
    "O7": "/agents/plant-control/temperature-reset?mode=CHW",
    "O8": "/agents/plant-control/temperature-reset?mode=CW",
    "O9": "/agents/plant-control/electronic-expansion-valve",
    "O10": "/agents/ventilation-airflow/economy-cycle",
    "O11": "/agents/ventilation-airflow/night-purge",
    "O12": "/agents/ventilation-airflow/demand-ventilation",
    "O13": "/agents/ventilation-airflow/dcv-co",
    "O14": "/agents/variable-speed/chilled-water-pump",
    "O15": "/agents/variable-speed/air-cooled-head-pressure",
    "O16": "/agents/variable-speed/water-cooled-head-pressure",
    "O17": "/agents/operations-maintenance/energy-management-planning",
    "O18": "/agents/operations-maintenance/training-awareness",
    "O19": "/agents/operations-maintenance/equipment-maintenance",
    "O20": "/agents/operations-maintenance/control-software",
}

CAT_MAP = {
    "scheduling": "scheduling",
    "plant-control": "plant",
    "ventilation": "ventilation",
    "variable-speed": "variablespeed",
    "operations": "om",
}

# NSW OEH teaching copy + slider defaults (not BMS). IDs match official_catalog.
GUIDE_META: Dict[str, Dict[str, Any]] = {
    "O1": {
        "scope": "HVAC energy",
        "pct": 10,
        "x_type": "hour",
        "sim_label": "Start/Stop Schedule — HVAC Run State",
        "summary": "Automates HVAC start and stop times using zone temperatures and outdoor conditions instead of a fixed schedule, cutting operating hours while still meeting comfort by the time occupants arrive.",
        "principle": "Calculates the latest possible start time and earliest possible stop time from real-time indoor/outdoor temperatures and the building's learned thermal response, adjusting automatically day to day.",
        "practice": "Most systems start 2–3 hours before occupancy on a fixed schedule year-round regardless of season — wasteful during mild weather.",
        "recommendation": "Verify occupancy times are current, confirm the enabling time suits seasonal extremes, and integrate with warm-up/cool-down and after-hours programs.",
        "equipment": "365-day schedule, outdoor temperature sensor, zone temperature sensors, trend-logging capability, OSS control software",
        "scenario": "One Sydney office cut HVAC operating hours ~17% (120 min/day) and energy use 12%, saving $35,280/yr with payback under 3 months.",
        "sliders": [
            {"key": "occStart", "label": "Occupancy Start Time", "min": 7, "max": 9.5, "step": 0.5, "default": 8.5, "unit": "h"},
            {"key": "severity", "label": "Outdoor Temp Severity (mild ↔ extreme)", "min": 0, "max": 100, "step": 5, "default": 50, "unit": "%"},
        ],
    },
    "O2": {
        "scope": "HVAC energy",
        "pct": 20,
        "x_type": "hour",
        "sim_label": "Heating/Cooling Output vs Time",
        "summary": "Widens the dead band and proportional bands around the temperature set point so equipment runs less often and at lower intensity, without occupants noticing the difference.",
        "principle": "A 1°C shift in set point can shift energy use by roughly 10%. Recommended ranges are 20–22°C in winter and 24–26°C in summer, with 2–3°C dead bands.",
        "practice": "Many buildings hold a tight 22–22.5°C target year-round with narrow control bands, forcing unnecessary heating/cooling cycling.",
        "recommendation": "Widen bands gradually (about 0.3°C at a time) so occupants can adjust, and switch PI/PID loops to P-only control where feasible.",
        "equipment": "Adjustable-band temperature controllers, 0.1°C sensor increments where possible, BMS or standalone HVAC controller, occupant consultation plan",
        "scenario": "A 20,000 m² office saved ~$19,650/yr (128 t CO₂) with under a month's payback by widening bands and shifting the set point 0.5°C.",
        "sliders": [
            {"key": "deadBand", "label": "Dead Band", "min": 1, "max": 3, "step": 0.5, "default": 1, "unit": "°C"},
            {"key": "propBand", "label": "Proportional Band", "min": 0.5, "max": 2, "step": 0.25, "default": 1, "unit": "°C"},
        ],
    },
    "O3": {
        "scope": "HVAC energy",
        "pct": 15,
        "x_type": "hour",
        "sim_label": "Master Signal — High-Select vs Weighted Average",
        "summary": "Replaces 'worst zone wins' supply-air control logic with a weighted average across the most-open VAV boxes, cutting simultaneous heating and cooling.",
        "principle": "A weighted or percentile-based signal from multiple VAV zones sets the AHU supply temperature, rather than letting one extreme or faulty zone drive the whole system.",
        "practice": "Most BMS use high-select logic — the single worst zone dictates supply air temperature, causing over-cooling and excess re-heat elsewhere.",
        "recommendation": "Use an average of the 2–5 most-open VAV boxes or a percentile rank, and exclude known-faulty sensors from the calculation.",
        "equipment": "Zone temperature sensors on every VAV box, weighting/percentile control software, damper-position feedback, coordination with set-point strategy",
        "scenario": "Replacing high-select with a 5-box average, fixing faulty dampers, and rebalancing airflow cut HVAC energy ~10% with a 3-month payback.",
        "sliders": [
            {"key": "numAvg", "label": "Zones Averaged (1 = high-select)", "min": 1, "max": 5, "step": 1, "default": 3, "unit": ""},
            {"key": "faultBias", "label": "Faulty Zone Sensor Bias", "min": 0, "max": 5, "step": 0.5, "default": 1.5, "unit": "°C"},
        ],
    },
    "O4": {
        "scope": "chiller energy",
        "pct": 10,
        "x_type": "hour",
        "sim_label": "Chillers Staged On",
        "summary": "Brings additional chillers online only when genuinely needed — based on sustained flow/temperature shortfall rather than simple return-temperature triggers.",
        "principle": "Stage-up should require a sustained inability to meet the CHW flow or temperature set point (5–20 minute delay); stage-down should happen quickly once load drops.",
        "practice": "Systems often stage on CHW return temperature with short delays, engaging extra chillers earlier than necessary and running them at inefficient part-load.",
        "recommendation": "Add current-draw and calculated field-load criteria, maximize the stage-up delay, minimize stage-down delay, and lock out cooling calls at low ambient temperatures.",
        "equipment": "Reliable cooling-call signal, CHW flow and temperature sensors, compressor current-draw monitoring, staging control logic",
        "sliders": [
            {"key": "peakLoad", "label": "Peak Cooling Load", "min": 40, "max": 100, "step": 5, "default": 75, "unit": "%"},
            {"key": "stageDelay", "label": "Stage-Up Delay", "min": 5, "max": 20, "step": 1, "default": 10, "unit": "min"},
        ],
    },
    "O5": {
        "scope": "fan energy",
        "pct": 30,
        "x_type": "hour",
        "sim_label": "Supply Fan Power — Fixed vs Reset Static Pressure",
        "summary": "Continuously lowers duct static pressure so VSD-driven supply fans work only as hard as the most-open VAV box requires, instead of holding a fixed high pressure.",
        "principle": "Keeps a representative most-open VAV damper near 90–95% open, trimming fan speed at regular intervals (e.g. every 300 seconds).",
        "practice": "Static pressure is usually fixed at a conservative, design-peak value that's far higher than needed for most of the year.",
        "recommendation": "Reset pressure on a percentile basis rather than the single most-open box, since that box has often failed; verify VAV boxes aren't faulty before relying on them as feedback.",
        "equipment": "Static pressure sensor on the index run, VSD fan controller, damper-position feedback from VAV boxes, reset control logic",
        "sliders": [
            {"key": "demandAmp", "label": "Peak Airflow Demand", "min": 40, "max": 100, "step": 5, "default": 80, "unit": "%"},
            {"key": "targetOpen", "label": "Target Most-Open VAV", "min": 85, "max": 98, "step": 1, "default": 92, "unit": "%"},
        ],
    },
    "O6": {
        "scope": "hot water energy",
        "pct": 5,
        "x_type": "hour",
        "sim_label": "Heating Hot Water Flow Temperature",
        "summary": "Runs boiler water at the lowest flow temperature that still meets heating demand, reserving high temperatures for extreme cold or warm-up periods.",
        "principle": "Non-condensing boilers must stay above 55°C return temperature to avoid corrosion, while condensing boilers gain efficiency below that same threshold.",
        "practice": "Many systems run a fixed HHW flow temperature regardless of load or outdoor conditions.",
        "recommendation": "Reset flow temperature against outdoor and load conditions; use the condensing boiler as lead unit, boosting to 80–85°C only under peak demand.",
        "equipment": "Field temperature sensors, controllers/data processors, reset control software, boiler sequencing logic",
        "sliders": [
            {"key": "boilerType", "label": "Boiler Type (0=Non-Condensing, 1=Condensing)", "min": 0, "max": 1, "step": 1, "default": 1, "unit": ""},
            {"key": "heatSeverity", "label": "Heating Demand Severity", "min": 0, "max": 100, "step": 5, "default": 60, "unit": "%"},
        ],
    },
    "O7": {
        "scope": "chiller energy",
        "pct": 15,
        "x_type": "hour",
        "sim_label": "Chilled Water Supply Temperature",
        "summary": "Raises chilled water temperature during mild weather so chillers work less hard, without sacrificing dehumidification when it actually matters.",
        "principle": "Each 1°C rise in CHW temperature cuts compressor energy roughly 2–3% for fixed-speed units and 4–5% for variable-speed units.",
        "practice": "CHW is typically fixed at 6–7°C year-round, sized for a design-day peak load that rarely occurs in practice.",
        "recommendation": "Reset upward to around 10–12°C in mild conditions, weighing the gain against any added pumping or airflow energy — especially on long CHW circuits.",
        "equipment": "Supply/return temperature sensors, field load indication, reset control software, humidity monitoring",
        "sliders": [
            {"key": "compType", "label": "Compressor Type (0=Fixed-Speed, 1=VSD)", "min": 0, "max": 1, "step": 1, "default": 0, "unit": ""},
            {"key": "loadSeverity", "label": "Cooling Load Severity", "min": 40, "max": 100, "step": 5, "default": 80, "unit": "%"},
        ],
    },
    "O8": {
        "scope": "chiller energy",
        "pct": 15,
        "x_type": "hour",
        "sim_label": "Condenser Water Temperature",
        "summary": "Lowers condenser water temperature to track outdoor wet-bulb conditions, cutting compressor load — balanced against cooling tower fan energy.",
        "principle": "Each 1°C drop in CW temperature cuts compressor energy roughly 2–3% (fixed-speed) to 4–5% (variable-speed); towers are typically designed for a 3–4°C approach to wet-bulb.",
        "practice": "CW temperature is usually held constant regardless of ambient wet-bulb conditions, wasting the free capacity available in cooler weather.",
        "recommendation": "Modulate cooling tower fan speed to approach — not undercut — the manufacturer's minimum CW temperature; run multiple fans together at part-load rather than cycling.",
        "equipment": "Wet-bulb/CW temperature sensors, VSD-controlled tower fans, reset control software, manufacturer minimum-temperature spec",
        "sliders": [
            {"key": "wetBulbMean", "label": "Ambient Wet-Bulb (avg)", "min": 10, "max": 28, "step": 1, "default": 20, "unit": "°C"},
            {"key": "approach", "label": "Tower Approach", "min": 3, "max": 5, "step": 0.5, "default": 3.5, "unit": "°C"},
        ],
    },
    "O9": {
        "scope": "compressor energy",
        "pct": 15,
        "x_type": "hour",
        "sim_label": "Superheat-Related Compressor Efficiency Loss",
        "summary": "Replacing older thermostatic expansion valves with electronic ones gives tighter refrigerant control and a smaller required superheat margin, improving compressor efficiency.",
        "principle": "EEVs regulate refrigerant flow more precisely than mechanical TXVs, reducing the superheat buffer needed to protect compressors from liquid slugging.",
        "practice": "Systems older than 5–10 years typically still run TXVs, which drift with wear and are set conservatively for safety.",
        "recommendation": "Retrofit EEVs on larger DX circuits, ideally alongside variable head-pressure control upgrades for compounding savings.",
        "equipment": "Temperature/pressure field sensors, controllers, EEV hardware, manufacturer retrofit guidance",
        "sliders": [
            {"key": "valveType", "label": "Valve Type (0=TXV, 1=EEV)", "min": 0, "max": 1, "step": 1, "default": 0, "unit": ""},
            {"key": "loadVar", "label": "Load Variability", "min": 0, "max": 100, "step": 5, "default": 60, "unit": "%"},
        ],
    },
    "O10": {
        "scope": "compressor energy",
        "pct": 20,
        "x_type": "hour",
        "sim_label": "Compressor Load — With/Without Economy Cycle",
        "summary": "Uses outdoor air directly for cooling whenever it holds less total energy than return air, cutting mechanical cooling load while improving indoor air quality.",
        "principle": "Should be enabled based on enthalpy or dew point comparison against return air — not outdoor temperature or relative humidity alone.",
        "practice": "Many economy cycles are disabled, mis-tuned to overly narrow temperature bands, or broken due to faulty humidity sensors and dampers.",
        "recommendation": "Enable when outdoor dew point is below ~12°C or enthalpy is at least 10 kJ/kg below return air; ensure lock-out during fire mode and high-humidity conditions.",
        "equipment": "Return and outdoor air temperature/humidity sensors, DDC controllers, correctly sized O/A and relief-air dampers, economy-cycle software",
        "sliders": [
            {"key": "oatMean", "label": "Outdoor Temp (avg)", "min": 10, "max": 30, "step": 1, "default": 18, "unit": "°C"},
            {"key": "dewPoint", "label": "Outdoor Dew Point", "min": 0, "max": 20, "step": 1, "default": 10, "unit": "°C"},
        ],
    },
    "O11": {
        "scope": "compressor start-up energy",
        "pct": 20,
        "x_type": "hour",
        "sim_label": "Indoor Temperature Pre-Occupancy",
        "summary": "Flushes accumulated heat out of the building with cool early-morning outdoor air just before start-up, reducing the mechanical cooling load needed at occupancy.",
        "principle": "Mechanical night purge only saves energy when outdoor air is significantly cooler and drier than indoor air (dew point below 12°C, 4–5°C temperature difference) and is timed for roughly 30–60 minutes before start-up.",
        "practice": "Night purge is often disabled, left running too long, or conflicts with subsequent heating — negating its intended benefit.",
        "recommendation": "Limit to selected AHUs, disable heating for at least an hour afterward, and reserve full-night operation for purely natural-ventilation systems.",
        "equipment": "Field temperature/humidity sensors, controllers, automated outdoor/return/relief air dampers, night purge software",
        "sliders": [
            {"key": "overnightLow", "label": "Overnight Outdoor Low", "min": 10, "max": 25, "step": 1, "default": 16, "unit": "°C"},
            {"key": "residual", "label": "Residual Indoor Temp (pre-purge)", "min": 24, "max": 30, "step": 0.5, "default": 27, "unit": "°C"},
        ],
    },
    "O12": {
        "scope": "outdoor air conditioning energy",
        "pct": 20,
        "x_type": "hour",
        "sim_label": "Outdoor Air Ventilation Rate",
        "summary": "Uses CO₂ sensors as an occupancy proxy to trim outdoor air intake in spaces with variable occupancy, cutting the heating/cooling load tied to ventilation air.",
        "principle": "CO₂ set points around 800–1,000 ppm balance energy savings against indoor air quality, since discomfort typically isn't detected until 1,500–2,000 ppm.",
        "practice": "Ventilation is often oversupplied at all times, or run on a fixed timer that ignores actual occupancy levels.",
        "recommendation": "Best suited to meeting rooms, foyers, cinemas, and shopping malls; use proportional-only control and never fully shut off ventilation.",
        "equipment": "CO₂ sensors, modulating O/A dampers or variable-speed fans, DCV control software, AS 1668.2 compliance check",
        "sliders": [
            {"key": "peakOcc", "label": "Peak Occupancy", "min": 20, "max": 100, "step": 5, "default": 80, "unit": "%"},
            {"key": "co2SP", "label": "CO₂ Set Point", "min": 600, "max": 1000, "step": 25, "default": 800, "unit": "ppm"},
        ],
    },
    "O13": {
        "scope": "carpark fan energy",
        "pct": 80,
        "x_type": "hour",
        "sim_label": "Carpark Ventilation Fan Power",
        "summary": "Ties carpark ventilation fan speed to measured carbon monoxide levels via VSDs, instead of running fans continuously at full speed.",
        "principle": "Fan power follows the cube of flow rate, so a 50% flow reduction can cut fan power by up to 87%. AS 1668.2 sets CO limits of 30 ppm (staffed) and 60 ppm (unstaffed).",
        "practice": "Carpark fans are commonly left running continuously at full speed, or switched off entirely — a safety risk in the second case.",
        "recommendation": "Install CO sensors with VSD-controlled fans and a high-select control signal spanning all sensor zones.",
        "equipment": "CO sensors across carpark zones, VSD-controlled fans, DCV control software, AS 1668.2 compliance verification",
        "scenario": "One carpark cut ventilation energy 60% (315,360 kWh/yr, $47,304/yr) after installing CO/VSD controls — payback in 1.8 years.",
        "sliders": [{"key": "peakDensity", "label": "Peak Car Density", "min": 10, "max": 100, "step": 5, "default": 55, "unit": "%"}],
    },
    "O14": {
        "scope": "pumping energy",
        "pct": 30,
        "x_type": "hour",
        "sim_label": "Secondary CHW Pump Power",
        "summary": "Lets secondary CHW pump speed float down whenever no valve needs full pressure, instead of holding a fixed pressure sized for peak summer load.",
        "principle": "Resets the pressure differential set point so the most-open CHW valve stays near 95% open — delivering water at the lowest pressure that still meets demand.",
        "practice": "Pumps typically hold a constant pressure set point sized for design-peak flow, wasting energy for nearly the whole year.",
        "recommendation": "Convert 3-port valves to 2-port where needed to enable true variable flow, then apply automated pressure-reset software at regular intervals.",
        "equipment": "CHW pressure-differential sensors, DDC controllers, SCHW control software, VSDs on secondary pumps, 2-port valve conversion where required",
        "sliders": [{"key": "loadAmp", "label": "Peak Cooling Load", "min": 40, "max": 100, "step": 5, "default": 75, "unit": "%"}],
    },
    "O15": {
        "scope": "condenser fan energy",
        "pct": 30,
        "x_type": "hour",
        "sim_label": "Condenser Fan Power — Air-Cooled",
        "summary": "Uses VSD-controlled condenser fans to hold the minimum head pressure that still lets expansion valves work correctly, instead of simple fan on/off cycling.",
        "principle": "Air-cooled condensing temperature is typically maintained 8–12°C above ambient dry-bulb; VSD or EC-motor fans track this far more precisely than staged switching.",
        "practice": "Most systems cycle single- or multi-speed condenser fans on and off, over- or under-condensing between cycles.",
        "recommendation": "Pair with EEV retrofits for compounding savings, and confirm the strategy with the equipment manufacturer before implementing.",
        "equipment": "Temperature/pressure sensors, controllers, VSD- or EC-motor-driven condenser fans, manufacturer head-pressure spec",
        "sliders": [{"key": "ambientMean", "label": "Ambient Temp (avg)", "min": 10, "max": 35, "step": 1, "default": 20, "unit": "°C"}],
    },
    "O16": {
        "scope": "CW pump energy",
        "pct": 30,
        "x_type": "hour",
        "sim_label": "Condenser Water Pump Power — Water-Cooled",
        "summary": "Matches condenser water flow to actual heat-rejection needs via VSD pumps or modulating valves, and shuts off flow entirely to idle units.",
        "principle": "Single units use direct VSD pump control; multiple units sharing one pump use modulating head-pressure valves to control flow per unit.",
        "practice": "CW commonly flows at a constant, manufacturer- or designer-specified rate even when units are idle or running at part-load.",
        "recommendation": "Isolate CW to units that are off using 2-port valves, and avoid over-condensing, which wastes pump energy without any operational benefit.",
        "equipment": "Temperature/pressure sensors, CW pump, head-pressure control valves, VSD controllers, 2-port isolation valves",
        "sliders": [
            {"key": "loadAmp", "label": "Peak Cooling Load", "min": 40, "max": 100, "step": 5, "default": 75, "unit": "%"},
            {"key": "idlePct", "label": "Units Idle (isolated when off)", "min": 0, "max": 50, "step": 5, "default": 20, "unit": "%"},
        ],
    },
    "O17": {
        "scope": "total energy",
        "pct": 50,
        "x_type": "month",
        "sim_label": "Relative Building Energy Index (Month 1 = 100)",
        "summary": "Establishes a documented, cross-team energy management plan — linking senior management, operators, and contractors — so optimizations are sustained rather than quietly reverting.",
        "principle": "Combines monitoring and reporting, SMART energy targets, measurement and verification, and stakeholder communication to keep gains in place long-term.",
        "practice": "Many sites have no energy management documentation and little coordination between facility managers, maintenance contractors, and senior management.",
        "recommendation": "Hold regular (three- to six-monthly) cross-team reviews, document a facility-specific plan, and communicate goals and progress to occupants.",
        "equipment": "Energy management plan document, BMS/utility/sub-meter reporting, designated sustainability lead, occupant communication channel",
        "scenario": "One office cut electricity and gas use 15% (~$61,000/yr, 418 t CO₂) after adopting a documented plan and training — payback under 6 months.",
        "sliders": [{"key": "coordScore", "label": "Program Coordination Score", "min": 0, "max": 100, "step": 5, "default": 55, "unit": "%"}],
    },
    "O18": {
        "scope": "total energy",
        "pct": 10,
        "x_type": "month",
        "sim_label": "Relative Energy Index (Month 1 = 100)",
        "summary": "Formal and informal training for operators, maintenance staff, and occupants closes the knowledge gaps that quietly waste energy day to day.",
        "principle": "Buildings with better-informed facility managers and active training programs measurably outperform on NABERS Energy ratings.",
        "practice": "Operators and maintenance staff are often undertrained on site-specific HVAC controls and the energy impact of ad hoc changes.",
        "recommendation": "Provide site-specific technical training for maintenance staff and procedural training for management; document training requirements by role. Advisory only — no HVAC dispatch.",
        "equipment": "Training materials, live training register, periodic awareness sessions or newsletters, new-starter onboarding pack",
        "sliders": [{"key": "coverage", "label": "Training Coverage", "min": 0, "max": 100, "step": 5, "default": 50, "unit": "%"}],
    },
    "O19": {
        "scope": "HVAC energy",
        "pct": 20,
        "x_type": "month",
        "sim_label": "Relative HVAC Energy Index (Month 1 = 100)",
        "summary": "Adds energy-efficiency KPIs and inspection routines to standard maintenance contracts, keeping plant running near its designed performance instead of drifting.",
        "principle": "Performance-based maintenance contracts with efficiency incentives measurably outperform standard, compliance-only contracts.",
        "practice": "Maintenance is usually scoped only for statutory compliance and occupant comfort, not energy performance.",
        "recommendation": "Build a site-specific maintenance schedule, calibrate sensors at least every six months, and verify control strategies stay compatible across systems. Maintenance records only — no setpoint writes.",
        "equipment": "Documented maintenance schedule, sensor calibration program, trained maintenance personnel, performance-based contract terms",
        "sliders": [{"key": "freq", "label": "Maintenance Checks / Year", "min": 0, "max": 12, "step": 1, "default": 4, "unit": "/yr"}],
    },
    "O20": {
        "scope": "HVAC energy",
        "pct": 10,
        "x_type": "month",
        "sim_label": "Optimized Settings Retained",
        "summary": "Protects hard-won BMS settings from being lost to software patches, factory resets, or undocumented ad hoc changes.",
        "principle": "Restricting system access, logging changes, and maintaining backups prevents optimized settings from silently reverting to defaults.",
        "practice": "Many systems are managed informally, with no change log and a real risk of reverting to factory defaults after a patch.",
        "recommendation": "Assign unique log-ins, maintain a change log, back up software off-site, and document control settings against the energy management plan. Change-request only — no auto deploy.",
        "equipment": "Access-controlled BMS accounts, off-site backup storage, antivirus/firewall protection, maintained change log",
        "sliders": [
            {"key": "accessCtrl", "label": "Access Control (0=Open, 1=Restricted)", "min": 0, "max": 1, "step": 1, "default": 1, "unit": ""},
            {"key": "backupFreq", "label": "Backup Frequency", "min": 0, "max": 12, "step": 1, "default": 4, "unit": "/yr"},
        ],
    },
}


def normalize_oid(raw: str) -> Optional[str]:
    s = (raw or "").strip().upper().replace(" ", "")
    if s in ("O6-O8", "O6_8", "O6/O8"):
        return None
    if s.isdigit():
        s = f"O{int(s)}"
    if catalog_entry(s):
        return s
    return None


def official_ids() -> List[str]:
    return [row[0] for row in CATALOG]


def neighbors(oid: str) -> Dict[str, Optional[str]]:
    ids = official_ids()
    i = ids.index(oid)
    prev_id = ids[i - 1] if i > 0 else None
    next_id = ids[i + 1] if i < len(ids) - 1 else None
    return {
        "prev_id": prev_id,
        "next_id": next_id,
        "prev_route": ROUTES.get(prev_id) if prev_id else None,
        "next_route": ROUTES.get(next_id) if next_id else None,
    }


def catalog_item(oid: str) -> Optional[Dict[str, Any]]:
    row = catalog_entry(oid)
    meta = GUIDE_META.get(oid)
    if not row or not meta:
        return None
    _oid, num, section, title, _desc = row
    item = {
        "opportunity_id": oid,
        "id": num,
        "title": title,
        "section": section,
        "cat": CAT_MAP[section],
        "route": ROUTES[oid],
        **{k: meta[k] for k in meta if k != "sliders"},
        "sliders": meta["sliders"],
        **neighbors(oid),
    }
    from backend.knowledge.hvac_guide_catalog import catalog_record

    knowledge = catalog_record(oid)
    if knowledge:
        item["guide_page"] = knowledge["guide_page"]
        item["guide_section"] = knowledge["section"]
        item["strategy_summary"] = knowledge["strategy_summary"]
        item["required_inputs"] = knowledge["required_inputs"]
        item["recommended_control_logic"] = knowledge["recommended_control_logic"]
        item["equipment_applicability"] = knowledge["equipment_applicability"]
        item["risks"] = knowledge["risks"]
        item["benefits"] = knowledge["benefits"]
        item["guide_savings_potential"] = knowledge["guide_savings_potential"]
        item["guide_potential"] = knowledge["guide_potential"]
        item["energy_impact_class"] = "GUIDE_POTENTIAL"
        item["control_kind"] = knowledge["control_kind"]
        item["source_reference"] = knowledge["source_reference"]
    return item


def catalog_list() -> List[Dict[str, Any]]:
    return [catalog_item(oid) for oid in official_ids() if catalog_item(oid)]
