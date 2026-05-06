# PRD: Multi-file Upload and Queued Conversion Refactor

---

## 1. 목적

현재 웹앱은 GLB 파일 1개를 업로드하고, 해당 파일 1개에 대해 변환 파이프라인 1개를 실행하는 단일 작업 구조이다.

이 리팩토링의 목적은 사용자가 여러 GLB 파일을 한 번에 선택하고, 시스템이 안전한 동시성 제한 안에서 업로드와 변환을 처리하도록 확장하는 것이다.

핵심 목표:

- 프론트에서 최대 10개 GLB 파일 선택
- 프론트에서 최대 3개 파일까지 병렬 업로드
- 백엔드에서 업로드 완료된 job을 변환 큐에 등록
- 백엔드에서 변환은 기본 1개씩 순차 실행
- 파일별 업로드 상태, 변환 상태, 실패 상태, 결과 확인 지원

---

## 2. 현재 구조 요약

```text
단일 파일 선택
  ↓
POST /upload?filename={filename}
  ↓
data/staging/{job_id}.glb 저장
  ↓
메모리 job 생성(status=uploading)
  ↓
POST /jobs { job_id, params }
  ↓
BackgroundTasks로 run_pipeline.py 실행
  ↓
data/output/{job_id}.glb 생성
  ↓
GET /jobs/{job_id} polling
  ↓
결과 비교 보기
```

현재 주요 제약:

- `UploadZone`은 `files[0]`만 처리한다.
- `OnProgressPage`는 `uploadedFile` 1개와 `activeJob` 1개만 관리한다.
- `POST /jobs`를 여러 번 호출하면 Blender subprocess가 여러 개 동시에 실행될 수 있다.
- job 상태는 백엔드 프로세스 메모리에만 존재한다.
- 변환 대기 상태(`queued`)가 없다.

---

## 3. 목표 사용자 흐름

```text
1. 사용자가 GLB 파일 최대 10개 선택
2. 프론트가 파일별 사전 검증 수행
3. 프론트가 최대 3개씩 병렬 업로드
4. 백엔드가 각 파일을 staging에 스트리밍 저장
5. 업로드 완료마다 job_id 반환
6. 프론트가 업로드 완료된 job_id들에 대해 변환 시작 요청
7. 백엔드가 job을 변환 큐에 등록(status=queued)
8. 백엔드 worker가 큐에서 1개씩 꺼내 변환 실행(status=running)
9. 완료 시 output 저장(status=done)
10. 프론트는 전체 job 상태를 polling하여 파일별 상태 표시
11. 완료된 파일은 개별적으로 Before/After 비교 가능
```

---

## 4. 책임 구조

### 4.1 Frontend

프론트는 사용자 입력과 업로드 요청 orchestration을 담당한다.

- 파일 선택 UI
- drag and drop 다중 파일 처리
- 파일 개수, 확장자, 파일 크기 사전 검증
- 업로드 대기열 관리
- 최대 3개 병렬 업로드 제어
- 파일별 업로드 진행률 표시
- 업로드 완료 후 `job_id` 보관
- 변환 시작 요청 전송
- 전체 job 상태 polling
- 파일별 상태 UI 표시
- 완료된 job의 결과 비교 UI 진입

### 4.2 Backend

백엔드는 업로드 수신, job lifecycle, 변환 큐, 파일 serving을 담당한다.

- 업로드 스트림 수신
- 원본 GLB를 `data/staging`에 저장
- `job_id` 생성
- job 상태 생성 및 관리
- 변환 큐 등록
- 변환 동시 실행 수 제한
- Blender/QEM 파이프라인 실행
- 결과 GLB를 `data/output`에 저장
- 상태 조회 API 제공
- 결과 파일 목록 제공
- 원본/결과 GLB static serving

---

## 5. 동시성 정책

### 5.1 파일 선택 제한

초기 권장 제한:

```text
maxFiles = 10
maxFileSize = 300MB
maxTotalUploadSize = 2GB
allowedExtensions = .glb
```

프론트는 UX를 위해 사전 검증을 수행한다.

백엔드는 최종 안전장치로 동일한 제한을 검증해야 한다. 프론트 검증은 우회될 수 있으므로 백엔드 검증이 최종 기준이다.

