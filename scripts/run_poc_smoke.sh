#!/usr/bin/env bash
# ESAA Supervisor PoC — Smoke Test Script
# Usage: bash scripts/run_poc_smoke.sh
# Requer: Python 3.11+, dependencias instaladas (pip install -r backend/requirements.txt)

set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$BASE_DIR/backend"
PORT=8099
BASE_URL="http://127.0.0.1:$PORT"
PASS=0
FAIL=0

check() {
  local label="$1"
  local result="$2"
  local expected="$3"
  # Strip spaces for compact-JSON compatibility
  local stripped_result; stripped_result=$(echo "$result" | tr -d ' ')
  local stripped_expected; stripped_expected=$(echo "$expected" | tr -d ' ')
  if echo "$stripped_result" | grep -qF "$stripped_expected"; then
    echo "  [PASS] $label"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $label"
    echo "         Expected substring: $expected"
    echo "         Got: $(echo "$result" | head -c 300)"
    FAIL=$((FAIL + 1))
  fi
}

check_status() {
  local label="$1"
  local actual_code="$2"
  local expected_code="$3"
  if [ "$actual_code" = "$expected_code" ]; then
    echo "  [PASS] $label (HTTP $actual_code)"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $label (expected HTTP $expected_code, got $actual_code)"
    FAIL=$((FAIL + 1))
  fi
}

echo "================================================"
echo " ESAA Supervisor PoC — Smoke Test"
echo "================================================"

# Kill any stale server on the port
echo ""
echo "[SETUP] Killing any existing process on port $PORT..."
if command -v fuser &>/dev/null; then
  fuser -k "${PORT}/tcp" 2>/dev/null || true
fi

echo "[SETUP] Starting backend on port $PORT..."
cd "$BACKEND_DIR"
python -m uvicorn app.main:app --host 127.0.0.1 --port $PORT --log-level warning &
SERVER_PID=$!
sleep 4

cleanup() {
  echo ""
  echo "[CLEANUP] Stopping backend (PID $SERVER_PID)..."
  kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

# ─── Step 1: Health check ──────────────────────────────────────────────────
echo ""
echo "--- Step 1: Health check ---"
R=$(curl -s "$BASE_URL/")
check "GET / returns running" "$R" '"status":"running"'

# ─── Step 2: Project discovery ────────────────────────────────────────────
echo ""
echo "--- Step 2: Project discovery ---"
R=$(curl -s "$BASE_URL/api/v1/projects/")
check "GET /projects/ returns project list" "$R" '"id"'
check "Project is_active=true" "$R" '"is_active":true'

PROJECT_ID=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null || echo "poc-project")
echo "  Project ID: $PROJECT_ID"

# ─── Step 3: State consolidado ────────────────────────────────────────────
echo ""
echo "--- Step 3: State consolidado ---"
R=$(curl -s "$BASE_URL/api/v1/projects/$PROJECT_ID/state/")
check "GET /state returns tasks array" "$R" '"tasks"'
check "GET /state returns is_consistent field" "$R" '"is_consistent"'
check "GET /state returns eligible_task_ids" "$R" '"eligible_task_ids"'

# ─── Step 4: Elegibilidade ────────────────────────────────────────────────
echo ""
echo "--- Step 4: Eligibility report ---"
R=$(curl -s "$BASE_URL/api/v1/projects/$PROJECT_ID/runs/eligibility")
check "GET /eligibility returns eligible_count" "$R" '"eligible_count"'
check "GET /eligibility returns tasks array" "$R" '"tasks"'

ELIGIBLE=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin)['eligible_count'])" 2>/dev/null || echo "?")
echo "  Eligible tasks: $ELIGIBLE"

# ─── Step 5: /runs/next com task in_progress (sem elegíveis) ──────────────
echo ""
echo "--- Step 5: POST /runs/next (no eligible tasks expected) ---"
# QA-017 is in_progress (this smoke IS QA-017), so no tasks are eligible.
# The API must correctly reject with 422.
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/projects/$PROJECT_ID/runs/next" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "smoke-test"}')
check_status "POST /runs/next correctly rejects (422) when no eligible task" "$HTTP_CODE" "422"

R=$(curl -s -X POST "$BASE_URL/api/v1/projects/$PROJECT_ID/runs/next" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "smoke-test"}')
check "422 body contains rejection detail" "$R" '"detail"'

# ─── Step 6: /runs/task com task bloqueada ────────────────────────────────
echo ""
echo "--- Step 6: POST /runs/task (blocked task QA-018) ---"
# QA-018 depends on QA-017 (in_progress). Must return 422 with message.
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/projects/$PROJECT_ID/runs/task" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "ESUP-QA-018", "agent_id": "smoke-test"}')
check_status "POST /runs/task blocked task correctly rejected (422)" "$HTTP_CODE" "422"

R=$(curl -s -X POST "$BASE_URL/api/v1/projects/$PROJECT_ID/runs/task" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "ESUP-QA-018", "agent_id": "smoke-test"}')
check "422 body contains message field" "$R" '"message"'

# ─── Step 7: GET /runs/{id} inexistente ───────────────────────────────────
echo ""
echo "--- Step 7: GET /runs/{bogus} — run not found ---"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/projects/$PROJECT_ID/runs/bogus-run-id-000")
check_status "GET /runs/{bogus} returns 404" "$HTTP_CODE" "404"

# ─── Step 8: DELETE /runs/{id} inexistente ────────────────────────────────
echo ""
echo "--- Step 8: DELETE /runs/{bogus} — run not found ---"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL/api/v1/projects/$PROJECT_ID/runs/bogus-run-id-000")
check_status "DELETE /runs/{bogus} returns 404" "$HTTP_CODE" "404"

echo ""
echo "================================================"
echo " RESULTADO: $PASS passed, $FAIL failed"
echo "================================================"
[ $FAIL -eq 0 ] && exit 0 || exit 1
