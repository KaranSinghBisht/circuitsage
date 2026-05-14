const stage = document.getElementById("stage");
const bubble = document.getElementById("bubble");
const clickZone = document.getElementById("clickZone");

const STATES = ["idle", "watching", "thinking", "found", "cautious", "refused"];
const TRANSIENT = new Set(["thinking", "found", "cautious", "refused"]);
const IDLE_TIMEOUT_MS = 9000;
const BUBBLE_TIMEOUT_MS = 6000;

let idleTimer = null;
let bubbleTimer = null;
let clickTimer = null;
let pendingClicks = 0;

function setState(next) {
  const state = STATES.includes(next) ? next : "idle";
  STATES.forEach((s) => stage.classList.remove(s));
  stage.classList.add(state);
  if (idleTimer) {
    clearTimeout(idleTimer);
    idleTimer = null;
  }
  if (TRANSIENT.has(state)) {
    idleTimer = setTimeout(() => setState("idle"), IDLE_TIMEOUT_MS);
  }
}

function showBubble(text) {
  if (!text) {
    stage.classList.remove("has-bubble");
    return;
  }
  bubble.textContent = String(text).slice(0, 80);
  stage.classList.add("has-bubble");
  if (bubbleTimer) clearTimeout(bubbleTimer);
  bubbleTimer = setTimeout(() => stage.classList.remove("has-bubble"), BUBBLE_TIMEOUT_MS);
}

window.circuitSagePet?.onState?.((state) => setState(state));
window.circuitSagePet?.onBubble?.((text) => showBubble(text));

clickZone.addEventListener("click", () => {
  pendingClicks += 1;
  if (clickTimer) clearTimeout(clickTimer);
  clickTimer = setTimeout(() => {
    const clicks = pendingClicks;
    pendingClicks = 0;
    clickTimer = null;
    if (clicks >= 2) {
      window.circuitSagePet?.startHighlight?.();
    } else if (clicks === 1) {
      window.circuitSagePet?.showCompanion?.();
    }
  }, 260);
});

clickZone.addEventListener("contextmenu", (event) => {
  event.preventDefault();
  window.circuitSagePet?.openMenu?.();
});

setState("idle");
