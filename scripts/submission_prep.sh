#!/usr/bin/env bash
#
# submission_prep.sh — One-command pre-submission readiness check.
#
# Runs every gate the SUBMISSION_CHECKLIST.md mentions that can be verified
# automatically, then prints a green/red dashboard so you know what is left
# before you click submit on Kaggle.
#
# Usage:
#   bash scripts/submission_prep.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

green="\033[0;32m"
red="\033[0;31m"
yellow="\033[0;33m"
dim="\033[2m"
reset="\033[0m"

pass=0
fail=0
warn=0
results=()

log_pass() {
  results+=("${green}✓${reset} $1")
  pass=$((pass + 1))
}
log_fail() {
  results+=("${red}✗${reset} $1")
  fail=$((fail + 1))
}
log_warn() {
  results+=("${yellow}!${reset} $1")
  warn=$((warn + 1))
}

# ── Code health ────────────────────────────────────────────────────────────────
echo "[1/8] Backend tests..."
if CIRCUITSAGE_EMBED_FALLBACK=bow PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests --tb=line -q > /tmp/circuitsage_pytest.log 2>&1; then
  log_pass "Backend tests pass ($(grep -E 'passed' /tmp/circuitsage_pytest.log | tail -1))"
else
  log_fail "Backend tests failed (see /tmp/circuitsage_pytest.log)"
fi

echo "[2/8] Frontend build..."
if npm --prefix frontend run build > /tmp/circuitsage_fe.log 2>&1; then
  log_pass "Frontend build passes"
else
  log_fail "Frontend build failed (see /tmp/circuitsage_fe.log)"
fi

echo "[3/8] Desktop syntax check..."
if npm --prefix apps/desktop run check > /tmp/circuitsage_desktop.log 2>&1; then
  log_pass "Desktop check passes (8 JS files including pet + highlight)"
else
  log_fail "Desktop check failed (see /tmp/circuitsage_desktop.log)"
fi

echo "[4/8] iOS typecheck..."
if npm --prefix apps/ios run check > /tmp/circuitsage_ios.log 2>&1; then
  log_pass "iOS typecheck passes"
else
  log_warn "iOS typecheck failed or skipped (see /tmp/circuitsage_ios.log)"
fi

# ── Submission artifacts ───────────────────────────────────────────────────────
echo "[5/8] Required documents..."
for doc in \
  README.md \
  docs/KAGGLE_WRITEUP_DRAFT.md \
  docs/DEMO_SCRIPT.md \
  docs/SUBMISSION_CHECKLIST.md \
  docs/HOSTED_OLLAMA_MODAL.md \
  scripts/deploy_ollama_modal.py \
  train/kaggle_kernel/UNSLOTH_TEMPLATE_INSTRUCTIONS.md \
  train/kaggle_kernel/circuitsage_lora_v9.py
do
  if [ -f "$doc" ]; then
    log_pass "$doc present"
  else
    log_fail "$doc MISSING"
  fi
done

WRITEUP_WORDS=$(wc -w < docs/KAGGLE_WRITEUP_DRAFT.md | tr -d ' ')
if [ "$WRITEUP_WORDS" -le 2200 ]; then
  log_pass "Writeup ${WRITEUP_WORDS} words (soft cap 1500, accepted up to 2200)"
else
  log_warn "Writeup ${WRITEUP_WORDS} words — over 2200, trim before submit"
fi

# ── Demo readiness ─────────────────────────────────────────────────────────────
echo "[6/8] Demo media..."
if [ -f media/cover.png ]; then
  log_pass "Cover image present"
else
  log_warn "media/cover.png missing"
