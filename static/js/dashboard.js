"use strict";

// ── State ─────────────────────────────────────────────────────────────────────
let currentScenario = "medium";
let currentEvent    = "normal";
let currentRec      = null;
let selectedItemId  = null;
let charts          = {};

// ── Chart.js defaults ─────────────────────────────────────────────────────────
Chart.defaults.color       = "#8b949e";
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size   = 11;
Chart.defaults.plugins.legend.display = false;

// ── Helpers ───────────────────────────────────────────────────────────────────
function toast(msg, type = "success") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className   = `toast toast-${type} show`;
  setTimeout(() => el.classList.remove("show"), 3200);
}
function setLoading(btn, v) { btn.disabled = v; btn.style.opacity = v ? "0.6" : "1"; }
function fmt$(n) { return "$" + parseFloat(n).toFixed(2); }
function escHtml(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// ── Risk helpers ──────────────────────────────────────────────────────────────
const RISK_COLORS = { critical: "#ff4757", high: "#ffa502", medium: "#f9ca24", low: "#2ed573" };
function riskColor(label) { return RISK_COLORS[label] || "#2ed573"; }

// ── Scenario & Event selectors ────────────────────────────────────────────────
function setScenario(level) {
  currentScenario = level;
  document.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
  document.getElementById(`pill-${level}`).classList.add("active");
}
function setEvent(val) { currentEvent = val; }

// ── Navbar helpers ────────────────────────────────────────────────────────────
function scrollToWhatIf() {
  const el = document.getElementById("whatif-section");
  if (el) {
    el.scrollIntoView({ behavior: "smooth" });
    openWhatIf();
  }
}
function openWhatIf() {
  document.getElementById("whatif-body").classList.remove("hidden");
  document.getElementById("whatif-toggle-label").textContent = "▲ Collapse";
}
function toggleWhatIf() {
  const body = document.getElementById("whatif-body");
  const lbl  = document.getElementById("whatif-toggle-label");
  if (body.classList.toggle("hidden")) {
    lbl.textContent = "▼ Expand";
  } else {
    lbl.textContent = "▲ Collapse";
  }
}

// ═══ API CALLS ════════════════════════════════════════════════════════════════
async function resetSimulation() {
  const btn = document.getElementById("btn-reset");
  setLoading(btn, true);
  try {
    const res  = await fetch("/api/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: currentScenario, event: currentEvent }),
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || "Reset failed.", "error"); return; }
    applyState(data);
    resetCharts();
    toast(`✓ Reset — ${currentScenario} / ${data.event_info?.label || currentEvent}`, "success");
  } catch (e) { toast("Network error: " + e.message, "error"); }
  finally { setLoading(btn, false); }
}

async function runNextDay() {
  const btn = document.getElementById("btn-next");
  setLoading(btn, true);
  try {
    const res  = await fetch("/api/step", { method: "POST" });
    const data = await res.json();
    if (!res.ok) {
      toast(data.error || "Step failed.", data.done ? "warn" : "error");
      if (data.done) btn.disabled = true;
      return;
    }
    applyState(data);
    pushChartData(data.history);
    if (data.done) { toast("🏁 Simulation complete!", "warn"); btn.disabled = true; }
    else           { toast(`Day ${data.current_day - 1} processed`, "success"); }
  } catch (e) { toast("Network error: " + e.message, "error"); }
  finally { if (!document.getElementById("btn-next").disabled) setLoading(btn, false); }
}

async function applyRecommendation() {
  if (!currentRec) { toast("No recommendation to apply.", "warn"); return; }
  const btn = document.getElementById("btn-apply");
  setLoading(btn, true);
  try {
    const res  = await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_id: currentRec.item_id, action_type: currentRec.action_type }),
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || "Action failed.", "error"); return; }
    applyState(data);
    pushChartData(data.history);
    toast(`✓ Applied: ${currentRec.action_type.replace(/_/g," ")}`, "success");
    if (data.done) document.getElementById("btn-next").disabled = true;
  } catch (e) { toast("Network error: " + e.message, "error"); }
  finally { setLoading(btn, false); }
}

