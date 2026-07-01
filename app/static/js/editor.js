/* global WaveSurfer, RECORDING_ID, AUDIO_URL */

let ws = null;
let regionsPlugin = null;
let segments = [];
let activeSegmentId = null;
let regionMap = new Map();
let saveTimer = null;
let audioReady = false;
let pxPerSec = 50;
let chunkStopAt = null;
let dragSelectionEnabled = false;

const $ = (sel) => document.querySelector(sel);
const MAX_AUTO_SEGMENTS = 150;
const PLAYBACK_SPEEDS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

function sortedSegments() {
  return [...segments].sort((a, b) => a.start_ms - b.start_ms);
}

function activeSegment() {
  return segments.find((s) => s.id === activeSegmentId) || null;
}

function chunkOnlyMode() {
  return $("#chunk-only")?.checked ?? true;
}

function setPlaybackRate(rate) {
  if (!ws) return;
  if (typeof ws.setPlaybackRate === "function") {
    ws.setPlaybackRate(rate);
  } else {
    const media = ws.getMediaElement?.();
    if (media) media.playbackRate = rate;
  }
}

function getPlaybackRate() {
  return parseFloat($("#playback-speed")?.value || "1") || 1;
}

function updateSpeedLabel() {
  const rate = `${getPlaybackRate()}×`;
  const label = $("#speed-label");
  const panel = $("#panel-speed-label");
  if (label) label.textContent = rate;
  if (panel) panel.textContent = rate;
}

function setSpeedIndex(index) {
  const select = $("#playback-speed");
  if (!select) return;
  const clamped = Math.max(0, Math.min(PLAYBACK_SPEEDS.length - 1, index));
  select.selectedIndex = clamped;
  const rate = PLAYBACK_SPEEDS[clamped];
  setPlaybackRate(rate);
  updateSpeedLabel();
}

function adjustPlaybackSpeed(delta) {
  const select = $("#playback-speed");
  if (!select) return;
  setSpeedIndex(select.selectedIndex + delta);
}

function syncSpeedSelect() {
  const select = $("#playback-speed");
  if (!select) return;
  select.innerHTML = PLAYBACK_SPEEDS.map(
    (s) => `<option value="${s}">${s}×</option>`
  ).join("");
  const current = getPlaybackRate();
  const idx = PLAYBACK_SPEEDS.findIndex((s) => s === current);
  select.selectedIndex = idx >= 0 ? idx : PLAYBACK_SPEEDS.indexOf(1);
  updateSpeedLabel();
}

function isPlaying() {
  if (!ws) return false;
  if (typeof ws.isPlaying === "function") return ws.isPlaying();
  const media = ws.getMediaElement?.();
  return media ? !media.paused : false;
}

function updateNavLabel() {
  const el = $("#seg-nav-label");
  if (!el) return;
  const sorted = sortedSegments();
  if (!activeSegmentId || !sorted.length) {
    el.textContent = "No segment selected";
    return;
  }
  const idx = sorted.findIndex((s) => s.id === activeSegmentId);
  const seg = sorted[idx];
  const speaker = (seg.speaker || "").trim() || "Segment";
  el.textContent = `${idx + 1} / ${sorted.length} · ${speaker}`;
}

function updatePlayButtons(playing) {
  const chunkBtn = $("#btn-play-chunk");
  const allBtn = $("#btn-play");
  if (chunkBtn) chunkBtn.textContent = playing ? "⏸ Chunk" : "▶ Chunk";
  if (allBtn) allBtn.textContent = playing ? "Pause all" : "Play all";
}

function setStatus(msg, isError = false) {
  const el = $("#wave-status");
  if (!el) return;
  el.textContent = msg;
  el.className = isError ? "wave-status error" : "wave-status";
  el.hidden = !msg;
}

function msToDisplay(ms) {
  const s = ms / 1000;
  const mins = Math.floor(s / 60);
  const secs = s % 60;
  return `${mins}:${secs.toFixed(3).padStart(6, "0")}`;
}

