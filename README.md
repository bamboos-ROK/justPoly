# JustPoly

여러 GLB 모델을 한 번에 업로드하고, QEM 기반 메시 경량화와 Cage Baking을 거친 결과를 브라우저에서 Before/After로 비교하는 로컬 웹 도구입니다.

---

## 빠른 시작

### 요구 사항

- Python 3.10+
- Node.js 18+
- Blender 설치

기본 Blender 경로는 macOS 기준으로 설정되어 있습니다.

```text
/Applications/Blender.app/Contents/MacOS/Blender
```

다른 경로를 사용한다면 프로젝트 루트에 `.env`를 만들고 설정하세요.

```bash
BLENDER_PATH=/path/to/blender
```

### 실행

프로젝트 루트에서 실행합니다.

```bash
./run_webapp.sh
```

스크립트가 백엔드/프론트엔드 의존성을 확인하고, 필요한 경우 자동 설치한 뒤 서버를 실행합니다.

```text
Frontend: http://localhost:5173
Backend:  http://localhost:8000
API Docs: http://localhost:8000/docs
```

---

## 무엇을 할 수 있나

- GLB 파일을 최대 10개까지 한 번에 선택
- 파일당 최대 300MB까지 업로드
- 업로드는 최대 3개씩 병렬 처리
- 변환은 백엔드 큐에서 1개씩 안전하게 처리
- 파일별 업로드 진행률과 변환 상태 확인
- 완료된 파일은 원본/결과 GLB를 나란히 비교
- Outputs 페이지에서 완료된 결과물 다시 열람
- Outputs 페이지에서 완료된 결과물 삭제

---

## 사용 흐름

```text
1. /progress 페이지에서 GLB 파일 선택
2. 파일들이 최대 3개씩 업로드됨
3. 파라미터 확인
4. "경량화 시작" 클릭
5. 업로드 완료된 job들이 변환 큐에 등록됨
6. 백엔드가 1개씩 Extract → Simplify → Bake 실행
7. 완료된 파일에서 "결과 비교 보기" 클릭
```

변환 상태는 다음처럼 표시됩니다.

```text
업로드 중 → 업로드 완료 → 변환 대기 → 변환 중 → 완료
```

---

## 주요 화면

### On Progress

파일 업로드와 변환 진행을 관리하는 화면입니다.

- 여러 파일 선택
- 파일별 업로드 진행률
- 파일별 변환 상태
- 전체 경량화 시작
- 완료 파일 비교 보기

### Outputs

완료된 결과물을 확인하는 화면입니다.

백엔드는 별도 DB가 아니라 `data/output` 폴더를 스캔해서 결과 목록을 보여줍니다.

### GLB Inspector

원본과 변환 결과를 비교하는 뷰어입니다.

- Before / After 듀얼 뷰어
- Wireframe
- Bounding Box
- 카메라 동기화

---

## 변환 파라미터

| 항목                   | 설명                                   | 기본값 |
| ---------------------- | -------------------------------------- | ------ |
| 삼각형 비율            | 원본 대비 유지할 삼각형 수 비율        | 10%    |
| 텍스처 비율            | 원본 텍스처 크기 대비 출력 해상도 비율 | 50%    |
| High Poly Cleanup 스킵 | high-poly cleanup 단계 생략            | false  |
| Cage Baking 스킵       | cage 없이 단순 ray casting baking      | false  |

---

## 처리 구조

```text
Frontend
  - 최대 10개 파일 선택
  - 최대 3개 병렬 업로드
  - 전체 job 상태 polling

Backend
  - GLB 스트리밍 업로드 저장
  - job 생성 및 상태 관리
  - 변환 큐 관리
  - Blender/QEM 파이프라인 1개씩 실행
```

파이프라인은 3단계입니다.

```text
Extract   GLB → QEM용 OBJ 추출
Simplify  QEM 기반 메시 축약
Bake      텍스처 베이킹 + GLB 내보내기
```

---

## 파일 저장 위치

런타임 파일은 프로젝트 루트의 `data` 폴더에 저장됩니다.

```text
data/
├── staging/
│   └── {job_id}.glb
└── output/
    ├── {job_id}.glb
    └── {job_id}.json
```

예시:

```text
data/staging/chair_a1b2c3d4.glb
data/output/chair_a1b2c3d4.glb
data/output/chair_a1b2c3d4.json
```

---

## API

| Method   | Path                          | 설명                          |
| -------- | ----------------------------- | ----------------------------- |
| `POST`   | `/api/upload?filename=x.glb`  | GLB 1개 업로드                |
| `POST`   | `/api/jobs`                   | 업로드된 job을 변환 큐에 등록 |
| `GET`    | `/api/jobs`                   | 전체 job 상태 조회            |
| `GET`    | `/api/jobs/{job_id}`          | 특정 job 상태 조회            |
| `GET`    | `/api/outputs`                | 완료된 결과 목록 조회         |
| `DELETE` | `/api/outputs/{job_id}`       | 결과물 삭제                   |
| `GET`    | `/files/staging/{job_id}.glb` | 원본 GLB 파일                 |
| `GET`    | `/files/output/{job_id}.glb`  | 결과 GLB 파일                 |

Job 상태:

```text
uploading | uploaded | queued | running | done | error
```

---

## 프로젝트 구조

```text
justPoly/
├── backend/
│   ├── routers/          # upload, jobs, outputs API
│   ├── services/         # 변환 큐와 pipeline 상태 관리
│   └── scripts/          # Blender/QEM 처리 스크립트
├── frontend/
│   └── src/
│       ├── pages/
│       ├── components/
│       ├── api/
│       └── store.ts
├── data/                 # 업로드/결과 파일 저장
└── run_webapp.sh
```

---

## 참고

- 변환 작업은 Blender를 사용하므로 파일 크기와 모델 복잡도에 따라 시간이 걸릴 수 있습니다.
- 서버를 재시작하면 메모리에 있던 job 상태는 초기화됩니다.
- 완료된 결과 파일은 `data/output`에 남아 Outputs 페이지에서 다시 확인할 수 있습니다.
