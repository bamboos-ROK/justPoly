# GLB Optimizer

GLB 3D 모델을 업로드하고 QEM 메시 경량화 + Cage Baking 텍스처 베이킹을 실행한 뒤, Before/After 결과를 웹 브라우저에서 비교할 수 있는 로컬 웹 도구입니다.

현재 버전은 **단일 파일 업로드 + 단일 파일 변환 job** 구조입니다. 멀티 파일 업로드/변환 큐 설계는 [MULTI_FILE_REFACTOR_PRD.md](MULTI_FILE_REFACTOR_PRD.md)에 별도로 정리되어 있으며 아직 적용 전입니다.

---

## 주요 기능

- **단일 GLB 업로드** — 드래그 앤 드롭 또는 파일 선택으로 `.glb` 1개 업로드
- **스트리밍 업로드** — 백엔드가 요청 body를 chunk 단위로 받아 디스크에 직접 저장
- **수동 파이프라인 시작** — 업로드 완료 후 파라미터를 확인하고 `경량화 시작` 버튼으로 변환 실행
- **진행 상태 표시** — Extract → Simplify → Bake 3단계 상태 polling
- **Before/After 비교 뷰어** — Three.js 기반 듀얼 GLB viewer
- **Wireframe / Bounding Box / 카메라 동기화 토글**
- **Outputs 페이지** — `data/output` 폴더의 완료된 GLB 파일 목록 표시

---

## 현재 처리 흐름

```text
1. 사용자가 /progress 페이지에서 GLB 파일 1개 선택
2. Frontend가 POST /upload?filename={filename} 요청
3. Backend가 data/staging/{job_id}.glb에 원본 저장
4. Backend가 메모리 job 생성(status=uploading)
5. 사용자가 파라미터를 확인하고 "경량화 시작" 클릭
6. Frontend가 POST /jobs { job_id, params } 요청
7. Backend가 BackgroundTasks로 pipeline 실행(status=running)
8. run_pipeline.py가 Extract → Simplify → Bake 순서로 처리
9. Backend가 data/output/{job_id}.glb 생성(status=done)
10. Frontend가 GET /jobs/{job_id} polling으로 상태 갱신
11. 완료 후 Before/After 비교 보기
```

---

## 파이프라인 구조

```text
Input GLB
  ↓
Stage 1 — Extract (Blender)
  GLB → QEM용 OBJ + metadata.json

Stage 2 — Simplify (Python/Open3D)
  QEM 기반 메시 축약
  기본값: 원본 삼각형 수의 10%

Stage 3 — Bake & Export (Blender)
  원본 high GLB + low OBJ
  → texture baking
  → output GLB export
  ↓
Output GLB
```

웹앱에서 실제 실행되는 오케스트레이터는 [backend/scripts/run_pipeline.py](backend/scripts/run_pipeline.py)입니다.

---

## 요구 사항

| 항목 | 버전/조건 |
|------|-----------|
| Python | 3.10 이상 |
| Node.js | 18 이상 |
| Blender | 시스템에 설치 필요 |
| Python deps | [backend/requirements.txt](backend/requirements.txt) 참고 |

기본 Blender 경로는 [backend/config.py](backend/config.py)에 정의되어 있습니다.

```text
/Applications/Blender.app/Contents/MacOS/Blender
```

다른 경로를 사용한다면 `.env`에 `BLENDER_PATH`를 설정합니다.

---

## 설치 및 실행

### 1. 저장소 준비

```bash
git clone <repo-url>
cd simplify_justin
```

이미 로컬에 저장소가 있다면 해당 디렉토리에서 실행하면 됩니다.

### 2. Blender 경로 설정

필요한 경우 `.env` 파일을 생성하거나 수정합니다.

```bash
BLENDER_PATH=/Applications/Blender.app/Contents/MacOS/Blender
```

### 3. 웹앱 실행

```bash
./run_webapp.sh
```

`run_webapp.sh`는 다음을 자동 처리합니다.

- `backend/.venv`가 없으면 Python 가상환경 생성
- `backend/requirements.txt` 변경 시 백엔드 의존성 설치/업데이트
- `frontend/node_modules`가 없으면 `npm install`
- `frontend/package.json` 변경 시 프론트엔드 의존성 업데이트
- FastAPI backend와 Vite frontend 동시 실행

실행 후 브라우저에서 접속합니다.

```text
Frontend: http://localhost:5173
Backend:  http://localhost:8000
API Docs: http://localhost:8000/docs
```

---

## 사용 방법

### 1. On Progress 페이지

1. GLB 파일 1개를 업로드 영역에 드래그 앤 드롭하거나 클릭해서 선택합니다.
2. 업로드가 완료되면 파일명이 표시됩니다.
3. 변환 파라미터를 조정합니다.
4. `경량화 시작` 버튼을 누릅니다.
5. Extract → Simplify → Bake 단계 진행 상태를 확인합니다.
6. 완료 후 `결과 비교 보기` 버튼으로 Before/After viewer를 엽니다.

현재 파라미터:

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| 삼각형 비율 | 원본 대비 유지할 삼각형 수 비율 | 10% |
| 텍스처 비율 | 원본 텍스처 크기 대비 출력 해상도 비율 | 50% |
| High Poly Cleanup 스킵 | high-poly cleanup 단계 생략 | false |
| Cage Baking 스킵 | cage 없이 단순 ray casting baking | false |

### 2. Outputs 페이지

완료된 결과물을 확인하는 페이지입니다.

백엔드는 별도 DB나 history table을 보지 않고, `data/output` 폴더의 `.glb` 파일을 직접 scan합니다.