### 5.2 업로드 동시성

```text
maxConcurrentUploads = 3
```

업로드 동시성은 프론트가 주도한다.

이유:

- 브라우저가 개별 파일별 진행률을 관리하기 쉽다.
- 현재 `/upload` API는 파일 1개 단위로 잘 분리되어 있다.
- 백엔드는 들어오는 스트림을 파일로 저장하는 책임에 집중할 수 있다.

백엔드도 과도한 요청에 대비해 파일 크기 제한과 요청 거부 정책을 가져야 한다.

### 5.3 변환 동시성

```text
maxConcurrentConversions = 1
```

변환 동시성은 백엔드가 제어한다.

이유:

- Blender subprocess는 메모리와 CPU 사용량이 크다.
- 여러 Blender 프로세스가 동시에 실행되면 로컬 머신이 불안정해질 수 있다.
- 변환은 업로드보다 비용이 훨씬 크므로 큐 기반 순차 처리가 안전하다.

향후 고성능 환경에서는 설정값으로 2 이상을 허용할 수 있다.

---

## 6. Job 상태 모델

현재 상태:

```text
uploading | running | done | error
```

변경 후 상태:

```text
uploading | uploaded | queued | running | done | error
```

상태 의미:

| Status | 의미 |
|--------|------|
| `uploading` | 업로드 요청 처리 중 |
| `uploaded` | staging 저장 완료, 아직 변환 큐에 들어가지 않음 |
| `queued` | 변환 큐에 등록됨 |
| `running` | 변환 파이프라인 실행 중 |
| `done` | 결과 GLB 생성 완료 |
| `error` | 업로드 또는 변환 실패 |

초기 구현에서는 `uploaded`를 생략하고 업로드 완료 직후 기존처럼 `uploading` 상태를 유지할 수도 있다. 다만 멀티 파일 UI에서는 `uploaded`가 있으면 “업로드 완료, 변환 대기 전” 상태를 더 명확히 표현할 수 있다.

---

## 7. API 설계

### 7.1 기존 API 유지

기존 파일 1개 단위 API는 유지한다.

```text
POST /upload?filename={filename}
POST /jobs
GET /jobs
GET /jobs/{job_id}
GET /outputs
GET /files/staging/{filename}
GET /files/output/{filename}
```

프론트는 여러 파일을 처리할 때 `/upload`와 `/jobs`를 파일별로 여러 번 호출한다.

### 7.2 POST /upload

역할:

- GLB 1개를 streaming upload로 수신
- `data/staging/{job_id}.glb` 저장
- job 생성
- `job_id`, `input_url` 반환

응답 예시:

```json
{
  "job_id": "chair_a1b2c3d4",
  "input_url": "/files/staging/chair_a1b2c3d4.glb"
}
```

추가 요구:

- 확장자 검증
- 파일 크기 검증
- 빈 파일 거부
- 업로드 중 예외 발생 시 partial file 처리 정책 정의

### 7.3 POST /jobs

역할:

- 업로드 완료된 job을 변환 큐에 등록
- 즉시 변환을 실행하지 않고 `queued` 상태로 전환
- worker가 큐에서 순차적으로 처리

요청 예시:

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

중복 호출 정책:

- `uploaded` 상태이면 `queued`로 전환
- `queued` 상태이면 현재 job 반환
- `running`, `done` 상태이면 409 반환
- `error` 상태 재시도는 별도 API 또는 명시 정책 필요

### 7.4 GET /jobs

멀티 파일 UI에서는 개별 polling보다 전체 polling을 우선한다.

```text
GET /jobs
```

프론트는 2초 간격으로 전체 job 목록을 조회하고, `job_id` 기준으로 로컬 작업 목록과 merge한다.

---

## 8. Frontend 변경 요구사항

### 8.1 UploadZone

변경 내용:

- `<input type="file">`에 `multiple` 추가
- drop 이벤트에서 `dataTransfer.files` 전체 처리
- props를 `onFile(file)`에서 `onFiles(files)`로 변경
- `.glb` 외 파일은 선택 단계에서 제외 또는 오류 표시

