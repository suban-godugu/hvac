import { avg, clamp, loadCurve, oat, occupancyCurve, type GuideStrategy } from './guideTypes';

export const GUIDE_STRATEGIES_B: GuideStrategy[] = [
  {
    id: 10,
    route: '/agents/ventilation-airflow/economy-cycle',
    cat: 'ventilation',
    title: 'Economy Cycle',
    scope: 'compressor energy',
    pct: 20,
    summary: 'Uses outdoor air directly for cooling whenever it holds less total energy than return air, cutting mechanical cooling load while improving indoor air quality.',
    principle: 'Should be enabled based on enthalpy or dew point comparison against return air — not outdoor temperature or relative humidity alone.',
    practice: 'Many economy cycles are disabled, mis-tuned to overly narrow temperature bands, or broken due to faulty humidity sensors and dampers.',
    recommendation: 'Enable when outdoor dew point is below ~12°C or enthalpy is at least 10 kJ/kg below return air; ensure lock-out during fire mode and high-humidity conditions.',
    equipment: 'Return and outdoor air temperature/humidity sensors, DDC controllers, correctly sized O/A and relief-air dampers, economy-cycle software',
    sim: {
      label: 'Compressor Load — With/Without Economy Cycle',
      xType: 'hour',
      sliders: [
        { key: 'oatMean', label: 'Outdoor Temp (avg)', min: 10, max: 30, step: 1, default: 18, unit: '°C' },
        { key: 'dewPoint', label: 'Outdoor Dew Point', min: 0, max: 20, step: 1, default: 10, unit: '°C' },
      ],
      compute: (hour, v) => {
        const temp = oat(hour, v.oatMean, 6);
        const active = temp < 21 && v.dewPoint < 12;
        const demand = 100 * loadCurve(hour);
        return { baseline: demand, optimized: active ? demand * 0.15 : demand };
      },
      metrics: (pts) => {
        const ab = avg(pts.map((p) => p.baseline));
        const ao = avg(pts.map((p) => p.optimized));
        const hoursActive = pts.filter((p) => p.optimized < p.baseline * 0.9).length;
        const savings = ab > 0 ? clamp(((ab - ao) / ab) * 100, 0, 20) : 0;
        return [
          { label: 'Economy cycle active', value: `${hoursActive} h/day` },
          { label: 'Optimized avg compressor load', value: `${ao.toFixed(0)}%` },
          { label: 'Compressor energy saved', value: `${savings.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 11,
    route: '/agents/ventilation-airflow/night-purge',
    cat: 'ventilation',
    title: 'Night Purge',
    scope: 'compressor start-up energy',
    pct: 20,
    summary: 'Flushes accumulated heat out of the building with cool early-morning outdoor air just before start-up, reducing the mechanical cooling load needed at occupancy.',
    principle: 'Mechanical night purge only saves energy when outdoor air is significantly cooler and drier than indoor air (dew point below 12°C, 4–5°C temperature difference) and is timed for roughly 30–60 minutes before start-up.',
    practice: 'Night purge is often disabled, left running too long, or conflicts with subsequent heating — negating its intended benefit.',
    recommendation: 'Limit to selected AHUs, disable heating for at least an hour afterward, and reserve full-night operation for purely natural-ventilation systems.',
    equipment: 'Field temperature/humidity sensors, controllers, automated outdoor/return/relief air dampers, night purge software',
    sim: {
      label: 'Indoor Temperature Pre-Occupancy',
      xType: 'hour',
      sliders: [
        { key: 'overnightLow', label: 'Overnight Outdoor Low', min: 10, max: 25, step: 1, default: 16, unit: '°C' },
        { key: 'residual', label: 'Residual Indoor Temp (pre-purge)', min: 24, max: 30, step: 0.5, default: 27, unit: '°C' },
      ],
      compute: (hour, v) => {
        if (hour < 4) return { baseline: v.residual - 1, optimized: v.residual - 1 };
        if (hour < 7.5) {
          const pf = clamp((hour - 4) / 2.5, 0, 1);
          return { baseline: v.residual, optimized: v.residual - pf * Math.max(0, v.residual - 2 - v.overnightLow) };
        }
        return { baseline: 23, optimized: 23 };
      },
      metrics: (pts, v) => {
        const windowPts = pts.filter((p) => p.x >= 4 && p.x < 7.5);
        const minOpt = windowPts.length ? Math.min(...windowPts.map((p) => p.optimized)) : v.residual;
        const savings = clamp((v.residual - minOpt) * 4, 0, 20);
        return [
          { label: 'Residual temp', value: `${v.residual.toFixed(1)}°C` },
          { label: 'Purged down to', value: `${minOpt.toFixed(1)}°C` },
          { label: 'Start-up energy saved', value: `${savings.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 12,
    route: '/agents/ventilation-airflow/demand-ventilation',
    cat: 'ventilation',
    title: 'Demand Control Ventilation — CO₂ (Occupied Spaces)',
    scope: 'outdoor air conditioning energy',
    pct: 20,
    summary: 'Uses CO₂ sensors as an occupancy proxy to trim outdoor air intake in spaces with variable occupancy, cutting the heating/cooling load tied to ventilation air.',
    principle: "CO₂ set points around 800–1,000 ppm balance energy savings against indoor air quality, since discomfort typically isn't detected until 1,500–2,000 ppm.",
    practice: 'Ventilation is often oversupplied at all times, or run on a fixed timer that ignores actual occupancy levels.',
    recommendation: 'Best suited to meeting rooms, foyers, cinemas, and shopping malls; use proportional-only control and never fully shut off ventilation.',
    equipment: 'CO₂ sensors, modulating O/A dampers or variable-speed fans, DCV control software, AS 1668.2 compliance check',
    sim: {
      label: 'Outdoor Air Ventilation Rate',
      xType: 'hour',
      sliders: [
        { key: 'peakOcc', label: 'Peak Occupancy', min: 20, max: 100, step: 5, default: 80, unit: '%' },
        { key: 'co2SP', label: 'CO₂ Set Point', min: 600, max: 1000, step: 25, default: 800, unit: 'ppm' },
      ],
      compute: (hour, v) => {
        const occ = v.peakOcc * occupancyCurve(hour);
        return { baseline: 100, optimized: clamp(30 + occ * 0.7, 30, 100) };
      },
      metrics: (pts, v) => {
        const ao = avg(pts.map((p) => p.optimized));
        const estCO2 = Math.round(400 + (v.peakOcc / 100) * (v.co2SP - 400));
        return [
          { label: 'Optimized avg OA flow', value: `${ao.toFixed(0)}%` },
          { label: 'Peak CO₂ estimate', value: `${estCO2} ppm` },
          { label: 'Ventilation energy saved', value: `${clamp(100 - ao, 0, 20).toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 13,
    route: '/agents/ventilation-airflow/dcv-co',
    cat: 'ventilation',
    title: 'Demand Control Ventilation — CO (Carparks & Loading Docks)',
    scope: 'carpark fan energy',
    pct: 80,
    summary: 'Ties carpark ventilation fan speed to measured carbon monoxide levels via VSDs, instead of running fans continuously at full speed.',
    principle: 'Fan power follows the cube of flow rate, so a 50% flow reduction can cut fan power by up to 87%. AS 1668.2 sets CO limits of 30 ppm (staffed) and 60 ppm (unstaffed).',
    practice: 'Carpark fans are commonly left running continuously at full speed, or switched off entirely — a safety risk in the second case.',
    recommendation: 'Install CO sensors with VSD-controlled fans and a high-select control signal spanning all sensor zones.',
    equipment: 'CO sensors across carpark zones, VSD-controlled fans, DCV control software, AS 1668.2 compliance verification',
    scenario: 'One carpark cut ventilation energy 60% (315,360 kWh/yr, $47,304/yr) after installing CO/VSD controls — payback in 1.8 years.',
    sim: {
      label: 'Carpark Ventilation Fan Power',
      xType: 'hour',
      sliders: [{ key: 'peakDensity', label: 'Peak Car Density', min: 10, max: 100, step: 5, default: 55, unit: '%' }],
      compute: (hour, v) => {
        const density = v.peakDensity * occupancyCurve(hour);
        const speed = clamp(25 + density * 0.75, 25, 100);
        return { baseline: 100, optimized: Math.pow(speed / 100, 3) * 100 };
      },
      metrics: (pts) => {
        const ao = avg(pts.map((p) => p.optimized));
        return [
          { label: 'Baseline fan power', value: '100%' },
          { label: 'Optimized avg fan power', value: `${ao.toFixed(0)}%` },
          { label: 'Fan energy saved', value: `${clamp(100 - ao, 0, 80).toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 14,
    route: '/agents/variable-speed/chilled-water-pump',
    cat: 'variablespeed',
    title: 'Optimised Secondary Chilled Water Pumping',
    scope: 'pumping energy',
    pct: 30,
    summary: 'Lets secondary CHW pump speed float down whenever no valve needs full pressure, instead of holding a fixed pressure sized for peak summer load.',
    principle: 'Resets the pressure differential set point so the most-open CHW valve stays near 95% open — delivering water at the lowest pressure that still meets demand.',
    practice: 'Pumps typically hold a constant pressure set point sized for design-peak flow, wasting energy for nearly the whole year.',
    recommendation: 'Convert 3-port valves to 2-port where needed to enable true variable flow, then apply automated pressure-reset software at regular intervals.',
    equipment: 'CHW pressure-differential sensors, DDC controllers, SCHW control software, VSDs on secondary pumps, 2-port valve conversion where required',
    sim: {
      label: 'Secondary CHW Pump Power',
      xType: 'hour',
      sliders: [{ key: 'loadAmp', label: 'Peak Cooling Load', min: 40, max: 100, step: 5, default: 75, unit: '%' }],
      compute: (hour, v) => {
        const load = (v.loadAmp / 100) * loadCurve(hour);
        const speed = clamp(100 * ((40 + load * 60) / 95), 30, 100);
        return { baseline: 100, optimized: Math.pow(speed / 100, 3) * 100 };
      },
      metrics: (pts) => {
        const ao = avg(pts.map((p) => p.optimized));
        return [
          { label: 'Baseline pump power', value: '100%' },
          { label: 'Optimized avg pump power', value: `${ao.toFixed(0)}%` },
          { label: 'Pumping energy saved', value: `${clamp(100 - ao, 0, 30).toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 15,
    route: '/agents/variable-speed/air-cooled-head-pressure',
    cat: 'variablespeed',
    title: 'Variable Head Pressure Control — Air-Cooled Condensers',
    scope: 'condenser fan energy',
    pct: 30,
    summary: 'Uses VSD-controlled condenser fans to hold the minimum head pressure that still lets expansion valves work correctly, instead of simple fan on/off cycling.',
    principle: 'Air-cooled condensing temperature is typically maintained 8–12°C above ambient dry-bulb; VSD or EC-motor fans track this far more precisely than staged switching.',
    practice: 'Most systems cycle single- or multi-speed condenser fans on and off, over- or under-condensing between cycles.',
    recommendation: 'Pair with EEV retrofits for compounding savings, and confirm the strategy with the equipment manufacturer before implementing.',
    equipment: 'Temperature/pressure sensors, controllers, VSD- or EC-motor-driven condenser fans, manufacturer head-pressure spec',
    sim: {
      label: 'Condenser Fan Power — Air-Cooled',
      xType: 'hour',
      sliders: [{ key: 'ambientMean', label: 'Ambient Temp (avg)', min: 10, max: 35, step: 1, default: 20, unit: '°C' }],
      compute: (hour, v) => ({ baseline: 95, optimized: clamp((oat(hour, v.ambientMean, 6) - 2) * 2.8, 25, 100) }),
      metrics: (pts) => {
        const ab = avg(pts.map((p) => p.baseline));
        const ao = avg(pts.map((p) => p.optimized));
        const savings = ab > 0 ? clamp(((ab - ao) / ab) * 100, 0, 30) : 0;
        return [
          { label: 'Baseline fan power', value: `${ab.toFixed(0)}%` },
          { label: 'Optimized avg fan power', value: `${ao.toFixed(0)}%` },
          { label: 'Condenser fan energy saved', value: `${savings.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 16,
    route: '/agents/variable-speed/water-cooled-head-pressure',
    cat: 'variablespeed',
    title: 'Variable Head Pressure Control — Water-Cooled Condensers',
    scope: 'CW pump energy',
    pct: 30,
    summary: 'Matches condenser water flow to actual heat-rejection needs via VSD pumps or modulating valves, and shuts off flow entirely to idle units.',
    principle: 'Single units use direct VSD pump control; multiple units sharing one pump use modulating head-pressure valves to control flow per unit.',
    practice: 'CW commonly flows at a constant, manufacturer- or designer-specified rate even when units are idle or running at part-load.',
    recommendation: 'Isolate CW to units that are off using 2-port valves, and avoid over-condensing, which wastes pump energy without any operational benefit.',
    equipment: 'Temperature/pressure sensors, CW pump, head-pressure control valves, VSD controllers, 2-port isolation valves',
    sim: {
      label: 'Condenser Water Pump Power — Water-Cooled',
      xType: 'hour',
      sliders: [
        { key: 'loadAmp', label: 'Peak Cooling Load', min: 40, max: 100, step: 5, default: 75, unit: '%' },
        { key: 'idlePct', label: 'Units Idle (isolated when off)', min: 0, max: 50, step: 5, default: 20, unit: '%' },
      ],
      compute: (hour, v) => {
        const load = (v.loadAmp / 100) * loadCurve(hour);
        return { baseline: 100, optimized: clamp(100 * (1 - v.idlePct / 100) * (0.4 + 0.6 * load), 20, 100) };
      },
      metrics: (pts) => {
        const ao = avg(pts.map((p) => p.optimized));
        return [
          { label: 'Baseline pump power', value: '100%' },
          { label: 'Optimized avg pump power', value: `${ao.toFixed(0)}%` },
          { label: 'CW pump energy saved', value: `${clamp(100 - ao, 0, 30).toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 17,
    route: '/agents/operations-maintenance/energy-management-planning',
    cat: 'om',
    title: 'Energy Management Planning',
    scope: 'total energy',
    pct: 50,
    summary: 'Establishes a documented, cross-team energy management plan — linking senior management, operators, and contractors — so optimizations are sustained rather than quietly reverting.',
    principle: 'Combines monitoring and reporting, SMART energy targets, measurement and verification, and stakeholder communication to keep gains in place long-term.',
    practice: 'Many sites have no energy management documentation and little coordination between facility managers, maintenance contractors, and senior management.',
    recommendation: 'Hold regular (three- to six-monthly) cross-team reviews, document a facility-specific plan, and communicate goals and progress to occupants.',
    equipment: 'Energy management plan document, BMS/utility/sub-meter reporting, designated sustainability lead, occupant communication channel',
    scenario: 'One office cut electricity and gas use 15% (~$61,000/yr, 418 t CO₂) after adopting a documented plan and training — payback under 6 months.',
    sim: {
      label: 'Relative Building Energy Index (Month 1 = 100)',
      xType: 'month',
      sliders: [{ key: 'coordScore', label: 'Program Coordination Score', min: 0, max: 100, step: 5, default: 55, unit: '%' }],
      compute: (month, v) => ({ baseline: 100 + month * 1.6, optimized: 100 - (v.coordScore / 100) * month * 3.2 }),
      metrics: (pts) => {
        const last = pts[pts.length - 1];
        const savings = last.baseline > 0 ? clamp(((last.baseline - last.optimized) / last.baseline) * 100, 0, 50) : 0;
        return [
          { label: 'Year-end index — no plan', value: last.baseline.toFixed(0) },
          { label: 'Year-end index — with plan', value: last.optimized.toFixed(0) },
          { label: 'Total energy saved', value: `${savings.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 18,
    route: '/agents/operations-maintenance/training-awareness',
    cat: 'om',
    title: 'Energy Management Training & Awareness',
    scope: 'total energy',
    pct: 10,
    summary: 'Formal and informal training for operators, maintenance staff, and occupants closes the knowledge gaps that quietly waste energy day to day.',
    principle: 'Buildings with better-informed facility managers and active training programs measurably outperform on NABERS Energy ratings.',
    practice: 'Operators and maintenance staff are often undertrained on site-specific HVAC controls and the energy impact of ad hoc changes.',
    recommendation: 'Provide site-specific technical training for maintenance staff and procedural training for management; document training requirements by role.',
    equipment: 'Training materials, live training register, periodic awareness sessions or newsletters, new-starter onboarding pack',
    sim: {
      label: 'Relative Energy Index (Month 1 = 100)',
      xType: 'month',
      sliders: [{ key: 'coverage', label: 'Training Coverage', min: 0, max: 100, step: 5, default: 50, unit: '%' }],
      compute: (month, v) => ({ baseline: 100 + month * 0.3, optimized: 100 - (v.coverage / 100) * month * 0.9 }),
      metrics: (pts, v) => {
        const last = pts[pts.length - 1];
        const savings = last.baseline > 0 ? clamp(((last.baseline - last.optimized) / last.baseline) * 100, 0, 10) : 0;
        return [
          { label: 'Total energy saved', value: `${savings.toFixed(0)}%` },
          { label: 'Est. NABERS star gain', value: `+${((v.coverage / 100) * 0.5).toFixed(1)} ★` },
          { label: 'Training coverage', value: `${v.coverage}%` },
        ];
      },
    },
  },
  {
    id: 19,
    route: '/agents/operations-maintenance/equipment-maintenance',
    cat: 'om',
    title: 'Energy Efficiency Maintenance',
    scope: 'HVAC energy',
    pct: 20,
    summary: 'Adds energy-efficiency KPIs and inspection routines to standard maintenance contracts, keeping plant running near its designed performance instead of drifting.',
    principle: 'Performance-based maintenance contracts with efficiency incentives measurably outperform standard, compliance-only contracts.',
    practice: 'Maintenance is usually scoped only for statutory compliance and occupant comfort, not energy performance.',
    recommendation: 'Build a site-specific maintenance schedule, calibrate sensors at least every six months, and verify control strategies stay compatible across systems.',
    equipment: 'Documented maintenance schedule, sensor calibration program, trained maintenance personnel, performance-based contract terms',
    sim: {
      label: 'Relative HVAC Energy Index (Month 1 = 100)',
      xType: 'month',
      sliders: [{ key: 'freq', label: 'Maintenance Checks / Year', min: 0, max: 12, step: 1, default: 4, unit: '/yr' }],
      compute: (month, v) => ({
        baseline: 100 + month * 1.2,
        optimized: 100 + month * 1.2 * (1 - clamp(v.freq / 12, 0, 1)),
      }),
      metrics: (pts) => {
        const last = pts[pts.length - 1];
        const savings = last.baseline > 0 ? clamp(((last.baseline - last.optimized) / last.baseline) * 100, 0, 20) : 0;
        return [
          { label: 'Year-end index — reactive', value: last.baseline.toFixed(0) },
          { label: 'Year-end index — maintained', value: last.optimized.toFixed(0) },
          { label: 'HVAC energy saved', value: `${savings.toFixed(0)}%` },
        ];
      },
    },
  },
  {
    id: 20,
    route: '/agents/operations-maintenance/control-software',
    cat: 'om',
    title: 'Management of System Control Software',
    scope: 'HVAC energy',
    pct: 10,
    summary: 'Protects hard-won BMS settings from being lost to software patches, factory resets, or undocumented ad hoc changes.',
    principle: 'Restricting system access, logging changes, and maintaining backups prevents optimized settings from silently reverting to defaults.',
    practice: 'Many systems are managed informally, with no change log and a real risk of reverting to factory defaults after a patch.',
    recommendation: 'Assign unique log-ins, maintain a change log, back up software off-site, and document control settings against the energy management plan.',
    equipment: 'Access-controlled BMS accounts, off-site backup storage, antivirus/firewall protection, maintained change log',
    sim: {
      label: 'Optimized Settings Retained',
      xType: 'month',
      sliders: [
        { key: 'accessCtrl', label: 'Access Control (0=Open, 1=Restricted)', min: 0, max: 1, step: 1, default: 1, unit: '' },
        { key: 'backupFreq', label: 'Backup Frequency', min: 0, max: 12, step: 1, default: 4, unit: '/yr' },
      ],
      compute: (month, v) => {
        const baseline = clamp(100 - month * 4, 40, 100);
        const controlFactor = v.accessCtrl * 0.5 + clamp(v.backupFreq / 12, 0, 1) * 0.5;
        return { baseline, optimized: clamp(100 - month * 4 * (1 - controlFactor), 40, 100) };
      },
      metrics: (pts) => {
        const last = pts[pts.length - 1];
        const savings = clamp((last.optimized - last.baseline) * 0.2, 0, 10);
        return [
          { label: 'Settings retained — baseline', value: `${last.baseline.toFixed(0)}%` },
          { label: 'Settings retained — managed', value: `${last.optimized.toFixed(0)}%` },
          { label: 'HVAC energy saved', value: `${savings.toFixed(0)}%` },
        ];
      },
    },
  },
];
