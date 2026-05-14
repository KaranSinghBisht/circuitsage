const state = {
  sources: [],
  selected: null,
  lastImage: "",
  timer: null,
  recognition: null,
  listening: false,
  analyzing: false,
  lastAutoAnalyzeAt: 0,
  lastActions: [],
  lastSessionId: null,
  usingPreCaptured: false,
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
  const typedActions = Array.isArray(result.actions) ? result.actions : [];
  const topology = result.detected_topology && result.detected_topology !== "unknown"
    ? ` · ${escapeHtml(result.detected_topology)}`
    : "";
  const durationLabel = result.duration_ms ? ` · ${result.duration_ms} ms` : "";
  const suspectedHtml = Array.isArray(result.suspected_faults) && result.suspected_faults.length > 0
    ? `<ul class="suspected">${result.suspected_faults.map((fault) => `<li>${escapeHtml(fault)}</li>`).join("")}</ul>`
    : "";
  const buttonsHtml = typedActions.length > 0
    ? `<div class="action-row">${typedActions
        .map((action, idx) => {
          const label = escapeHtml(action.label || "Action");
          const dataset = `data-idx="${idx}"`;
          return `<button class="action-chip" ${dataset}>${label}</button>`;
        })
        .join("")}</div><div id="actionResults"></div>`
    : `<ol>${(result.next_actions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>`;

  $("result").innerHTML = `
    <div class="result-meta">${escapeHtml(result.mode || "analysis")} · ${escapeHtml(result.confidence || "unknown")} confidence${durationLabel}</div>
    <h2>${escapeHtml(result.workspace || "workspace")}${topology}</h2>
    <p>${escapeHtml(result.visible_context || "")}</p>
    <strong>${escapeHtml(result.answer || "")}</strong>
    ${suspectedHtml}
    ${buttonsHtml}
    ${result.gemma_error ? `<small class="error">${escapeHtml(result.gemma_error)}</small>` : ""}
  `;

  if (typedActions.length > 0) {
    state.lastActions = typedActions;
    state.lastSessionId = result.session_id || null;
    document.querySelectorAll("#result .action-chip").forEach((button) => {
      button.addEventListener("click", () => runAction(Number(button.dataset.idx)));
    });
  }
}

async function runAction(index) {
  const action = (state.lastActions || [])[index];
  if (!action) return;
  if (action.action === "capture") {
    quickAnalyze().catch(console.error);
    return;
  }
  if (action.action === "measurement") {
    appendActionResult(action.label, { hint: "Open Bench Mode to log this measurement, then re-ask.", args: action.args });
    return;
  }
  const tool = action.args && action.args.tool;
  if (!tool || !["score_faults", "lookup_datasheet", "retrieve_rag"].includes(tool)) {
    appendActionResult(action.label, { error: "Unknown tool" });
    return;
  }
  const args = { ...(action.args || {}) };
  delete args.tool;
  delete args.already_ran;
  try {
    const response = await window.circuitSage.runTool({
      tool,
      args,
      session_id: state.lastSessionId,
    });
    appendActionResult(action.label, response.result);
  } catch (error) {
    appendActionResult(action.label, { error: error.message || String(error) });
  }
}

function appendActionResult(label, value) {
  const container = $("actionResults");
  if (!container) return;
  const block = document.createElement("pre");
  block.className = "action-result";
  block.innerHTML = `<strong>${escapeHtml(label)}</strong>\n${escapeHtml(JSON.stringify(value, null, 2).slice(0, 1200))}`;
  container.appendChild(block);
}

function setGlow(enabled) {
  document.body.classList.toggle("watch-glow", enabled);
}

function inferWorkspace(source) {
  const text = `${source?.name || ""} ${source?.activeAppName || ""} ${source?.activeWindowName || ""}`.toLowerCase();
  if (text.includes("tinkercad") || text.includes("arduino")) return "tinkercad";
  if (text.includes("ltspice") || text.includes("spice")) return "ltspice";
  if (text.includes("matlab") || text.includes("simulink")) return "matlab";
  return "electronics_workspace";
}

function selectedAppHint() {
  const requested = $("appHint").value;
  return requested === "auto" ? inferWorkspace(state.selected) : requested;
}

function setWatchContext(prefix = "Watching") {
  if (!state.selected) {
    $("watchContext").textContent = "Waiting for a screen or window.";
    return;
  }
  const sourceName = state.selected.name || "selected source";
  const activeName = state.selected.activeAppName ? ` · active app: ${state.selected.activeAppName}` : "";
  const workspace = selectedAppHint().replaceAll("_", " ");
  $("watchContext").textContent = `${prefix}: ${sourceName}${activeName} · ${workspace}`;
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
  setWatchContext("Selected");
  setStatus("ready");
}

