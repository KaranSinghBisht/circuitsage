const path = require("node:path");
const {
  app,
  BrowserWindow,
  Menu,
  Tray,
  desktopCapturer,
  globalShortcut,
  ipcMain,
  nativeImage,
  screen,
  shell,
  systemPreferences,
} = require("electron");
const { clickPoint, getActiveWindowInfo, openAccessibilitySettings, typeText } = require("./automation");

const DEFAULT_API_URL = process.env.CIRCUITSAGE_API_URL || "http://127.0.0.1:8000";
const DEFAULT_SHORTCUT = process.env.CIRCUITSAGE_SHORTCUT || "CommandOrControl+Shift+Space";
const HIGHLIGHT_SHORTCUT = process.env.CIRCUITSAGE_HIGHLIGHT_SHORTCUT || "CommandOrControl+Shift+X";
const HIDE_DOCK = process.env.CIRCUITSAGE_SHOW_DOCK !== "1";

let mainWindow;
let tray;
let isQuitting = false;
let highlightWindow = null;
let highlightCapture = null;
let petWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 430,
    height: 740,
    minWidth: 360,
    minHeight: 520,
    title: "CircuitSage Companion",
    alwaysOnTop: true,
    frame: true,
    backgroundColor: "#0c100e",
    skipTaskbar: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
  mainWindow.on("close", (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
}

async function listSources() {
  const active = await getActiveWindowInfo().catch(() => ({ appName: "", windowName: "" }));
  const sources = await desktopCapturer.getSources({
    types: ["screen", "window"],
    thumbnailSize: { width: 1280, height: 720 },
    fetchWindowIcons: true,
  });
  return sources.map((source) => ({
    id: source.id,
    name: source.name,
    displayId: source.display_id,
    thumbnail: source.thumbnail.toDataURL(),
    appIcon: source.appIcon ? source.appIcon.toDataURL() : null,
    isActiveCandidate: Boolean(
      active.appName &&
        (source.name.toLowerCase().includes(active.appName.toLowerCase()) ||
          (active.windowName && source.name.toLowerCase().includes(active.windowName.toLowerCase())))
    ),
    activeAppName: active.appName,
    activeWindowName: active.windowName,
  }));
}

async function postCompanionAnalyze(payload) {
  const apiUrl = payload.apiUrl || DEFAULT_API_URL;
  sendPetState("thinking", "looking…");
  try {
    const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/companion/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: payload.question || "",
        image_data_url: payload.image_data_url || null,
        app_hint: payload.app_hint || "auto",
        session_id: payload.session_id || null,
        save_snapshot: Boolean(payload.save_snapshot),
        source_title: payload.source_title || "",
      }),
    });
    if (!response.ok) {
      sendPetState("cautious", "backend error");
      throw new Error(await response.text());
    }
    const data = await response.json();
    sendPetState(petStateForResponse(data), petBubbleForResponse(data));
    return data;
  } catch (error) {
    sendPetState("cautious", "couldn't reach backend");
    throw error;
  }
}

