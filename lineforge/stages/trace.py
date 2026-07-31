from __future__ import annotations

import tempfile
from pathlib import Path
from PIL import Image, ImageOps

from ..utils import run_cmd


def trace_to_svg(
    vpipe: str,
    src: Path,
    dst: Path,
    cutoff_pct: int = 45,
    invert: bool = False,
    turdsize: int = 8,
    smooth: bool = True,
    out_fmt: str = "svg",
) -> Path:
    """
    Trace a raster image to SVG using vpipe-cli.
    """
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        raise FileNotFoundError(f"Source image not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        raw_file = td_path / (src.stem + ".gray")

        # 1) Prepare the image for the Rust engine (apply invert/threshold here if needed)
        # Note: vpipe-cli applies its own 0.5 threshold internally.
        img = Image.open(src).convert("L")
        if invert:
            img = ImageOps.invert(img)
            
        threshold_val = int(255 * cutoff_pct / 100)
        img = img.point(lambda p: 255 if p > threshold_val else 0)
        
        with open(raw_file, "wb") as f:
            f.write(img.tobytes())

        # 2) vpipe-cli -> file export
        args = [
            vpipe,
            str(raw_file),
            str(img.width),
            str(img.height),
            "--turdsize",
            str(int(turdsize)),
            "--format",
            out_fmt,
            "--out",
            str(dst)
        ]

        if not smooth:
            args.append("--flat")

        run_cmd(args)

    return dst
