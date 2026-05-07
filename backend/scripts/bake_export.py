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
    parser.add_argument("--normal-png", default=None)
    parser.add_argument("--skip-normal-bake", action="store_true")
    parser.add_argument("--texture-size", type=int, default=4096)
    parser.add_argument("--uv-angle-deg", type=float, default=66.0)
    parser.add_argument("--uv-margin", type=float, default=0.005)
    parser.add_argument("--bake-margin", type=int, default=16)
    parser.add_argument("--ray-factor", type=float, default=0.01)
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--skip-high-poly-cleanup", action="store_true")
    parser.add_argument("--cage-factor", type=float, default=0.005)
    parser.add_argument("--skip-cage", action="store_true")
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


# ── UV 전략 ───────────────────────────────────────────────────────────────────

def _uv_smart_project(obj, angle_deg, margin):
    """Smart UV Project: island 다수이나 항상 0-1 범위 내 패킹 보장."""
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(angle_deg),
        island_margin=margin,
        area_weight=1.0,
    )
    bpy.ops.object.mode_set(mode="OBJECT")


def create_uv(obj, angle_deg: float, margin: float):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="BakedUV")
    obj.data.uv_layers.active = obj.data.uv_layers[0]

    _uv_smart_project(obj, angle_deg, margin)


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


# ── High Poly Cleanup ────────────────────────────────────────────────────────

def cleanup_high_poly(high_objs, skip=False):
    if skip:
        print("[Cleanup] 건너뜀 (--skip-high-poly-cleanup)")
        return
    for obj in high_objs:
        if obj.type != "MESH":
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        try:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
            bpy.ops.mesh.normals_make_consistent(inside=False)
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")
        print(f"[Cleanup] {obj.name} 완료")


# ── Shade Smooth ──────────────────────────────────────────────────────────────

