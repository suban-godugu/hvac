import {
  avg,
  clamp,
  loadCurve,
  oat,
  type GuideStrategy,
} from './guideTypes';

export const GUIDE_STRATEGIES: GuideStrategy[] = [
  {
    id: 1,
    route: '/agents/scheduling/optimum-start-stop',
    cat: 'scheduling',
    title: 'Optimum Start/Stop Programming',
    scope: 'HVAC energy',
    pct: 10,
    summary:
      'Automates HVAC start and stop times using zone temperatures and outdoor conditions instead of a fixed schedule, cutting operating hours while still meeting comfort by the time occupants arrive.',
    principle:
      "Calculates the latest possible start time and earliest possible stop time from real-time indoor/outdoor temperatures and the building's learned thermal response, adjusting automatically day to day.",
    practice:
      'Most systems start 2–3 hours before occupancy on a fixed schedule year-round regardless of season — wasteful during mild weather.',
    recommendation:
      'Verify occupancy times are current, confirm the enabling time suits seasonal extremes, and integrate with warm-up/cool-down and after-hours programs.',
    equipment: '365-day schedule, outdoor temperature sensor, zone temperature sensors, trend-logging capability, OSS control software',
    scenario: 'One Sydney office cut HVAC operating hours ~17% (120 min/day) and energy use 12%, saving $35,280/yr with payback under 3 months.',
    sim: {
      label: 'Start/Stop Schedule — HVAC Run State',
      xType: 'hour',
      sliders: [
        { key: 'occStart', label: 'Occupancy Start Time', min: 7, max: 9.5, step: 0.5, default: 8.5, unit: 'h' },
        { key: 'severity', label: 'Outdoor Temp Severity (mild ↔ extreme)', min: 0, max: 100, step: 5, default: 50, unit: '%' },
      ],
      compute: (hour, v) => {
        const baseStart = v.occStart - 2.5;
        const baseStop = 17.5;
        const optStart = v.occStart - (0.5 + (v.severity / 100) * 2);
        const optStop = 17.5 - (0.1 + ((100 - v.severity) / 100) * 0.4);
        return { baseline: hour >= baseStart && hour < baseStop ? 100 : 0, optimized: hour >= optStart && hour < optStop ? 100 : 0 };
      },
      metrics: (pts) => {
        const baseHrs = pts.filter((p) => p.baseline > 0).length;
        const optHrs = pts.filter((p) => p.optimized > 0).length;
        const red = baseHrs > 0 ? ((baseHrs - optHrs) / baseHrs) * 100 : 0;
        return [
          { label: 'Baseline runtime', value: `${baseHrs} h/day` },
          { label: 'Optimized runtime', value: `${optHrs} h/day` },
          { label: 'Operating hours cut', value: `${red.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 2,
    route: '/agents/scheduling/space-temperature',
    cat: 'scheduling',
    title: 'Space Temperature Set Points & Control Bands',
    scope: 'HVAC energy',
    pct: 20,
    summary:
      'Widens the dead band and proportional bands around the temperature set point so equipment runs less often and at lower intensity, without occupants noticing the difference.',
    principle: 'A 1°C shift in set point can shift energy use by roughly 10%. Recommended ranges are 20–22°C in winter and 24–26°C in summer, with 2–3°C dead bands.',
    practice: 'Many buildings hold a tight 22–22.5°C target year-round with narrow control bands, forcing unnecessary heating/cooling cycling.',
    recommendation: 'Widen bands gradually (about 0.3°C at a time) so occupants can adjust, and switch PI/PID loops to P-only control where feasible.',
    equipment: 'Adjustable-band temperature controllers, 0.1°C sensor increments where possible, BMS or standalone HVAC controller, occupant consultation plan',
    scenario: 'A 20,000 m² office saved ~$19,650/yr (128 t CO₂) with under a month\'s payback by widening bands and shifting the set point 0.5°C.',
    sim: {
      label: 'Heating/Cooling Output vs Time',
      xType: 'hour',
      sliders: [
        { key: 'deadBand', label: 'Dead Band', min: 1, max: 3, step: 0.5, default: 1, unit: '°C' },
        { key: 'propBand', label: 'Proportional Band', min: 0.5, max: 2, step: 0.25, default: 1, unit: '°C' },
      ],
      compute: (hour, v) => {
        const dev = clamp(3 * Math.sin(((hour - 9) / 14) * Math.PI), -3, 3);
        const out = (d: number, db: number, pb: number) => {
          const half = db / 2;
          if (Math.abs(d) <= half) return 0;
          return clamp(((Math.abs(d) - half) / pb) * 100, 0, 100);
        };
        return { baseline: out(dev, 1, 1), optimized: out(dev, v.deadBand, v.propBand) };
      },
      metrics: (pts) => {
        const ab = avg(pts.map((p) => p.baseline));
        const ao = avg(pts.map((p) => p.optimized));
        const red = ab > 0 ? ((ab - ao) / ab) * 100 : 0;
        return [
          { label: 'Baseline avg output', value: `${ab.toFixed(0)}%` },
          { label: 'Optimized avg output', value: `${ao.toFixed(0)}%` },
          { label: 'Est. HVAC energy cut', value: `${red.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 3,
    route: '/agents/scheduling/master-ahu-sat',
    cat: 'scheduling',
    title: 'Master AHU Supply Air Temperature Signal',
    scope: 'HVAC energy',
    pct: 15,
    summary: "Replaces 'worst zone wins' supply-air control logic with a weighted average across the most-open VAV boxes, cutting simultaneous heating and cooling.",
    principle: 'A weighted or percentile-based signal from multiple VAV zones sets the AHU supply temperature, rather than letting one extreme or faulty zone drive the whole system.',
    practice: "Most BMS use 'high-select' logic — the single worst zone dictates supply air temperature, causing over-cooling and excess re-heat elsewhere.",
    recommendation: 'Use an average of the 2–5 most-open VAV boxes or a percentile rank, and exclude known-faulty sensors from the calculation.',
    equipment: 'Zone temperature sensors on every VAV box, weighting/percentile control software, damper-position feedback, coordination with set-point strategy',
    scenario: 'Replacing high-select with a 5-box average, fixing faulty dampers, and rebalancing airflow cut HVAC energy ~10% with a 3-month payback.',
    sim: {
      label: 'Master Signal — High-Select vs Weighted Average',
      xType: 'hour',
      sliders: [
        { key: 'numAvg', label: 'Zones Averaged (1 = high-select)', min: 1, max: 5, step: 1, default: 3, unit: '' },
        { key: 'faultBias', label: 'Faulty Zone Sensor Bias', min: 0, max: 5, step: 0.5, default: 1.5, unit: '°C' },
      ],
      compute: (hour, v) => {
        const phases = [0, 1.2, 2.4, 3.6, 4.8];
        const devs = phases.map((ph) => Math.max(0, 2.5 * Math.sin(((hour - 8 + ph) / 12) * Math.PI)));
        devs[4] += v.faultBias;
        const baseline = Math.max(...devs);
        const sorted = [...devs].sort((a, b) => b - a);
        const n = Math.min(v.numAvg, sorted.length);
        const optimized = sorted.slice(0, n).reduce((a, b) => a + b, 0) / n;
        return { baseline, optimized };
      },
      metrics: (pts) => {
        const ab = avg(pts.map((p) => p.baseline));
        const ao = avg(pts.map((p) => p.optimized));
        const red = ab > 0 ? ((ab - ao) / ab) * 100 : 0;
        return [
          { label: 'Baseline signal (high-select)', value: `${ab.toFixed(1)}°C` },
          { label: 'Optimized signal (weighted)', value: `${ao.toFixed(1)}°C` },
          { label: 'Over-cooling reduced', value: `${red.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 4,
    route: '/agents/scheduling/chiller-staging',
    cat: 'scheduling',
    title: 'Staging of Chillers & Compressors',
    scope: 'chiller energy',
    pct: 10,
    summary: 'Brings additional chillers online only when genuinely needed — based on sustained flow/temperature shortfall rather than simple return-temperature triggers.',
    principle: 'Stage-up should require a sustained inability to meet the CHW flow or temperature set point (5–20 minute delay); stage-down should happen quickly once load drops.',
    practice: 'Systems often stage on CHW return temperature with short delays, engaging extra chillers earlier than necessary and running them at inefficient part-load.',
    recommendation: 'Add current-draw and calculated field-load criteria, maximize the stage-up delay, minimize stage-down delay, and lock out cooling calls at low ambient temperatures.',
    equipment: 'Reliable cooling-call signal, CHW flow and temperature sensors, compressor current-draw monitoring, staging control logic',
    sim: {
      label: 'Chillers Staged On',
      xType: 'hour',
      sliders: [
        { key: 'peakLoad', label: 'Peak Cooling Load', min: 40, max: 100, step: 5, default: 75, unit: '%' },
        { key: 'stageDelay', label: 'Stage-Up Delay', min: 5, max: 20, step: 1, default: 10, unit: 'min' },
      ],
      compute: (hour, v) => {
        const load = (v.peakLoad / 100) * loadCurve(hour);
        return {
          baseline: clamp(Math.ceil(load * 3 + 0.45), 0, 3),
          optimized: clamp(Math.ceil(load * 3 - ((v.stageDelay - 5) / 15) * 0.3), 0, 3),
        };
      },
      metrics: (pts) => {
        const ab = avg(pts.map((p) => p.baseline));
        const ao = avg(pts.map((p) => p.optimized));
        const red = ab > 0 ? clamp(((ab - ao) / ab) * 100, 0, 10) : 0;
        return [
          { label: 'Avg stages — baseline', value: ab.toFixed(1) },
          { label: 'Avg stages — optimized', value: ao.toFixed(1) },
          { label: 'Chiller-hours saved', value: `${red.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 5,
    route: '/agents/plant-control/duct-static-pressure',
    cat: 'plant',
    title: 'Duct Static Pressure Reset (DSPR)',
    scope: 'fan energy',
    pct: 30,
    summary: 'Continuously lowers duct static pressure so VSD-driven supply fans work only as hard as the most-open VAV box requires, instead of holding a fixed high pressure.',
    principle: 'Keeps a representative most-open VAV damper near 90–95% open, trimming fan speed at regular intervals (e.g. every 300 seconds).',
    practice: "Static pressure is usually fixed at a conservative, design-peak value that's far higher than needed for most of the year.",
    recommendation: "Reset pressure on a percentile basis rather than the single most-open box, since that box has often failed; verify VAV boxes aren't faulty before relying on them as feedback.",
    equipment: 'Static pressure sensor on the index run, VSD fan controller, damper-position feedback from VAV boxes, reset control logic',
    sim: {
      label: 'Supply Fan Power — Fixed vs Reset Static Pressure',
      xType: 'hour',
      sliders: [
        { key: 'demandAmp', label: 'Peak Airflow Demand', min: 40, max: 100, step: 5, default: 80, unit: '%' },
        { key: 'targetOpen', label: 'Target Most-Open VAV', min: 85, max: 98, step: 1, default: 92, unit: '%' },
      ],
      compute: (hour, v) => {
        const demand = (v.demandAmp / 100) * loadCurve(hour);
        const openNeeded = 40 + demand * 60;
        const optSpeed = clamp(100 * (openNeeded / v.targetOpen), 25, 100);
        return { baseline: 100, optimized: Math.pow(optSpeed / 100, 3) * 100 };
      },
      metrics: (pts) => {
        const ao = avg(pts.map((p) => p.optimized));
        const red = clamp(100 - ao, 0, 30);
        return [
          { label: 'Baseline fan power', value: '100%' },
          { label: 'Optimized fan power', value: `${ao.toFixed(0)}%` },
          { label: 'Fan energy saved', value: `${red.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 6,
    route: '/agents/plant-control/temperature-reset?mode=HHW',
    cat: 'plant',
    title: 'Temperature Reset — Heating Hot Water (HHW)',
    scope: 'hot water energy',
    pct: 5,
    summary: 'Runs boiler water at the lowest flow temperature that still meets heating demand, reserving high temperatures for extreme cold or warm-up periods.',
    principle: 'Non-condensing boilers must stay above 55°C return temperature to avoid corrosion, while condensing boilers gain efficiency below that same threshold.',
    practice: 'Many systems run a fixed HHW flow temperature regardless of load or outdoor conditions.',
    recommendation: 'Reset flow temperature against outdoor and load conditions; use the condensing boiler as lead unit, boosting to 80–85°C only under peak demand.',
    equipment: 'Field temperature sensors, controllers/data processors, reset control software, boiler sequencing logic',
    sim: {
      label: 'Heating Hot Water Flow Temperature',
      xType: 'hour',
      sliders: [
        { key: 'boilerType', label: 'Boiler Type (0=Non-Condensing, 1=Condensing)', min: 0, max: 1, step: 1, default: 1, unit: '' },
        { key: 'heatSeverity', label: 'Heating Demand Severity', min: 0, max: 100, step: 5, default: 60, unit: '%' },
      ],
      compute: (hour, v) => {
        const demand = (v.heatSeverity / 100) * (1 - loadCurve(hour));
        const floor = v.boilerType ? 40 : 55;
        return { baseline: 82, optimized: floor + demand * (82 - floor) };
      },
      metrics: (pts) => {
        const ao = avg(pts.map((p) => p.optimized));
        const savings = clamp((82 - ao) * 0.15, 0, 5);
        return [
          { label: 'Baseline flow temp', value: '82°C' },
          { label: 'Optimized avg flow temp', value: `${ao.toFixed(0)}°C` },
          { label: 'Boiler efficiency gain', value: `${savings.toFixed(1)}%` },
        ];
      },
    },
  },
  {
    id: 7,
    route: '/agents/plant-control/temperature-reset?mode=CHW',
    cat: 'plant',
    title: 'Temperature Reset — Chilled Water (CHW)',
    scope: 'chiller energy',
    pct: 15,
    summary: 'Raises chilled water temperature during mild weather so chillers work less hard, without sacrificing dehumidification when it actually matters.',
    principle: 'Each 1°C rise in CHW temperature cuts compressor energy roughly 2–3% for fixed-speed units and 4–5% for variable-speed units.',
    practice: 'CHW is typically fixed at 6–7°C year-round, sized for a design-day peak load that rarely occurs in practice.',
    recommendation: 'Reset upward to around 10–12°C in mild conditions, weighing the gain against any added pumping or airflow energy — especially on long CHW circuits.',
    equipment: 'Supply/return temperature sensors, field load indication, reset control software, humidity monitoring',
    sim: {
      label: 'Chilled Water Supply Temperature',
      xType: 'hour',
      sliders: [
        { key: 'compType', label: 'Compressor Type (0=Fixed-Speed, 1=VSD)', min: 0, max: 1, step: 1, default: 0, unit: '' },
        { key: 'loadSeverity', label: 'Cooling Load Severity', min: 40, max: 100, step: 5, default: 80, unit: '%' },
      ],
      compute: (hour, v) => {
        const load = (v.loadSeverity / 100) * loadCurve(hour);
        return { baseline: 6.5, optimized: 6.5 + (1 - load) * 5.5 };
      },
      metrics: (pts, v) => {
        const ao = avg(pts.map((p) => p.optimized));
        const perDeg = v.compType ? 4.5 : 2.5;
        const savings = clamp((ao - 6.5) * perDeg, 0, 15);
        return [
          { label: 'Baseline CHW temp', value: '6.5°C' },
          { label: 'Optimized avg CHW temp', value: `${ao.toFixed(1)}°C` },
          { label: 'Chiller energy saved', value: `${savings.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 8,
    route: '/agents/plant-control/temperature-reset?mode=CW',
    cat: 'plant',
    title: 'Temperature Reset — Condenser Water (CW)',
    scope: 'chiller energy',
    pct: 15,
    summary: 'Lowers condenser water temperature to track outdoor wet-bulb conditions, cutting compressor load — balanced against cooling tower fan energy.',
    principle: 'Each 1°C drop in CW temperature cuts compressor energy roughly 2–3% (fixed-speed) to 4–5% (variable-speed); towers are typically designed for a 3–4°C approach to wet-bulb.',
    practice: 'CW temperature is usually held constant regardless of ambient wet-bulb conditions, wasting the free capacity available in cooler weather.',
    recommendation: "Modulate cooling tower fan speed to approach — not undercut — the manufacturer's minimum CW temperature; run multiple fans together at part-load rather than cycling.",
    equipment: 'Wet-bulb/CW temperature sensors, VSD-controlled tower fans, reset control software, manufacturer minimum-temperature spec',
    sim: {
      label: 'Condenser Water Temperature',
      xType: 'hour',
      sliders: [
        { key: 'wetBulbMean', label: 'Ambient Wet-Bulb (avg)', min: 10, max: 28, step: 1, default: 20, unit: '°C' },
        { key: 'approach', label: 'Tower Approach', min: 3, max: 5, step: 0.5, default: 3.5, unit: '°C' },
      ],
      compute: (hour, v) => {
        const wb = oat(hour, v.wetBulbMean, 4);
        return { baseline: v.wetBulbMean + 11.5, optimized: wb + v.approach };
      },
      metrics: (pts) => {
        const ab = avg(pts.map((p) => p.baseline));
        const ao = avg(pts.map((p) => p.optimized));
        const savings = clamp((ab - ao) * 2.5, 0, 15);
        return [
          { label: 'Baseline CW temp', value: `${ab.toFixed(1)}°C` },
          { label: 'Optimized avg CW temp', value: `${ao.toFixed(1)}°C` },
          { label: 'Chiller energy saved', value: `${savings.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 9,
    route: '/agents/plant-control/electronic-expansion-valve',
    cat: 'plant',
    title: 'Retrofit of Electronic Expansion Valves (EEVs)',
    scope: 'compressor energy',
    pct: 15,
    summary: 'Replacing older thermostatic expansion valves with electronic ones gives tighter refrigerant control and a smaller required superheat margin, improving compressor efficiency.',
    principle: 'EEVs regulate refrigerant flow more precisely than mechanical TXVs, reducing the superheat buffer needed to protect compressors from liquid slugging.',
    practice: 'Systems older than 5–10 years typically still run TXVs, which drift with wear and are set conservatively for safety.',
    recommendation: 'Retrofit EEVs on larger DX circuits, ideally alongside variable head-pressure control upgrades for compounding savings.',
    equipment: 'Temperature/pressure field sensors, controllers, EEV hardware, manufacturer retrofit guidance',
    sim: {
      label: 'Superheat-Related Compressor Efficiency Loss',
      xType: 'hour',
      sliders: [
        { key: 'valveType', label: 'Valve Type (0=TXV, 1=EEV)', min: 0, max: 1, step: 1, default: 0, unit: '' },
        { key: 'loadVar', label: 'Load Variability', min: 0, max: 100, step: 5, default: 60, unit: '%' },
      ],
      compute: (hour, v) => {
        const load = 100 * loadCurve(hour) * (v.loadVar / 100) + (1 - v.loadVar / 100) * 70;
        const baseline = 5 + (100 - load) * 0.08;
        const optimized = v.valveType ? 2 + (100 - load) * 0.02 : baseline;
        return { baseline, optimized };
      },
      metrics: (pts) => {
        const ab = avg(pts.map((p) => p.baseline));
        const ao = avg(pts.map((p) => p.optimized));
        const savings = clamp((ab - ao) * 3, 0, 15);
        return [
          { label: 'Baseline efficiency loss', value: `${ab.toFixed(1)}%` },
          { label: 'Optimized efficiency loss', value: `${ao.toFixed(1)}%` },
          { label: 'Compressor energy saved', value: `${savings.toFixed(0)}%` },
        ];
      },
    },
  },
];
