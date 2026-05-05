const { execFile } = require("node:child_process");
const { promisify } = require("node:util");

const execFileAsync = promisify(execFile);

async function runAppleScript(script) {
  const { stdout, stderr } = await execFileAsync("osascript", ["-e", script], { timeout: 5000 });
  return { stdout: stdout.trim(), stderr: stderr.trim() };
}

async function clickPoint(x, y) {
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    throw new Error("Invalid click coordinates");
  }
  return runAppleScript(`tell application "System Events" to click at {${Math.round(x)}, ${Math.round(y)}}`);
}

async function typeText(text) {
  const safe = String(text).replaceAll("\\", "\\\\").replaceAll('"', '\\"');
  return runAppleScript(`tell application "System Events" to keystroke "${safe}"`);
}

async function openAccessibilitySettings() {
  return runAppleScript('tell application "System Settings" to activate');
}

async function getActiveWindowInfo() {
  const script = `
    tell application "System Events"
      set frontApp to first application process whose frontmost is true
      set appName to name of frontApp
      set windowName to ""
      try
        set windowName to name of front window of frontApp
      end try
      return appName & "||" & windowName
    end tell
  `;
  const { stdout } = await runAppleScript(script);
  const [appName = "", windowName = ""] = stdout.split("||");
  return { appName, windowName };
}

module.exports = {
  clickPoint,
  getActiveWindowInfo,
  openAccessibilitySettings,
  typeText,
};
