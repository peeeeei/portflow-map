const PF_DATA = {};

const DEFAULT_STATE = {
  entity: "miritituba",
  entityType: "river_hub",
  corridor: "tapajos",
  product: "corn",
  timeRange: "2023-01:2024-12",
  mode: "descriptive"
};

const PAGE_LINKS = [
  ["System", "index.html"],
  ["Municipalities", "municipalities.html"],
  ["Water", "water.html"],
  ["Flows", "flows.html"],
  ["Prices", "prices.html"],
  ["Event", "event.html"]
];

function parseHash() {
  const raw = location.hash.replace(/^#/, "");
  const out = { ...DEFAULT_STATE };
  if (!raw) return out;
  for (const part of raw.split("&")) {
    const [k, v] = part.split("=");
    if (k && v !== undefined) out[decodeURIComponent(k)] = decodeURIComponent(v);
  }
  return out;
}

let PF_STATE = parseHash();
const PF_SUBS = [];

function stateHash(state) {
  return Object.entries(state)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");
}

function setState(patch) {
  PF_STATE = { ...PF_STATE, ...patch };
  if (patch.entity && !patch.entityType) {
    const ent = window.PF_ENTITIES_BY_ID && window.PF_ENTITIES_BY_ID[patch.entity];
    if (ent) {
      PF_STATE.entityType = ent.entity_type;
      PF_STATE.corridor = ent.corridor || PF_STATE.corridor;
    }
  }
  location.hash = stateHash(PF_STATE);
  PF_SUBS.forEach(fn => fn(PF_STATE));
  updateNavHashes();
}

function subscribeState(fn) {
  PF_SUBS.push(fn);
  fn(PF_STATE);
}

window.addEventListener("hashchange", () => {
  PF_STATE = parseHash();
  PF_SUBS.forEach(fn => fn(PF_STATE));
  updateNavHashes();
});

async function loadJSON(name) {
  if (PF_DATA[name]) return PF_DATA[name];
  const manifest = await loadManifest();
  if (manifest.files && !manifest.files[name] && !name.endsWith("manifest.json")) {
    console.warn(`Data file ${name} is not listed in manifest.json`);
  }
  const res = await fetch(`data/${name}`);
  if (!res.ok) throw new Error(`Failed to load data/${name}: ${res.status}`);
  PF_DATA[name] = await res.json();
  return PF_DATA[name];
}

async function loadManifest() {
  if (PF_DATA["manifest.json"]) return PF_DATA["manifest.json"];
  const res = await fetch("data/manifest.json");
  if (!res.ok) return { files: {} };
  PF_DATA["manifest.json"] = await res.json();
  return PF_DATA["manifest.json"];
}

function updateNavHashes() {
  document.querySelectorAll(".nav a[data-page-link]").forEach(a => {
    const base = a.getAttribute("data-page-link");
    a.href = `${base}#${stateHash(PF_STATE)}`;
  });
}

function shell(activeFile) {
  const active = activeFile || (location.pathname.split("/").pop() || "index.html");
  const nav = document.createElement("header");
  nav.className = "nav";
  nav.innerHTML = `
    <div class="brand">Brazil Portflow</div>
    <nav>${PAGE_LINKS.map(([label, href]) =>
      `<a data-page-link="${href}" class="${href === active ? "active" : ""}" href="${href}">${label}</a>`
    ).join("")}</nav>
    <div class="nav-controls">
      <div class="product-picker" role="group" aria-label="Product">
        <span>Product</span>
        <button type="button" data-product="corn">Corn</button>
        <button type="button" data-product="soy">Soy</button>
        <button type="button" data-product="all">All</button>
        <button type="button" data-product="coffee">Coffee</button>
      </div>
      <label>Window <input id="timeRangeInput" value="${PF_STATE.timeRange}" /></label>
    </div>`;
  document.body.prepend(nav);
  const productButtons = [...document.querySelectorAll("[data-product]")];
  productButtons.forEach(btn => {
    btn.addEventListener("click", () => setState({ product: btn.dataset.product }));
  });
  const time = document.getElementById("timeRangeInput");
  time.addEventListener("change", e => setState({ timeRange: e.target.value || DEFAULT_STATE.timeRange }));
  subscribeState(s => {
    productButtons.forEach(btn => btn.classList.toggle("active", btn.dataset.product === (s.product || DEFAULT_STATE.product)));
    time.value = s.timeRange || DEFAULT_STATE.timeRange;
  });
  updateNavHashes();
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

function fmtNum(value, digits = 0) {
  if (value === null || value === undefined || value === "") return "no data";
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return n.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function entityLabel(entity) {
  if (!entity) return "No entity selected";
  return entity.name_pt && entity.label_en !== entity.name_pt
    ? `${entity.label_en} (${entity.name_pt})`
    : entity.label_en;
}

function initEntities(entities) {
  window.PF_ENTITIES = entities;
  window.PF_ENTITIES_BY_ID = Object.fromEntries(entities.map(e => [e.id, e]));
}

function selectedEntity() {
  return window.PF_ENTITIES_BY_ID && window.PF_ENTITIES_BY_ID[PF_STATE.entity];
}

function hasLinkedWater(entity) {
  return Boolean(entity && entity.has_water && entity.water_station_id);
}

function renderSelectionCard(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  subscribeState(state => {
    const ent = window.PF_ENTITIES_BY_ID && window.PF_ENTITIES_BY_ID[state.entity];
    if (!ent) {
      el.innerHTML = `<div class="eyebrow">Selection</div><h2>No entity selected</h2>`;
      return;
    }
    el.innerHTML = `
      <div class="eyebrow">${escapeHTML(ent.entity_type.replaceAll("_", " "))} / ${escapeHTML(ent.corridor)}</div>
      <h2>${escapeHTML(entityLabel(ent))}</h2>
      <p>${escapeHTML(ent.description_en || "")}</p>
      <div class="pill-row">
        <span>${hasLinkedWater(ent) ? `water station ${escapeHTML(ent.water_station_id)}` : "no linked gauge"}</span>
        <span>${ent.has_flow ? "flow data" : "limited flow"}</span>
        <span>${ent.has_price_link ? "price link" : "no price link"}</span>
      </div>
      <p class="caveat">${escapeHTML(ent.caveats || "Descriptive view only.")}</p>`;
  });
}

function makeChart(id, option) {
  const el = document.getElementById(id);
  if (!el) return null;
  const chart = echarts.init(el);
  chart.setOption({
    animation: false,
    tooltip: { trigger: "axis" },
    grid: { left: 54, right: 24, top: 34, bottom: 42 },
    ...option
  });
  window.addEventListener("resize", () => chart.resize());
  return chart;
}

function makeTable(id, columns, rows, rowIdField) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `
    <table>
      <thead><tr>${columns.map(c => `<th>${escapeHTML(c.label)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map(r => {
        const rowId = rowIdField ? ` data-row-id="${escapeHTML(r[rowIdField])}"` : "";
        return `<tr${rowId}>${columns.map(c => {
          const cls = c.numeric ? " class=\"num\"" : "";
          const val = c.format ? c.format(r[c.key], r) : r[c.key];
          return `<td${cls}>${escapeHTML(val ?? "")}</td>`;
        }).join("")}</tr>`;
      }).join("")}</tbody>
    </table>`;
}

function downloadCSV(rows, filename) {
  if (!rows || !rows.length) return;
  const keys = Object.keys(rows[0]);
  const csv = [keys.join(","), ...rows.map(r => keys.map(k => JSON.stringify(r[k] ?? "")).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function bindCSVButton(buttonId, rowsGetter, filename) {
  const btn = document.getElementById(buttonId);
  if (!btn) return;
  btn.addEventListener("click", () => downloadCSV(rowsGetter(), filename));
}

function renderCoverage(id, manifest, files) {
  const el = document.getElementById(id);
  if (!el) return;
  const lines = files.map(f => {
    const m = manifest.files && manifest.files[f];
    if (!m) return `${f}: not listed in manifest`;
    return `${f}: ${fmtNum(m.rows)} rows, ${m.date_start || "n/a"} to ${m.date_end || "n/a"}. ${m.caveats || ""}`;
  });
  el.innerHTML = lines.map(x => `<div>${escapeHTML(x)}</div>`).join("");
}

function corridorColor(corridor) {
  return {
    north: "#1f77b4",
    amazon: "#1f77b4",
    madeira: "#009E73",
    tapajos: "#7B61FF",
    south: "#D55E00",
    paraguay: "#8B5A2B",
    other: "#777777"
  }[corridor] || "#777777";
}

function statusRing(entity) {
  if (!hasLinkedWater(entity)) return "#9aa0a6";
  if (entity.water_status === "official") return "#c62828";
  if (entity.water_status === "p10") return "#f4a261";
  return "#2a9d8f";
}

function addLegend(map) {
  const legend = L.control({ position: "bottomleft" });
  legend.onAdd = function() {
    const div = L.DomUtil.create("div", "legend");
    div.innerHTML = `
      <div><i style="background:${corridorColor("north")}"></i>North / Amazon</div>
      <div><i style="background:${corridorColor("tapajos")}"></i>Tapajos</div>
      <div><i style="background:${corridorColor("madeira")}"></i>Madeira</div>
      <div><i style="background:${corridorColor("south")}"></i>South</div>
      <div><i style="background:${corridorColor("paraguay")}"></i>Paraguay</div>`;
    return div;
  };
  legend.addTo(map);
}

function entityMarker(entity) {
  const radius = entity.entity_type === "producing_region" ? 6
    : entity.entity_type === "rail_or_road_node" ? 6
    : entity.entity_type === "river_hub" ? 9
    : 8;
  return L.circleMarker([entity.lat, entity.lon], {
    radius,
    color: statusRing(entity),
    weight: hasLinkedWater(entity) ? 3 : 1.5,
    fillColor: corridorColor(entity.corridor),
    fillOpacity: entity.entity_type === "rail_or_road_node" ? 0.55 : 0.82
  });
}

function initMap(id, entities, routes, options = {}) {
  const map = L.map(id, { zoomControl: true, preferCanvas: true }).setView(options.center || [-12.5, -55.5], options.zoom || 4);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 9,
    attribution: "&copy; OpenStreetMap"
  }).addTo(map);
  const routeLayer = L.layerGroup().addTo(map);
  (routes || []).forEach(r => {
    const line = L.polyline(r.coords, {
      color: corridorColor(r.corridor),
      weight: r.leg_type === "barge" ? 5 : 3,
      opacity: 0.68,
      dashArray: r.leg_type === "rail" ? "7 5" : r.leg_type === "truck" ? "3 5" : null
    }).addTo(routeLayer);
    line.bindTooltip(`<b>${escapeHTML(r.name)}</b><br>${escapeHTML(r.leg_type)} leg, ${fmtNum(r.distance_km)} km<br>${escapeHTML(r.description)}`);
    line.on("click", () => setState({ corridor: r.corridor }));
  });
  const markers = {};
  entities.forEach(e => {
    const marker = entityMarker(e).addTo(map);
    markers[e.id] = marker;
    marker.bindTooltip(`<b>${escapeHTML(entityLabel(e))}</b><br>${escapeHTML(e.role)}<br>${hasLinkedWater(e) ? `Gauge ${escapeHTML(e.water_station_id)}` : "No linked gauge"} / ${e.has_flow ? "flow data" : "limited flow"}`);
    marker.on("click", () => setState({ entity: e.id, entityType: e.entity_type, corridor: e.corridor }));
  });
  addLegend(map);
  subscribeState(s => {
    Object.entries(markers).forEach(([id, m]) => {
      const e = window.PF_ENTITIES_BY_ID[id];
      m.setStyle({
        fillOpacity: id === s.entity ? 1 : 0.35,
        opacity: id === s.entity ? 1 : 0.65,
        radius: id === s.entity ? 12 : (e.entity_type === "river_hub" ? 9 : 7),
        weight: id === s.entity ? 4 : hasLinkedWater(e) ? 3 : 1.5
      });
    });
    const selected = markers[s.entity];
    if (selected && options.panOnSelect) map.panTo(selected.getLatLng());
  });
  return { map, markers, routeLayer };
}

async function bootstrap(activeFile) {
  shell(activeFile);
  const [entities, manifest] = await Promise.all([loadJSON("entities.json"), loadManifest()]);
  initEntities(entities);
  return { entities, manifest };
}
