files=(input/*.glb)

if [ ${#files[@]} -eq 0 ]; then
  echo "input/ 폴더에 GLB 파일이 없습니다."
  exit 1
fi

echo "처리할 파일을 선택하세요:"
select f in "${files[@]}"; do
  if [ -n "$f" ]; then
    python3 run_pipeline.py \
      --input "$f" \
      --output "output/simple_$(basename "$f")" \
      --blender /Applications/Blender.app/Contents/MacOS/Blender
    break
  else
    echo "올바른 번호를 입력하세요."
  fi
done
