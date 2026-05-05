const state = {
  sources: [],
  selected: null,
  lastImage: "",
  timer: null,
  recognition: null,
  listening: false,
};

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setStatus(text, live = false) {
  $("statusDot").textContent = text;
  $("statusDot").classList.toggle("live", live);
}

function renderResult(result) {
  $("result").innerHTML = `
    <div class="result-meta">${escapeHtml(result.mode || "analysis")} · ${escapeHtml(result.confidence || "unknown")} confidence</div>
    <h2>${escapeHtml(result.workspace || "workspace")}</h2>
    <p>${escapeHtml(result.visible_context || "")}</p>
    <strong>${escapeHtml(result.answer || "")}</strong>
    <ol>${(result.next_actions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
    ${result.gemma_error ? `<small class="error">${escapeHtml(result.gemma_error)}</small>` : ""}
  `;
}

function setGlow(enabled) {
  document.body.classList.toggle("watch-glow", enabled);
}

function showCommandOverlay() {
  $("commandOverlay").classList.remove("hidden");
  $("quickQuestion").focus();
  setGlow(true);
}

function hideCommandOverlay() {
  $("commandOverlay").classList.add("hidden");
  setGlow($("autoWatch").checked);
}

async function refreshSources() {
  setStatus("scanning", true);
  state.sources = await window.circuitSage.getSources();
  $("sourceSelect").innerHTML = state.sources
    .map((source) => `<option value="${escapeHtml(source.id)}">${escapeHtml(source.name)}</option>`)
    .join("");
  state.selected = state.sources.find((source) => source.isActiveCandidate) || state.sources[0] || null;
  if (state.selected) {
    $("sourceSelect").value = state.selected.id;
    updatePreview();
  }
  setStatus("ready");
}

function updatePreview() {
  const sourceId = $("sourceSelect").value;
  state.selected = state.sources.find((source) => source.id === sourceId) || state.sources[0] || null;
  if (!state.selected) return;
  state.lastImage = state.selected.thumbnail;
  $("preview").src = state.lastImage;
}

async function refreshSelectedThumbnail() {
  const selectedId = $("sourceSelect").value;
  state.sources = await window.circuitSage.getSources();
  state.selected = state.sources.find((source) => source.id === selectedId) || state.sources[0] || null;
  if (!state.selected) return;
  $("sourceSelect").innerHTML = state.sources
    .map((source) => `<option value="${escapeHtml(source.id)}">${escapeHtml(source.name)}</option>`)
    .join("");
  $("sourceSelect").value = state.selected.id;
  updatePreview();
}

async function selectActiveSource() {
  setStatus("finding active", true);
  const active = await window.circuitSage.getActiveWindow().catch(() => null);
  state.sources = await window.circuitSage.getSources();
  const app = active?.appName?.toLowerCase() || "";
  const windowName = active?.windowName?.toLowerCase() || "";
  const match =
    state.sources.find((source) => source.isActiveCandidate) ||
    state.sources.find((source) => app && source.name.toLowerCase().includes(app)) ||
    state.sources.find((source) => windowName && source.name.toLowerCase().includes(windowName)) ||
    state.sources[0];
  $("sourceSelect").innerHTML = state.sources
    .map((source) => `<option value="${escapeHtml(source.id)}">${source.isActiveCandidate ? "● " : ""}${escapeHtml(source.name)}</option>`)
    .join("");
  if (match) {
    $("sourceSelect").value = match.id;
    state.selected = match;
    updatePreview();
  }
  setStatus(active?.appName ? `current: ${active.appName}` : "ready", Boolean(active?.appName));
}

async function analyze() {
  setStatus("thinking", true);
  try {
    await refreshSelectedThumbnail();
    const result = await window.circuitSage.analyze({
      apiUrl: $("apiUrl").value,
      question: $("question").value,
      image_data_url: state.lastImage,
      app_hint: $("appHint").value,
      session_id: $("sessionId").value,
      save_snapshot: $("saveSnapshot").checked,
    });
    renderResult(result);
    setStatus("ready");
  } catch (error) {
    $("result").innerHTML = `<h2>Could not analyze</h2><p class="error">${escapeHtml(error.message || error)}</p>`;
    setStatus("error");
  }
}

async function quickAnalyze() {
  $("question").value = $("quickQuestion").value;
  await selectActiveSource();
  await analyze();
  hideCommandOverlay();
}

function setAutoWatch(enabled) {
  window.clearInterval(state.timer);
  state.timer = null;
  if (enabled) {
    state.timer = window.setInterval(() => {
      refreshSelectedThumbnail().catch(() => undefined);
    }, 3500);
    setStatus("watching", true);
    setGlow(true);
  } else {
    setStatus("ready");
    setGlow(false);
  }
}

function startVoice(targetId) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    $("result").innerHTML = "<h2>Voice unavailable</h2><p class=\"error\">This Electron runtime does not expose Web Speech recognition. Type the prompt for now.</p>";
    return;
  }
  if (state.recognition && state.listening) {
    state.recognition.stop();
    return;
  }
  const recognition = new SpeechRecognition();
  state.recognition = recognition;
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = "en-US";
  state.listening = true;
  setStatus("listening", true);
  setGlow(true);
  recognition.onresult = (event) => {
    const text = Array.from(event.results)
      .map((result) => result[0]?.transcript || "")
      .join(" ")
      .trim();
    if (text) $(targetId).value = text;
  };
  recognition.onend = () => {
    state.listening = false;
    setStatus($("autoWatch").checked ? "watching" : "ready", $("autoWatch").checked);
    setGlow($("autoWatch").checked || !$("commandOverlay").classList.contains("hidden"));
  };
  recognition.onerror = (event) => {
    state.listening = false;
    $("result").innerHTML = `<h2>Voice failed</h2><p class="error">${escapeHtml(event.error || "speech recognition error")}</p>`;
  };
  recognition.start();
}

$("refreshSources").addEventListener("click", () => refreshSources().catch(console.error));
$("activeSource").addEventListener("click", () => selectActiveSource().catch(console.error));
$("sourceSelect").addEventListener("change", updatePreview);
$("analyze").addEventListener("click", () => analyze().catch(console.error));
$("autoWatch").addEventListener("change", (event) => setAutoWatch(event.target.checked));
$("alwaysTop").addEventListener("change", (event) => window.circuitSage.setAlwaysOnTop(event.target.checked));
$("compactMode").addEventListener("change", (event) => window.circuitSage.setCompact(event.target.checked));
$("screenPerm").addEventListener("click", () => window.circuitSage.openPermissions("screen"));
$("accessPerm").addEventListener("click", () => window.circuitSage.openPermissions("accessibility"));
$("voicePrompt").addEventListener("click", () => startVoice("question"));
$("hideWindow").addEventListener("click", () => window.circuitSage.hide());
$("quickVoice").addEventListener("click", () => startVoice("quickQuestion"));
$("quickAnalyze").addEventListener("click", () => quickAnalyze().catch(console.error));
$("quickClose").addEventListener("click", hideCommandOverlay);

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    hideCommandOverlay();
  }
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    const visible = !$("commandOverlay").classList.contains("hidden");
    (visible ? quickAnalyze() : analyze()).catch(console.error);
  }
});

window.circuitSage.onInvoke(() => {
  showCommandOverlay();
  selectActiveSource().catch(() => undefined);
});

refreshSources().catch((error) => {
  $("result").innerHTML = `<h2>Screen capture unavailable</h2><p class="error">${escapeHtml(error.message || error)}</p>`;
  setStatus("permission needed");
});
