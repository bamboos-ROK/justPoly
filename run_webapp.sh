#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/backend/.venv"
VENV_PIP="$VENV/bin/pip"
VENV_PYTHON="$VENV/bin/python"

# ── 유틸 ────────────────────────────────────────────────────────────────────
info()  { echo "  $1"; }
ok()    { echo "  ✓ $1"; }
step()  { echo; echo "▶ $1"; }

# ── Python 감지 ──────────────────────────────────────────────────────────────
detect_python() {
  for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
      echo "$cmd"; return
    fi
  done
  echo ""
}

# ── 백엔드 의존성 체크 ───────────────────────────────────────────────────────
step "백엔드 의존성 확인 중..."

if [ ! -f "$VENV/bin/uvicorn" ]; then
  info "가상환경이 없습니다. 생성합니다..."
  PY=$(detect_python)
  if [ -z "$PY" ]; then
    echo "  ✕ Python 3.10+ 이 설치되어 있지 않습니다. 설치 후 다시 실행하세요." >&2
    exit 1
  fi
  "$PY" -m venv "$VENV"
  info "의존성을 설치합니다 (backend/requirements.txt)..."
  "$VENV_PIP" install --quiet -r "$ROOT/backend/requirements.txt"
  ok "백엔드 가상환경 준비 완료"
else
  # 이미 venv가 있어도 requirements.txt 변경 여부 확인
  REQ="$ROOT/backend/requirements.txt"
  STAMP="$VENV/.req_stamp"
  if [ "$REQ" -nt "$STAMP" ]; then
    info "requirements.txt 변경 감지 → 업데이트 중..."
    "$VENV_PIP" install --quiet -r "$REQ"
    touch "$STAMP"
    ok "백엔드 의존성 업데이트 완료"
  else
    ok "백엔드 의존성 최신 상태"
  fi
fi
# 최초 설치 후 stamp 생성
[ ! -f "$VENV/.req_stamp" ] && touch "$VENV/.req_stamp"

# ── 프론트엔드 의존성 체크 ──────────────────────────────────────────────────
step "프론트엔드 의존성 확인 중..."

if ! command -v node &>/dev/null; then
  echo "  ✕ Node.js 가 설치되어 있지 않습니다. https://nodejs.org 에서 설치 후 다시 실행하세요." >&2
  exit 1
fi

FRONTEND="$ROOT/frontend"
if [ ! -d "$FRONTEND/node_modules" ]; then
  info "node_modules 없음. npm install 실행 중..."
  npm --prefix "$FRONTEND" install --silent
  ok "프론트엔드 의존성 설치 완료"
else
  # package.json 변경 여부 확인
  if [ "$FRONTEND/package.json" -nt "$FRONTEND/node_modules/.package_stamp" ]; then
    info "package.json 변경 감지 → npm install 실행 중..."
    npm --prefix "$FRONTEND" install --silent
    touch "$FRONTEND/node_modules/.package_stamp"
    ok "프론트엔드 의존성 업데이트 완료"
  else
    ok "프론트엔드 의존성 최신 상태"
  fi
fi
[ ! -f "$FRONTEND/node_modules/.package_stamp" ] && touch "$FRONTEND/node_modules/.package_stamp"

# ── 서버 실행 ────────────────────────────────────────────────────────────────
step "서버 시작..."

"$VENV/bin/uvicorn" backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

npm --prefix "$FRONTEND" run dev &
FRONTEND_PID=$!

echo
echo "  ✓ 백엔드:  http://localhost:8000"
echo "  ✓ 프론트:  http://localhost:5173"
echo
echo "  종료하려면 Ctrl+C"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo ''; echo '  서버 종료'" EXIT
wait
