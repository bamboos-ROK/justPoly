# 📄 PRD: GLB Optimization Web Viewer (React + Three.js)

---

## 1. 제품 개요

### 1.1 목적

GLB 모델을 업로드하고 QEM 기반 경량화 + Cage Baking 결과를 시각적으로 비교할 수 있는 웹 기반 경량 툴.

CLI 기반 파이프라인을 웹 UI로 감싸서 **비개발자도 사용할 수 있는 결과 검수 도구**로 만드는 것이 목표.

---

### 1.2 핵심 문제

- CLI 기반 pipeline은 결과 확인이 어려움
- GLB 비교를 위한 시각적 UI 부재
- 파일 기반 결과는 존재하지만 탐색 UX 없음
- 비개발자 사용 불가

---

### 1.3 제품 목표

- GLB upload 기반 pipeline 실행
- Before / After GLB 비교 inspector 제공
- output 파일 탐색 UI 제공
- lightweight stateless 구조 유지
- 관리 시스템이 아닌 “결과 확인 도구”

---

## 2. 제품 철학

> “이 시스템은 관리 툴이 아니라 결과를 빠르게 확인하는 inspection tool이다.”

---

### 핵심 원칙

- Job system 없음
- History system 없음
- DB 없음 (filesystem only)
- Stateless pipeline execution
- UI = result viewer only

---

## 3. 기술 스택

---

### Frontend

- React (Vite)
- Three.js
- React Router (page navigation)
- Zustand (optional state management)

---

### Backend

- FastAPI
- Python pipeline (QEM + Cage Baking)
- streaming upload handling

---

### Rendering

- Three.js (GLTFLoader)
- OrbitControls
- dual canvas rendering (before/after)

---

### Storage

- local filesystem
  - `/staging`
  - `/output`

---

## 4. 시스템 아키텍처

```text id="arch"
React (Vite Frontend)
        ↓
FastAPI Backend
        ↓
/staging (input)
/output (result)
        ↓
Three.js Viewer (GLB Inspector)
```

---

## 5. 핵심 설계 원칙

---

### 5.1 Stateless System

- pipeline = function
- no persistent job tracking
- no DB layer

---

### 5.2 File-driven architecture

```text id="file_flow"
Upload → /staging/{uuid}/input.glb
Run → pipeline execution
Output → /output/{uuid}/output.glb
```

---

### 5.3 UI = Viewer 중심

- UI는 상태 관리하지 않음
- file path만 기반으로 rendering

---

## 6. UI 구조

---

### 6.1 Layout

```text id="ui_layout"
┌──────── Sidebar ────────┐┌──────── Main ─────────┐
│ ▶ On Progress           ││                      │
│ ▶ Outputs               ││                      │
└─────────────────────────┘└──────────────────────┘
```

---

### 6.2 Pages

---

#### 1. On Progress Page

- 현재 실행 중 pipeline 상태
- progress indicator
- live viewer (optional)

👉 ephemeral state only

---

#### 2. Outputs Page

- `/output` folder scan
- GLB file list
- click → inspector load

👉 no history system, just file listing

---

#### 3. Inspector Page (Core)

- Input GLB viewer (left)
- Output GLB viewer (right)
- synchronized camera (optional ON)

---

### Inspector 기능

- orbit controls
- wireframe toggle
- lighting default
- bounding box
- minimal metrics overlay

---

## 7. GLB Upload System

---

### 7.1 Upload 방식

- drag & drop upload
- streaming upload (no memory buffering)

---

### 7.2 Storage 구조

```text id="storage"
/staging/{uuid}/input.glb
/output/{uuid}/output.glb
```

---

### 7.3 특징

- file-based lifecycle
- no in-memory GLB retention
- backend writes directly to disk

---

## 8. Pipeline System

---

### 기능

- QEM-based mesh simplification
- Cage baking texture generation
- GLB export

---

### 특징

- stateless execution
- input = file path
- output = file path
- no job abstraction

---

## 9. Inspector (Three.js Core)

---

### 역할

GLB Before / After 비교 UI

---

### 구조

- dual canvas rendering OR split viewport
- shared camera system
- independent model loading

---

### 기능

- GLTFLoader
- OrbitControls
- wireframe toggle
- bounding box
- basic lighting setup

---

### UX 특징

- always comparison-based view
- no navigation complexity
- no selection hierarchy

---

## 10. Performance Requirements

- GLB up to 100MB+
- streaming upload required
- lazy texture loading
- disk-first pipeline execution
- no full memory buffering

---

## 11. Non-Goals

- ❌ job management system
- ❌ history tracking system
- ❌ multi-user system
- ❌ analytics dashboard
- ❌ database layer
- ❌ cloud storage dependency

---

## 12. Success Criteria

- GLB upload → pipeline execution → result visualization 완료
- Before / After inspector 정상 동작
- CLI 없이 전체 workflow 가능
- 비개발자도 사용 가능 수준 UX

---

## 13. 핵심 구조 요약

> Upload → Process → Inspect → Output List

---

## 14. 최종 설계 철학

> “A minimal, file-driven 3D inspection tool built with React + Three.js, not a management system.”