def apply_shade_smooth(obj):
    """UV 생성 후 적용해야 tangent basis seam artifact 최소화."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()


# ── Bake 전략 ─────────────────────────────────────────────────────────────────

def create_bake_material(low_obj, color_image, normal_image):
    """베이크 중 순환 의존성 방지: 이미지 노드는 active만 유지, BSDF 연결은 베이크 후 수행."""
    mat = bpy.data.materials.new("BakedMaterial")
    mat.use_nodes = True

    nodes = mat.node_tree.nodes

    color_tex = nodes.new(type="ShaderNodeTexImage")
    color_tex.name = "BakedBaseColor"
    color_tex.image = color_image

    if normal_image is not None:
        normal_tex = nodes.new(type="ShaderNodeTexImage")
        normal_tex.name = "BakedNormal"
        normal_tex.image = normal_image
        normal_tex.image.colorspace_settings.name = "Non-Color"

    low_obj.data.materials.clear()
    low_obj.data.materials.append(mat)

    for node in nodes:
        node.select = False


def _set_active_image_node(low_obj, node_name: str):
    mat = low_obj.data.materials[0]
    nodes = mat.node_tree.nodes
    for node in nodes:
        node.select = False
    target = nodes.get(node_name)
    if target is None:
        raise RuntimeError(f"Image node '{node_name}' not found in material")
    target.select = True
    nodes.active = target


def _connect_baked_material(low_obj):
    """베이크 완료 후 BaseColor + Normal Map을 BSDF에 연결 (GLB export용)."""
    mat = low_obj.data.materials[0]
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)

    color_tex = nodes.get("BakedBaseColor")
    if bsdf and color_tex:
        links.new(color_tex.outputs["Color"], bsdf.inputs["Base Color"])

    normal_tex = nodes.get("BakedNormal")
    if bsdf and normal_tex:
        nm_node = nodes.new(type="ShaderNodeNormalMap")
        nm_node.space = 'TANGENT'
        links.new(normal_tex.outputs["Color"], nm_node.inputs["Color"])
        links.new(nm_node.outputs["Normal"], bsdf.inputs["Normal"])


def _bake_diffuse(high_objs, low_obj, max_ray_distance, bake_margin,
                  use_cage=False, cage_extrusion=0.0):
    """DIFFUSE + COLOR pass: 재질 조작 없이 high poly albedo를 직접 베이크."""
    bpy.ops.object.select_all(action="DESELECT")
    for obj in high_objs:
        obj.select_set(True)
    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj

    bake_kwargs = dict(
        type="DIFFUSE",
        pass_filter={"COLOR"},
        use_selected_to_active=True,
        max_ray_distance=max_ray_distance,
        margin=bake_margin,
    )
    if use_cage and cage_extrusion > 0:
        bake_kwargs["use_cage"] = True
        bake_kwargs["cage_extrusion"] = cage_extrusion

    try:
        result = bpy.ops.object.bake(**bake_kwargs)
        if "FINISHED" not in result:
            raise RuntimeError(f"bake returned: {result}")
        print("[Bake] BaseColor 완료" + (" (cage)" if use_cage else ""))
    except Exception as e:
        if use_cage:
            print(f"[Bake] Cage bake 실패: {e} — fallback")
            bpy.ops.object.bake(
                type="DIFFUSE",
                pass_filter={"COLOR"},
                use_selected_to_active=True,
                max_ray_distance=max_ray_distance,
                margin=bake_margin,
            )
        else:
            raise


def _bake_normal(high_objs, low_obj, max_ray_distance, bake_margin,
                 use_cage=False, cage_extrusion=0.0):
    """Tangent Space Normal Map bake."""
    bpy.context.scene.render.bake.normal_space = 'TANGENT'

    bpy.ops.object.select_all(action="DESELECT")
    for obj in high_objs:
        obj.select_set(True)
    low_obj.select_set(True)
    bpy.context.view_layer.objects.active = low_obj

    bake_kwargs = dict(
        type="NORMAL",
        use_selected_to_active=True,
        max_ray_distance=max_ray_distance,
        margin=bake_margin,
    )
    if use_cage and cage_extrusion > 0:
        bake_kwargs["use_cage"] = True
        bake_kwargs["cage_extrusion"] = cage_extrusion

    try:
        result = bpy.ops.object.bake(**bake_kwargs)
        if "FINISHED" not in result:
            raise RuntimeError(f"bake returned: {result}")
        print("[Bake] Normal 완료" + (" (cage)" if use_cage else ""))
    except Exception as e:
        if use_cage:
            print(f"[Bake] Normal cage bake 실패: {e} — fallback")
            bpy.ops.object.bake(
                type="NORMAL",
                use_selected_to_active=True,
                max_ray_distance=max_ray_distance,
                margin=bake_margin,
            )
        else:
            raise


def bake_textures(high_objs, low_obj,
                  color_image, baked_png,
                  normal_image, normal_png,
                  bake_margin, max_ray_distance, samples,
                  skip_high_poly_cleanup=False,
                  use_cage=False, cage_extrusion=0.0,
                  skip_normal_bake=False):
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = samples

    cleanup_high_poly(high_objs, skip=skip_high_poly_cleanup)
    create_bake_material(low_obj, color_image, normal_image)

    _set_active_image_node(low_obj, "BakedBaseColor")
    _bake_diffuse(high_objs, low_obj, max_ray_distance, bake_margin,
                  use_cage=use_cage, cage_extrusion=cage_extrusion)

    if not skip_normal_bake:
        _set_active_image_node(low_obj, "BakedNormal")
        _bake_normal(high_objs, low_obj, max_ray_distance, bake_margin,
                     use_cage=use_cage, cage_extrusion=cage_extrusion)

    _connect_baked_material(low_obj)

    color_image.filepath_raw = baked_png
    color_image.file_format = "PNG"
    color_image.save()
    color_image.pack()

    if not skip_normal_bake and normal_image and normal_png:
        normal_image.filepath_raw = normal_png
        normal_image.file_format = "PNG"
        normal_image.save()
        normal_image.pack()


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
        export_tangents=True,
    )


def main():
    try:
        _main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _main():
    args = parse_args()

    clear_scene()

    bpy.ops.import_scene.gltf(filepath=args.high_glb)
    high_objs = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]

    if not high_objs:
        raise RuntimeError("No high-poly mesh objects found in GLB.")

    low_obj = load_simple_obj(args.low_obj, "LowPoly")
    create_uv(low_obj, args.uv_angle_deg, args.uv_margin)
    apply_shade_smooth(low_obj)

    color_image = bpy.data.images.new(
        name="BakedBaseColor",
        width=args.texture_size,
        height=args.texture_size,
        alpha=True,
    )

    if not args.skip_normal_bake:
        normal_image = bpy.data.images.new(
            name="BakedNormal",
            width=args.texture_size,
            height=args.texture_size,
            alpha=False,
        )
        normal_image.colorspace_settings.name = "Non-Color"
    else:
        normal_image = None
        print("[Main] Normal Bake 스킵")

    diag = bbox_diag(high_objs + [low_obj])
    max_ray_distance = diag * args.ray_factor
    cage_extrusion = max(diag * args.cage_factor, 1e-5)

    print(f"[Main] diag={diag:.4f}, ray={max_ray_distance:.6f}, cage={cage_extrusion:.6f}")

    bake_textures(
        high_objs=high_objs,
        low_obj=low_obj,
        color_image=color_image,
        baked_png=args.baked_png,
        normal_image=normal_image,
        normal_png=args.normal_png,
        skip_normal_bake=args.skip_normal_bake,
        bake_margin=args.bake_margin,
        max_ray_distance=max_ray_distance,
        samples=args.samples,
        skip_high_poly_cleanup=args.skip_high_poly_cleanup,
        use_cage=not args.skip_cage,
        cage_extrusion=cage_extrusion,
    )

    export_glb(low_obj, args.output_glb)
    print(f"Exported GLB: {args.output_glb}")


if __name__ == "__main__":
    main()