function regionLabel(seg) {
  if (seg.id !== activeSegmentId) return "";
  const speaker = (seg.speaker || "").trim();
  if (speaker) return speaker;
  return `${(seg.start_ms / 1000).toFixed(1)}–${(seg.end_ms / 1000).toFixed(1)}s`;
}

function regionColor(seg) {
  const isSameTime = sameTimeOverlap(seg);
  if (seg.id === activeSegmentId) {
    if (isSameTime) {
      return "rgba(147, 112, 219, 0.55)"; // Purple for same-time active
    }
    return segmentOverlaps(seg)
      ? "rgba(91, 120, 160, 0.6)"
      : "rgba(91, 143, 134, 0.55)";
  }
  if (isSameTime) {
    return "rgba(180, 140, 220, 0.35)"; // Light purple for same-time inactive
  }
  return segmentOverlaps(seg)
    ? "rgba(143, 160, 188, 0.35)"
    : "rgba(143, 188, 176, 0.28)";
}

function segmentOverlaps(seg) {
  return segments.some(
    (other) =>
      other.id !== seg.id &&
      other.start_ms < seg.end_ms &&
      seg.start_ms < other.end_ms
  );
}

function sameTimeOverlap(seg) {
  return segments.some(
    (other) =>
      other.id !== seg.id &&
      other.start_ms === seg.start_ms &&
      other.end_ms === seg.end_ms
  );
}

function getDivideMode() {
  const checked = document.querySelector('input[name="divide-mode"]:checked');
  return checked?.value || "duration";
}

function estimateChunkCount() {
  const duration = getDurationMs();
  if (!duration) return null;
  const mode = getDivideMode();
  if (mode === "count") {
    const count = parseInt($("#divide-count")?.value, 10);
    if (!count || count < 1) return null;
    return Math.min(count, MAX_AUTO_SEGMENTS);
  }
  const value = parseFloat($("#divide-value")?.value);
  if (!value || value <= 0) return null;
  const step =
    $("#divide-unit")?.value === "milliseconds"
      ? Math.round(value)
      : Math.round(value * 1000);
  if (step < 100) return null;
  return Math.min(MAX_AUTO_SEGMENTS, Math.ceil(duration / step));
}

function updateDividePreview() {
  const el = $("#divide-preview");
  if (!el) return;
  const count = estimateChunkCount();
  const duration = getDurationMs();
  if (!duration) {
    el.textContent = "";
    return;
  }
  if (count == null) {
    el.textContent = "";
    return;
  }
  if (count > MAX_AUTO_SEGMENTS) {
    el.textContent = `Too many (~${count}) — max ${MAX_AUTO_SEGMENTS}`;
    el.className = "divide-preview divide-preview-warn";
    return;
  }
  el.textContent = `≈ ${count} chunk${count === 1 ? "" : "s"}`;
  el.className = "divide-preview";
}

function showPanel(show) {
  $("#editor-panel").hidden = !show;
  $("#no-select").hidden = show;
}

function refreshAllRegionStyles() {
  segments.forEach((s) => {
    const r = regionMap.get(s.id);
    if (r) {
      r.setOptions({ color: regionColor(s), content: regionLabel(s) });
    }
  });
}

async function api(url, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (opts.body && typeof opts.body === "string") {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(url, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail) || res.statusText
    );
  }
  return res.status === 204 ? null : res.json();
}

