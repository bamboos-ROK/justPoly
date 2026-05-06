# 리팩토링 진행 상황

> **목표**: GLB 단일 파일 처리 → 최대 10개 멀티 파일, 병렬 업로드(3개), 백엔드 순차 변환 큐  
> **원본 PRD**: `MULTI_FILE_REFACTOR_PRD.md`  
> **최종 빌드 상태**: Phase 1 완료 후 `npm run build` 성공 확인

---

## 전체 작업 상태

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | 프론트엔드 — 다중 파일 선택, 업로드 큐, 폴링 재작성 | ✅ 완료 |
| Phase 2 | 백엔드 — asyncio.Queue 변환 큐, 상태 추가, 검증 | ✅ 완료 |
| Phase 3 | UX 폴리시 — FileJobCard 컴포넌트 추출, 버튼 polish | ✅ 완료 |

---

## Phase 1 완료 내역

아래 7개 파일이 수정되었고 빌드가 통과된 상태다.

### `frontend/src/types.ts` ✅
- `JobStatus`에 `'uploaded' | 'queued'` 추가
- `UploadItem` 인터페이스 추가 (local_id, file, upload_status, upload_progress, job_id 등)

### `frontend/src/store.ts` ✅ (전체 재작성)
- 기존: `activeJob`, `updateJob`, `pollingId`
- 변경 후: `uploadItems: UploadItem[]`, `jobsById: Record<string, Job>`, `selectedJobId`, `updateUploadItem`, `mergeJobs`

### `frontend/src/api/jobs.ts` ✅
- `listJobs(): Promise<Job[]>` 추가 (GET `/jobs` 전체 polling용)

### `frontend/src/api/index.ts` ✅
- `listJobs` re-export 추가

### `frontend/src/components/UploadZone.tsx` ✅
- Props: `onFile(file)` → `onFiles(files: File[])`
- `<input multiple>` 추가
- 서브텍스트: "최대 10개, 파일당 300MB, .glb 형식"

### `frontend/src/components/Sidebar.tsx` ✅
- `activeJob` 의존성 제거
- `jobsById`에서 `running | queued` 상태 job이 있으면 badge 표시

### `frontend/src/pages/OnProgressPage.tsx` ✅ (전체 재작성)
- 상태: `uploadItems` (store), `jobsById` (store), `selectedJobId` (store)
- `uploadQueueRef`: 업로드 대기 local_id 목록
- `runningCountRef`: 현재 업로드 중 개수 (≤ 3)
- `drainQueue()`: runningCount < 3이면 다음 항목 업로드 시작
- `handleFiles(files)`: .glb 필터, 300MB 검증, 10개 제한 체크 후 큐에 추가
- `handleStartAll()`: `job.status === 'uploaded'`인 항목 모두 `startPipeline()` 병렬 호출
- 폴링: `listJobs()` 전체 polling (2초), 모든 job terminal 상태 시 중지
- `FileCard` 인라인 컴포넌트: 파일별 카드 (업로드 progress bar, 변환 badge, 오류 표시, "결과 비교 보기" 버튼)
- GLBInspector: `selectedJobId` 기반으로 구동

**주의**: Phase 1에서 `FileCard`는 `OnProgressPage.tsx` 안에 인라인으로 작성됨.  
Phase 3에서 `frontend/src/components/FileJobCard.tsx`로 추출 예정.

---

## Phase 2 완료 내역

아래 5개 파일이 수정되었다.

### `backend/models.py` ✅

- `JobStatus.status` Literal에 `"uploaded"`, `"queued"` 추가
- 변경 후: `Literal["uploading", "uploaded", "queued", "running", "done", "error"]`

### `backend/services/pipeline.py` ✅

