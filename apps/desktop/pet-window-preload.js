const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("circuitSagePet", {
  onState: (callback) => {
    ipcRenderer.removeAllListeners("pet:state");
    ipcRenderer.on("pet:state", (_event, state) => callback(state));
  },
  onBubble: (callback) => {
    ipcRenderer.removeAllListeners("pet:bubble");
    ipcRenderer.on("pet:bubble", (_event, text) => callback(text));
  },
  showCompanion: () => ipcRenderer.send("pet:showCompanion"),
  startHighlight: () => ipcRenderer.send("pet:startHighlight"),
  openMenu: () => ipcRenderer.send("pet:openMenu"),
});
