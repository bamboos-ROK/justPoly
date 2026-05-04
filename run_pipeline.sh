SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python3"

PYTHON3_BIN=$(command -v python3.11 || command -v python3.12 || command -v python3.10)
if [ -z "$PYTHON3_BIN" ]; then
  echo "Python 3.10 이상이 필요합니다. 'brew install python@3.11'로 설치하세요."
  exit 1
fi

if [ ! -f "$PYTHON" ]; then
  echo "가상환경을 처음 설정합니다... ($PYTHON3_BIN)"
  "$PYTHON3_BIN" -m venv "$SCRIPT_DIR/.venv"
  "$SCRIPT_DIR/.venv/bin/pip" install --upgrade pip -q
fi

"$SCRIPT_DIR/.venv/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"

files=(input/*.glb)

if [ ${#files[@]} -eq 0 ]; then
  echo "input/ 폴더에 GLB 파일이 없습니다."
  exit 1
fi

echo "처리할 파일을 선택하세요:"
select f in "${files[@]}"; do
  if [ -n "$f" ]; then
    "$PYTHON" run_pipeline.py \
      --input "$f" \
      --output "output/simple_$(basename "$f")" \
      --blender /Applications/Blender.app/Contents/MacOS/Blender
    break
  else
    echo "올바른 번호를 입력하세요."
  fi
done
