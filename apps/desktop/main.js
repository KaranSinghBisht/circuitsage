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
  shell,
  systemPreferences,
} = require("electron");
const { clickPoint, getActiveWindowInfo, openAccessibilitySettings, typeText } = require("./automation");

const DEFAULT_API_URL = process.env.CIRCUITSAGE_API_URL || "http://127.0.0.1:8000";
const DEFAULT_SHORTCUT = process.env.CIRCUITSAGE_SHORTCUT || "CommandOrControl+Shift+Space";

let mainWindow;
let tray;
let isQuitting = false;

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
  const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/companion/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: payload.question || "",
      image_data_url: payload.image_data_url || null,
      app_hint: payload.app_hint || "auto",
      session_id: payload.session_id || null,
      save_snapshot: Boolean(payload.save_snapshot),
    }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function showCompanion(reason = "shortcut") {
  if (!mainWindow) createWindow();
  mainWindow.show();
  mainWindow.setAlwaysOnTop(true, "floating");
  mainWindow.focus();
  mainWindow.webContents.send("companion:invoke", { reason });
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
  createWindow();
  createTray();
  globalShortcut.register(DEFAULT_SHORTCUT, () => showCompanion("shortcut"));

  ipcMain.handle("sources:list", listSources);
  ipcMain.handle("context:activeWindow", () => getActiveWindowInfo());
  ipcMain.handle("companion:analyze", (_event, payload) => postCompanionAnalyze(payload));
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