- 모듈 레벨 변수 추가: `_queue`, `_pending_params`, `_worker_task`
- `enqueue_job(job_id, params)`: job status를 `"queued"`로 전환 후 큐에 등록
- `start_worker()`: startup에서 호출, `_worker_loop` 태스크 생성
- `_worker_loop()`: 큐에서 job_id를 순차적으로 꺼내 `run_pipeline_async` 실행

### `backend/routers/upload.py` ✅

- `MAX_FILE_SIZE = 300 * 1024 * 1024` (300MB) 상수 추가
- `.glb` 확장자 검증 → 400 에러
- Content-Length 헤더 사전 검증 → 413 에러
- 스트리밍 중 누적 바이트 초과 시 파일 삭제 후 413 에러
- 빈 파일(0바이트) 거부 → 400 에러
- 업로드 완료 후 `job.status = "uploaded"` 설정

### `backend/routers/jobs.py` ✅

- `BackgroundTasks` import 및 파라미터 제거
- 가드 조건 변경: `status != "uploading"` → `status not in ("uploaded",)`
- `bg.add_task(...)` → `pipeline.enqueue_job(body.job_id, body.params)`

### `backend/main.py` ✅

- `pipeline as pipeline_service` import 추가
- `startup()`에 `await pipeline_service.start_worker()` 추가

---

## Phase 2 작업 내용 (참고용 원본 계획)

### 2-1. `backend/models.py`
```python
# 변경 전
status: Literal["uploading", "running", "done", "error"]

# 변경 후
status: Literal["uploading", "uploaded", "queued", "running", "done", "error"]
```

### 2-2. `backend/services/pipeline.py`
모듈 레벨에 큐/워커 추가:
```python
_queue: asyncio.Queue[str] = asyncio.Queue()
_pending_params: dict[str, PipelineParams] = {}
_worker_task: asyncio.Task | None = None

def enqueue_job(job_id: str, params: PipelineParams) -> None:
    job = _jobs[job_id]
    job.status = "queued"
    _pending_params[job_id] = params
    _queue.put_nowait(job_id)

async def start_worker() -> None:
    global _worker_task
    _worker_task = asyncio.create_task(_worker_loop())

async def _worker_loop() -> None:
    while True:
        job_id = await _queue.get()
        params = _pending_params.pop(job_id, PipelineParams())
        try:
            await run_pipeline_async(job_id, params)
        except Exception:
            pass
        finally:
            _queue.task_done()
```
`run_pipeline_async`는 변경 없음.

### 2-3. `backend/routers/upload.py`
현재 코드에서 추가/변경할 내용:
1. `MAX_FILE_SIZE = 300 * 1024 * 1024` 상수 추가
2. filename `.glb` 검증 → 400 에러
3. Content-Length 헤더 사전 검증 → 413 에러
4. 스트리밍 중 누적 바이트 계산, 초과 시 파일 삭제 후 413 에러
5. 빈 파일(0바이트) 거부 → 400 에러
6. `pipeline.create_job()` 호출 후 **`job.status = "uploaded"`** 설정
   (현재는 `create_job` 내부에서 `"uploading"`으로 초기화하고 그대로 둠)

현재 upload.py 코드:
```python
pipeline.create_job(job_id, filename)  # status="uploading" 상태로 생성 후 변경 없음
```
변경 후:
```python
job = pipeline.create_job(job_id, filename)
job.status = "uploaded"  # 파일 저장 완료 후 즉시 업데이트
```

### 2-4. `backend/routers/jobs.py`
현재 코드:
```python
async def start_pipeline(body: StartPipelineRequest, bg: BackgroundTasks) -> JobStatus:
    if job.status != "uploading":  # 가드 조건
        raise HTTPException(409, ...)
    bg.add_task(pipeline.run_pipeline_async, body.job_id, body.params)  # 직접 실행
```
변경 후:
```python
async def start_pipeline(body: StartPipelineRequest) -> JobStatus:  # BackgroundTasks 제거
    if job.status not in ("uploaded",):  # 가드 조건 변경
        raise HTTPException(409, ...)
    pipeline.enqueue_job(body.job_id, body.params)  # 큐에 등록
    return pipeline.get_job(body.job_id)
```

