# GLB Optimizer

GLB 3D 모델을 업로드하면 QEM 메시 경량화 + Cage Baking 텍스처를 자동으로 처리하고, Before/After를 웹 브라우저에서 바로 비교할 수 있는 도구입니다.

---

## 주요 기능

- **드래그 앤 드롭 업로드** — 100MB+ GLB 파일 스트리밍 업로드
- **파이프라인 자동 실행** — QEM 메시 축약 + Cage Baking 텍스처 베이킹
- **실시간 진행 표시** — 3단계(Extract → Simplify → Bake) 상태 모니터링
- **Before/After 비교 뷰어** — Three.js 듀얼 캔버스, 카메라 동기화
- **Wireframe / Bounding Box 토글**

---

## 파이프라인 구조

```
GLB 업로드
    ↓
Stage 1 — Extract (Blender)
  GLB → 고폴리 OBJ + metadata.json

Stage 2 — Simplify (Open3D)
  QEM 기반 메시 축약 (기본값: 원본의 10%)

Stage 3 — Bake & Export (Blender)
  UV 생성 + Cage Baking + GLB 내보내기
    ↓
output/{uuid}/output.glb
```

---

## 요구 사항

| 항목 | 버전 |
|------|------|
| Python | 3.10 이상 |
| Node.js | 18 이상 |
| Blender | 3.x 이상 (시스템에 설치 필요) |
| open3d | requirements.txt 참고 |

---

## 설치 및 실행

### 1. 저장소 클론

```bash
git clone <repo-url>
cd simplify_justin
```

### 2. Blender 경로 설정

`.env` 파일을 열어 실제 Blender 바이너리 경로를 입력합니다.

```bash
# .env
BLENDER_PATH=/Applications/Blender.app/Contents/MacOS/Blender
```

### 3. 실행

```bash
./run_webapp.sh
```

**이것으로 끝입니다.** 나머지는 스크립트가 자동으로 처리합니다.

- Python 가상환경(`backend/.venv`)이 없으면 자동 생성
- `backend/requirements.txt` 변경 감지 시 자동으로 `pip install`
- `frontend/node_modules`가 없으면 자동으로 `npm install`
- `frontend/package.json` 변경 감지 시 자동으로 `npm install`
- Node.js 또는 Python 3.10+가 없으면 설치 안내 후 종료

브라우저에서 **[http://localhost:5173](http://localhost:5173)** 접속.

> **파이프라인 전용 가상환경** (`open3d` 포함) 은 최초 실행 시 `run_pipeline.sh` 가 별도로 생성합니다.

---

## 사용 방법

### 1. On Progress 페이지

1. GLB 파일을 업로드 영역에 드래그 앤 드롭 (또는 클릭하여 선택)
2. 파라미터를 조정합니다.
   - **삼각형 비율** — 원본 대비 유지할 삼각형 수 비율 (기본 10%)
   - **텍스처 비율** — 원본 텍스처 크기 대비 출력 해상도 (기본 50%)
   - **High Poly Cleanup 스킵** — AI 생성 메시의 내부 잡면 정리 생략
   - **Cage Baking 스킵** — Cage 없이 단순 ray casting 베이킹
3. 업로드 완료 후 파이프라인이 자동 시작됩니다.
4. 3단계 진행 상황이 실시간으로 표시됩니다.
5. 완료 후 **결과 비교 보기** 버튼을 누릅니다.

### 2. Outputs 페이지

완료된 모든 결과물 목록을 확인할 수 있습니다. 카드를 클릭하면 Inspector로 이동합니다.

### 3. Inspector 페이지

| 기능 | 설명 |
|------|------|
| Before / After | 원본과 최적화 결과를 나란히 비교 |
| Wireframe | 메시 구조를 와이어프레임으로 표시 |
| Bounding Box | 모델 경계 상자 표시 |
| 카메라 동기화 | 두 뷰어의 카메라를 연동 |

---

## 파일 구조

```
simplify_justin/
├── backend/              # FastAPI 백엔드
│   ├── main.py           # API 엔드포인트
│   ├── pipeline.py       # subprocess 실행 + 상태 추적
│   ├── models.py         # Pydantic 모델
│   └── config.py         # 환경변수 (BLENDER_PATH 등)
├── frontend/             # React + Vite 프론트엔드
│   └── src/
│       ├── pages/        # OnProgress / Outputs / Inspector
│       └── components/
│           └── GLBInspector/  # Three.js 듀얼 뷰어
├── run_pipeline.py       # CLI 파이프라인 오케스트레이터
├── extract_for_qem.py    # Blender: GLB → OBJ 추출
├── qem_simplify.py       # Open3D: QEM 메시 축약
├── bake_export.py        # Blender: 텍스처 베이킹 + GLB 내보내기
├── staging/              # 업로드된 원본 GLB (런타임 생성)
├── output/               # 처리 완료된 GLB
├── .env                  # 환경변수
└── run_webapp.sh         # 웹앱 실행 스크립트
```

---

## CLI 직접 실행

웹 UI 없이 터미널에서 직접 파이프라인을 실행할 수 있습니다.

```bash
./run_pipeline.sh
```

또는 파라미터를 직접 지정:

```bash
python run_pipeline.py \
  --input input/model.glb \
  --output output/model_opt.glb \
  --tris-ratio 0.1 \
  --texture-ratio 0.5 \
  --blender /Applications/Blender.app/Contents/MacOS/Blender
```

---

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/upload?filename=x.glb` | GLB 스트리밍 업로드 |
| POST | `/jobs` | 파이프라인 시작 |
| GET | `/jobs/{job_id}` | 잡 상태 조회 |
| GET | `/outputs` | 완료된 파일 목록 |
| GET | `/files/staging/{id}/input.glb` | 원본 GLB 서빙 |
| GET | `/files/output/{id}/output.glb` | 결과 GLB 서빙 |

대화형 API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)
