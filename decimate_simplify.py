import argparse
import sys
from pathlib import Path

import bmesh
import bpy


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target-tris", type=int, required=True)
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def load_simple_obj(path: str, name: str):
    verts = []
    faces = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("v "):
                _, x, y, z = line.strip().split()[:4]
                verts.append((float(x), float(y), float(z)))
            elif line.startswith("f "):
                parts = line.strip().split()[1:]
                idx = [int(p.split("/")[0]) - 1 for p in parts]
                if len(idx) == 3:
                    faces.append(tuple(idx))

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    return obj


def triangle_count(obj):
    return sum(1 for poly in obj.data.polygons if len(poly.vertices) == 3)


def rebuild_mesh(obj, *, merge_distance: float = 0.0):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    if merge_distance > 0:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_distance)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def apply_decimate(obj, target_tris: int):
    rebuild_mesh(obj, merge_distance=1e-9)
    original_tris = triangle_count(obj)
    if original_tris == 0:
        raise RuntimeError("Input mesh has no triangles.")

    ratio = min(1.0, max(0.0, target_tris / original_tris))

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    mod = obj.modifiers.new("DecimateToTarget", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio

    bpy.ops.object.modifier_apply(modifier=mod.name)
    rebuild_mesh(obj)

    return original_tris, triangle_count(obj)


def write_obj(path: str, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    mesh = obj.data
    with path.open("w", encoding="utf-8") as f:
        for v in mesh.vertices:
            f.write(f"v {v.co.x:.9g} {v.co.y:.9g} {v.co.z:.9g}\n")
        for poly in mesh.polygons:
            if len(poly.vertices) != 3:
                continue
            a, b, c = poly.vertices
            f.write(f"f {a + 1} {b + 1} {c + 1}\n")


def main():
    args = parse_args()
    clear_scene()

    obj = load_simple_obj(args.input, "DecimateSource")
    original_tris, simplified_tris = apply_decimate(obj, args.target_tris)
    write_obj(args.output, obj)

    print(f"Original triangles: {original_tris}")
    print(f"Simplified triangles: {simplified_tris}")
    if simplified_tris > args.target_tris:
        print(
            "Warning: Blender Decimate did not reach target_tris. "
            "This can happen when boundary/disconnected geometry limits edge collapse."
        )
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