기대 동작:

```text
사용자가 12개 선택
  → 10개 제한 오류 표시
  → 업로드 시작하지 않음

사용자가 8개 선택
  → 파일 크기/확장자 검증
  → 유효한 파일들을 업로드 대기열에 등록
```

### 8.2 OnProgressPage 상태 구조

현재:

```text
uploadedFile: 1개
activeJob: 1개
uploadPct: 단일 숫자
```

변경 후:

```text
uploadItems: UploadItem[]
jobsById: Record<string, Job>
selectedJobId: string | null
```

`UploadItem` 예시:

```ts
interface UploadItem {
  local_id: string
  file: File
  filename: string
  size_bytes: number
  upload_status: 'pending' | 'uploading' | 'uploaded' | 'error'
  upload_progress: number
  job_id?: string
  input_url?: string
  error?: string
}
```

### 8.3 업로드 큐

프론트는 최대 3개씩 업로드한다.

```text
pending files
  ↓
run up to 3 upload promises
  ↓
each success stores job_id
  ↓
next pending file starts
```

요구사항:

- 파일별 progress 표시
- 파일별 upload error 표시
- 하나의 파일 실패가 전체 업로드를 중단하지 않음
- 실패 파일만 재업로드 가능하도록 설계 여지 확보

### 8.4 변환 시작 UX

초기 UX 옵션:

```text
옵션 A: 업로드 완료된 파일을 자동으로 변환 큐에 등록
옵션 B: 사용자가 "전체 경량화 시작" 버튼을 눌러 등록
```

권장: 옵션 B

이유:

- 사용자가 파라미터를 업로드 후 확인할 수 있다.
- 실수로 큰 파일 여러 개가 바로 변환되는 것을 막을 수 있다.
- 현재 단일 파일 UX의 “업로드 후 경량화 시작” 모델과 일관된다.

### 8.5 작업 리스트 UI

On Progress 페이지는 파일별 카드 리스트를 제공한다.

카드 표시 정보:

- 원본 파일명
- 파일 크기
- 업로드 진행률
- 변환 상태
- 현재 step
- 에러 메시지
- 완료 시 “결과 비교 보기”

상태별 대표 UI:

```text
pending upload
uploading 42%
uploaded
queued
running: extract / simplify / bake
done
error
```

---

## 9. Backend 변경 요구사항

### 9.1 Job 모델

`JobStatus.status`에 `uploaded`, `queued`를 추가한다.

추가 필드 후보:

```text
queued_at
started_at
finished_at
params
input_size_bytes
```

초기 구현에서는 DB 없이 메모리 상태를 유지한다.

### 9.2 변환 큐

`backend/services/pipeline.py`에 변환 큐를 도입한다.

권장 구조:

```text
asyncio.Queue[str]
asyncio.Semaphore(maxConcurrentConversions)
worker task
```

동작:

```text
POST /jobs
  → job.status = queued
  → queue.put(job_id)
  → job 반환

worker
  → queue.get()
  → job.status = running
  → run_pipeline_async(job_id, params)
  → done/error
  → queue.task_done()
```

초기 설정:

```text
max_concurrent_conversions = 1
```

### 9.3 Startup worker

FastAPI startup 시 변환 worker를 시작한다.

주의:

- app reload 시 메모리 queue는 초기화된다.
- 현재 PRD에서는 DB persistence를 요구하지 않는다.
- output 파일 목록은 기존처럼 filesystem scan으로 복구 가능하다.

### 9.4 업로드 검증

백엔드에서 검증해야 할 항목:

- filename extension `.glb`
- request body size limit
- empty file reject
- staging 저장 실패 처리
- partial file cleanup

파일 크기 제한은 streaming 중 누적 byte를 계산하여 초과 시 중단하는 방식이 적합하다.

---

## 10. Storage 구조

현재 구조를 유지한다.

```text
data/staging/{job_id}.glb
data/output/{job_id}.glb
```

중간 작업 파일은 기존처럼 temporary directory에 생성한다.

멀티 파일에서도 job_id가 UUID suffix를 포함하므로 파일명 충돌 위험은 낮다.

---

## 11. 리스크와 대응

### 11.1 Blender 다중 실행 리스크