fi
SCREENSHOT_COUNT=$(ls media/screenshots/*.png 2>/dev/null | wc -l | tr -d ' ')
if [ "$SCREENSHOT_COUNT" -ge 6 ]; then
  log_pass "${SCREENSHOT_COUNT} demo screenshots present"
else
  log_warn "${SCREENSHOT_COUNT} screenshots present — demo script targets 8+"
fi
if [ -f media/demo.mp4 ] || [ -f media/demo.mov ] || [ -f media/demo_hero.gif ]; then
  log_pass "Demo video / hero gif file present"
else
  log_fail "No demo video file in media/ — REQUIRED for submission"
fi

# ── Local environment ──────────────────────────────────────────────────────────
echo "[7/8] Runtime environment..."
if [ -f .env ]; then
  if grep -q "modal.run" .env; then
    log_pass ".env points at Modal-hosted Ollama"
  elif grep -q "localhost:11434" .env; then
    log_warn ".env points at local Ollama (fine for dev, may not be reachable for judges)"
  else
    log_warn ".env exists but OLLAMA_BASE_URL ambiguous"
  fi
else
  log_warn ".env missing — backend will use defaults"
fi

# ── Distribution / publication ────────────────────────────────────────────────
echo "[8/8] Distribution status..."
LOCAL_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")
REMOTE_HEAD=$(git rev-parse origin/master 2>/dev/null || echo "")
if [ -z "$REMOTE_HEAD" ]; then
  log_fail "No origin/master tracked — push not configured. Run: git push -u origin master"
elif [ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]; then
  AHEAD=$(git rev-list --count "${REMOTE_HEAD}..${LOCAL_HEAD}" 2>/dev/null || echo "?")
  log_fail "Local is ${AHEAD} commits ahead of origin/master — JUDGES WILL SEE STALE CODE. Run: git push origin master"
else
  log_pass "origin/master is up to date"
fi

UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [ "$UNCOMMITTED" -eq 0 ]; then
  log_pass "Working tree clean"
else
  log_warn "${UNCOMMITTED} uncommitted changes — commit before pushing"
fi

echo "  ↳ probing Kaggle URLs..."
KAGGLE_URLS=(
  "https://www.kaggle.com/datasets/karansinghbisht/circuitsage-faults-v1|dataset"
  "https://www.kaggle.com/code/karansinghbisht/circuitsage-eval|eval kernel"
  "https://www.kaggle.com/code/karansinghbisht/circuitsage-gemma-lora|training kernel"
  "https://www.kaggle.com/code/karansinghbisht/circuitsage-writeup|writeup"
)
for entry in "${KAGGLE_URLS[@]}"; do
  url="${entry%%|*}"
  label="${entry##*|}"
  rc=$(curl -s -o /dev/null -w "%{http_code}" "$url")
  if [ "$rc" = "200" ]; then
    log_pass "Kaggle ${label} live (200)"
  else
    log_fail "Kaggle ${label} returns ${rc} — toggle to PUBLIC in Kaggle web UI: ${url}/settings"
  fi
done

echo "  ↳ probing GitHub URL..."
GH_RC=$(curl -s -o /dev/null -w "%{http_code}" https://github.com/KaranSinghBisht/circuitsage)
if [ "$GH_RC" = "200" ]; then
  log_pass "GitHub repo public (200)"
else
  log_fail "GitHub repo returns ${GH_RC} — toggle to PUBLIC at https://github.com/KaranSinghBisht/circuitsage/settings"
fi

# ── Report ─────────────────────────────────────────────────────────────────────
echo
echo -e "${dim}─────────────────────────────────────────${reset}"
echo -e "${green}${pass} pass${reset}  ${yellow}${warn} warn${reset}  ${red}${fail} fail${reset}"
echo -e "${dim}─────────────────────────────────────────${reset}"
for line in "${results[@]}"; do
  echo -e "  $line"
done
echo
if [ "$fail" -gt 0 ]; then
  echo -e "${red}NOT READY${reset} — fix ${fail} red items before submission."
  exit 1
fi
if [ "$warn" -gt 0 ]; then
  echo -e "${yellow}READY WITH CAVEATS${reset} — review ${warn} yellow items."
  exit 0
fi
echo -e "${green}READY TO SUBMIT.${reset}"