function renderSegmentList() {
  const list = $("#segment-list");
  const sorted = [...segments].sort((a, b) => a.start_ms - b.start_ms);
  $("#seg-count").textContent = sorted.length;
  const clearBtn = $("#btn-clear-segs");
  if (clearBtn) clearBtn.hidden = sorted.length === 0;

  if (segments.length > 40) {
    setStatus(
      `${segments.length} segments — use zoom + scroll below the wave. Only the selected segment shows a label.`,
      false
    );
  }

  if (!sorted.length) {
    list.innerHTML =
      '<li class="empty-item">No chunks yet — use <strong>Divide into chunks</strong> above.</li>';
    return;
  }

  list.innerHTML = sorted
    .map((s) => {
      const overlap = segmentOverlaps(s);
      const sameTime = sameTimeOverlap(s);
      let badge = "";
      if (sameTime) {
        badge = '<span class="overlap-badge overlap-badge-same">same time</span>';
      } else if (overlap) {
        badge = '<span class="overlap-badge">overlap</span>';
      }
      const classes = [
        s.id === activeSegmentId ? "active" : "",
        overlap ? " has-overlap" : "",
        sameTime ? " has-same-time" : ""
      ].join(" ").trim();
      return `
    <li data-id="${s.id}" class="${classes}">
      <span class="seg-times">${s.start_ms}–${s.end_ms} ms${badge}</span>
      <span class="seg-speaker-label">${s.speaker || "—"}</span>
      <span class="seg-preview">${s.transcript || "(empty)"}</span>
    </li>`;
    })
    .join("");

  list.querySelectorAll("li[data-id]").forEach((li) => {
    li.addEventListener("click", () => selectSegment(Number(li.dataset.id), false));
  });
}

function fillPanel(seg) {
  $("#seg-start").value = seg.start_ms;
  $("#seg-end").value = seg.end_ms;
  $("#seg-speaker").value = seg.speaker || "";
  $("#seg-transcript").value = seg.transcript || "";
}

function getPanelData() {
  return {
    start_ms: parseInt($("#seg-start").value, 10) || 0,
    end_ms: parseInt($("#seg-end").value, 10) || 0,
    speaker: $("#seg-speaker").value,
    transcript: $("#seg-transcript").value,
  };
}

function scrollToSegment(seg) {
  if (!ws || !audioReady) return;
  const t = seg.start_ms / 1000;
  if (typeof ws.setScrollTime === "function") {
    ws.setScrollTime(t);
  }
}

function syncRegion(seg) {
  if (!regionsPlugin) return;

  const existing = regionMap.get(seg.id);
  if (existing) {
    existing.setOptions({
      id: String(seg.id),
      start: seg.start_ms / 1000,
      end: seg.end_ms / 1000,
      color: regionColor(seg),
      content: regionLabel(seg),
      drag: true,
      resize: true,
    });
    return;
  }

  const region = regionsPlugin.addRegion({
    id: String(seg.id),
    start: seg.start_ms / 1000,
    end: seg.end_ms / 1000,
    color: regionColor(seg),
    content: regionLabel(seg),
    drag: true,
    resize: true,
  });
  regionMap.set(seg.id, region);

  region.on("click", (e) => {
    e.stopPropagation();
    selectSegment(seg.id, false);
  });

  region.on("update-end", () => {
    const start_ms = Math.round(region.start * 1000);
    const end_ms = Math.round(region.end * 1000);
    if (end_ms <= start_ms) return;
    const idx = segments.findIndex((s) => s.id === seg.id);
    if (idx === -1) return;
    segments[idx] = { ...segments[idx], start_ms, end_ms };
    region.setOptions({ content: regionLabel(segments[idx]) });
    if (activeSegmentId === seg.id) {
      $("#seg-start").value = start_ms;
      $("#seg-end").value = end_ms;
    }
    renderSegmentList();
    debouncePersist(seg.id, { start_ms, end_ms });
  });
}

function renderAllRegions() {
  if (!regionsPlugin) return;
  regionsPlugin.clearRegions();
  regionMap.clear();
  segments.forEach(syncRegion);
}

