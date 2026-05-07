import argparse
from pathlib import Path

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target-tris", type=int, required=True)
    args = parser.parse_args()

    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(args.input)

    original_faces = ms.current_mesh().face_number()
    if original_faces == 0:
        raise RuntimeError("Input mesh has no triangles.")

    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_null_faces()
    ms.meshing_remove_unreferenced_vertices()
    ms.compute_normal_per_vertex()

    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=args.target_tris,
        preservetopology=True,
        preservenormal=True,
        planarquadric=False,
        qualitythr=0.9
    )

    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_null_faces()
    ms.meshing_remove_unreferenced_vertices()
    ms.compute_normal_per_vertex()

    simplified_faces = ms.current_mesh().face_number()
    write_obj(args.output, ms)

    print(f"Original triangles: {original_faces}")
    print(f"Simplified triangles: {simplified_faces}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
