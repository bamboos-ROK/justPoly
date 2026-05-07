import argparse
import json
import math
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

import bpy
import bmesh
import mathutils
from mathutils.bvhtree import BVHTree


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-component-ratio", type=float, default=0.005)
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def import_obj(filepath: str):
    try:
        bpy.ops.wm.obj_import(filepath=filepath)  # Blender 4.x
    except AttributeError:
        bpy.ops.import_scene.obj(filepath=filepath)  # Blender 3.x


def compute_visibility_scores(bm, n_rays: int = 512) -> dict[int, float]:
    """각 face의 visibility score (0~1) 계산. 삭제 없음. pure data generation."""
    bvh = BVHTree.FromBMesh(bm)

    all_co = [v.co for v in bm.verts]
    center = sum(all_co, mathutils.Vector()) / len(all_co)
    max_dist = max((v.co - center).length for v in bm.verts)
    radius = max_dist * 1.3

    golden_ratio = (1 + math.sqrt(5)) / 2
    hit_counts: dict[int, int] = defaultdict(int)

    for i in range(n_rays):
        theta = math.acos(1 - 2 * (i + 0.5) / n_rays)
        phi = 2 * math.pi * i / golden_ratio
        d = mathutils.Vector((
            math.sin(theta) * math.cos(phi),
            math.sin(theta) * math.sin(phi),
            math.cos(theta),
        ))
        origin = center + d * radius
        hit = bvh.ray_cast(origin, (center - origin).normalized())
        if hit[0] is not None:
            hit_counts[hit[2]] += 1

    max_hits = max(hit_counts.values(), default=1)
    return {face.index: hit_counts.get(face.index, 0) / max_hits for face in bm.faces}


def compute_confidence(scores: dict[int, float]) -> float:
    """sampling이 mesh를 얼마나 커버했는지. 0~1."""
    if not scores:
        return 0.0
    return sum(1 for s in scores.values() if s > 0) / len(scores)


def apply_filtering_policy(
    bm,
    scores: dict[int, float],
    min_confidence: float = 0.3,
    visibility_threshold: float = 0.0,
) -> tuple[list, float, str]:
    """
    Policy layer: 삭제 대상 face 결정.
    Returns: (faces_to_delete, confidence, decision_reason)
    """
    confidence = compute_confidence(scores)
    if confidence < min_confidence:
        return [], confidence, f"low_confidence({confidence:.2f})"
    faces_to_delete = [f for f in bm.faces if scores.get(f.index, 0.0) <= visibility_threshold]
    return faces_to_delete, confidence, "ok"


def write_culled_obj(bm, output_path: str, scores: dict[int, float]) -> list[float]:
    """
    BMesh에서 직접 OBJ 작성. vertex 순서를 통제해 visibility와 인덱스를 일치시킨다.
    Returns: vertex_visibility (OBJ vertex 순서와 동일한 float 리스트)
    """
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # face에 참조된 vertex만 수집 (OBJ 순서 = sorted BMesh vertex index)
    used = sorted({v.index for face in bm.faces for v in face.verts})
    remap = {old: new for new, old in enumerate(used)}

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for v_idx in used:
            v = bm.verts[v_idx]
            f.write(f"v {v.co.x:.9g} {v.co.y:.9g} {v.co.z:.9g}\n")
        for face in bm.faces:
            f.write(f"f {' '.join(str(remap[v.index] + 1) for v in face.verts)}\n")

    # vertex visibility = 인접 face score 평균
    vert_vis: list[float] = []
    for v_idx in used:
        v = bm.verts[v_idx]
        adj = [scores.get(f.index, 0.0) for f in v.link_faces]
        vert_vis.append(float(sum(adj) / len(adj)) if adj else 0.0)

    return vert_vis


