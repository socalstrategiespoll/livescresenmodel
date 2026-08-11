const API_BASE = "https://sc-senate-gop-primary-model.onrender.com";
const REFRESH_MS = 20000;

const CANDIDATES = ["graham", "norman", "fry", "sanford", "lynch", "other"];
const LABELS = { graham: "Graham", norman: "Norman", fry: "Fry", sanford: "Sanford", lynch: "Lynch", other: "Other" };
const COLOR = (c) => getComputedStyle(document.documentElement).getPropertyValue("--" + c).trim();

let geoCache = null;
let latest = null;

function fmtPct(v) { return v === null || v === undefined ? "—" : v.toFixed(1) + "%"; }
function fmtInt(v) { return v === null || v === undefined ? "—" : Math.round(v).toLocaleString(); }

function fmtProb(v, pctIn) {
  // Pre-election (no votes counted yet), never show a bare 100%/0% -- the
  // simulation's shrinkage means those are the pre-election baseline
  // ceiling/floor, not a certainty. Once real votes start coming in, show
  // the simulated number as-is.
  if (v === null || v === undefined) return "—";
  if (!pctIn || pctIn <= 0) {
    if (v >= 99.95) return ">99%";
    if (v <= 0.05) return "<0.1%";
  }
  return v.toFixed(1) + "%";
}

