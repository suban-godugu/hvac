/** OEH teaching curves — same model as backend/services/oeh_guide_physics.py. Always SIMULATED. */
(function (g) {
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const avg = (arr) => (arr.length ? arr.reduce((s, n) => s + n, 0) / arr.length : 0);
  const oat = (hour, mean, amp) => mean + amp * Math.cos((hour - 15) * (Math.PI / 12));
  const loadCurve = (hour) => clamp(Math.sin(((hour - 6) / 14) * Math.PI), 0.05, 1);
  const occupancyCurve = (hour) => clamp(Math.sin(((hour - 8) / 10) * Math.PI), 0.03, 1);
  const f = (v, key, d) => {
    const n = Number(v[key]);
    return Number.isFinite(n) ? n : d;
  };
  const pct = (n) => `${n.toFixed(0)}%`;

  function pointAt(oid, x, v) {
    if (oid === "O1") {
      const occ = f(v, "occStart", 8.5);
      const sev = f(v, "severity", 50);
      const baseStart = occ - 2.5, baseStop = 17.5;
      const optStart = occ - (0.5 + (sev / 100) * 2);
      const optStop = 17.5 - (0.1 + ((100 - sev) / 100) * 0.4);
      return [baseStart <= x && x < baseStop ? 100 : 0, optStart <= x && x < optStop ? 100 : 0];
    }
    if (oid === "O2") {
      const db = f(v, "deadBand", 1);
      const pb = f(v, "propBand", 1);
      const dev = clamp(3 * Math.sin(((x - 9) / 14) * Math.PI), -3, 3);
      const out = (d, band, p) => {
        const half = band / 2;
        if (Math.abs(d) <= half) return 0;
        return clamp(((Math.abs(d) - half) / Math.max(p, 0.01)) * 100, 0, 100);
      };
      return [out(dev, 1, 1), out(dev, db, pb)];
    }
    if (oid === "O3") {
      const phases = [0, 1.2, 2.4, 3.6, 4.8];
      const devs = phases.map((ph) => Math.max(0, 2.5 * Math.sin(((x - 8 + ph) / 12) * Math.PI)));
      devs[4] += f(v, "faultBias", 1.5);
      const baseline = Math.max(...devs);
      const n = Math.min(Math.trunc(f(v, "numAvg", 3)), 5);
      const sorted = [...devs].sort((a, b) => b - a);
      const optimized = sorted.slice(0, n).reduce((s, n) => s + n, 0) / n;
      return [baseline, optimized];
    }
    if (oid === "O4") {
      const load = (f(v, "peakLoad", 75) / 100) * loadCurve(x);
      const delay = f(v, "stageDelay", 10);
      const baseline = clamp(Math.ceil(load * 3 + 0.45), 0, 3);
      const optimized = clamp(Math.ceil(load * 3 - ((delay - 5) / 15) * 0.3), 0, 3);
      return [baseline, optimized];
    }
    if (oid === "O5") {
      const demand = (f(v, "demandAmp", 80) / 100) * loadCurve(x);
      const openNeeded = 40 + demand * 60;
      const optSpeed = clamp(100 * (openNeeded / Math.max(f(v, "targetOpen", 92), 1)), 25, 100);
      return [100, (optSpeed / 100) ** 3 * 100];
    }
    if (oid === "O6") {
      const demand = (f(v, "heatSeverity", 60) / 100) * (1 - loadCurve(x));
      const floor = f(v, "boilerType", 1) ? 40 : 55;
      return [82, floor + demand * (82 - floor)];
    }
    if (oid === "O7") {
      const load = (f(v, "loadSeverity", 80) / 100) * loadCurve(x);
      return [6.5, 6.5 + (1 - load) * 5.5];
    }
    if (oid === "O8") {
      const wb = oat(x, f(v, "wetBulbMean", 20), 4);
      return [f(v, "wetBulbMean", 20) + 11.5, wb + f(v, "approach", 3.5)];
    }
    if (oid === "O9") {
      const load = 100 * loadCurve(x) * (f(v, "loadVar", 60) / 100) + (1 - f(v, "loadVar", 60) / 100) * 70;
      const baseline = 5 + (100 - load) * 0.08;
      const optimized = f(v, "valveType", 0) ? 2 + (100 - load) * 0.02 : baseline;
      return [baseline, optimized];
    }
    if (oid === "O10") {
      const temp = oat(x, f(v, "oatMean", 18), 6);
      const active = temp < 21 && f(v, "dewPoint", 10) < 12;
      const demand = 100 * loadCurve(x);
      return [demand, active ? demand * 0.15 : demand];
    }
    if (oid === "O11") {
      const residual = f(v, "residual", 27);
      const low = f(v, "overnightLow", 16);
      if (x < 4) return [residual - 1, residual - 1];
      if (x < 7.5) {
        const pf = clamp((x - 4) / 2.5, 0, 1);
        return [residual, residual - pf * Math.max(0, residual - 2 - low)];
      }
      return [23, 23];
    }
    if (oid === "O12") {
      const occ = f(v, "peakOcc", 80) * occupancyCurve(x);
      return [100, clamp(30 + occ * 0.7, 30, 100)];
    }
    if (oid === "O13") {
      const density = f(v, "peakDensity", 55) * occupancyCurve(x);
      const speed = clamp(25 + density * 0.75, 25, 100);
      return [100, (speed / 100) ** 3 * 100];
    }
    if (oid === "O14") {
      const load = (f(v, "loadAmp", 75) / 100) * loadCurve(x);
      const speed = clamp(100 * ((40 + load * 60) / 95), 30, 100);
      return [100, (speed / 100) ** 3 * 100];
    }
    if (oid === "O15") return [95, clamp((oat(x, f(v, "ambientMean", 20), 6) - 2) * 2.8, 25, 100)];
    if (oid === "O16") {
      const load = (f(v, "loadAmp", 75) / 100) * loadCurve(x);
      return [100, clamp(100 * (1 - f(v, "idlePct", 20) / 100) * (0.4 + 0.6 * load), 20, 100)];
    }
    if (oid === "O17") return [100 + x * 1.6, 100 - (f(v, "coordScore", 55) / 100) * x * 3.2];
    if (oid === "O18") return [100 + x * 0.3, 100 - (f(v, "coverage", 50) / 100) * x * 0.9];
    if (oid === "O19") {
      const base = 100 + x * 1.2;
      return [base, base * (1 - clamp(f(v, "freq", 4) / 12, 0, 1))];
    }
    if (oid === "O20") {
      const baseline = clamp(100 - x * 4, 40, 100);
      const factor = f(v, "accessCtrl", 1) * 0.5 + clamp(f(v, "backupFreq", 4) / 12, 0, 1) * 0.5;
      return [baseline, clamp(100 - x * 4 * (1 - factor), 40, 100)];
    }
    return [100, 100];
  }

  function seriesFor(oid, sliders, xType) {
    const n = xType === "month" ? 12 : 24;
    const out = [];
    for (let x = 0; x < n; x++) {
      const [b, o] = pointAt(oid, x, sliders);
      out.push({ x, baseline: Math.round(b * 1000) / 1000, optimized: Math.round(o * 1000) / 1000 });
    }
    return out;
  }

  function metricsFor(oid, pts, v) {
    const ab = avg(pts.map((p) => p.baseline));
    const ao = avg(pts.map((p) => p.optimized));
    const last = pts[pts.length - 1] || { baseline: 0, optimized: 0 };
    if (oid === "O1") {
      const bh = pts.filter((p) => p.baseline > 0).length;
      const oh = pts.filter((p) => p.optimized > 0).length;
      const red = bh ? ((bh - oh) / bh) * 100 : 0;
      return [
        { label: "Baseline runtime", value: `${bh} h/day` },
        { label: "Optimized runtime", value: `${oh} h/day` },
        { label: "Operating hours cut", value: pct(red) },
      ];
    }
    if (oid === "O2") {
      const red = ab ? ((ab - ao) / ab) * 100 : 0;
      return [
        { label: "Baseline avg output", value: `${ab.toFixed(0)}%` },
        { label: "Optimized avg output", value: `${ao.toFixed(0)}%` },
        { label: "Est. HVAC energy cut", value: pct(red) },
      ];
    }
    if (oid === "O3") {
      const red = ab ? ((ab - ao) / ab) * 100 : 0;
      return [
        { label: "Baseline signal (high-select)", value: `${ab.toFixed(1)}°C` },
        { label: "Optimized signal (weighted)", value: `${ao.toFixed(1)}°C` },
        { label: "Over-cooling reduced", value: pct(red) },
      ];
    }
    if (oid === "O4") {
      const red = ab ? clamp(((ab - ao) / ab) * 100, 0, 10) : 0;
      return [
        { label: "Avg stages — baseline", value: ab.toFixed(1) },
        { label: "Avg stages — optimized", value: ao.toFixed(1) },
        { label: "Chiller-hours saved", value: pct(red) },
      ];
    }
    if (oid === "O5")
      return [
        { label: "Baseline fan power", value: "100%" },
        { label: "Optimized fan power", value: `${ao.toFixed(0)}%` },
        { label: "Fan energy saved", value: pct(clamp(100 - ao, 0, 30)) },
      ];
    if (oid === "O6")
      return [
        { label: "Baseline flow temp", value: "82°C" },
        { label: "Optimized avg flow temp", value: `${ao.toFixed(0)}°C` },
        { label: "Boiler efficiency gain", value: `${clamp((82 - ao) * 0.15, 0, 5).toFixed(1)}%` },
      ];
    if (oid === "O7") {
      const per = f(v, "compType", 0) ? 4.5 : 2.5;
      return [
        { label: "Baseline CHW temp", value: "6.5°C" },
        { label: "Optimized avg CHW temp", value: `${ao.toFixed(1)}°C` },
        { label: "Chiller energy saved", value: pct(clamp((ao - 6.5) * per, 0, 15)) },
      ];
    }
    if (oid === "O8") {
      const sav = clamp((ab - ao) * 2.5, 0, 15);
      return [
        { label: "Baseline CW temp", value: `${ab.toFixed(1)}°C` },
        { label: "Optimized avg CW temp", value: `${ao.toFixed(1)}°C` },
        { label: "Chiller energy saved", value: pct(sav) },
      ];
    }
    if (oid === "O9") {
      const sav = clamp((ab - ao) * 3, 0, 15);
      return [
        { label: "Baseline efficiency loss", value: `${ab.toFixed(1)}%` },
        { label: "Optimized efficiency loss", value: `${ao.toFixed(1)}%` },
        { label: "Compressor energy saved", value: pct(sav) },
      ];
    }
    if (oid === "O10") {
      const hours = pts.filter((p) => p.optimized < p.baseline * 0.9).length;
      const sav = ab ? clamp(((ab - ao) / ab) * 100, 0, 20) : 0;
      return [
        { label: "Economy cycle active", value: `${hours} h/day` },
        { label: "Optimized avg compressor load", value: `${ao.toFixed(0)}%` },
        { label: "Compressor energy saved", value: pct(sav) },
      ];
    }
    if (oid === "O11") {
      const window = pts.filter((p) => p.x >= 4 && p.x < 7.5);
      const minOpt = window.length ? Math.min(...window.map((p) => p.optimized)) : f(v, "residual", 27);
      const residual = f(v, "residual", 27);
      return [
        { label: "Residual temp", value: `${residual.toFixed(1)}°C` },
        { label: "Purged down to", value: `${minOpt.toFixed(1)}°C` },
        { label: "Start-up energy saved", value: pct(clamp((residual - minOpt) * 4, 0, 20)) },
      ];
    }
    if (oid === "O12") {
      const est = Math.round(400 + (f(v, "peakOcc", 80) / 100) * (f(v, "co2SP", 800) - 400));
      return [
        { label: "Optimized avg OA flow", value: `${ao.toFixed(0)}%` },
        { label: "Peak CO₂ estimate", value: `${est} ppm` },
        { label: "Ventilation energy saved", value: pct(clamp(100 - ao, 0, 20)) },
      ];
    }
    if (oid === "O13")
      return [
        { label: "Baseline fan power", value: "100%" },
        { label: "Optimized avg fan power", value: `${ao.toFixed(0)}%` },
        { label: "Fan energy saved", value: pct(clamp(100 - ao, 0, 80)) },
      ];
    if (oid === "O14")
      return [
        { label: "Baseline pump power", value: "100%" },
        { label: "Optimized avg pump power", value: `${ao.toFixed(0)}%` },
        { label: "Pumping energy saved", value: pct(clamp(100 - ao, 0, 30)) },
      ];
    if (oid === "O15") {
      const sav = ab ? clamp(((ab - ao) / ab) * 100, 0, 30) : 0;
      return [
        { label: "Baseline fan power", value: `${ab.toFixed(0)}%` },
        { label: "Optimized avg fan power", value: `${ao.toFixed(0)}%` },
        { label: "Condenser fan energy saved", value: pct(sav) },
      ];
    }
    if (oid === "O16")
      return [
        { label: "Baseline pump power", value: "100%" },
        { label: "Optimized avg pump power", value: `${ao.toFixed(0)}%` },
        { label: "CW pump energy saved", value: pct(clamp(100 - ao, 0, 30)) },
      ];
    if (oid === "O17") {
      const sav = last.baseline ? clamp(((last.baseline - last.optimized) / last.baseline) * 100, 0, 50) : 0;
      return [
        { label: "Year-end index — no plan", value: last.baseline.toFixed(0) },
        { label: "Year-end index — with plan", value: last.optimized.toFixed(0) },
        { label: "Total energy saved", value: pct(sav) },
      ];
    }
    if (oid === "O18") {
      const cov = f(v, "coverage", 50);
      const sav = last.baseline ? clamp(((last.baseline - last.optimized) / last.baseline) * 100, 0, 10) : 0;
      return [
        { label: "Total energy saved", value: pct(sav) },
        { label: "Est. NABERS star gain", value: `+${((cov / 100) * 0.5).toFixed(1)} ★` },
        { label: "Training coverage", value: `${cov.toFixed(0)}%` },
      ];
    }
    if (oid === "O19") {
      const sav = last.baseline ? clamp(((last.baseline - last.optimized) / last.baseline) * 100, 0, 20) : 0;
      return [
        { label: "Year-end index — reactive", value: last.baseline.toFixed(0) },
        { label: "Year-end index — maintained", value: last.optimized.toFixed(0) },
        { label: "HVAC energy saved", value: pct(sav) },
      ];
    }
    if (oid === "O20") {
      const sav = clamp((last.optimized - last.baseline) * 0.2, 0, 10);
      return [
        { label: "Settings retained — baseline", value: `${last.baseline.toFixed(0)}%` },
        { label: "Settings retained — managed", value: `${last.optimized.toFixed(0)}%` },
        { label: "HVAC energy saved", value: pct(sav) },
      ];
    }
    const sav = ab ? clamp(((ab - ao) / ab) * 100, 0, 80) : 0;
    return [
      { label: "Baseline avg", value: ab.toFixed(1) },
      { label: "Optimized avg", value: ao.toFixed(1) },
      { label: "Guide reduction", value: pct(sav) },
    ];
  }

  g.OehPhysics = { seriesFor, metricsFor, clamp };
})(window);
