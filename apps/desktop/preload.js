const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("circuitSage", {
  getSources: () => ipcRenderer.invoke("sources:list"),
  getActiveWindow: () => ipcRenderer.invoke("context:activeWindow"),
  analyze: (payload) => ipcRenderer.invoke("companion:analyze", payload),
  runTool: (payload) => ipcRenderer.invoke("companion:runTool", payload),
  openExternal: (url) => ipcRenderer.invoke("shell:openExternal", url),
  openPermissions: (kind) => ipcRenderer.invoke("permissions:open", kind),
  clickPoint: (point) => ipcRenderer.invoke("automation:click", point),
  typeText: (text) => ipcRenderer.invoke("automation:type", text),
  setAlwaysOnTop: (value) => ipcRenderer.invoke("window:alwaysOnTop", value),
  setCompact: (value) => ipcRenderer.invoke("window:compact", value),
  hide: () => ipcRenderer.invoke("window:hide"),
  onInvoke: (callback) => {
    ipcRenderer.removeAllListeners("companion:invoke");
    ipcRenderer.on("companion:invoke", (_event, payload) => callback(payload));
  },
});