function navigateSegment(direction) {
  const sorted = sortedSegments();
  if (!sorted.length) return;
  let idx = sorted.findIndex((s) => s.id === activeSegmentId);
  if (idx === -1) {
    selectSegment(sorted[direction > 0 ? 0 : sorted.length - 1].id, true);
    return;
  }
  const next = sorted[idx + direction];
  if (next) selectSegment(next.id, true);
}

async function playChunk(seg = activeSegment()) {
  if (!ws || !audioReady || !seg) {
    alert("Select a segment first.");
    return;
  }
  const start = seg.start_ms / 1000;
  const end = seg.end_ms / 1000;
  if (end <= start) return;
  chunkStopAt = end;
  ws.setTime(start);
  setPlaybackRate(getPlaybackRate());
  await ws.play(start, end);
}

async function togglePlayAll() {
  if (!ws || !audioReady) return;
  chunkStopAt = null;
  if (isPlaying()) {
    ws.pause();
    return;
  }
  setPlaybackRate(getPlaybackRate());
  await ws.play();
}

function skipSeconds(delta) {
  if (!ws || !audioReady) return;
  const dur = ws.getDuration();
  const t = Math.max(0, Math.min(dur, ws.getCurrentTime() + delta));
  ws.setTime(t);
  updateTimeDisplay();
}

async function selectSegment(id, seek = false) {
  activeSegmentId = id;
  const seg = segments.find((s) => s.id === id);
  if (!seg) return;
  fillPanel(seg);
  showPanel(true);
  renderSegmentList();
  refreshAllRegionStyles();
  updateNavLabel();
  scrollToSegment(seg);
  if (seek && ws && audioReady) {
    ws.setTime(seg.start_ms / 1000);
  }
}

function debouncePersist(id, fields) {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => persistSegment(id, fields, true), 400);
}

function debounceSavePanel() {
  if (!activeSegmentId) return;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => saveSegment(activeSegmentId, true), 500);
}