### 2-5. `backend/main.py`
startup 이벤트에 워커 시작 추가:
```python
from .services import pipeline as pipeline_service

@app.on_event("startup")
async def startup() -> None:
    # 기존 코드 유지...
    await pipeline_service.start_worker()  # 추가
```

---

## Phase 3 완료 내역

### `frontend/src/components/FileJobCard.tsx` ✅ (신규 파일 생성)

- `OnProgressPage.tsx`의 인라인 `FileCard` 컴포넌트를 별도 파일로 추출
- Props: `{ item: UploadItem, job?: Job, onViewResult: (job_id: string) => void }`
- 포함 항목: `STATUS_COLOR`, `STATUS_LABEL`, `formatBytes`, `cardStyles`

### `frontend/src/pages/OnProgressPage.tsx` ✅

- `import { FileJobCard }` 추가
- 인라인 `FileCard`, `FileCardProps`, `STATUS_COLOR`, `STATUS_LABEL`, `cardStyles`, `formatBytes` 제거
- `Job` 타입 import 제거 (더 이상 직접 사용 안 함)
- `<FileCard>` → `<FileJobCard>` 교체

**최종 빌드 상태**: Phase 3 완료 후 `npm run build` 성공 확인

---

## 주요 설계 결정 사항

| 항목 | 결정 | 이유 |
|------|------|------|
| 업로드 동시성 | 프론트에서 3개 제한 | 파일별 progress 관리가 프론트에서 쉬움 |
| 변환 동시성 | 백엔드 asyncio.Queue, 1개씩 | Blender subprocess 메모리/CPU 과부하 방지 |
| 폴링 방식 | `GET /jobs` 전체 polling | 개별 polling보다 단순, max 10개라 부하 낮음 |
| status 전환 | `uploading→uploaded` 업로드 완료 후 | 업로드 완료와 변환 대기를 명확히 분리 |
| 전체 job state | Zustand `jobsById: Record<string, Job>` | job_id 기준 O(1) lookup |
| 업로드 local state | Zustand `uploadItems: UploadItem[]` | File 객체 포함, 백엔드 job 상태와 분리 관리 |

---

## 새 세션에서 작업 재개하는 방법

1. 이 문서(`PROGRESS.md`)와 `MULTI_FILE_REFACTOR_PRD.md` 첨부
2. Phase 1은 완료됨 — 프론트 7개 파일 수정/재작성 완료, 빌드 통과
3. **다음 작업**: Phase 2 백엔드부터 시작
   - 순서: `models.py` → `services/pipeline.py` → `routers/upload.py` → `routers/jobs.py` → `main.py`
4. Phase 2 완료 후 통합 테스트, Phase 3 UX 폴리시

---

## 검증 체크리스트

### Phase 1 완료 검증
- [x] `npm run build` 타입 오류 없이 통과

### Phase 3 완료 검증
- [x] `npm run build` 타입 오류 없이 통과

### Phase 2 완료 후 검증 (미실시)
- [ ] 백엔드 서버 시작 후 `GET /jobs` → `[]` 반환
- [ ] GLB 파일 3개 드래그 → 3개 progress bar 동시 표시
- [ ] 4번째 파일은 앞 3개 완료 후 자동 시작
- [ ] "경량화 시작" 클릭 → 첫 번째 job `running`, 나머지 `queued`
- [ ] 첫 번째 완료 후 두 번째 자동 시작 (동시 running 1개만)
- [ ] 한 파일 오류가 다른 파일 처리에 영향 없음
- [ ] 완료 파일에서 "결과 비교 보기" → GLBInspector 정상 동작
- [ ] 300MB 초과 파일 → 413 에러, UI 오류 표시
- [ ] 기존 단일 파일 흐름도 계속 동작
