/* global RECORDING_ID */

const $ = (sel) => document.querySelector(sel);
let evaluationResults = null;

async function api(url, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (opts.body && typeof opts.body === "string") {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(url, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
          : res.statusText;
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

function showStatus(el, msg, isError = false) {
  if (!el) return;
  el.textContent = msg;
  el.className = isError ? "status-msg error" : "status-msg";
  el.hidden = !msg;
}

function showIngestSuccess(result) {
  const statusEl = $("#upload-status");
  const fmt = result.format_name || result.format || "unknown";
  showStatus(
    statusEl,
    `Detected ${fmt} — matched ${result.matched_segments}/${result.total_segments} chunks.`
  );
  showEvaluateSection();
}

function getFormatHint(selectId) {
  const val = $(selectId)?.value;
  return val || undefined;
}

function getLanguage(selectId) {
  return $(selectId)?.value || "en";
}

async function pasteLLMTranscript() {
  const textarea = $("#llm-paste");
  const statusEl = $("#upload-status");
  const content = textarea?.value?.trim();

  if (!content) {
    showStatus(statusEl, "Paste your LLM transcript first.", true);
    return;
  }

  showStatus(statusEl, "Applying…");
  try {
    const result = await api(`/api/recordings/${RECORDING_ID}/llm-transcript/paste`, {
      method: "POST",
      body: JSON.stringify({
        content,
        language: getLanguage("#paste-language"),
        format_hint: getFormatHint("#paste-format") || "",
      }),
    });
    showIngestSuccess(result);
    textarea.value = "";
    await loadLLMStatus();
  } catch (e) {
    showStatus(statusEl, e.message, true);
  }
}

async function uploadLLMTranscript() {
  const fileInput = $("#llm-file");
  const statusEl = $("#upload-status");

  if (!fileInput?.files?.length) {
    showStatus(statusEl, "Please choose a file first.", true);
    return;
  }

  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", getLanguage("#upload-language"));
  const hint = getFormatHint("#upload-format");
  if (hint) formData.append("format_hint", hint);

  showStatus(statusEl, "Uploading…");
  try {
    const res = await fetch(`/api/recordings/${RECORDING_ID}/llm-transcript`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(
        typeof err.detail === "string" ? err.detail : res.statusText
      );
    }
    const result = await res.json();
    showIngestSuccess(result);
    fileInput.value = "";
    await loadLLMStatus();
  } catch (e) {
    showStatus(statusEl, e.message, true);
  }
}

async function loadLLMStatus() {
  try {
    const status = await api(`/api/recordings/${RECORDING_ID}/llm-transcript/status`);

    $("#llm-status-section").hidden = false;
    $("#stat-segments-total").textContent = status.segments.total;
    $("#stat-segments-with-llm").textContent = status.segments.with_transcript;
    $("#stat-coverage").textContent = status.segments.coverage_percent + "%";
    $("#stat-format").textContent = status.format || "—";

    // Keep upload visible so users can replace LLM text
  } catch (e) {
    console.error("Failed to load LLM status:", e);
  }
}

async function deleteLLMTranscript() {
  if (!confirm("Delete LLM transcript? This cannot be undone.")) return;

  try {
    await api(`/api/recordings/${RECORDING_ID}/llm-transcript`, { method: "DELETE" });
    $("#llm-status-section").hidden = true;
    $("#evaluate-section").hidden = true;
    $("#results-section").hidden = true;
    $("#segment-details").hidden = true;
    if ($("#upload-status")) $("#upload-status").hidden = true;
    evaluationResults = null;
  } catch (e) {
    alert("Failed to delete: " + e.message);
  }
}

function showEvaluateSection() {
  $("#evaluate-section").hidden = false;
}

async function runEvaluation() {
  const statusEl = $("#evaluate-status");
  showStatus(statusEl, "Evaluating…");

  try {
    const result = await api(
      `/api/recordings/${RECORDING_ID}/evaluation?language=en`
    );

    evaluationResults = result;
    showResults(result);
    showStatus(statusEl, "Evaluation complete!");
  } catch (e) {
    showStatus(statusEl, e.message, true);
  }
}

function showResults(result) {
  $("#results-section").hidden = false;
  $("#segment-details").hidden = false;

  const summary = result.summary;
  const agg = result.aggregated;

  const semanticWer = summary.semantic_wer_percent ?? summary.semantic_score_percent;

  $("#result-semantic-wer").textContent = semanticWer + "%";
  $("#result-semantic-wer").className =
    "eval-score-value " + getScoreClass(semanticWer);

  $("#result-wer").textContent = summary.wer_percent + "%";
  $("#result-wer").className = "eval-score-value " + getScoreClass(summary.wer_percent);

  $("#result-semantic-accuracy").textContent =
    (summary.semantic_accuracy_percent ?? (100 - semanticWer)).toFixed(1) + "%";
  $("#result-accuracy").textContent = summary.accuracy_percent + "%";
  $("#result-quality").textContent = summary.quality.replace(/_/g, " ");

  const totalErrors = agg.substitutions + agg.deletions + agg.insertions;
  if (totalErrors > 0) {
    const subPct = (agg.substitutions / totalErrors * 100).toFixed(0);
    const delPct = (agg.deletions / totalErrors * 100).toFixed(0);
    const insPct = (agg.insertions / totalErrors * 100).toFixed(0);

    $("#bar-subs").style.width = subPct + "%";
    $("#bar-dels").style.width = delPct + "%";
    $("#bar-ins").style.width = insPct + "%";
    $("#val-subs").textContent = agg.substitutions;
    $("#val-dels").textContent = agg.deletions;
    $("#val-ins").textContent = agg.insertions;
  }

  renderSegmentDetails(result.segments);
}

function getScoreClass(werPercent) {
  if (werPercent <= 5) return "score-excellent";
  if (werPercent <= 15) return "score-good";
  if (werPercent <= 30) return "score-fair";
  return "score-poor";
}

function renderSegmentDetails(segments) {
  const container = $("#segment-list");

  if (!segments || segments.length === 0) {
    container.innerHTML = '<p class="empty">No segments to display.</p>';
    return;
  }

  container.innerHTML = segments.map(seg => {
    const strictWer = (seg.wer * 100).toFixed(1);
    const semanticWer = ((seg.semantic_wer ?? seg.wer) * 100).toFixed(1);
    const werClass = getScoreClass(parseFloat(semanticWer));

    let semanticInfo = "";
    if (seg.semantic_matches && seg.semantic_matches.length > 0) {
      semanticInfo = seg.semantic_matches.map(m =>
        `<span class="sem-match">"${m.ref}" ↔ "${m.hyp}" (${(m.weight * 100).toFixed(0)}%)</span>`
      ).join("");
    }

    return `
      <div class="eval-segment ${seg.reference && seg.hypothesis ? "" : "segment-empty"}">
        <div class="eval-segment-header">
          <span class="seg-id">Segment ${seg.segment_id}</span>
          <span class="seg-time">${seg.start_ms}–${seg.end_ms} ms</span>
          <span class="seg-wer ${werClass}">Semantic WER: ${semanticWer}%</span>
          <span class="seg-semantic">Strict: ${strictWer}%</span>
        </div>
        <div class="eval-segment-content">
          <div class="eval-text-row">
            <span class="eval-label">Human:</span>
            <span class="eval-text ref">${seg.reference || "(empty)"}</span>
          </div>
          <div class="eval-text-row">
            <span class="eval-label">LLM:</span>
            <span class="eval-text hyp">${seg.hypothesis || "(empty)"}</span>
          </div>
          ${semanticInfo ? `<div class="semantic-matches">${semanticInfo}</div>` : ""}
        </div>
      </div>
    `;
  }).join("");
}

function switchInputTab(tabId) {
  document.querySelectorAll(".input-tab").forEach((btn) => {
    const active = btn.dataset.tab === tabId;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });
  $("#tab-paste").hidden = tabId !== "paste";
  $("#tab-upload").hidden = tabId !== "upload";
}

function bindEvents() {
  document.querySelectorAll(".input-tab").forEach((btn) => {
    btn.addEventListener("click", () => switchInputTab(btn.dataset.tab));
  });

  $("#btn-paste-llm")?.addEventListener("click", pasteLLMTranscript);
  $("#btn-upload-llm")?.addEventListener("click", uploadLLMTranscript);
  $("#btn-delete-llm")?.addEventListener("click", deleteLLMTranscript);
  $("#btn-evaluate")?.addEventListener("click", runEvaluation);
}

function populateFormatSelects(formats) {
  const opts = formats
    .map((f) => `<option value="${f.id}">${f.name}</option>`)
    .join("");

  ["#paste-format", "#upload-format"].forEach((sel) => {
    const el = $(sel);
    if (el) el.insertAdjacentHTML("beforeend", opts);
  });
}

function populateLanguageSelects(languages, defaultLang) {
  const html = languages
    .map(
      (lang) =>
        `<option value="${lang.code}"${lang.code === defaultLang ? " selected" : ""}>${lang.name}</option>`
    )
    .join("");

  ["#paste-language", "#upload-language"].forEach((sel) => {
    const el = $(sel);
    if (el) el.innerHTML = html;
  });
}

async function loadFormats() {
  try {
    const data = await api("/api/transcript-formats");
    const listEl = $("#format-list");
    const extsHint = $("#accepted-exts-hint");
    const fileInput = $("#llm-file");

    if (!data.formats?.length) return;

    populateFormatSelects(data.formats);

    if (extsHint && data.accepted_extensions_label) {
      const maxMb = data.max_upload_mb || 5;
      extsHint.textContent =
        `Accepted file types: ${data.accepted_extensions_label} · UTF-8 · max ${maxMb} MB`;
    }

    if (fileInput && data.accepted_extensions?.length) {
      fileInput.accept = data.accepted_extensions.join(",");
    }

    if (listEl) {
      listEl.innerHTML = `
        <details class="format-details">
          <summary>Format help (${data.formats.length})</summary>
          <ul class="format-docs">
            ${data.formats
              .map((f) => `<li><strong>${f.name}</strong> — ${f.description || ""}</li>`)
              .join("")}
          </ul>
        </details>`;
    }
  } catch (e) {
    console.warn("Could not load transcript formats:", e);
  }
}

async function loadLanguages() {
  try {
    const cfg = await api("/api/evaluation/config");
    if (!cfg.languages?.length) return;
    populateLanguageSelects(cfg.languages, cfg.default_language);
  } catch (e) {
    console.warn("Could not load evaluation languages:", e);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  await loadFormats();
  await loadLanguages();
  await loadLLMStatus();
  if ($("#stat-segments-with-llm")?.textContent !== "—" &&
      parseInt($("#stat-segments-with-llm").textContent) > 0) {
    showEvaluateSection();
  }
});