import argparse
import json
import sys
from pathlib import Path

import bpy
import bmesh


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def export_world_tri_mesh_obj(output_path: str):
    depsgraph = bpy.context.evaluated_depsgraph_get()

    vertices = []
    faces = []

    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        if obj.hide_get():
            continue

        eval_obj = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()

        # Triangulate + Mesh Normalize (Stage 1)
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))

        before_norm = len(bm.faces)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=list(bm.edges))
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
        bm.faces.ensure_lookup_table()
        non_tri = [f for f in bm.faces if len(f.verts) > 3]
        if non_tri:
            bmesh.ops.triangulate(bm, faces=non_tri)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        print(
            f"[Normalize] {before_norm} → {len(bm.faces)} tris "
            f"(removed {before_norm - len(bm.faces)})",
            flush=True,
        )

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        base_index = len(vertices)
        matrix = eval_obj.matrix_world

        for v in mesh.vertices:
            world_v = matrix @ v.co
            vertices.append((world_v.x, world_v.y, world_v.z))

        for poly in mesh.polygons:
            if len(poly.vertices) == 3:
                a, b, c = poly.vertices
                faces.append((base_index + a, base_index + b, base_index + c))

        eval_obj.to_mesh_clear()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for x, y, z in vertices:
            f.write(f"v {x:.9g} {y:.9g} {z:.9g}\n")
        for a, b, c in faces:
            f.write(f"f {a + 1} {b + 1} {c + 1}\n")

    print(f"Exported {len(vertices)} vertices, {len(faces)} triangles to {output_path}")
    return len(faces)


def save_metadata(output_path: str, original_tris: int):
    max_tex = max(
        (max(img.size) for img in bpy.data.images if img.size[0] > 0),
        default=0,
    )
    meta = {"original_tris": original_tris, "max_texture_size": max_tex}
    meta_path = Path(output_path).parent / "metadata.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f)
    print(f"Metadata saved: {meta}")


def main():
    args = parse_args()
    clear_scene()

    bpy.ops.import_scene.gltf(filepath=args.input)
    original_tris = export_world_tri_mesh_obj(args.output)
    save_metadata(args.output, original_tris)


if __name__ == "__main__":
    print("TOP LEVEL extract_for_qem.py is running", flush=True)
    main()