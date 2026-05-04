import argparse
import json
import subprocess
import sys
from pathlib import Path


def nearest_pow2(n: int) -> int:
    p = 1
    while p * 2 <= n:
        p *= 2
    return p


def run(cmd):
    print(" ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True)


def require_file(path: Path, label: str):
    if not path.exists():
        raise FileNotFoundError(f"{label} was not created: {path}")
    if path.stat().st_size == 0:
        raise RuntimeError(f"{label} is empty: {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target-tris", type=int, default=None)
    parser.add_argument("--texture-size", type=int, default=None)
    parser.add_argument("--tris-ratio", type=float, default=0.1)
    parser.add_argument("--texture-ratio", type=float, default=0.5)
    parser.add_argument("--skip-high-poly-cleanup", action="store_true")
    parser.add_argument("--skip-cage", action="store_true")
    parser.add_argument("--blender", default="blender")
    parser.add_argument("--workdir", default="_glb_opt_work")
    args = parser.parse_args()

    workdir = Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    input_glb = Path(args.input).resolve()
    output_glb = Path(args.output).resolve()

    qem_source = workdir / "qem_source.obj"
    low_obj = workdir / "low.obj"
    baked_png = workdir / "baked_basecolor.png"

    print(f"Working directory: {workdir}", flush=True)

    run([
        args.blender, "-b",
        "--python", str(Path("extract_for_qem.py").resolve()),
        "--",
        "--input", str(input_glb),
        "--output", str(qem_source),
    ])

    require_file(qem_source, "QEM source OBJ")

    meta_path = workdir / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if args.target_tris is None:
            args.target_tris = max(1000, int(meta["original_tris"] * args.tris_ratio))
        if args.texture_size is None:
            raw = int(meta["max_texture_size"] * args.texture_ratio)
            args.texture_size = min(4096, max(512, nearest_pow2(raw)))
        print(f"Auto: target_tris={args.target_tris}, texture_size={args.texture_size}", flush=True)
    else:
        if args.target_tris is None:
            args.target_tris = 50000
        if args.texture_size is None:
            args.texture_size = 4096

    run([
        sys.executable, str(Path("qem_simplify.py").resolve()),
        "--input", str(qem_source),
        "--output", str(low_obj),
        "--target-tris", str(args.target_tris),
    ])

    require_file(low_obj, "Low-poly OBJ")

    bake_cmd = [
        args.blender, "-b",
        "--python", str(Path("bake_export.py").resolve()),
        "--",
        "--high-glb", str(input_glb),
        "--low-obj", str(low_obj),
        "--output-glb", str(output_glb),
        "--baked-png", str(baked_png),
        "--texture-size", str(args.texture_size),
    ]
    
    if args.skip_high_poly_cleanup:
        bake_cmd.append("--skip-high-poly-cleanup")
    if args.skip_cage:
        bake_cmd.append("--skip-cage")

    run(bake_cmd)

    require_file(output_glb, "Output GLB")


if __name__ == "__main__":
    main()