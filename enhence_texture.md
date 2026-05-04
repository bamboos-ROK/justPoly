# Bake 텍스처 품질 이슈 분석 및 해결 보고서

## 1. 이슈 개요

AI Generated High Poly 모델을 QEM 기반으로 Low Poly 변환 후 텍스처 베이킹 시,
결과물에 **부분적 얼룩, 랜덤 Blotch, 표면 오염**이 발생하였음.

---

## 2. 원인 분석

초기 판단인 "UV 붕괴" 가능성을 검토하였으나, 실제 원인은 **Bake Projection 오염**으로 확인됨.
Low Poly 메시가 High Poly의 잘못된 위치에서 텍스처를 샘플링하는 현상이었으며, 두 가지 세부 원인이 복합적으로 작용하였음.

### 원인 1 — High Poly 내부 잡면 및 Hidden Geometry

AI 생성 메시는 특성상 다음의 오염 요소를 포함하는 경우가 빈번함:

- 중복 버텍스 (Duplicated Vertices) : 동일 위치 면이 겹쳐 레이가 중복 충돌
- Loose Geometry : 메시와 무관한 부유 버텍스/엣지가 레이를 왜곡
- 반전 Normal : 레이가 내부에서 출발하여 잘못된 면을 샘플링

### 원인 2 — Cage 미사용

기본 Bake는 Low Poly 표면에서 단순히 `max_ray_distance` 방향으로 레이를 발사함.
비정형 AI 메시에서는 레이가 의도치 않은 의도하지 않은 표면을 샘플링하여 오염이 발생함.

---

## 3. 해결책

### 해결책 1 — High Poly Cleanup (`--skip-high-poly-cleanup` 플래그로 제어)

Bake 직전에 High Poly 메시에 대해 다음 정리를 수행함:

| 단계                | Blender 연산                            | 목적               |
| ------------------- | --------------------------------------- | ------------------ |
| Merge by Distance   | `remove_doubles(threshold=0.0001)`      | 중복 버텍스 제거   |
| Delete Loose        | `delete_loose(verts, edges)`            | 부유 Geometry 제거 |
| Recalculate Normals | `normals_make_consistent(inside=False)` | 반전 Normal 정정   |

각 오브젝트를 개별 처리하여 오브젝트 경계 간 의도치 않은 병합을 방지하였음.

### 해결책 2 — Cage Bake (`--skip-cage` 플래그로 제어)

Low Poly 메시를 법선 방향으로 `cage_extrusion`만큼 팽창시킨 **암묵적 Cage**를 생성하고,
Low Poly 표면 기준 Bake Projection 범위를 법선 방향으로 확장하여, 보다 안정적인 샘플링 범위를 확보함.

- 레이의 탐색 범위가 Cage~Low Poly 사이로 제한되어 원거리 오염 차단
- `cage_extrusion = bbox_diagonal × 0.005` (기본값)
- Cage Bake 실패 시 기존 방식으로 자동 Fallback

---

## 4. 테스트 결과

| 조합     | cleanup | cage  | 결과                                                              |
| -------- | ------- | ----- | ----------------------------------------------------------------- |
| None     | ✗       | ✗     | 오염 발생 (개선 전 동작)                                          |
| Cleanup  | ✓       | ✗     | 오염 발생 (개선 전과 차이 없음)                                   |
| Cage     | ✗       | ✓     | 대다수의 케이스에서 오염 해소 확인(특정 케이스에서 텍스쳐 뭉개짐) |
| **Both** | **✓**   | **✓** | **오염 해소 확인**                                                |

---

## 5. 결론

본 이슈의 핵심 병목은 UV 구조가 아닌 **Bake Projection 정확도**였다.
**Cage Bake가 주요 해결책**으로 작동했으며,
High Poly Cleanup은 입력 메시 품질 편차에 대응하는 안정성 보조 수단으로 유지하는 것이 적절하다.
