import argparse
from pathlib import Path

import open3d as o3d


def write_obj(path: str, mesh: o3d.geometry.TriangleMesh):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    vertices = mesh.vertices
    triangles = mesh.triangles

    with path.open("w", encoding="utf-8") as f:
        for v in vertices:
            f.write(f"v {v[0]:.9g} {v[1]:.9g} {v[2]:.9g}\n")
        for tri in triangles:
            f.write(f"f {tri[0] + 1} {tri[1] + 1} {tri[2] + 1}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target-tris", type=int, required=True)
    args = parser.parse_args()

    mesh = o3d.io.read_triangle_mesh(args.input)

    if len(mesh.triangles) == 0:
        raise RuntimeError("Input mesh has no triangles.")

    mesh.remove_duplicated_vertices()
    mesh.remove_duplicated_triangles()
    mesh.remove_degenerate_triangles()
    mesh.remove_unreferenced_vertices()
    mesh.compute_vertex_normals()

    low = mesh.simplify_quadric_decimation(
        target_number_of_triangles=args.target_tris
    )

    low.remove_duplicated_vertices()
    low.remove_duplicated_triangles()
    low.remove_degenerate_triangles()
    low.remove_unreferenced_vertices()
    low.compute_vertex_normals()

    write_obj(args.output, low)

    print(f"Original triangles: {len(mesh.triangles)}")
    print(f"Simplified triangles: {len(low.triangles)}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()