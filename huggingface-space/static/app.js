const CATS = {
  scheduling: { label: "Scheduling", color: "#F0A93A" },
  "plant-control": { label: "Plant Control", color: "#4FD1C5" },
  ventilation: { label: "Ventilation", color: "#5B9BD5" },
  "variable-speed": { label: "Variable Speed", color: "#9C7BDB" },
  operations: { label: "Operations", color: "#6FCF97" },
};
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const GROUPS = [
  ["scheduling", "Scheduling"],
  ["plant-control", "Plant Control"],
  ["ventilation", "Ventilation"],
  ["variable-speed", "Variable Speed"],
  ["operations", "Operations"],
];

let catalog = [];
let byId = {};
let tab = "ops";
let included = false;
let achieved = 70;
let annualCost = 250000;
let sliders = {};
let checks = {};
let openGroups = { scheduling: true, "plant-control": false, ventilation: false, "variable-speed": false, operations: false };

function route() {
  const raw = (location.hash || "#/overview").replace(/^#\/?/, "");
  const id = raw.split("?")[0].toUpperCase();
  if (raw.includes("view=guide")) tab = "guide";
  if (/^O\d+$/.test(id) && byId[id]) return { page: "opp", id };
  return { page: "overview" };
}

function go(path) {
  location.hash = path;
}

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function navItem(href, label, active, oid) {
  return `<a class="nav-item ${active ? "active" : ""}" href="${href}">${
    oid ? `<span class="nav-oid">${esc(oid)}</span>` : ""
  }<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(label)}</span></a>`;
}

function renderSidebar(current) {
  const r = route();
  let html = `<div class="nav-sec">Platform</div>${navItem("#/overview", "Fleet Overview", r.page === "overview")}`;
  html += `<div class="nav-sec">Opportunities</div>`;
  GROUPS.forEach(([sec, title]) => {
    const color = CATS[sec].color;
    const items = catalog.filter((o) => o.section === sec);
    const expanded = openGroups[sec] || items.some((o) => r.id === o.opportunity_id);
    html += `<div>
      <button class="group-btn" data-group="${sec}"><span style="color:${color}">▸</span> <span>${title}</span></button>
      <div class="group-body" style="display:${expanded ? "block" : "none"}">`;
    items.forEach((o) => {
      html += navItem(`#/${o.opportunity_id}`, o.title, r.id === o.opportunity_id, o.opportunity_id);
    });
    html += `</div></div>`;
  });
  document.getElementById("sidebar").innerHTML = html;
  document.querySelectorAll("[data-group]").forEach((btn) => {
    btn.onclick = () => {
      const g = btn.dataset.group;
      openGroups[g] = !openGroups[g];
      renderSidebar();
    };
  });
}

function drawChart(canvas, pts, color, xType) {
  if (!canvas || !pts.length) return;
  const ctx = canvas.getContext("2d");
  const w = (canvas.width = canvas.clientWidth * 2);
  const h = (canvas.height = canvas.clientHeight * 2);
  ctx.clearRect(0, 0, w, h);
  const ys = pts.flatMap((p) => [p.baseline, p.optimized]);
  const ymin = Math.min(...ys);
  const ymax = Math.max(...ys);
  const span = ymax - ymin || 1;
  const xOf = (i) => (i / Math.max(pts.length - 1, 1)) * w;
  const yOf = (v) => h - ((v - ymin) / span) * (h - 24) - 12;
  ctx.strokeStyle = "rgba(255,255,255,0.06)";
  ctx.lineWidth = 2;
  for (let i = 1; i < 4; i++) {
    ctx.beginPath();
    ctx.moveTo(0, (h / 4) * i);
    ctx.lineTo(w, (h / 4) * i);
    ctx.stroke();
  }
  const line = (key, stroke, dash) => {
    ctx.beginPath();
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 4;
    ctx.setLineDash(dash || []);
    pts.forEach((p, i) => {
      const x = xOf(i);
      const y = yOf(p[key]);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  };
  line("baseline", "#64748b", [10, 8]);
  line("optimized", color);
}

function sliderDefaults(item) {
  const v = {};
  (item.sliders || []).forEach((s) => {
    v[s.key] = sliders[s.key] ?? s.default;
  });
  return v;
}

function fmtSlider(v, unit, step) {
  const d = step < 1 ? 2 : 0;
  return `${Number(v).toFixed(d)}${unit ? ` ${unit}` : ""}`;
}

function renderOverview() {
  tab = "ops";
  const sections = GROUPS.map(([sec, title]) => {
    const cards = catalog
      .filter((o) => o.section === sec)
      .map(
        (o) => `<a class="glass-card" href="#/${o.opportunity_id}">
        <div>
          <div style="display:flex;justify-content:space-between;gap:8px">
            <span class="mono" style="font-size:10px;padding:2px 6px;border-radius:6px;border:1px solid rgba(34,211,238,0.25);background:rgba(6,182,212,0.1);color:#67e8f9">${esc(o.opportunity_id)}</span>
            <span class="badge badge-warn">AWAITING TELEMETRY</span>
          </div>
          <h3 style="font-size:15px;margin:12px 0 0;font-weight:600">${esc(o.title)}</h3>
        </div>
        <div class="muted" style="font-size:11px;margin-top:12px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.06)">
          GUIDE_POTENTIAL ${esc(String(o.pct))}% · ${esc(o.control_kind || "control")}
        </div>
      </a>`
      )
      .join("");
    return `<section style="margin-bottom:28px">
      <h2 class="muted" style="font-size:11px;letter-spacing:0.16em;text-transform:uppercase;margin:0 0 10px">${esc(title)}</h2>
      <div class="kpi-grid">${cards}</div>
    </section>`;
  }).join("");
  document.getElementById("root").innerHTML = `
    <div style="margin-bottom:20px">
      <div class="muted" style="font-size:10px;letter-spacing:0.18em;text-transform:uppercase">Fleet</div>
      <h1 style="margin:6px 0 0;font-size:1.55rem">Overview</h1>
      <p class="muted" style="max-width:42rem">Same Control Center as the product: O1–O20, Operations vs OEH guide. This Space has no live BMS — telemetry stays AWAITING / SIMULATED. Guide % is GUIDE_POTENTIAL, not measured kWh.</p>
    </div>${sections}`;
}

function renderGuide(item) {
  const cat = CATS[item.section] || CATS.scheduling;
  const v = sliderDefaults(item);
  const pts = window.OehPhysics.seriesFor(item.opportunity_id, v, item.x_type);
  const metrics = window.OehPhysics.metricsFor(item.opportunity_id, pts, v);
  const effectivePct = included ? (item.pct * achieved) / 100 : 0;
  const dollars = annualCost * (effectivePct / 100);
  const optWidth = included ? Math.max(100 - effectivePct, 4) : 100;
  const circ = 2 * Math.PI * 32;
  const dash = (item.pct / 100) * circ;
  const equip = String(item.equipment || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const sliderHtml = (item.sliders || [])
    .map(
      (sl) => `<label>
        <span class="mono muted" style="font-size:11px">${esc(sl.label)}</span>
        <div style="display:flex;align-items:center;gap:8px;margin-top:4px">
          <input type="range" data-key="${esc(sl.key)}" min="${sl.min}" max="${sl.max}" step="${sl.step}" value="${v[sl.key]}" style="accent-color:${cat.color};flex:1" />
          <span class="mono" style="width:4.5rem;text-align:right;font-size:11px;color:${cat.color}">${fmtSlider(v[sl.key], sl.unit, sl.step)}</span>
        </div>
      </label>`
    )
    .join("");
  return `
    <div class="kpi-tile" style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap">
      <div>
        <div class="mono" style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:${cat.color}">OEH guide ${esc(item.opportunity_id)} · SIMULATED — not live BMS · agent read-only</div>
        <p style="color:#cbd5e1;max-width:42rem">${esc(item.summary)}</p>
      </div>
      <div style="display:flex;align-items:center;gap:16px">
        <button type="button" id="include-btn" style="background:none;border:0;cursor:pointer;text-align:center">
          <div class="mono muted" style="font-size:9px;text-transform:uppercase">Include in savings estimate</div>
          <div style="width:3.5rem;height:1.75rem;border-radius:999px;border:1px solid ${included ? "#34d399" : "rgba(255,255,255,0.2)"};background:${included ? "rgba(16,185,129,0.2)" : "rgba(255,255,255,0.05)"};position:relative;margin:6px auto">
            <span style="position:absolute;top:2px;width:1.25rem;height:1.25rem;border-radius:999px;background:${included ? "#34d399" : "#64748b"};left:${included ? "1.95rem" : "2px"}"></span>
          </div>
          <div class="mono" style="font-size:9px;color:${included ? "#6ee7b7" : "#64748b"}">${included ? "INCLUDED" : "NOT INCLUDED"}</div>
        </button>
        <div style="position:relative;width:76px;height:76px">
          <svg width="76" height="76" viewBox="0 0 76 76" style="transform:rotate(-90deg)">
            <circle cx="38" cy="38" r="32" stroke="rgba(255,255,255,0.08)" stroke-width="6" fill="none"></circle>
            <circle cx="38" cy="38" r="32" stroke="${cat.color}" stroke-width="6" fill="none" stroke-linecap="round" stroke-dasharray="${circ}" stroke-dashoffset="${circ - dash}"></circle>
          </svg>
          <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center" class="mono">
            <strong>${item.pct}%</strong>
            <span class="muted" style="font-size:8px;text-transform:uppercase">OEH potential</span>
          </div>
        </div>
      </div>
    </div>
    <div class="kpi-tile" style="margin-top:12px">
      <div class="mono muted" style="font-size:10px;text-transform:uppercase;margin-bottom:8px">Guide comparison (simulated) — ${esc(item.scope)}</div>
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px"><span class="mono muted" style="width:6rem;font-size:11px">Baseline</span><div style="flex:1;height:20px;border-radius:4px;background:rgba(255,255,255,0.06)"><div style="height:100%;width:100%;background:#64748b"></div></div><span class="mono" style="width:2.5rem;text-align:right;font-size:11px">100%</span></div>
      <div style="display:flex;align-items:center;gap:12px"><span class="mono muted" style="width:6rem;font-size:11px">Optimized</span><div style="flex:1;height:20px;border-radius:4px;background:rgba(255,255,255,0.06)"><div style="height:100%;width:${optWidth}%;background:${cat.color}"></div></div><span class="mono" style="width:2.5rem;text-align:right;font-size:11px;color:${cat.color}">${optWidth.toFixed(0)}%</span></div>
    </div>
    <div class="kpi-tile" style="margin-top:12px">
      <div class="mono muted" style="font-size:10px;text-transform:uppercase;margin-bottom:12px">Simulation console — ${esc(item.sim_label)}</div>
      <div class="slider-row" id="guide-sliders">${sliderHtml}</div>
      <div class="chart-wrap" style="margin-top:12px"><canvas id="guide-chart"></canvas></div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding-top:12px;margin-top:8px;border-top:1px solid rgba(255,255,255,0.06)">
        ${metrics.map((m) => `<div><div class="mono" style="font-size:18px;font-weight:700;color:${cat.color}">${esc(m.value)}</div><div class="mono muted" style="font-size:9px;text-transform:uppercase;margin-top:4px">${esc(m.label)}</div></div>`).join("")}
      </div>
    </div>
    <div class="kpi-tile" style="margin-top:12px">
      <div class="mono muted" style="font-size:10px;text-transform:uppercase;margin-bottom:8px">Savings Calculator</div>
      <p class="muted" style="font-size:11px">Not verified M&amp;V. Not a BMS result. Assumed spend only.</p>
      <div class="slider-row">
        <label><span class="mono muted" style="font-size:11px">Assumed annual ${esc(item.scope)} spend (USD)</span>
          <div style="margin-top:6px;display:flex;align-items:center;gap:4px;border:1px solid rgba(255,255,255,0.1);border-radius:6px;padding:0 8px;background:rgba(0,0,0,0.2)">
            <span class="muted">$</span>
            <input id="annual" type="number" min="0" step="1000" value="${annualCost}" style="width:100%;background:transparent;border:0;padding:8px;outline:none" class="mono" />
          </div>
        </label>
        <label><span class="mono muted" style="font-size:11px">Assumed achievement (% of OEH max ${item.pct}%)</span>
          <div style="display:flex;align-items:center;gap:8px;margin-top:10px">
            <input id="achieved" type="range" min="0" max="100" value="${achieved}" style="flex:1;accent-color:${cat.color}" />
            <span class="mono" style="color:${cat.color};width:2.5rem;text-align:right">${achieved}%</span>
          </div>
        </label>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.06)">
        <div><div class="mono" style="font-size:18px;font-weight:700;${included ? `color:${cat.color}` : "color:#475569"}">${effectivePct.toFixed(1)}%</div><div class="mono muted" style="font-size:9px;text-transform:uppercase;margin-top:4px">Effective saving</div></div>
        <div><div class="mono" style="font-size:18px;font-weight:700;${included ? `color:${cat.color}` : "color:#475569"}">$${Math.round(dollars).toLocaleString()}</div><div class="mono muted" style="font-size:9px;text-transform:uppercase;margin-top:4px">Estimated $ / year</div></div>
        <div><div class="mono" style="font-size:18px;font-weight:700;${included ? `color:${cat.color}` : "color:#475569"}">$${Math.round(dollars * 5).toLocaleString()}</div><div class="mono muted" style="font-size:9px;text-transform:uppercase;margin-top:4px">Projected / 5 years</div></div>
      </div>
    </div>
    ${item.scenario ? `<div class="kpi-tile" style="margin-top:12px;background:${cat.color}26;border-color:${cat.color}"><div class="mono" style="font-size:10px;text-transform:uppercase;color:${cat.color};margin-bottom:6px">Field result · OEH example (not this building)</div><p style="margin:0">${esc(item.scenario)}</p></div>` : ""}
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px">
      <div class="kpi-tile"><div class="mono muted" style="font-size:10px;text-transform:uppercase;margin-bottom:8px">Control Principle</div><p style="margin:0;color:#cbd5e1">${esc(item.principle)}</p></div>
      <div class="kpi-tile"><div class="mono muted" style="font-size:10px;text-transform:uppercase;margin-bottom:8px">Typical current practice</div><p style="margin:0;color:#cbd5e1">${esc(item.practice)}</p></div>
      <div class="kpi-tile"><div class="mono muted" style="font-size:10px;text-transform:uppercase;margin-bottom:8px">Recommended action</div><p style="margin:0;color:#cbd5e1">${esc(item.recommendation)}</p></div>
    </div>
    <div class="kpi-tile" style="margin-top:12px">
      <div class="mono muted" style="font-size:10px;text-transform:uppercase;margin-bottom:8px">Commissioning checklist — minimum equipment</div>
      <ul style="display:grid;grid-template-columns:1fr 1fr;gap:8px;list-style:none;padding:0;margin:0">
        ${equip
          .map(
            (eq, i) => `<li><button type="button" class="check-eq" data-i="${i}" style="background:none;border:0;display:flex;gap:8px;text-align:left;cursor:pointer;color:#cbd5e1">
              <span style="width:16px;height:16px;border-radius:4px;border:1px solid ${checks[i] ? cat.color : "rgba(255,255,255,0.2)"};background:${checks[i] ? cat.color : "transparent"};flex-shrink:0;margin-top:2px"></span>
              <span style="${checks[i] ? "text-decoration:line-through;color:#64748b" : ""}">${esc(eq)}</span>
            </button></li>`
          )
          .join("")}
      </ul>
    </div>
    <div style="display:flex;gap:8px;margin-top:12px">
      ${item.prev_id ? `<a class="btn-secondary mono" style="flex:1;font-size:11px" href="#/${item.prev_id}">← ${esc(item.prev_id)}</a>` : `<div style="flex:1"></div>`}
      ${item.next_id ? `<a class="btn-secondary mono" style="flex:1;font-size:11px" href="#/${item.next_id}">${esc(item.next_id)} →</a>` : ""}
    </div>`;
}

function bindGuide(item) {
  const cat = CATS[item.section] || CATS.scheduling;
  const canvas = document.getElementById("guide-chart");
  const v = sliderDefaults(item);
  drawChart(canvas, window.OehPhysics.seriesFor(item.opportunity_id, v, item.x_type), cat.color, item.x_type);
  document.getElementById("include-btn")?.addEventListener("click", () => {
    included = !included;
    render();
  });
  document.getElementById("annual")?.addEventListener("change", (e) => {
    annualCost = Number(e.target.value) || 0;
    render();
  });
  document.getElementById("achieved")?.addEventListener("input", (e) => {
    achieved = Number(e.target.value);
    render();
  });
  document.querySelectorAll("#guide-sliders input").forEach((input) => {
    input.addEventListener("input", () => {
      sliders[input.dataset.key] = Number(input.value);
      render();
    });
  });
  document.querySelectorAll(".check-eq").forEach((btn) => {
    btn.addEventListener("click", () => {
      const i = Number(btn.dataset.i);
      checks[i] = !checks[i];
      render();
    });
  });
}

function renderOps(item) {
  const inputs = (item.required_inputs || []).map((x) => `<li>${esc(x)}</li>`).join("");
  const risks = (item.risks || []).map((x) => `<li>${esc(x)}</li>`).join("");
  return `
    <div class="kpi-tile" style="border-color:rgba(251,191,36,0.25)">
      <div class="badge badge-warn">AWAITING TELEMETRY</div>
      <p style="margin:10px 0 0;color:#cbd5e1">No live BMS in this Space. Operations KPIs stay empty on purpose — same contract as the product (NO LIVE DATA / AWAITING TELEMETRY). Open <strong>OEH guide</strong> for the teaching simulation used in the app.</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px">
      <div class="kpi-tile"><div class="mono muted" style="font-size:10px;text-transform:uppercase">Telemetry</div><strong>NO DATA</strong></div>
      <div class="kpi-tile"><div class="mono muted" style="font-size:10px;text-transform:uppercase">ML</div><strong>NO DATA</strong></div>
      <div class="kpi-tile"><div class="mono muted" style="font-size:10px;text-transform:uppercase">BMS</div><strong>OFFLINE</strong></div>
      <div class="kpi-tile"><div class="mono muted" style="font-size:10px;text-transform:uppercase">Dispatch</div><strong>WRITE OFF</strong></div>
    </div>
    <div class="kpi-tile" style="margin-top:12px">
      <div class="mono muted" style="font-size:10px;text-transform:uppercase;margin-bottom:8px">Recommended control logic</div>
      <p style="margin:0;color:#cbd5e1">${esc(item.recommended_control_logic || item.principle)}</p>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
      <div class="kpi-tile"><div class="mono muted" style="font-size:10px;text-transform:uppercase;margin-bottom:8px">Required inputs</div><ul class="muted">${inputs}</ul></div>
      <div class="kpi-tile"><div class="mono muted" style="font-size:10px;text-transform:uppercase;margin-bottom:8px">Risks</div><ul class="muted">${risks}</ul></div>
    </div>`;
}

function renderOpportunity(item) {
  const cat = CATS[item.section] || CATS.scheduling;
  const kind = item.control_kind === "advisory" ? "Advisory — no automatic plant write" : "Supervisory control (simulation)";
  document.getElementById("root").innerHTML = `
    <div class="workspace" style="border-top:3px solid ${cat.color}">
      <div style="padding:20px 20px 12px">
        <div class="muted" style="font-size:11px">${esc(CATS[item.section]?.label || item.section)} / ${esc(item.opportunity_id)}</div>
        <div class="mono" style="font-size:10px;letter-spacing:0.18em;color:#22d3ee;margin-top:8px">${esc(item.opportunity_id)}</div>
        <h1 style="margin:6px 0 0;font-size:1.55rem;font-weight:600">${esc(item.title)}</h1>
        <p class="muted" style="max-width:42rem">${esc(item.summary)}</p>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:12px">
          <span class="badge badge-warn">Telemetry NO DATA</span>
          <span class="badge badge-muted">ML NO DATA</span>
          <span class="badge badge-danger">BMS OFFLINE</span>
          <span class="badge badge-muted">${esc(kind)}</span>
        </div>
      </div>
      <div style="display:flex;gap:4px;padding:0 20px 16px" role="tablist">
        <button class="tab-btn" data-tab="ops" ${tab === "ops" ? `style="border-color:${cat.color};color:${cat.color};background:${cat.color}18"` : ""}>Operations</button>
        <button class="tab-btn" data-tab="guide" ${tab === "guide" ? `style="border-color:${cat.color};color:${cat.color};background:${cat.color}18"` : ""}>OEH guide</button>
      </div>
    </div>
    <div id="studio" style="margin-top:16px">${tab === "guide" ? renderGuide(item) : renderOps(item)}</div>`;
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.onclick = () => {
      tab = btn.dataset.tab;
      if (tab === "guide") {
        sliders = {};
        checks = {};
      }
      render();
    };
  });
  if (tab === "guide") bindGuide(item);
}

function render() {
  renderSidebar();
  const r = route();
  if (r.page === "opp") renderOpportunity(byId[r.id]);
  else renderOverview();
}

fetch("catalog.json")
  .then((r) => r.json())
  .then((data) => {
    catalog = data;
    byId = Object.fromEntries(data.map((o) => [o.opportunity_id, o]));
    let lastId = null;
    window.addEventListener("hashchange", () => {
      const r = route();
      if (r.id !== lastId) {
        sliders = {};
        checks = {};
        lastId = r.id || null;
      }
      render();
    });
    render();
  })
  .catch(() => {
    document.getElementById("root").textContent = "Could not load catalog.json";
  });
