#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8000}"
BASE_URL="http://127.0.0.1:${PORT}"
BACKEND_PY="${BACKEND_PY:-${ROOT}/backend/.venv/bin/python}"
UVICORN="${UVICORN:-${ROOT}/backend/.venv/bin/uvicorn}"
LOG_FILE="${LOG_FILE:-/tmp/circuitsage-demo-smoke.log}"
PID=""
FAILED=0

SEEDS=(
  "op-amp"
  "rc-lowpass"
  "voltage-divider"
  "bjt-common-emitter"
  "op-amp-noninverting"
  "full-wave-rectifier"
  "active-highpass"
  "integrator"
  "differentiator"
  "schmitt-trigger"
  "timer-555-astable"
  "nmos-low-side"
  "instrumentation-amplifier"
)

cleanup() {
  if [[ -n "${PID}" ]] && kill -0 "${PID}" >/dev/null 2>&1; then
    kill "${PID}" >/dev/null 2>&1 || true
    wait "${PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

green() {
  printf "GREEN %-58s %s\n" "$1" "$2"
}

red() {
  printf "RED   %-58s %s\n" "$1" "$2"
  FAILED=1
}

require_file() {
  if [[ ! -x "$1" ]]; then
    red "preflight $1" "missing executable"
    exit 1
  fi
}

extract_json_field() {
  "${BACKEND_PY}" -c 'import json,sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"
}

assert_nonempty_educator() {
  "${BACKEND_PY}" -c '
import json, sys
body = json.load(sys.stdin)
assert body.get("total_sessions", 0) > 0
assert body.get("common_faults")
assert body.get("stalled_measurements")
'
}

require_file "${BACKEND_PY}"
require_file "${UVICORN}"

cd "${ROOT}"
rm -f "${LOG_FILE}"
CIRCUITSAGE_EMBED_FALLBACK="${CIRCUITSAGE_EMBED_FALLBACK:-bow}" \
PYTHONPATH="${ROOT}/backend" \
"${UVICORN}" app.main:app --host 127.0.0.1 --port "${PORT}" >"${LOG_FILE}" 2>&1 &
PID="$!"

for _ in {1..40}; do
  if curl -fsS "${BASE_URL}/api/health" >/dev/null 2>&1; then
    green "GET /api/health" "backend ready on ${BASE_URL}"
    break
  fi
  if ! kill -0 "${PID}" >/dev/null 2>&1; then
    red "backend startup" "process exited; see ${LOG_FILE}"
    exit 1
  fi
  sleep 0.25
done

if ! curl -fsS "${BASE_URL}/api/health" >/dev/null 2>&1; then
  red "GET /api/health" "backend did not become ready; see ${LOG_FILE}"
  exit 1
fi

FIRST_SESSION_ID=""
for slug in "${SEEDS[@]}"; do
  path="/api/sessions/seed/${slug}"
  if response="$(curl -fsS -X POST "${BASE_URL}${path}")"; then
    session_id="$(printf "%s" "${response}" | extract_json_field id)"
    if [[ -n "${session_id}" ]]; then
      FIRST_SESSION_ID="${FIRST_SESSION_ID:-${session_id}}"
      green "POST ${path}" "${session_id}"
    else
      red "POST ${path}" "missing session id"
    fi
  else
    red "POST ${path}" "request failed"
  fi
done

if overview="$(curl -fsS "${BASE_URL}/api/educator/overview")" && printf "%s" "${overview}" | assert_nonempty_educator; then
  green "GET /api/educator/overview" "non-empty aggregates"
else
  red "GET /api/educator/overview" "empty or invalid aggregates"
fi

if [[ -n "${FIRST_SESSION_ID}" ]]; then
  pdf_path="/tmp/circuitsage-demo-smoke-${FIRST_SESSION_ID}.pdf"
  if curl -fsS -o "${pdf_path}" "${BASE_URL}/api/sessions/${FIRST_SESSION_ID}/report.pdf" \
    && [[ "$(head -c 4 "${pdf_path}")" == "%PDF" ]]; then
    green "GET /api/sessions/${FIRST_SESSION_ID}/report.pdf" "pdf ok"
  else
    red "GET /api/sessions/${FIRST_SESSION_ID}/report.pdf" "pdf failed"
  fi
else
  red "GET /api/sessions/<id>/report.pdf" "no seeded session id"
fi

exit "${FAILED}"