async function persistSegment(id, fields, silent = false) {
  const seg = segments.find((s) => s.id === id);
  if (!seg) return;
  const data = {
    start_ms: fields.start_ms ?? seg.start_ms,
    end_ms: fields.end_ms ?? seg.end_ms,
    speaker: fields.speaker ?? seg.speaker ?? "",
    transcript: fields.transcript ?? seg.transcript ?? "",
  };
  if (data.end_ms <= data.start_ms) {
    if (!silent) alert("End must be after start.");
    return;
  }
  try {
    const updated = await api(`/api/segments/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    const idx = segments.findIndex((s) => s.id === id);
    if (idx !== -1) segments[idx] = updated;
    const r = regionMap.get(id);
    if (r) r.setOptions({ content: regionLabel(updated) });
    renderSegmentList();
  } catch (e) {
    if (!silent) alert(e.message);
  }
}

async function saveSegment(id, silent = false) {
  await persistSegment(id, getPanelData(), silent);
}

async function createSegmentFromRegion(startSec, endSec) {
  const start_ms = Math.round(startSec * 1000);
  const end_ms = Math.round(endSec * 1000);
  if (end_ms - start_ms < 100) return;

  try {
    const created = await api(`/api/recordings/${RECORDING_ID}/segments`, {
      method: "POST",
      body: JSON.stringify({ start_ms, end_ms, speaker: "", transcript: "" }),
    });
    segments.push(created);
    syncRegion(created);
    renderSegmentList();
    selectSegment(created.id, false);
  } catch (e) {
    alert("Could not create segment: " + e.message);
  }
}

async function loadData() {
  const data = await api(`/api/recordings/${RECORDING_ID}`);
  segments = data.segments;
  renderSegmentList();
  if (audioReady) renderAllRegions();
}

async function saveDuration() {
  if (!ws) return;
  const duration_ms = Math.round(ws.getDuration() * 1000);
  await fetch(`/api/recordings/${RECORDING_ID}/duration`, {
    method: "PATCH",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ duration_ms: String(duration_ms) }),
  });
}

function getDurationMs() {
  return ws && audioReady ? Math.round(ws.getDuration() * 1000) : 0;
}

function defaultZoom(durSec) {
  // ~150px wide per 5-second segment, capped for very long files
  return Math.min(80, Math.max(25, 150 / 5));
}

function applyZoom(level) {
  if (!ws || !audioReady) return;
  pxPerSec = Math.max(10, Math.min(200, level));
  const dur = ws.getDuration();
  const widthPx = Math.max(800, Math.ceil(dur * pxPerSec));
  ws.setOptions({ fillParent: false, minPxPerSec: pxPerSec, width: widthPx });
  const lbl = $("#zoom-label");
  if (lbl) lbl.textContent = `${pxPerSec}px/s`;
}

function initWaveform() {
  if (typeof WaveSurfer === "undefined") {
    setStatus("Waveform library failed to load. Check your internet connection.", true);
    return;
  }
  if (!WaveSurfer.Regions) {
    setStatus("Regions plugin failed to load. Refresh the page.", true);
    return;
  }

  setStatus("Loading audio…");

  ws = WaveSurfer.create({
    container: "#waveform",
    waveColor: "#b8d4cc",
    progressColor: "#5b8f86",
    cursorColor: "#4a7a72",
    height: 180,
    barWidth: 2,
    barGap: 1,
    normalize: true,
    url: AUDIO_URL,
    fillParent: false,
    minPxPerSec: pxPerSec,
    autoScroll: true,
    autoCenter: true,
    hideScrollbar: false,
  });

  regionsPlugin = ws.registerPlugin(WaveSurfer.Regions.create());
  if (WaveSurfer.Zoom) {
    ws.registerPlugin(
      WaveSurfer.Zoom.create({ scale: 0.5, maxZoom: 200 })
    );
  }

  ws.on("ready", async () => {
    audioReady = true;
    pxPerSec = defaultZoom(ws.getDuration());
    applyZoom(pxPerSec);
    setStatus("");
    await saveDuration();
    await loadData();
    updateNavLabel();
    updateTimeDisplay();
    updateDividePreview();
    setPlaybackRate(getPlaybackRate());
  });

  ws.on("error", (err) => {
    setStatus("Failed to load audio: " + (err.message || err), true);
  });

  ws.on("audioprocess", () => {
    if (chunkStopAt != null && ws.getCurrentTime() >= chunkStopAt - 0.02) {
      ws.pause();
      ws.setTime(chunkStopAt);
      chunkStopAt = null;
    }
    updateTimeDisplay();
  });
  ws.on("seeking", updateTimeDisplay);
  ws.on("play", () => updatePlayButtons(true));
  ws.on("pause", () => {
    chunkStopAt = null;
    updatePlayButtons(false);
  });
  ws.on("finish", () => {
    chunkStopAt = null;
    updatePlayButtons(false);
  });

  regionsPlugin.on("region-created", async (region) => {
    if (region.id && segments.some((s) => String(s.id) === region.id)) return;
    const start = region.start;
    const end = region.end;
    region.remove();
    await createSegmentFromRegion(start, end);
  });
}

function updateTimeDisplay() {
  const el = $("#time-display");
  if (!el) return;
  const cur = ws && audioReady ? ws.getCurrentTime() : 0;
  const dur = ws && audioReady ? ws.getDuration() : 0;
  const seg = activeSegment();
  if (seg && chunkOnlyMode()) {
    const segStart = seg.start_ms / 1000;
    const segEnd = seg.end_ms / 1000;
    const rel = Math.max(0, Math.min(segEnd - segStart, cur - segStart));
    el.textContent = `chunk ${msToDisplay(rel * 1000)} / ${msToDisplay((segEnd - segStart) * 1000)} · full ${msToDisplay(cur * 1000)} / ${msToDisplay(dur * 1000)}`;
  } else {
    el.textContent = `${msToDisplay(cur * 1000)} / ${msToDisplay(dur * 1000)}`;
  }
}

function closePanel() {
  activeSegmentId = null;
  showPanel(false);
  renderSegmentList();
  refreshAllRegionStyles();
  updateNavLabel();
  updateTimeDisplay();
}

function setManualDrag(enabled) {
  if (!regionsPlugin) return;
  if (enabled && !dragSelectionEnabled) {
    regionsPlugin.enableDragSelection({
      color: "rgba(143, 188, 176, 0.4)",
    });
    dragSelectionEnabled = true;
    return;
  }
  if (!enabled && dragSelectionEnabled) {
    if (typeof regionsPlugin.disableDragSelection === "function") {
      regionsPlugin.disableDragSelection();
    }
    dragSelectionEnabled = false;
  }
}

async function divideChunks() {
  const duration_ms = getDurationMs();
  if (!duration_ms) return alert("Wait for the waveform to finish loading.");

  const mode = getDivideMode();
  const replace = $("#divide-replace")?.checked ?? true;

  let value;
  let unit = "seconds";
  if (mode === "count") {
    value = parseInt($("#divide-count")?.value, 10);
    if (!value || value < 1) return alert("Enter a valid chunk count (1–150).");
  } else {
    value = parseFloat($("#divide-value")?.value);
    unit = $("#divide-unit")?.value || "seconds";
    if (!value || value <= 0) return alert("Enter a valid chunk length.");
  }

  const estimated = estimateChunkCount();
  if (estimated != null && estimated > MAX_AUTO_SEGMENTS) {
    return alert(
      `This would create ~${estimated} chunks (max ${MAX_AUTO_SEGMENTS}). Use longer chunks or fewer splits.`
    );
  }

  if (!replace && segments.length > 0) {
    if (
      !confirm(
        `This adds new chunks alongside ${segments.length} existing. Check "Replace existing chunks" for a clean slate. Continue?`
      )
    ) {
      return;
    }
  } else if (replace && segments.length > 0) {
    if (!confirm(`Replace all ${segments.length} existing chunks?`)) return;
  }

  try {
    const res = await api(`/api/recordings/${RECORDING_ID}/divide-chunks`, {
      method: "POST",
      body: JSON.stringify({ mode, unit, value, replace, duration_ms }),
    });
    if (res.replaced) {
      segments = res.created;
      activeSegmentId = null;
      showPanel(false);
    } else {
      segments.push(...res.created);
    }
    renderAllRegions();
    renderSegmentList();
    refreshAllRegionStyles();
    updateNavLabel();
    setStatus(
      res.replaced
        ? `Divided into ${res.count} chunks.`
        : `Added ${res.count} chunks (${segments.length} total).`
    );
    if (segments.length === 1) selectSegment(segments[0].id, false);
  } catch (e) {
    alert(e.message);
  }
}

async function createOverlapSegment() {
  if (!activeSegmentId) return alert("Select a segment first.");
  try {
    const created = await api(
      `/api/recordings/${RECORDING_ID}/segments/overlap?source_segment_id=${activeSegmentId}`,
      { method: "POST" }
    );
    segments.push(created);
    syncRegion(created);
    renderSegmentList();
    refreshAllRegionStyles();
    selectSegment(created.id, false);

    // Visual feedback - highlight the new segment briefly
    requestAnimationFrame(() => {
      const newSegmentEl = document.querySelector(`li[data-id="${created.id}"]`);
      if (newSegmentEl) {
        newSegmentEl.classList.add("just-added");
        newSegmentEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
        setTimeout(() => newSegmentEl.classList.remove("just-added"), 1200);
      }
    });

    setStatus("Added another speaker at the same time — fill in who spoke and what they said.");
  } catch (e) {
    alert(e.message);
  }
}

async function deleteActiveSegment() {
  if (!activeSegmentId || !confirm("Delete this segment?")) return;
  await api(`/api/segments/${activeSegmentId}`, { method: "DELETE" });
  const r = regionMap.get(activeSegmentId);
  if (r) r.remove();
  regionMap.delete(activeSegmentId);
  segments = segments.filter((s) => s.id !== activeSegmentId);
  activeSegmentId = null;
  showPanel(false);
  renderSegmentList();
  refreshAllRegionStyles();
  updateNavLabel();
}

function isTypingField(target) {
  return target.matches("input, textarea, select");
}

function toggleHotkeysPanel() {
  const details = document.querySelector(".hotkeys-card details");
  if (details) details.open = !details.open;
}

async function handleHotkey(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
    e.preventDefault();
    if (activeSegmentId) saveSegment(activeSegmentId);
    return;
  }

  if (e.key === "?") {
    e.preventDefault();
    toggleHotkeysPanel();
    return;
  }

  if (isTypingField(e.target)) {
    if (e.key === "Escape") e.target.blur();
    return;
  }

  if (!ws || !audioReady) return;

  if (e.code === "Space") {
    e.preventDefault();
    if (e.shiftKey) {
      await togglePlayAll();
    } else if (chunkOnlyMode() && activeSegment()) {
      if (isPlaying()) ws.pause();
      else await playChunk();
    } else {
      await togglePlayAll();
    }
    return;
  }

  if (e.key === "c" || e.key === "C") {
    e.preventDefault();
    if (isPlaying()) ws.pause();
    else await playChunk();
    return;
  }

  if (e.key === "[" || e.key === "j" || e.key === "J") {
    e.preventDefault();
    navigateSegment(-1);
    return;
  }

  if (e.key === "]" || e.key === "k" || e.key === "K") {
    e.preventDefault();
    navigateSegment(1);
    return;
  }

  if (e.key === "Escape") {
    e.preventDefault();
    closePanel();
    return;
  }

  if (e.key === "Delete" || e.key === "Backspace") {
    e.preventDefault();
    deleteActiveSegment();
    return;
  }

  if (e.key === "+" || e.key === "=") {
    e.preventDefault();
    applyZoom(pxPerSec + 15);
    return;
  }

  if (e.key === "-") {
    e.preventDefault();
    applyZoom(pxPerSec - 15);
    return;
  }

  if (e.key === "0") {
    e.preventDefault();
    applyZoom(defaultZoom(ws.getDuration()));
    return;
  }

  if (e.key === "<" || e.key === ",") {
    e.preventDefault();
    adjustPlaybackSpeed(-1);
    return;
  }

  if (e.key === ">" || e.key === ".") {
    e.preventDefault();
    adjustPlaybackSpeed(1);
    return;
  }

  if (e.code === "ArrowLeft") {
    e.preventDefault();
    skipSeconds(e.shiftKey ? -5 : -2);
    return;
  }

  if (e.code === "ArrowRight") {
    e.preventDefault();
    skipSeconds(e.shiftKey ? 5 : 2);
  }
}

function bindControls() {
  $("#btn-prev-seg").addEventListener("click", () => navigateSegment(-1));
  $("#btn-next-seg").addEventListener("click", () => navigateSegment(1));

  $("#btn-play-chunk").addEventListener("click", async () => {
    if (!ws || !audioReady) return;
    if (isPlaying()) {
      ws.pause();
      return;
    }
    await playChunk();
  });

  $("#btn-play").addEventListener("click", () => togglePlayAll());

  $("#btn-skip-back").addEventListener("click", () => skipSeconds(-5));
  $("#btn-skip-fwd").addEventListener("click", () => skipSeconds(5));

  $("#playback-speed").addEventListener("change", (e) => {
    setPlaybackRate(parseFloat(e.target.value) || 1);
    updateSpeedLabel();
  });

  $("#btn-speed-down")?.addEventListener("click", () => adjustPlaybackSpeed(-1));
  $("#btn-speed-up")?.addEventListener("click", () => adjustPlaybackSpeed(1));
  $("#btn-panel-speed-down")?.addEventListener("click", () => adjustPlaybackSpeed(-1));
  $("#btn-panel-speed-up")?.addEventListener("click", () => adjustPlaybackSpeed(1));

  $("#chunk-only").addEventListener("change", updateTimeDisplay);

  $("#btn-zoom-in").addEventListener("click", () => applyZoom(pxPerSec + 15));
  $("#btn-zoom-out").addEventListener("click", () => applyZoom(pxPerSec - 15));
  $("#btn-zoom-fit").addEventListener("click", () => {
    if (ws && audioReady) applyZoom(defaultZoom(ws.getDuration()));
  });

  document.addEventListener("keydown", (e) => handleHotkey(e));

  $("#btn-save-seg").addEventListener("click", () => {
    if (activeSegmentId) saveSegment(activeSegmentId);
  });

  $("#btn-delete-seg").addEventListener("click", () => deleteActiveSegment());
  $("#btn-close-panel").addEventListener("click", () => closePanel());

  ["#seg-start", "#seg-end", "#seg-speaker", "#seg-transcript"].forEach((sel) => {
    $(sel).addEventListener("input", () => {
      if (!activeSegmentId) return;
      const seg = segments.find((s) => s.id === activeSegmentId);
      if (seg && sel === "#seg-speaker") {
        seg.speaker = $("#seg-speaker").value;
        refreshAllRegionStyles();
        renderSegmentList();
      }
      debounceSavePanel();
    });
  });

  $("#btn-jump-start").addEventListener("click", () => playChunk());

  $("#btn-divide").addEventListener("click", () => divideChunks());
  $("#btn-overlap-seg").addEventListener("click", () => createOverlapSegment());

  document.querySelectorAll('input[name="divide-mode"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      const isCount = getDivideMode() === "count";
      $("#divide-duration-row").hidden = isCount;
      $("#divide-count-row").hidden = !isCount;
      updateDividePreview();
    });
  });

  ["#divide-value", "#divide-count", "#divide-unit"].forEach((sel) => {
    const el = $(sel);
    if (el) {
      el.addEventListener("input", updateDividePreview);
      el.addEventListener("change", updateDividePreview);
    }
  });

  $("#manual-drag")?.addEventListener("change", (e) => {
    setManualDrag(e.target.checked);
  });

  $("#divide-replace")?.addEventListener("change", updateDividePreview);

  $("#rec-notes").addEventListener("change", async (e) => {
    await api(`/api/recordings/${RECORDING_ID}`, {
      method: "PATCH",
      body: JSON.stringify({ notes: e.target.value }),
    });
  });

  $("#btn-export").addEventListener("click", () => {
    const fmt = $("#export-format")?.value || "txt";
    window.location.href = `/api/recordings/${RECORDING_ID}/export?format=${encodeURIComponent(fmt)}`;
  });

  $("#btn-clear-segs").addEventListener("click", async () => {
    if (!segments.length || !confirm(`Delete all ${segments.length} segments?`)) return;
    await api(`/api/recordings/${RECORDING_ID}/segments`, { method: "DELETE" });
    segments = [];
    activeSegmentId = null;
    renderAllRegions();
    showPanel(false);
    renderSegmentList();
    updateNavLabel();
    setStatus("");
  });

  $("#btn-delete-rec").addEventListener("click", async () => {
    if (!confirm("Delete this recording and all segments?")) return;
    await api(`/api/recordings/${RECORDING_ID}`, { method: "DELETE" });
    window.location.href = PROJECT_ID ? `/projects/${PROJECT_ID}` : "/";
  });
}

document.addEventListener("DOMContentLoaded", () => {
  try {
    syncSpeedSelect();
    bindControls();
    initWaveform();
  } catch (e) {
    setStatus("Editor failed to start: " + e.message, true);
    console.error(e);
  }
});