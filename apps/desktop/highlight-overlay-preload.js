const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("circuitSageHighlight", {
  onBackdrop: (callback) => {
    ipcRenderer.removeAllListeners("highlight:backdrop");
    ipcRenderer.on("highlight:backdrop", (_event, dataUrl) => callback(dataUrl));
  },
  complete: (rect) => ipcRenderer.send("highlight:complete", rect),
  cancel: () => ipcRenderer.send("highlight:cancel"),
});
