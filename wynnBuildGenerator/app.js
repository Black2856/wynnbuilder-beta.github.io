"use strict";

const API_BASE = "";  // Same origin; api.py serves this page

const SLOT_NAMES = ["helmet", "chestplate", "leggings", "boots", "ring1", "ring2", "bracelet", "necklace", "weapon"];
const SLOT_LABELS = ["ヘルメット", "チェストプレート", "レギンス", "ブーツ", "リング1", "リング2", "ブレスレット", "ネックレス", "武器"];

// Common stat keys for dropdowns (full list loaded from API)
let availableStatKeys = [
  "hp", "eDef", "tDef", "wDef", "fDef", "aDef",
  "sdRaw", "sdPct", "mdRaw", "mdPct",
  "hprRaw", "hprPct", "hpBonus",
  "spRaw1", "spRaw2", "spRaw3", "spRaw4",
  "spPct1", "spPct2", "spPct3", "spPct4",
  "atkSpd", "mana", "ls",
  "str", "dex", "int", "def", "agi",
  "strReq", "dexReq", "intReq", "defReq", "agiReq",
  "eDamPct", "tDamPct", "wDamPct", "fDamPct", "aDamPct",
  "eMDamPct", "tMDamPct", "wMDamPct", "fMDamPct", "aMDamPct",
  "eDamRaw", "tDamRaw", "wDamRaw", "fDamRaw", "aDamRaw",
  "damPct", "damRaw", "nDamRaw", "nDamPct",
];

// Load full stat key list from API
async function loadStatKeys() {
  try {
    const res = await fetch(`${API_BASE}/api/stat_keys`);
    if (res.ok) {
      const data = await res.json();
      availableStatKeys = data.stat_keys || availableStatKeys;
    }
  } catch (_) {}
}

// Scoring rows
let scoringRows = [];

function addScoringRow(mode) {
  const id = `scoring-${Date.now()}-${Math.random()}`;
  scoringRows.push({ id, mode });
  renderScoringRows();
}

function removeScoringRow(id) {
  scoringRows = scoringRows.filter(r => r.id !== id);
  renderScoringRows();
}

function renderScoringRows() {
  const container = document.getElementById("scoring-rows");
  container.innerHTML = scoringRows.map(row => {
    const badge = row.mode === "maximize"
      ? '<span class="badge bg-success me-1">MAX</span>'
      : '<span class="badge bg-warning text-dark me-1">MIN</span>';
    return `
      <div class="scoring-row d-flex align-items-center gap-2" data-id="${row.id}">
        ${badge}
        <select class="form-select form-select-sm bg-dark text-light border-secondary" style="flex:2"
                data-scoring-key="${row.id}" onchange="void(0)">
          ${availableStatKeys.map(k => `<option value="${k}">${k}</option>`).join("")}
        </select>
        <span class="small text-secondary">×</span>
        <input type="number" class="form-control form-control-sm bg-dark text-light border-secondary" style="width:70px"
               data-scoring-weight="${row.id}" value="1" step="0.1" min="0.01" />
        <button class="btn btn-sm btn-outline-danger p-1 lh-1" onclick="removeScoringRow('${row.id}')">✕</button>
      </div>`;
  }).join("");
}

// Condition rows
let conditionRows = [];

function addConditionRow() {
  const id = `cond-${Date.now()}-${Math.random()}`;
  conditionRows.push({ id });
  renderConditionRows();
}

function removeConditionRow(id) {
  conditionRows = conditionRows.filter(r => r.id !== id);
  renderConditionRows();
}

function renderConditionRows() {
  const container = document.getElementById("condition-rows");
  container.innerHTML = conditionRows.map(row => `
    <div class="condition-row d-flex align-items-center gap-2" data-id="${row.id}">
      <select class="form-select form-select-sm bg-dark text-light border-secondary" style="flex:2"
              data-cond-key="${row.id}">
        ${availableStatKeys.map(k => `<option value="${k}">${k}</option>`).join("")}
      </select>
      <select class="form-select form-select-sm bg-dark text-light border-secondary" style="width:70px"
              data-cond-op="${row.id}">
        <option value=">=">&gt;=</option>
        <option value="<=">&lt;=</option>
      </select>
      <input type="number" class="form-control form-control-sm bg-dark text-light border-secondary" style="width:90px"
             data-cond-val="${row.id}" value="0" />
      <button class="btn btn-sm btn-outline-danger p-1 lh-1" onclick="removeConditionRow('${row.id}')">✕</button>
    </div>`).join("");
}

