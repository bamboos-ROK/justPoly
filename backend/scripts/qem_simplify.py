import argparse
import json
from pathlib import Path

import numpy as np
import pymeshlab


def write_obj(path: str, ms: pymeshlab.MeshSet):
    m = ms.current_mesh()
    vertices = m.vertex_matrix()  # (N, 3) float64
    faces = m.face_matrix()       # (F, 3) int32
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for v in vertices:
            f.write(f"v {v[0]:.9g} {v[1]:.9g} {v[2]:.9g}\n")
        for tri in faces:
            f.write(f"f {tri[0]+1} {tri[1]+1} {tri[2]+1}\n")


def _load_vertex_visibility(vis_path: str, n_verts: int) -> np.ndarray | None:
    """face_visibility.json에서 vertex_visibility 배열을 로드."""
    p = Path(vis_path)
    if not p.exists():
        return None
    try:
        with p.open() as f:
            vis_data = json.load(f)
        raw = np.array(vis_data.get("vertex_visibility", []), dtype=np.float64)
        if len(raw) == 0:
            return None
        print(f"Visibility scores: {len(raw)} verts, confidence={vis_data.get('confidence', 'n/a')}")
        if len(raw) >= n_verts:
            return raw[:n_verts]
        # 남은 vertex는 visible로 처리 (보수적 fallback)
        return np.pad(raw, (0, n_verts - len(raw)), constant_values=1.0)
    except Exception as e:
        print(f"Visibility score load failed ({e}), skipping")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target-tris", type=int, required=True)
    parser.add_argument("--visibility-scores", default=None,
                        help="face_visibility.json path (optional)")
    args = parser.parse_args()

    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(args.input)

    original_faces = ms.current_mesh().face_number()
    if original_faces == 0:
        raise RuntimeError("Input mesh has no triangles.")

    # visibility scores 로드 (mesh op 이전 vertex 수 기준)
    vert_vis_preop: np.ndarray | None = None
    if args.visibility_scores:
        vert_vis_preop = _load_vertex_visibility(
            args.visibility_scores,
            ms.current_mesh().vertex_number(),
        )

    # Phase 1: Pre-clean
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_null_faces()
    ms.meshing_remove_unreferenced_vertices()
    ms.compute_normal_per_vertex()

    # Phase 2: Importance Hint Injection (curvature + visibility combined)
    use_quality_weight = False
    try:
        ms.meshing_repair_non_manifold_edges()
        ms.meshing_repair_non_manifold_vertices()
        ms.compute_scalar_by_discrete_curvature_per_vertex(curvaturetype=3)
        q = ms.current_mesh().vertex_scalar_array()
        q_p95 = float(np.percentile(q, 95))

        if q_p95 > 1e-8:
            q_norm = np.clip(np.abs(q), 0, q_p95) / q_p95

            # visibility와 결합
            current_nv = ms.current_mesh().vertex_number()
            if vert_vis_preop is not None:
                if len(vert_vis_preop) >= current_nv:
                    vert_vis = vert_vis_preop[:current_nv]
                else:
                    vert_vis = np.pad(vert_vis_preop, (0, current_nv - len(vert_vis_preop)), constant_values=1.0)
                # invisible area → 낮은 보존 우선순위 → QEM이 먼저 collapse
                combined = q_norm * (0.3 + 0.7 * vert_vis)
                label = "curvature+visibility"
            else:
                combined = q_norm
                label = "curvature"

            c_p95 = float(np.percentile(combined, 95))
            if c_p95 > 1e-8:
                combined_final = np.clip(combined, 0, c_p95) / c_p95
            else:
                combined_final = combined

            # pymeshlab에 quality 주입: Mesh 재구성으로 v_scalar_array 교체
            m = ms.current_mesh()
            try:
                vnormals = m.vertex_normal_matrix()
            except Exception:
                vnormals = None
            new_m = pymeshlab.Mesh(
                vertex_matrix=m.vertex_matrix(),
                face_matrix=m.face_matrix(),
                v_normals_matrix=vnormals,
                v_scalar_array=combined_final.astype(np.float64),
            )
            ms.add_mesh(new_m)
            use_quality_weight = True
            print(f"Quality weight: {label}")

    except Exception as e:
        print(f"Quality weight computation skipped ({e}), falling back to uniform QEM")

    # Phase 3: Guided QEM Decimation
    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=args.target_tris,
        preservetopology=True,
        preservenormal=True,
        preserveboundary=True,
        boundaryweight=2.0,
        planarquadric=False,
        qualityweight=use_quality_weight,
        qualitythr=0.7,
        autoclean=True,
    )

    # Phase 4: Post-clean
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_null_faces()
    ms.meshing_remove_unreferenced_vertices()
    ms.compute_normal_per_vertex()

    simplified_faces = ms.current_mesh().face_number()
    write_obj(args.output, ms)

    print(f"Original triangles: {original_faces}")
    print(f"Simplified triangles: {simplified_faces}")
    print(f"Feature-weight active: {use_quality_weight}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