카드의 `비교 보기` 버튼을 누르면 원본 파일이 남아 있는 경우 Before/After 비교 viewer를 열 수 있습니다.

### 3. GLB Inspector

| 기능 | 설명 |
|------|------|
| Before / After | 원본과 최적화 결과를 나란히 비교 |
| Wireframe | 메시 구조를 와이어프레임으로 표시 |
| Bounding Box | 모델 경계 상자 표시 |
| 카메라 동기화 | 두 viewer의 카메라를 연동 |

---

## 파일 저장 구조

현재 웹앱의 런타임 파일은 repo root 아래 `data` 디렉토리에 저장됩니다.

```text
data/
├── staging/
│   └── {job_id}.glb      # 업로드된 원본 GLB
└── output/
    └── {job_id}.glb      # 변환 완료된 결과 GLB
```

예시:

```text
원본 파일명: chair.glb
job_id: chair_a1b2c3d4

data/staging/chair_a1b2c3d4.glb
data/output/chair_a1b2c3d4.glb
```

Static file URL:

```text
/files/staging/chair_a1b2c3d4.glb
/files/output/chair_a1b2c3d4.glb
```

---

## 프로젝트 구조

```text
simplify_justin/
├── backend/
│   ├── main.py                 # FastAPI app, CORS, static file mount
│   ├── config.py               # BLENDER_PATH, staging/output 경로
│   ├── models.py               # Pydantic request/response/job models
│   ├── utils.py                # 파일명 sanitize, job_id 생성
│   ├── routers/
│   │   ├── upload.py           # POST /upload
│   │   ├── jobs.py             # POST/GET /jobs
│   │   └── files.py            # GET /outputs
│   ├── services/
│   │   └── pipeline.py         # 메모리 job 상태, subprocess 실행
│   └── scripts/
│       ├── run_pipeline.py     # CLI 파이프라인 오케스트레이터
│       ├── extract_for_qem.py  # Blender: GLB → QEM용 OBJ
│       ├── qem_simplify.py     # QEM 메시 축약
│       └── bake_export.py      # Blender: baking + GLB export
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── OnProgressPage.tsx
│       │   └── OutputsPage.tsx
│       ├── components/
│       │   ├── UploadZone.tsx
│       │   ├── ProgressCard.tsx
│       │   └── GLBInspector/
│       ├── api/
│       ├── hooks/
│       └── store.ts
├── data/
│   ├── staging/                # 런타임 생성
│   └── output/                 # 런타임 생성
├── PRD_webapp.md
├── MULTI_FILE_REFACTOR_PRD.md
└── run_webapp.sh
```

---

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/upload?filename=x.glb` | GLB 1개 스트리밍 업로드 |
| `POST` | `/jobs` | 업로드된 job의 파이프라인 시작 |
| `GET` | `/jobs` | 현재 메모리에 있는 job 목록 조회 |
| `GET` | `/jobs/{job_id}` | 특정 job 상태 조회 |
| `GET` | `/outputs` | `data/output`의 완료 GLB 목록 조회 |
| `GET` | `/files/staging/{job_id}.glb` | 원본 GLB static serving |
| `GET` | `/files/output/{job_id}.glb` | 결과 GLB static serving |

### POST /upload 응답 예시

```json
{
  "job_id": "chair_a1b2c3d4",
  "input_url": "/files/staging/chair_a1b2c3d4.glb"
}
```

### POST /jobs 요청 예시

```json
{
  "job_id": "chair_a1b2c3d4",
  "params": {
    "tris_ratio": 0.1,
    "texture_ratio": 0.5,
    "skip_high_poly_cleanup": false,
    "skip_cage": false
  }
}
```

### Job 상태

현재 job 상태는 다음 중 하나입니다.

```text
uploading | running | done | error
```

step 상태는 다음 3단계로 표시됩니다.

```text
extract | simplify | bake
```

---

## CLI 직접 실행

웹 UI 없이 파이프라인 스크립트를 직접 실행할 수도 있습니다.

```bash
cd backend/scripts
../.venv/bin/python run_pipeline.py \
  --input ../../input/model.glb \
  --output ../../output/model_opt.glb \
  --tris-ratio 0.1 \
  --texture-ratio 0.5 \
  --blender /Applications/Blender.app/Contents/MacOS/Blender
```

`run_pipeline.py`는 같은 디렉토리의 `extract_for_qem.py`, `qem_simplify.py`, `bake_export.py`를 호출하므로 `backend/scripts`를 작업 디렉토리로 두고 실행하는 것을 권장합니다.

---

## 현재 제약

- 한 번에 선택/업로드 가능한 파일은 1개입니다.
- 변환 job도 한 번에 1개의 active job UI를 기준으로 표시됩니다.
- `POST /jobs`를 여러 번 동시에 호출하는 것을 막는 변환 queue는 아직 없습니다.
- job 상태는 백엔드 프로세스 메모리에 저장되므로 서버 재시작 시 사라집니다.
- 완료된 output GLB는 `data/output` 폴더 scan으로 다시 확인할 수 있습니다.
- DB, 사용자 계정, 영구 history, cloud storage는 현재 scope에 없습니다.

---

## 다음 리팩토링

멀티 파일 업로드와 안전한 변환 큐 설계는 [MULTI_FILE_REFACTOR_PRD.md](MULTI_FILE_REFACTOR_PRD.md)를 기준으로 진행합니다.

요약:

```text
Frontend
  - 최대 10개 파일 선택
  - 최대 3개 병렬 업로드

Backend
  - 업로드 완료 job을 queue에 등록
  - Blender 변환은 기본 1개씩 순차 실행
```