async function fetchJSON(path) {
  const res = await fetch(API_BASE + path, { cache: "no-store" });
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

function setPulse(state, stamp) {
  const el = document.getElementById("pulse");
  el.dataset.state = state;
  document.getElementById("pulse-label").textContent =
    state === "live" ? "live" : state === "stale" ? "reconnecting" : "connecting";
  if (stamp) document.getElementById("stamp").textContent = new Date(stamp).toLocaleTimeString();
}

function renderVerdict(data) {
  const p = data.projection;
  const leadEl = document.getElementById("lead-name");
  leadEl.textContent = LABELS[p.leader];
  leadEl.className = "verdict-name cand-" + p.leader;
  const marginEl = document.getElementById("lead-margin");
  marginEl.textContent = "+" + p.lead_margin.toFixed(1);
  marginEl.className = "verdict-number cand-" + p.leader;

  const sub = document.getElementById("verdict-sub");
  const pctIn = data.counted.pct_of_projected_turnout;
  sub.textContent = pctIn > 0
    ? pctIn.toFixed(1) + "% of projected vote counted"
    : "Pre-election baseline — no votes counted yet";

  document.getElementById("p-runoff").textContent = fmtProb(data.runoff.p_runoff, pctIn);
}

function renderAdvanceBars(data) {
  const container = document.getElementById("advance-bars");
  container.innerHTML = "";
  const pctIn = data.counted.pct_of_projected_turnout;
  const order = [...CANDIDATES].sort((a, b) => data.runoff.advance[b] - data.runoff.advance[a]);
  order.forEach((c) => {
    const row = document.createElement("div");
    row.className = "adv-row";
    const pct = data.runoff.advance[c];
    row.innerHTML =
      '<span class="adv-name cand-' + c + '">' + LABELS[c] + '</span>' +
      '<span class="adv-track"><span class="adv-fill cand-' + c + '-bg" style="width:' + pct.toFixed(1) + '%"></span></span>' +
      '<span class="adv-pct">' + fmtProb(pct, pctIn) + '</span>';
    container.appendChild(row);
  });
}

function renderCandidateStats(data) {
  const r = data.runoff;
  CANDIDATES.forEach((c) => {
    document.getElementById("pct-" + c).textContent = fmtPct(data.projection.pct[c]);
    document.getElementById("votes-" + c).textContent = fmtInt(data.projection.votes[c]) + " votes";
    const p50 = r.p50 ? r.p50[c] : null;
    const p90 = r.p90 ? r.p90[c] : null;
    document.getElementById("pctl-" + c).textContent =
      p50 != null && p90 != null
        ? "50th " + p50.toFixed(1) + "% · 90th " + p90.toFixed(1) + "%"
        : "—";
  });
}

function renderTurnout(data) {
  document.getElementById("counted").textContent = fmtInt(
    Object.values(data.counted.votes || {}).reduce((a, b) => a + b, 0));
  document.getElementById("precincts").textContent =
    data.counted.pct_precincts_reporting != null ? data.counted.pct_precincts_reporting.toFixed(1) + "%" : "—";
  document.getElementById("turnout").textContent = fmtInt(data.turnout.projected);
}

function renderTally(data) {
  const bar = document.getElementById("tally-bar");
  bar.innerHTML = "";
  CANDIDATES.forEach((c) => {
    const seg = document.createElement("span");
    seg.className = "tally-seg cand-" + c + "-bg";
    seg.style.width = data.projection.pct[c] + "%";
    bar.appendChild(seg);
  });
}

function renderCountyTable(data) {
  const tbody = document.getElementById("county-rows");
  const reporting = data.counties.filter((r) => r.reporting);
  if (reporting.length === 0) {
    tbody.innerHTML = '<tr class="empty"><td colspan="8">No counties reporting yet.</td></tr>';
    return;
  }
  tbody.innerHTML = "";
  reporting.forEach((r) => {
    const leader = CANDIDATES.reduce((a, b) => (r.pct[b] || 0) > (r.pct[a] || 0) ? b : a);
    const tr = document.createElement("tr");
    tr.innerHTML =
      '<td class="name">' + r.county + '</td>' +
      '<td class="num">' + r.pct_of_projected.toFixed(0) + '%</td>' +
      CANDIDATES.slice(0, 5).map((c) => '<td class="num">' + (r.pct[c] != null ? r.pct[c].toFixed(1) : "—") + '</td>').join("") +
      '<td class="cand-' + leader + '">' + LABELS[leader] + '</td>';
    tbody.appendChild(tr);
  });
}

function renderRegions(data) {
  const container = document.getElementById("regions");
  container.innerHTML = "";
  Object.entries(data.regional_shift).forEach(([region, shifts]) => {
    const leader = CANDIDATES.reduce((a, b) => shifts[b] > shifts[a] ? b : a);
    const row = document.createElement("div");
    row.className = "region";
    row.innerHTML =
      '<span class="region-name">' + region + '</span>' +
      '<span class="region-val cand-' + leader + '">' + LABELS[leader] + ' ' +
      (shifts[leader] >= 0 ? "+" : "") + shifts[leader].toFixed(1) + '</span>';
    container.appendChild(row);
  });
}

function renderDiagnostics(data) {
  document.getElementById("d-counties").textContent = data.diagnostics.counties_reporting + " / 46";
  ["graham", "norman", "fry", "sanford", "lynch"].forEach((c) => {
    const v = data.diagnostics.statewide_shift[c];
    document.getElementById("d-shift-" + c).textContent = (v >= 0 ? "+" : "") + v.toFixed(1);
  });
}

function renderLegend() {
  const legend = document.getElementById("legend-candidates");
  if (legend.childElementCount) return;
  CANDIDATES.forEach((c) => {
    const span = document.createElement("span");
    span.innerHTML = '<span class="swatch cand-' + c + '-bg"></span>' + LABELS[c];
    legend.appendChild(span);
  });
}

// ---- maps: simple lat/lon projection, no library, no CDN ----

function projectCounties(features) {
  let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
  features.forEach((f) => {
    const polys = f.geometry.type === "MultiPolygon" ? f.geometry.coordinates : [f.geometry.coordinates];
    polys.forEach((poly) => poly.forEach((ring) => ring.forEach(([lon, lat]) => {
      if (lon < minLon) minLon = lon;
      if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    })));
  });
  const meanLat = (minLat + maxLat) / 2;
  const aspect = Math.cos((meanLat * Math.PI) / 180);
  const W = 620, H = 400, PAD = 8;

  const toXY = (lon, lat) => [(lon - minLon) * aspect, maxLat - lat];
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  features.forEach((f) => {
    const polys = f.geometry.type === "MultiPolygon" ? f.geometry.coordinates : [f.geometry.coordinates];
    polys.forEach((poly) => poly.forEach((ring) => ring.forEach(([lon, lat]) => {
      const [x, y] = toXY(lon, lat);
      if (x < minX) minX = x; if (x > maxX) maxX = x;
      if (y < minY) minY = y; if (y > maxY) maxY = y;
    })));
  });
  const scale = Math.min((W - 2 * PAD) / (maxX - minX), (H - 2 * PAD) / (maxY - minY));

  const paths = {};
  features.forEach((f) => {
    const name = f.properties.NAME;
    const polys = f.geometry.type === "MultiPolygon" ? f.geometry.coordinates : [f.geometry.coordinates];
    let d = "";
    polys.forEach((poly) => poly.forEach((ring) => {
      const pts = ring.map(([lon, lat]) => {
        const [x, y] = toXY(lon, lat);
        return [PAD + (x - minX) * scale, PAD + (y - minY) * scale];
      });
      d += "M" + pts.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join("L") + "Z";
    }));
    paths[name] = d;
  });
  return paths;
}

async function ensureGeo() {
  if (geoCache) return geoCache;
  const res = await fetch("sc-counties.geojson", { cache: "force-cache" });
  const geo = await res.json();
  geoCache = projectCounties(geo.features);
  return geoCache;
}

function leaderFromPct(pctObj) {
  let best = null, bestVal = -1;
  CANDIDATES.forEach((c) => {
    const v = pctObj[c];
    if (v != null && v > bestVal) { best = c; bestVal = v; }
  });
  return best;
}

async function renderMaps(data) {
  const paths = await ensureGeo();
  renderLegend();

  const countedGroup = document.getElementById("shapes-counted");
  const projGroup = document.getElementById("shapes-projected");
  countedGroup.innerHTML = "";
  projGroup.innerHTML = "";

  const byCounty = {};
  data.counties.forEach((r) => { byCounty[r.county] = r; });

  Object.entries(paths).forEach(([name, d]) => {
    const row = byCounty[name];
    const countedLeader = row && row.reporting ? leaderFromPct(row.pct) : null;
    const projLeader = row ? leaderFromPct(row.projected_final) : null;

    const c1 = document.createElementNS("http://www.w3.org/2000/svg", "path");
    c1.setAttribute("d", d);
    c1.setAttribute("fill", countedLeader ? COLOR(countedLeader) : "var(--paper-2)");
    c1.addEventListener("mouseenter", () => { c1.classList.add("hov"); showDetail(name, row); });
    c1.addEventListener("mouseleave", () => c1.classList.remove("hov"));
    countedGroup.appendChild(c1);

    const c2 = document.createElementNS("http://www.w3.org/2000/svg", "path");
    c2.setAttribute("d", d);
    c2.setAttribute("fill", projLeader ? COLOR(projLeader) : "var(--paper-2)");
    c2.addEventListener("mouseenter", () => { c2.classList.add("hov"); showDetail(name, row); });
    c2.addEventListener("mouseleave", () => c2.classList.remove("hov"));
    projGroup.appendChild(c2);
  });

  document.getElementById("note-counted").textContent =
    data.diagnostics.counties_reporting + " of 46 counties reporting";
  document.getElementById("note-projected").textContent =
    "Model's blended projection for all 46 counties";
}

function showDetail(name, row) {
  const el = document.getElementById("map-detail");
  if (!row) {
    el.innerHTML = '<p class="map-hint">' + name + ' — no baseline row found.</p>';
    return;
  }
  const rows = CANDIDATES.map((c) =>
    "<dt class='cand-" + c + "'>" + LABELS[c] + "</dt><dd>" +
    (row.reporting && row.pct[c] != null ? row.pct[c].toFixed(1) + "%" : "—") + "</dd>"
  ).join("");
  el.innerHTML =
    "<h3>" + name + "</h3>" +
    "<dl>" + rows + "</dl>" +
    "<p class='split-note'>" +
    (row.reporting ? row.pct_of_projected.toFixed(0) + "% of projected turnout counted. " : "Not yet reporting. ") +
    "Baseline: " + CANDIDATES.map((c) => LABELS[c] + " " + row.expected_baseline[c].toFixed(1) + "%").join(", ") +
    "</p>";
}

async function refresh() {
  try {
    const data = await fetchJSON("/api/projection");
    latest = data;
    renderVerdict(data);
    renderAdvanceBars(data);
    renderCandidateStats(data);
    renderTurnout(data);
    renderTally(data);
    renderCountyTable(data);
    renderRegions(data);
    renderDiagnostics(data);
    await renderMaps(data);
    setPulse("live", data.updated_at);
    document.getElementById("alert").hidden = true;
  } catch (err) {
    setPulse("stale");
    const alertEl = document.getElementById("alert");
    alertEl.hidden = false;
    alertEl.textContent = "Waiting for the model service — " + err.message;
  }
}

refresh();
setInterval(refresh, REFRESH_MS);
