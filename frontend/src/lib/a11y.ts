export const focusableSelector = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export function trapEscape(event: KeyboardEvent, close: () => void) {
  if (event.key === "Escape") close();
}
