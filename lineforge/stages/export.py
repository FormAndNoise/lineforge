from __future__ import annotations

from pathlib import Path

from ..utils import run_cmd


def export_svg(
    inkscape: str,
    svg: Path,
    dst: Path,
    width: int = 512,
    area_drawing: bool = True,
    export_format: str = "png",
) -> Path:
    """Export an SVG to various formats using Inkscape CLI."""
    svg = Path(svg)
    dst = Path(dst)

    if not svg.exists():
        raise FileNotFoundError(f"SVG not found: {svg}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    valid_formats = ("png", "svg", "pdf", "eps")
    export_format = export_format if export_format in valid_formats else "png"

    w = max(1, int(width))

    args = [
        inkscape,
        str(svg),
        f"--export-type={export_format}",
        f"--export-filename={dst}",
        f"--export-width={w}",
    ]
    if area_drawing and export_format == "png":
        args.append("--export-area-drawing")

    run_cmd(args)
    return dst


def export_svg_to_png(
    inkscape: str,
    svg: Path,
    dst: Path,
    width: int = 512,
    area_drawing: bool = True,
) -> Path:
    return export_svg(inkscape, svg, dst, width, area_drawing, "png")