async function postCompanionRunTool(payload) {
  const apiUrl = payload.apiUrl || DEFAULT_API_URL;
  const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/companion/run-tool`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tool: payload.tool,
      args: payload.args || {},
      session_id: payload.session_id || null,
    }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function showCompanion(reason = "shortcut", extras = {}) {
  if (!mainWindow) createWindow();
  mainWindow.show();
  mainWindow.setAlwaysOnTop(true, "floating");
  mainWindow.focus();
  mainWindow.webContents.send("companion:invoke", { reason, ...extras });
}

function createPetWindow() {
  if (petWindow && !petWindow.isDestroyed()) return petWindow;
  const primary = screen.getPrimaryDisplay();
  const { width: screenW, height: screenH, x: screenX, y: screenY } = primary.workArea;
  const petW = 140;
  const petH = 160;
  petWindow = new BrowserWindow({
    x: screenX + Math.max(0, screenW - petW - 28),
    y: screenY + Math.max(0, screenH - petH - 28),
    width: petW,
    height: petH,
    frame: false,
    transparent: true,
    resizable: false,
    movable: true,
    hasShadow: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    focusable: false,
    show: false,
    title: "CircuitSage Pet",
    backgroundColor: "#00000000",
    webPreferences: {
      preload: path.join(__dirname, "pet-window-preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });
  petWindow.setAlwaysOnTop(true, "floating");
  petWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  petWindow.loadFile(path.join(__dirname, "pet-window.html"));
  petWindow.webContents.once("did-finish-load", () => {
    if (petWindow && !petWindow.isDestroyed()) petWindow.show();
  });
  petWindow.on("close", (event) => {
    if (!isQuitting) {
      event.preventDefault();
      petWindow?.hide();
    }
  });
  petWindow.on("closed", () => {
    petWindow = null;
  });
  return petWindow;
}

function sendPetState(state, bubble) {
  if (!petWindow || petWindow.isDestroyed()) return;
  try {
    petWindow.webContents.send("pet:state", state);
    if (bubble) petWindow.webContents.send("pet:bubble", bubble);
  } catch (_) {
    // window torn down between checks
  }
}

function petBubbleForResponse(response) {
  if (!response || typeof response !== "object") return "";
  if (response.mode === "safety_refusal") return "Stopped — high-voltage risk";
  if (response.gemma_error) return "Vision unavailable";
  const topology = response.detected_topology;
  const confidence = response.confidence;
  if (topology && topology !== "unknown") {
    return `${topology.replace(/_/g, " ")} · ${confidence || "?"}`;
  }
  if (Array.isArray(response.suspected_faults) && response.suspected_faults.length) {
    return response.suspected_faults[0].slice(0, 60);
  }
  return confidence ? `confidence: ${confidence}` : "got something";
}

function petStateForResponse(response) {
  if (!response) return "cautious";
  if (response.mode === "safety_refusal") return "refused";
  if (response.gemma_error) return "cautious";
  const conf = String(response.confidence || "").toLowerCase();
  if (conf === "high" || conf === "medium_high" || conf === "medium-high") return "found";
  if (conf === "medium") return "found";
  return "cautious";
}

function closeHighlight() {
  if (highlightWindow && !highlightWindow.isDestroyed()) {
    try {
      highlightWindow.close();
    } catch (_) {
      // window already closing
    }
  }
  highlightWindow = null;
  highlightCapture = null;
}

async function startHighlight(reason = "shortcut") {
  if (highlightWindow) return; // already in the middle of one
  let display;
  try {
    display = screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
  } catch (_) {
    display = screen.getPrimaryDisplay();
  }
  const { bounds, scaleFactor } = display;

  const physicalW = Math.max(1, Math.round(bounds.width * scaleFactor));
  const physicalH = Math.max(1, Math.round(bounds.height * scaleFactor));

  let sources;
  try {
    sources = await desktopCapturer.getSources({
      types: ["screen"],
      thumbnailSize: { width: physicalW, height: physicalH },
    });
  } catch (error) {
    console.error("[highlight] desktopCapturer failed:", error);
    return;
  }

  const source =
    sources.find((s) => String(s.display_id) === String(display.id)) || sources[0];
  if (!source || !source.thumbnail) {
    console.error("[highlight] no screen source available");
    return;
  }
  const fullImage = source.thumbnail;
  highlightCapture = { fullImage, bounds, scaleFactor, reason };

  highlightWindow = new BrowserWindow({
    x: bounds.x,
    y: bounds.y,
    width: bounds.width,
    height: bounds.height,
    transparent: false,
    backgroundColor: "#00000000",
    frame: false,
    resizable: false,
    movable: false,
    skipTaskbar: true,
    fullscreenable: false,
    hasShadow: false,
    alwaysOnTop: true,
    show: false,
    focusable: true,
    webPreferences: {
      preload: path.join(__dirname, "highlight-overlay-preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });
  highlightWindow.setAlwaysOnTop(true, "screen-saver");
  highlightWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  highlightWindow.loadFile(path.join(__dirname, "highlight-overlay.html"));

  highlightWindow.webContents.once("did-finish-load", () => {
    if (!highlightWindow || highlightWindow.isDestroyed()) return;
    highlightWindow.webContents.send("highlight:backdrop", fullImage.toDataURL());
    highlightWindow.show();
    highlightWindow.focus();
  });

  highlightWindow.on("closed", () => {
    highlightWindow = null;
  });
}

function createTray() {
  const icon = nativeImage.createFromDataURL(
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABFUlEQVR4AWP4//8/Ay0xw6gFo2AUjIJRMApGQbAAYoKZmRkGRkYGBkZGZgYGBsa/f/8YGBj+//9fQGJiooGRkZEhKSmpgYGBgYGB4f///wwMDP/+/WMgNDTUwMjIyMDIyMjAv3//GBgY/v//T0BsbKwBkpaWloGxsTEGhoaGBgYGBoZ///4xMDA8f/6cgYGB4f///wwMDE+ePGEgNDQ0w8DAwMDIyMjAv3//GBgY/v//T0BsbKwBkpaWloGxsTEGhoaGBgYGBoZ///4xMDA8f/6cgYGB4f///wwMDE+ePGEgNDQ0w8DAwMDIyMjAv3//GBgY/v//T0BsbKwBkpaWlgGyYhSMglEwCkbBKBgFo2AUjAJRAABdS0SR2Z6V8gAAAABJRU5ErkJggg=="
  );
  tray = new Tray(icon);
  tray.setToolTip(`CircuitSage Companion (${DEFAULT_SHORTCUT})`);
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: `Ask CircuitSage (${DEFAULT_SHORTCUT})`, click: () => showCompanion("tray") },
      { label: `Highlight region (${HIGHLIGHT_SHORTCUT})`, click: () => startHighlight("tray").catch(console.error) },
      {
        label: "Toggle desktop pet",
        click: () => {
          if (!petWindow || petWindow.isDestroyed()) {
            createPetWindow();
          } else if (petWindow.isVisible()) {
            petWindow.hide();
          } else {
            petWindow.show();
          }
        },
      },
      { type: "separator" },
      { label: "Screen Recording Permission", click: () => shell.openExternal("x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture") },
      { label: "Accessibility Permission", click: () => shell.openExternal("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") },
      { type: "separator" },
      {
        label: "Quit",
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ])
  );
  tray.on("click", () => showCompanion("tray"));
}

app.whenReady().then(() => {
  if (HIDE_DOCK && app.dock) {
    app.dock.hide();
  }
  createWindow();
  createTray();
  createPetWindow();
  globalShortcut.register(DEFAULT_SHORTCUT, () => showCompanion("shortcut"));
  globalShortcut.register(HIGHLIGHT_SHORTCUT, () => startHighlight("shortcut").catch(console.error));

  ipcMain.on("pet:showCompanion", () => showCompanion("pet"));
  ipcMain.on("pet:startHighlight", () => {
    startHighlight("pet").catch(console.error);
  });
  ipcMain.on("pet:openMenu", () => {
    const menu = Menu.buildFromTemplate([
      { label: "Open companion", click: () => showCompanion("pet") },
      { label: `Highlight region (${HIGHLIGHT_SHORTCUT})`, click: () => startHighlight("pet").catch(console.error) },
      { type: "separator" },
      { label: "Hide pet", click: () => petWindow?.hide() },
      {
        label: "Quit",
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ]);
    if (petWindow && !petWindow.isDestroyed()) {
      menu.popup({ window: petWindow });
    }
  });

  ipcMain.on("highlight:cancel", () => closeHighlight());
  ipcMain.on("highlight:complete", (_event, rect) => {
    if (!highlightCapture || !rect) {
      closeHighlight();
      return;
    }
    const { fullImage, scaleFactor } = highlightCapture;
    const size = fullImage.getSize();
    const physicalRect = {
      x: Math.max(0, Math.min(size.width - 1, Math.round(rect.x * scaleFactor))),
      y: Math.max(0, Math.min(size.height - 1, Math.round(rect.y * scaleFactor))),
      width: Math.max(1, Math.round(rect.width * scaleFactor)),
      height: Math.max(1, Math.round(rect.height * scaleFactor)),
    };
    physicalRect.width = Math.min(physicalRect.width, size.width - physicalRect.x);
    physicalRect.height = Math.min(physicalRect.height, size.height - physicalRect.y);
    let cropped;
    try {
      cropped = fullImage.crop(physicalRect);
    } catch (error) {
      console.error("[highlight] crop failed:", error, physicalRect, size);
      closeHighlight();
      showCompanion("highlight_crop_error");
      return;
    }
    const croppedDataUrl = cropped.toDataURL();
    closeHighlight();
    showCompanion("highlight", { image_data_url: croppedDataUrl });
  });

  ipcMain.handle("sources:list", listSources);
  ipcMain.handle("context:activeWindow", () => getActiveWindowInfo());
  ipcMain.handle("companion:analyze", (_event, payload) => postCompanionAnalyze(payload));
  ipcMain.handle("companion:runTool", (_event, payload) => postCompanionRunTool(payload));
  ipcMain.handle("shell:openExternal", (_event, url) => shell.openExternal(url));
  ipcMain.handle("window:alwaysOnTop", (_event, value) => {
    mainWindow?.setAlwaysOnTop(Boolean(value), "floating");
    return Boolean(value);
  });
  ipcMain.handle("window:compact", (_event, value) => {
    if (!mainWindow) return false;
    if (value) {
      mainWindow.setSize(380, 540, true);
    } else {
      mainWindow.setSize(430, 740, true);
    }
    return Boolean(value);
  });
  ipcMain.handle("permissions:open", (_event, kind) => {
    if (kind === "screen") {
      shell.openExternal("x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture");
      return systemPreferences.getMediaAccessStatus?.("screen") || "unknown";
    }
    if (kind === "accessibility") {
      shell.openExternal("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility");
      return openAccessibilitySettings();
    }
    return "unknown";
  });
  ipcMain.handle("automation:click", (_event, point) => clickPoint(Number(point.x), Number(point.y)));
  ipcMain.handle("automation:type", (_event, text) => typeText(String(text)));
  ipcMain.handle("window:hide", () => {
    mainWindow?.hide();
    return true;
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  isQuitting = true;
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
});
