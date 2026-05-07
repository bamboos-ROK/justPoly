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

# ── Blender 설치 확인 ───────────────────────────────────────────────────────
step "Blender 설치 확인 중..."

detect_blender() {
  # 1) config.py 기본 하드코딩 경로 (macOS 기준)
  DEFAULT_BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
  if [ -x "$DEFAULT_BLENDER" ]; then
    echo "$DEFAULT_BLENDER"
    return
  fi

  # 2) .env 파일의 BLENDER_PATH 확인
  if [ -f "$ROOT/.env" ]; then
    ENV_BLENDER_PATH=$(grep -E '^BLENDER_PATH=' "$ROOT/.env" | cut -d '=' -f2- | tr -d '"' | tr -d "'")
    if [ -n "$ENV_BLENDER_PATH" ] && [ -x "$ENV_BLENDER_PATH" ]; then
      echo "$ENV_BLENDER_PATH"
      return
    fi
  fi

  echo ""
}

BLENDER=$(detect_blender)

if [ -z "$BLENDER" ]; then
  echo "  ✕ Blender를 찾을 수 없습니다.$BLENDER" >&2
  echo "    확인 순서:" >&2
  echo "    1. 기본 경로(MacOS): /Applications/Blender.app/Contents/MacOS/Blender" >&2
  echo "    2. .env 의 BLENDER_PATH" >&2
  echo "" >&2
  echo "    Blender 설치: https://www.blender.org/download/" >&2
  exit 1
fi

export BLENDER_PATH="$BLENDER"
ok "Blender 확인 완료: $BLENDER"

# ── Python 감지 ──────────────────────────────────────────────────────────────
detect_python() {
  for cmd in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
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

# ── 기존 프로세스 확인 ──────────────────────────────────────────────────────
step "포트 사용 현황 확인 중..."

OCCUPIED_PORTS=()
for port in 8000 5173; do
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    OCCUPIED_PORTS+=("$port")
    info "포트 $port 사용 중 (PID: $pids)"
  fi
done

if [ ${#OCCUPIED_PORTS[@]} -gt 0 ]; then
  echo
  printf "  위 포트를 점유 중인 프로세스를 종료하고 계속하시겠습니까? [Y/n] "
  read -r answer
  case "$answer" in
    [yY]|[yY][eE][sS])
      for port in "${OCCUPIED_PORTS[@]}"; do
        pids=$(lsof -ti:"$port" 2>/dev/null || true)
        [ -n "$pids" ] && echo "$pids" | xargs kill -9 2>/dev/null || true
        info "포트 $port 프로세스 종료"
      done
      ok "포트 정리 완료"
      ;;
    *)
      echo "  취소되었습니다." >&2
      exit 1
      ;;
  esac
else
  ok "사용 중인 포트 없음"
fi

# ── 서버 실행 ────────────────────────────────────────────────────────────────
step "서버 시작..."

"$VENV/bin/uvicorn" backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

npm --prefix "$FRONTEND" run dev &
FRONTEND_PID=$!

# ── 프론트엔드 서버 준비 대기 ───────────────────────────────────────────────
step "프론트엔드 서버 준비 대기 중..."

until curl -s http://localhost:5173 >/dev/null; do
  sleep 1
done

ok "프론트엔드 서버 준비 완료"

# ── 브라우저 자동 실행 (OS 감지) ────────────────────────────────────────────
step "브라우저 실행 중..."

if command -v open >/dev/null 2>&1; then
  # macOS
  open http://localhost:5173
elif command -v xdg-open >/dev/null 2>&1; then
  # Linux
  xdg-open http://localhost:5173 >/dev/null 2>&1 &
elif command -v start >/dev/null 2>&1; then
  # Windows (Git Bash 등)
  start http://localhost:5173
else
  info "브라우저 자동 실행을 지원하지 않는 환경입니다."
  info "수동 접속: http://localhost:5173"
fi

echo
echo "  ✓ 백엔드:  http://localhost:8000"
echo "  ✓ 프론트:  http://localhost:5173"
echo
echo "  종료하려면 Ctrl+C"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo ''; echo '  서버 종료'" EXIT
wait