리스크:

- 메모리 부족
- CPU 과부하
- Blender subprocess 실패
- OS level resource contention

대응:

- 변환 큐 도입
- 기본 동시 변환 수 1
- 설정으로만 동시 변환 수 확장

### 11.2 대용량 파일 저장 공간 리스크

리스크:

- staging + output + temp workdir로 디스크 사용량 증가
- 여러 파일 업로드 시 빠르게 GB 단위 사용

대응:

- 파일당 최대 300MB 권장
- 선택 총합 최대 2GB 권장
- 향후 cleanup 정책 추가

### 11.3 프론트 상태 복잡도 증가

리스크:

- 단일 `activeJob` 구조로는 멀티 상태 표현 불가
- polling merge 로직이 필요

대응:

- `job_id` 기준 map 구조 사용
- 업로드 로컬 상태와 백엔드 job 상태를 분리

### 11.4 서버 재시작 시 job 상태 유실

리스크:

- 메모리 job과 queue가 사라짐
- 실행 중이던 job 상태 복구 불가

대응:

- 현재 scope에서는 non-goal
- output 파일은 `/outputs` scan으로 확인 가능
- 장기적으로는 manifest JSON 또는 SQLite 검토

---

## 12. Non-goals

이번 리팩토링에서 제외한다.

- DB 기반 영구 job history
- 사용자 계정/권한
- 클라우드 스토리지
- 분산 worker
- 변환 취소 기능
- 서버 재시작 후 running job 복구
- 파일 자동 삭제 정책
- 여러 파라미터 preset 관리

---

## 13. Success Criteria

기능 성공 기준:

- 사용자가 GLB 파일 최대 10개를 한 번에 선택할 수 있다.
- 프론트가 업로드를 최대 3개씩 병렬 처리한다.
- 각 파일별 업로드 progress가 표시된다.
- 업로드 완료된 파일들이 변환 큐에 등록된다.
- 백엔드는 변환을 1개씩 순차 실행한다.
- 각 job의 상태가 `queued`, `running`, `done`, `error`로 구분되어 표시된다.
- 한 파일 실패가 다른 파일의 업로드/변환을 막지 않는다.
- 완료된 각 파일의 원본/결과 GLB를 비교할 수 있다.
- 기존 Outputs 페이지는 완료 결과 목록을 계속 표시한다.

기술 성공 기준:

- `/upload`, `/jobs`, `/jobs`, `/jobs/{job_id}`, `/outputs` API가 멀티 파일 흐름에서 정상 동작한다.
- 동시에 여러 `/jobs` 요청이 들어와도 Blender subprocess는 기본 1개만 실행된다.
- 기존 단일 파일 업로드/변환 흐름도 계속 사용할 수 있다.

---

## 14. 구현 우선순위

### Phase 1: Frontend multi-select and upload queue

- `UploadZone` 다중 파일 선택 지원
- 파일 제한 검증
- `OnProgressPage` 리스트 UI 도입
- 최대 3개 병렬 업로드 구현
- 파일별 upload progress 표시

### Phase 2: Backend conversion queue

- job status에 `queued` 추가
- `POST /jobs`를 queue 등록 방식으로 변경
- pipeline worker 도입
- 변환 동시 실행 수 1로 제한
- `GET /jobs` 기반 전체 polling 안정화

### Phase 3: Multi-job UX polish

- 전체 경량화 시작 버튼
- 파일별 재시도 버튼
- 완료 job 비교 보기
- error 표시 개선
- Outputs 페이지와 상태 일관성 확인

---

## 15. 최종 요약

이 리팩토링의 핵심은 “업로드는 여러 개를 빠르게 받고, 변환은 안전하게 한 줄로 처리한다”이다.

```text
Frontend
  - 최대 10개 파일 선택
  - 최대 3개 병렬 업로드
  - 파일별 상태 표시

Backend
  - 파일별 job 생성
  - 변환 queue 관리
  - Blender pipeline은 1개씩 실행
```

이 구조는 현재 파일 기반 아키텍처를 유지하면서도, 실제 사용자가 여러 GLB를 한 번에 처리할 수 있는 workflow로 확장한다.