function updatePreview() {
  const sourceId = $("sourceSelect").value;
  state.selected = state.sources.find((source) => source.id === sourceId) || state.sources[0] || null;
  if (!state.selected) return;
  state.lastImage = state.selected.thumbnail;
  $("preview").src = state.lastImage;
  setWatchContext("Selected");
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

async function selectActiveSource(options = {}) {
  if (!options.quiet) setStatus("finding active", true);
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
  setWatchContext(active?.appName ? "Following" : "Selected");
  if (!options.quiet) setStatus(active?.appName ? `current: ${active.appName}` : "ready", Boolean(active?.appName));
}

async function analyze(options = {}) {
  if (state.analyzing) return;
  state.analyzing = true;
  let originalQuestion = "";
  setStatus("thinking", true);
  try {
    if (state.usingPreCaptured) {
      // lastImage is already the highlighted crop; do not recapture or it'll clobber.
    } else if ($("followActive").checked || options.followActive) {
      await selectActiveSource({ quiet: true });
    } else {
      await refreshSelectedThumbnail();
    }
    originalQuestion = $("question").value;
    if (options.passive) {
      $("question").value = "Watch this workspace and summarize what changed, what looks risky, and the next useful check.";
    }
    const result = await window.circuitSage.analyze({
      apiUrl: $("apiUrl").value,
      question: $("question").value,
      image_data_url: state.lastImage,
      app_hint: selectedAppHint(),
      source_title: state.selected?.name || "",
      session_id: $("sessionId").value,
      save_snapshot: $("saveSnapshot").checked,
    });
    renderResult(result);
    setStatus($("autoWatch").checked ? "watching" : "ready", $("autoWatch").checked);
  } catch (error) {
    $("result").innerHTML = `<h2>Could not analyze</h2><p class="error">${escapeHtml(error.message || error)}</p>`;
    setStatus("error");
  } finally {
    if (options.passive) $("question").value = originalQuestion;
    state.usingPreCaptured = false;
    state.analyzing = false;
  }
}

async function quickAnalyze() {
  $("question").value = $("quickQuestion").value;
  if (!state.usingPreCaptured) {
    await selectActiveSource();
  }
  await analyze();
  hideCommandOverlay();
}

function setAutoWatch(enabled) {
  window.clearInterval(state.timer);
  state.timer = null;
  if (enabled) {
    state.timer = window.setInterval(() => {
      const refresh = $("followActive").checked ? selectActiveSource({ quiet: true }) : refreshSelectedThumbnail();
      refresh
        .then(() => {
          const shouldAutoAnalyze = $("autoInsight").checked && Date.now() - state.lastAutoAnalyzeAt > 25000;
          if (shouldAutoAnalyze) {
            state.lastAutoAnalyzeAt = Date.now();
            return analyze({ passive: true, followActive: true });
          }
          return undefined;
        })
        .catch(() => undefined);
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
$("followActive").addEventListener("change", () => setWatchContext($("followActive").checked ? "Following" : "Selected"));
$("autoInsight").addEventListener("change", () => {
  state.lastAutoAnalyzeAt = 0;
  if ($("autoWatch").checked && $("autoInsight").checked) analyze({ passive: true, followActive: true }).catch(console.error);
});
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

window.circuitSage.onInvoke((payload) => {
  if (payload && payload.image_data_url) {
    // Highlight flow: main process already captured + cropped. Skip recapture.
    state.usingPreCaptured = true;
    state.lastImage = payload.image_data_url;
    state.selected = {
      id: "highlight-crop",
      name: "Highlight selection",
      thumbnail: payload.image_data_url,
      activeAppName: "",
      activeWindowName: "",
    };
    const previewEl = $("preview");
    if (previewEl) previewEl.src = payload.image_data_url;
    setWatchContext("Highlight");
    setStatus("highlight ready", true);
    showCommandOverlay();
    // Pre-fill a default question and auto-fire after a 700 ms grace period.
    // If the user starts typing inside the grace window we skip auto-fire and
    // let them submit manually. Turns the highlight gesture into a single
    // "drag → answer" beat for the demo.
    const quick = $("quickQuestion");
    if (quick && !quick.value.trim()) {
      quick.value = "What is wrong with this part of the circuit?";
    }
    const initialQuestion = quick ? quick.value : "";
    window.setTimeout(() => {
      const stillUnchanged = quick && quick.value === initialQuestion;
      if (stillUnchanged && state.usingPreCaptured && !state.analyzing) {
        quickAnalyze().catch(console.error);
      }
    }, 700);
    return;
  }
  state.usingPreCaptured = false;
  showCommandOverlay();
  selectActiveSource().catch(() => undefined);
});

refreshSources().catch((error) => {
  $("result").innerHTML = `<h2>Screen capture unavailable</h2><p class="error">${escapeHtml(error.message || error)}</p>`;
  setStatus("permission needed");
});