async function applyManualAction(itemId, actionType) {
  try {
    const res  = await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_id: itemId, action_type: actionType }),
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || "Action failed.", "error"); return; }
    applyState(data);
    pushChartData(data.history);
    toast(`✓ Item #${itemId}: ${actionType.replace(/_/g," ")}`, "success");
    if (data.done) document.getElementById("btn-next").disabled = true;
  } catch (e) { toast("Network error: " + e.message, "error"); }
}

async function selectItem(itemId) {
  selectedItemId = itemId;
  document.querySelectorAll("#inv-tbody tr").forEach(r => r.classList.remove("row-selected"));
  const row = document.querySelector(`tr[data-item-id="${itemId}"]`);
  if (row) row.classList.add("row-selected");
  try {
    const res  = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_id: itemId }),
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || "Cannot recommend.", "warn"); return; }
    renderRecommendation(data);
  } catch (e) { toast("Network error: " + e.message, "error"); }
}

function exportReport() {
  window.location.href = "/api/export";
  toast("⬇ Downloading report…", "success");
}

async function runWhatIf() {
  const btn         = document.getElementById("btn-whatif");
  const demandDrop  = parseInt(document.getElementById("wi-demand").value, 10);
  const priceSens   = parseFloat(document.getElementById("wi-price").value) / 10;
  setLoading(btn, true);
  try {
    const res  = await fetch("/api/whatif", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ demand_drop_pct: demandDrop, price_sensitivity: priceSens }),
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || "What-if failed.", "error"); return; }
    renderWhatIf(data);
  } catch (e) { toast("Network error: " + e.message, "error"); }
  finally { setLoading(btn, false); }
}

// ═══ STATE APPLICATION ════════════════════════════════════════════════════════
function applyState(data) {
  document.getElementById("day-badge").textContent = `Day ${data.current_day}`;

  // KPI cards
  animateValue("kpi-revenue-val", fmt$(data.total_revenue));
  animateValue("kpi-rescued-val", data.impact?.food_rescued ?? data.food_rescued ?? 0);
  animateValue("kpi-risk-val",    data.items_at_risk);
  animateValue("kpi-waste-val",   data.landfill_waste_count);

  // Impact strip
  const imp = data.impact || {};
  setText("imp-meals",  imp.meals_donated ?? 0);
  setText("imp-co2",    (imp.co2_saved_kg ?? 0) + " kg");
  setText("imp-value",  fmt$(imp.value_saved ?? 0));
  setText("imp-risk",   (data.avg_risk_score ?? 0) + "%");

  // Event banner
  renderEventBanner(data.event_info, data.current_event);

  // Inventory table
  renderTable(data.inventory);

  // Recommendation panel
  if (data.recommendation) {
    currentRec = data.recommendation;
    renderRecommendation(data.recommendation);
  }

  // Action log
  renderActionLog(data.action_log || []);
}

function animateValue(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.transform = "scale(1.08)";
  el.style.color     = "var(--accent)";
  el.textContent     = val;
  setTimeout(() => { el.style.transform = ""; el.style.color = ""; }, 350);
}
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ═══ EVENT BANNER ═════════════════════════════════════════════════════════════
function renderEventBanner(info, eventKey) {
  const banner = document.getElementById("event-banner");
  if (!info || eventKey === "normal") { banner.style.display = "none"; return; }
  banner.style.display = "flex";
  document.getElementById("event-banner-icon").textContent  = info.emoji;
  document.getElementById("event-banner-label").textContent = info.label + " Active";
  document.getElementById("event-banner-desc").textContent  = info.description;
}

// ═══ TABLE RENDER ═════════════════════════════════════════════════════════════
function daysClass(d) {
  if (d <= 1)  return "days-critical";
  if (d <= 3)  return "days-warn";
  return "days-ok";
}
function riskBarHtml(score, label) {
  const color = riskColor(label);
  return `<div class="risk-bar-wrap">
    <div class="risk-bar-track"><div class="risk-bar-fill risk-fill-${label}" style="width:${score}%"></div></div>
    <span class="risk-pct-label" style="color:${color}">${score}%</span>
  </div>`;
}