def main():
    args = parse_args()
    clear_scene()
    import_obj(args.input)

    mesh_objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not mesh_objs:
        raise RuntimeError("No mesh found after import.")

    if len(mesh_objs) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in mesh_objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = mesh_objs[0]
        bpy.ops.object.join()

    obj = bpy.context.active_object
    total_faces = len(obj.data.polygons)
    min_faces = max(1, int(total_faces * args.min_component_ratio))
    t0 = time.perf_counter()
    print(f"Input: {total_faces} faces  (min_component_threshold={min_faces})", flush=True)

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # --- Stage 1: BFS로 connected component 탐색 → 소형 component 삭제 ---
    print("Stage 1: BFS connected components...", flush=True)
    t1 = time.perf_counter()

    visited: set = set()
    components: list = []
    for seed in bm.faces:
        if seed in visited:
            continue
        comp: list = []
        stack = [seed]
        while stack:
            face = stack.pop()
            if face in visited:
                continue
            visited.add(face)
            comp.append(face)
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked not in visited:
                        stack.append(linked)
        components.append(comp)

    small_faces = [f for comp in components if len(comp) < min_faces for f in comp]
    removed_component_faces = len(small_faces)

    if removed_component_faces > total_faces * 0.5:
        print(
            f"Stage 1: would remove {removed_component_faces}/{total_faces} faces "
            f"({100 * removed_component_faces / total_faces:.0f}%) — too aggressive, skipping",
            flush=True,
        )
        small_faces = []
        removed_component_faces = 0
    elif small_faces:
        bmesh.ops.delete(bm, geom=small_faces, context="FACES")

    after_stage1 = total_faces - removed_component_faces
    print(
        f"Stage 1 (loose components): {len(components)} components, "
        f"removed {removed_component_faces} → {after_stage1} remaining  "
        f"[{time.perf_counter() - t1:.1f}s]",
        flush=True,
    )

    # --- Stage 2: multi-view ray casting visibility scoring ---
    print("Stage 2: computing visibility scores...", flush=True)
    t2 = time.perf_counter()

    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    N_RAYS = 512
    scores = compute_visibility_scores(bm, n_rays=N_RAYS)
    confidence = compute_confidence(scores)

    print(
        f"Stage 2 (visibility): {N_RAYS} rays, confidence={confidence:.2f}, "
        f"visible={sum(1 for s in scores.values() if s > 0)}/{len(scores)} faces  "
        f"[{time.perf_counter() - t2:.1f}s]",
        flush=True,
    )

    # Policy layer: filtering decision (결정 로직 분리)
    faces_to_delete, confidence, reason = apply_filtering_policy(bm, scores)
    removed_interior = len(faces_to_delete)

    if reason != "ok":
        print(f"Stage 2: filtering skipped — {reason}", flush=True)
    elif faces_to_delete:
        bmesh.ops.delete(bm, geom=faces_to_delete, context="FACES_ONLY")
        print(f"Stage 2: removed {removed_interior} invisible faces", flush=True)

    # --- 결과 요약 및 출력 ---
    final_faces = len(list(bm.faces))
    total_removed = total_faces - final_faces
    ratio = 100.0 * final_faces / total_faces if total_faces > 0 else 0.0
    print(
        f"Culled: {total_faces} → {final_faces} faces "
        f"({ratio:.1f}% remaining, {total_removed} removed)  "
        f"[total {time.perf_counter() - t0:.1f}s]",
        flush=True,
    )

    if final_faces == 0:
        print("WARNING: 0 faces after culling — falling back to original mesh", flush=True)
        bm.free()
        shutil.copy2(args.input, args.output)
    else:
        # OBJ 직접 작성 + vertex visibility 수집
        vert_vis = write_culled_obj(bm, args.output, scores)
        bm.free()

        # Artifact: face_visibility.json (QEM weight 입력용)
        score_path = Path(args.output).parent / "face_visibility.json"
        score_path.write_text(
            json.dumps({
                "vertex_visibility": vert_vis,
                "confidence": confidence,
                "n_rays": N_RAYS,
                "removed_faces": removed_interior,
                "decision": reason,
            }),
            encoding="utf-8",
        )
        print(f"Stage 2: visibility saved → {score_path}", flush=True)

    print(f"Output: {args.output}", flush=True)


if __name__ == "__main__":
    print("TOP LEVEL cull_interior.py is running", flush=True)
    main()
