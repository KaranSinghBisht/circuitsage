const rect = document.getElementById("rect");
const backdrop = document.getElementById("backdrop");
const dims = document.getElementById("dims");
const scrim = document.getElementById("scrim");

let dragging = false;
let startX = 0;
let startY = 0;

window.circuitSageHighlight?.onBackdrop?.((dataUrl) => {
  if (!dataUrl) return;
  backdrop.style.backgroundImage = `url(${dataUrl})`;
  backdrop.style.opacity = "1";
  scrim.style.background = "rgba(0,0,0,0.35)";
});

function clampToViewport(value, max) {
  return Math.max(0, Math.min(max, value));
}

function drawRect(currentX, currentY) {
  const x = Math.min(currentX, startX);
  const y = Math.min(currentY, startY);
  const w = Math.abs(currentX - startX);
  const h = Math.abs(currentY - startY);
  rect.style.left = `${x}px`;
  rect.style.top = `${y}px`;
  rect.style.width = `${w}px`;
  rect.style.height = `${h}px`;
  rect.style.display = "block";
  dims.style.display = "block";
  dims.textContent = `${Math.round(w)} × ${Math.round(h)}`;
  const dimsX = clampToViewport(x + w + 8, window.innerWidth - 80);
  const dimsY = clampToViewport(y + h + 8, window.innerHeight - 30);
  dims.style.left = `${dimsX}px`;
  dims.style.top = `${dimsY}px`;
  return { x, y, width: w, height: h };
}

document.addEventListener("mousedown", (event) => {
  if (event.button !== 0) return;
  dragging = true;
  startX = event.clientX;
  startY = event.clientY;
  drawRect(event.clientX, event.clientY);
});

document.addEventListener("mousemove", (event) => {
  if (!dragging) return;
  drawRect(event.clientX, event.clientY);
});

document.addEventListener("mouseup", (event) => {
  if (!dragging) return;
  dragging = false;
  const rectInfo = drawRect(event.clientX, event.clientY);
  if (rectInfo.width < 12 || rectInfo.height < 12) {
    window.circuitSageHighlight?.cancel?.();
    return;
  }
  window.circuitSageHighlight?.complete?.(rectInfo);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    window.circuitSageHighlight?.cancel?.();
  }
});

window.addEventListener("blur", () => {
  // If the user clicks away or the overlay loses focus mid-drag, cancel.
  if (dragging) {
    dragging = false;
    window.circuitSageHighlight?.cancel?.();
  }
});