function renderTable(inventory) {
  const tbody = document.getElementById("inv-tbody");
  const total = (inventory || []).length;
  document.getElementById("inv-count").textContent = `${total} item${total !== 1 ? "s" : ""}`;
  if (!inventory || inventory.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="7">No inventory data</td></tr>`;
    return;
  }
  tbody.innerHTML = inventory.map(item => {
    const isOnShelf = item.status === "on_shelf";
    const dc        = daysClass(item.days_to_expiration);
    const actionBtns = isOnShelf
      ? `<div style="display:flex;gap:4px;flex-wrap:wrap">
           <button class="action-btn action-btn-hold"   onclick="event.stopPropagation();applyManualAction(${item.item_id},'hold_price')">Hold</button>
           <button class="action-btn action-btn-disc"   onclick="event.stopPropagation();applyManualAction(${item.item_id},'set_discount')">Discount</button>
           <button class="action-btn action-btn-donate" onclick="event.stopPropagation();applyManualAction(${item.item_id},'donate')">Donate</button>
         </div>`
      : `<span style="color:var(--text-muted);font-size:11px">—</span>`;
    return `
      <tr data-item-id="${item.item_id}" onclick="selectItem(${item.item_id})" title="Click for AI recommendation">
        <td><span style="color:var(--text-muted);font-size:12px">#${item.item_id}</span></td>
        <td style="font-weight:600">${escHtml(item.name)}</td>
        <td>${riskBarHtml(item.risk_score, item.risk_label)}</td>
        <td><span class="days-chip ${dc}">${isOnShelf ? item.days_to_expiration + "d" : "—"}</span></td>
        <td style="font-weight:500;color:var(--accent)">${fmt$(item.base_price)}</td>
        <td><span class="status-badge status-${item.status}">${item.status.replace(/_/g," ")}</span></td>
        <td>${actionBtns}</td>
      </tr>`;
  }).join("");
  if (selectedItemId !== null) {
    const row = document.querySelector(`tr[data-item-id="${selectedItemId}"]`);
    if (row) row.classList.add("row-selected");
  }
}

// ═══ RECOMMENDATION PANEL ════════════════════════════════════════════════════
function renderRecommendation(rec) {
  currentRec = rec;
  document.getElementById("rec-placeholder").classList.add("hidden");
  document.getElementById("rec-content").classList.remove("hidden");

  document.getElementById("rec-item-name").textContent  = rec.item_name;
  document.getElementById("rec-item-price").textContent = fmt$(rec.base_price);

  // Days + expiry colour
  const expEl  = document.getElementById("rec-item-expiry");
  expEl.textContent = `${rec.days_to_expiry} day(s)`;
  expEl.className   = "rec-item-expiry " + daysClass(rec.days_to_expiry);

  // Risk bar in panel
  const rBar  = document.getElementById("rec-risk-bar");
  const rPct  = document.getElementById("rec-risk-pct");
  const color = riskColor(rec.risk_label);
  rBar.style.setProperty("--risk-pct",   rec.risk_score + "%");
  rBar.style.setProperty("--risk-color", color);
  rPct.textContent = rec.risk_score + "%";
  rPct.style.color = color;

  // Badge
  const badge   = document.getElementById("rec-badge");
  badge.textContent = rec.badge;
  badge.className   = `action-badge ${rec.badge_class}`;

  // Text blocks
  document.getElementById("rec-reason").textContent    = rec.reason;
  document.getElementById("rec-financial").textContent = rec.financial_note;
  document.getElementById("rec-result").textContent    = rec.expected_result;

  // Donation partner
  const partnerBlock = document.getElementById("partner-block");
  const partnerCard  = document.getElementById("partner-card");
  if (rec.partner) {
    partnerBlock.classList.remove("hidden");
    const p = rec.partner;
    partnerCard.innerHTML = `
      <div class="partner-name">${p.emoji} ${escHtml(p.name)}</div>
      <div class="partner-detail">📍 ${p.distance_km} km away &nbsp;·&nbsp; Capacity: ${p.capacity}</div>
      <div class="partner-detail">Accepts: ${escHtml(p.accepts)}</div>
      <div class="partner-contact">✉ ${escHtml(p.contact)}</div>`;
  } else {
    partnerBlock.classList.add("hidden");
  }
}

// ═══ WHAT-IF RESULTS ══════════════════════════════════════════════════════════
function renderWhatIf(data) {
  const results = document.getElementById("whatif-results");
  results.classList.remove("hidden");
  const nrl = data.without_rl;
  const rl  = data.with_rl;
  document.getElementById("wi-no-waste").textContent  = nrl.projected_waste  + " items";
  document.getElementById("wi-no-rev").textContent    = fmt$(nrl.projected_revenue);
  document.getElementById("wi-no-donate").textContent = nrl.projected_donations + " items";
  document.getElementById("wi-rl-waste").textContent  = rl.projected_waste   + " items";
  document.getElementById("wi-rl-rev").textContent    = fmt$(rl.projected_revenue);
  document.getElementById("wi-rl-donate").textContent = rl.projected_donations + " items";
  document.getElementById("wi-meals").textContent     = rl.meals_saved       + " meals";
  document.getElementById("wi-co2").textContent       = rl.co2_saved_kg      + " kg CO₂";
  const delta = data.delta;
  toast(`RL saves ${delta.waste_reduction} wasted items & gains ${fmt$(delta.revenue_gain)} revenue`, "success");
}

// ═══ ACTION LOG ═══════════════════════════════════════════════════════════════
const ACTION_LABEL = { hold_price: "Hold Price", set_discount: "Set Discount", donate: "Donate" };
const ACTION_COLOR = { hold_price: "var(--blue)", set_discount: "var(--orange)", donate: "var(--accent)" };

function renderActionLog(log) {
  const tbody = document.getElementById("log-tbody");
  document.getElementById("log-count").textContent = `${log.length} action${log.length !== 1 ? "s" : ""}`;
  if (!log || log.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="5">No actions yet — start the simulation</td></tr>`;
    return;
  }
  tbody.innerHTML = [...log].reverse().map(entry => `
    <tr>
      <td style="color:var(--text-muted)">Day ${entry.day}</td>
      <td>${escHtml(entry.item_name)} <span style="color:var(--text-muted);font-size:11px">#${entry.item_id}</span></td>
      <td><span style="color:${ACTION_COLOR[entry.action] || "var(--text-primary)"}; font-weight:600">${ACTION_LABEL[entry.action] || entry.action}</span></td>
      <td style="color:var(--green)">${entry.reward}</td>
      <td style="color:var(--accent);font-weight:600">${fmt$(entry.revenue)}</td>
    </tr>`).join("");
}

