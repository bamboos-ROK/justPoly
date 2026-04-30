import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--high-glb", required=True)
    parser.add_argument("--low-obj", required=True)
    parser.add_argument("--output-glb", required=True)
    parser.add_argument("--baked-png", required=True)
    parser.add_argument("--texture-size", type=int, default=4096)
    parser.add_argument("--uv-angle-deg", type=float, default=66.0)
    parser.add_argument("--uv-margin", type=float, default=0.005)
    parser.add_argument("--bake-margin", type=int, default=16)
    parser.add_argument("--ray-factor", type=float, default=0.01)
    parser.add_argument("--samples", type=int, default=64)
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
                idx = []
                for p in parts:
                    idx.append(int(p.split("/")[0]) - 1)
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


def create_uv(obj, angle_deg: float, margin: float):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="BakedUV")
    obj.data.uv_layers.active = obj.data.uv_layers[0]

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(angle_deg),
        island_margin=margin,
        area_weight=0.0,
    )
    try:
        bpy.ops.uv.pack_islands(margin=margin)
    except Exception:
        pass
    bpy.ops.object.mode_set(mode="OBJECT")


def bbox_diag(objects):
    mins = Vector((float("inf"), float("inf"), float("inf")))
    maxs = Vector((float("-inf"), float("-inf"), float("-inf")))

    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            p = obj.matrix_world @ Vector(corner)
            mins.x = min(mins.x, p.x)
            mins.y = min(mins.y, p.y)
            mins.z = min(mins.z, p.z)
            maxs.x = max(maxs.x, p.x)
            maxs.y = max(maxs.y, p.y)
            maxs.z = max(maxs.z, p.z)

    return (maxs - mins).length


def create_bake_material(low_obj, image):
    mat = bpy.data.materials.new("BakedMaterial")
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    tex = nodes.new(type="ShaderNodeTexImage")
    tex.name = "BakedBaseColor"
    tex.image = image

    if bsdf:
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

    low_obj.data.materials.clear()
    low_obj.data.materials.append(mat)

    for node in nodes:
        node.select = False
    tex.select = True
    nodes.active = tex


def bake_basecolor(high_objs, low_obj, image, baked_png, bake_margin, max_ray_distance, samples):
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = samples

    create_bake_material(low_obj, image)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in high_objs:
        obj.select_set(True)

    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj

    # BaseColor 중심 bake.
    # 복잡한 material node가 있으면 DIFFUSE COLOR 대신 EMIT bake 방식으로 확장 가능.
    bpy.ops.object.bake(
        type="DIFFUSE",
        pass_filter={"COLOR"},
        use_selected_to_active=True,
        max_ray_distance=max_ray_distance,
        margin=bake_margin,
    )

    image.filepath_raw = baked_png
    image.file_format = "PNG"
    image.save()

    # GLB export 시 image 포함 안정성을 위해 pack
    image.pack()


def export_glb(low_obj, output_glb):
    bpy.ops.object.select_all(action="DESELECT")
    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj

    Path(output_glb).parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
    )


def main():
    args = parse_args()

    clear_scene()

    bpy.ops.import_scene.gltf(filepath=args.high_glb)
    high_objs = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]

    if not high_objs:
        raise RuntimeError("No high-poly mesh objects found in GLB.")

    low_obj = load_simple_obj(args.low_obj, "LowPoly")
    create_uv(low_obj, args.uv_angle_deg, args.uv_margin)

    image = bpy.data.images.new(
        name="BakedBaseColor",
        width=args.texture_size,
        height=args.texture_size,
        alpha=True,
    )

    diag = bbox_diag(high_objs + [low_obj])
    max_ray_distance = diag * args.ray_factor

    print(f"Ray distance: {max_ray_distance}")

    bake_basecolor(
        high_objs=high_objs,
        low_obj=low_obj,
        image=image,
        baked_png=args.baked_png,
        bake_margin=args.bake_margin,
        max_ray_distance=max_ray_distance,
        samples=args.samples,
    )

    export_glb(low_obj, args.output_glb)
    print(f"Exported GLB: {args.output_glb}")


if __name__ == "__main__":
    main()