// Fixed item rows
let fixedRows = [];

function addFixedRow() {
  const id = `fixed-${Date.now()}-${Math.random()}`;
  fixedRows.push({ id });
  renderFixedRows();
}

function removeFixedRow(id) {
  fixedRows = fixedRows.filter(r => r.id !== id);
  renderFixedRows();
}

function renderFixedRows() {
  const container = document.getElementById("fixed-rows");
  container.innerHTML = fixedRows.map(row => `
    <div class="fixed-row d-flex align-items-center gap-2" data-id="${row.id}">
      <select class="form-select form-select-sm bg-dark text-light border-secondary" style="width:130px"
              data-fixed-slot="${row.id}">
        ${SLOT_NAMES.map((s, i) => `<option value="${s}">${SLOT_LABELS[i]}</option>`).join("")}
      </select>
      <input type="text" class="form-control form-control-sm bg-dark text-light border-secondary"
             style="flex:2" placeholder="アイテム名"
             data-fixed-name="${row.id}" />
      <button class="btn btn-sm btn-outline-danger p-1 lh-1" onclick="removeFixedRow('${row.id}')">✕</button>
    </div>`).join("");
}

// Collect form data
function collectRequest() {
  const class_ = document.getElementById("inp-class").value;
  const level = parseInt(document.getElementById("inp-level").value, 10);

  // Scoring
  const maximize = {};
  const minimize = {};
  for (const row of scoringRows) {
    const keyEl = document.querySelector(`[data-scoring-key="${row.id}"]`);
    const wtEl = document.querySelector(`[data-scoring-weight="${row.id}"]`);
    if (!keyEl || !wtEl) continue;
    const key = keyEl.value;
    const wt = parseFloat(wtEl.value) || 1;
    if (row.mode === "maximize") maximize[key] = wt;
    else minimize[key] = wt;
  }
  const scoring = {};
  if (Object.keys(maximize).length) scoring.maximize = maximize;
  if (Object.keys(minimize).length) scoring.minimize = minimize;

  // Conditions
  const conditions = conditionRows.map(row => {
    const keyEl = document.querySelector(`[data-cond-key="${row.id}"]`);
    const opEl = document.querySelector(`[data-cond-op="${row.id}"]`);
    const valEl = document.querySelector(`[data-cond-val="${row.id}"]`);
    if (!keyEl || !opEl || !valEl) return null;
    return { key: keyEl.value, op: opEl.value, value: parseFloat(valEl.value) || 0 };
  }).filter(Boolean);

  // Fixed items
  const fixed_items = {};
  for (const row of fixedRows) {
    const slotEl = document.querySelector(`[data-fixed-slot="${row.id}"]`);
    const nameEl = document.querySelector(`[data-fixed-name="${row.id}"]`);
    if (!slotEl || !nameEl) continue;
    const name = nameEl.value.trim();
    if (name) fixed_items[slotEl.value] = name;
  }

  // Search params
  const beam_width = parseInt(document.getElementById("param-beam").value, 10) || 50;
  const max_candidates_per_slot = parseInt(document.getElementById("param-maxslot").value, 10) || 40;
  const result_limit = parseInt(document.getElementById("param-results").value, 10) || 10;

  return {
    class: class_,
    level,
    conditions,
    scoring,
    fixed_items,
    search_params: { beam_width, max_candidates_per_slot, result_limit },
  };
}

