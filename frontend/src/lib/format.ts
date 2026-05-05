export function titleize(value: string | undefined) {
  return (value ?? "unknown").replaceAll("_", " ");
}

export function pct(value: number | undefined) {
  return `${Math.round((value ?? 0) * 100)}%`;
}