// ═══ CHARTS ══════════════════════════════════════════════════════════════════
function buildChart(canvasId, label, color) {
  const ctx  = document.getElementById(canvasId).getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 180);
  grad.addColorStop(0, color + "40");
  grad.addColorStop(1, color + "00");
  return new Chart(ctx, {
    type: "line",
    data: { labels: [], datasets: [{ label, data: [], borderColor: color, backgroundColor: grad,
      borderWidth: 2, pointRadius: 3, pointHoverRadius: 5, pointBackgroundColor: color, fill: true, tension: 0.4 }] },
    options: {
      responsive: true, maintainAspectRatio: true,
      animation: { duration: 400, easing: "easeInOutQuart" },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#484f58", font: { size: 10 } } },
        y: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#484f58", font: { size: 10 } }, beginAtZero: true },
      },
      plugins: { tooltip: { backgroundColor: "#161b22", borderColor: "rgba(255,255,255,0.08)", borderWidth: 1,
        titleColor: "#e6edf3", bodyColor: "#8b949e" } },
    },
  });
}

function initCharts() {
  charts.waste     = buildChart("chart-waste",     "Landfill Waste", "#ff4757");
  charts.revenue   = buildChart("chart-revenue",   "Revenue ($)",    "#00e5a0");
  charts.donations = buildChart("chart-donations", "Donations",      "#74b9ff");
}
function resetCharts() {
  Object.values(charts).forEach(c => { c.data.labels = []; c.data.datasets[0].data = []; c.update(); });
}
function pushChartData(h) {
  if (!h || !h.days || h.days.length === 0) return;
  const labels = h.days.map(d => `D${d}`);
  const upd = (chart, vals) => { chart.data.labels = labels; chart.data.datasets[0].data = vals; chart.update("active"); };
  upd(charts.waste,     h.waste);
  upd(charts.revenue,   h.revenue);
  upd(charts.donations, h.donations);
}

// ═══ INIT ═════════════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  initCharts();
  resetSimulation();
});