// Search
async function runSearch() {
  const btn = document.getElementById("btn-search");
  btn.disabled = true;
  btn.textContent = "検索中...";

  setStatus("searching", "検索中...");

  try {
    const req = collectRequest();

    const res = await fetch(`${API_BASE}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    renderResults(data, req);
    setStatus("success", `${data.results.length} 件 / ${data.total_candidates_evaluated} 候補評価 / ${data.elapsed_ms.toFixed(0)} ms`);
  } catch (e) {
    setStatus("error", `エラー: ${e.message}`);
    document.getElementById("results-container").innerHTML = `
      <div class="alert alert-danger">${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "検索";
  }
}

function setStatus(type, msg) {
  const el = document.getElementById("status-bar");
  el.className = `alert py-2 small mb-3 ${type}`;
  el.textContent = msg;
  el.classList.remove("d-none");
}

// Render results
function renderResults(data, req) {
  const container = document.getElementById("results-container");

  if (!data.results || data.results.length === 0) {
    container.innerHTML = `<div class="alert alert-warning">結果が見つかりませんでした。条件を緩めてみてください。</div>`;
    return;
  }

  const cards = data.results.map((r, i) => buildResultCard(r, i + 1, req)).join("");
  container.innerHTML = cards;
}

function buildResultCard(r, rank, req) {
  const builderUrl = r.build_hash
    ? `../builder/#${r.build_hash}`
    : null;

  const builderBtn = builderUrl
    ? `<a href="${builderUrl}" target="_blank" class="btn btn-sm btn-outline-success">Builder で開く</a>`
    : `<span class="text-muted small">ハッシュなし</span>`;

  const condOk = r.conditions_met;
  const spOk = r.skillpoints_valid;

  // Equipment list
  const equipment = (r.equipment || []).map((name, i) => {
    const label = SLOT_LABELS[i] || SLOT_NAMES[i] || `slot${i}`;
    const display = name || "—";
    return `<div class="item-slot"><span class="slot-label">${label}</span>${escHtml(display)}</div>`;
  }).join("");

  const weaponDisplay = r.weapon || "—";

  // Score breakdown
  let breakdownHtml = "";
  if (r.score_breakdown && Object.keys(r.score_breakdown).length > 0) {
    const parts = Object.entries(r.score_breakdown).map(([k, v]) =>
      `<span class="stat-badge">${escHtml(k)}: ${v.toFixed(1)}</span>`
    ).join("");
    breakdownHtml = `<div class="mt-2">${parts}</div>`;
  }

  // Highlight scoring stats
  let scoringStatHtml = "";
  const sm = r.stat_map || {};
  const scoringKeys = new Set([
    ...Object.keys((req.scoring.maximize) || {}),
    ...Object.keys((req.scoring.minimize) || {}),
    ...((req.conditions || []).map(c => c.key)),
  ]);
  if (scoringKeys.size > 0) {
    const statParts = [...scoringKeys].filter(k => sm[k] !== undefined).map(k =>
      `<span class="stat-badge">${escHtml(k)}: <strong>${formatStat(sm[k])}</strong></span>`
    ).join("");
    if (statParts) {
      scoringStatHtml = `<div class="mt-2 small">${statParts}</div>`;
    }
  }

  return `
    <div class="result-card">
      <div class="d-flex justify-content-between align-items-start">
        <div>
          <span class="result-rank">#${rank}</span>
          <span class="result-score ms-3">${r.score.toFixed(1)}</span>
          <span class="small ms-2 ${condOk ? "conditions-met-yes" : "conditions-met-no"}">
            ${condOk ? "✓ 条件OK" : "✗ 条件NG"}
          </span>
          <span class="small ms-2 ${spOk ? "sp-valid-yes" : "sp-valid-no"}">
            ${spOk ? "✓ SP OK" : "✗ SP不足"}
          </span>
        </div>
        ${builderBtn}
      </div>

      <div class="row mt-2 g-2">
        <div class="col-md-6">
          <div class="small text-secondary mb-1">装備</div>
          ${equipment}
        </div>
        <div class="col-md-6">
          <div class="small text-secondary mb-1">武器</div>
          <div class="item-slot"><span class="slot-label">武器</span>${escHtml(weaponDisplay)}</div>
        </div>
      </div>

      ${scoringStatHtml}
      ${breakdownHtml}
    </div>`;
}

function formatStat(v) {
  if (typeof v === "number") return Number.isInteger(v) ? v.toString() : v.toFixed(1);
  return String(v);
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Keyboard shortcut: Enter submits
document.addEventListener("keydown", e => {
  if (e.key === "Enter" && e.ctrlKey) runSearch();
});

// Init
loadStatKeys().then(() => {
  // Add a default hp maximize row on load
  addScoringRow("maximize");
  const keyEl = document.querySelector(`[data-scoring-key="${scoringRows[0].id}"]`);
  if (keyEl) keyEl.value = "hp";
});
