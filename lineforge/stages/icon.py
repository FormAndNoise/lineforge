from __future__ import annotations

from pathlib import Path
from typing import List
from PIL import Image


def split_ico_to_pngs(ico_path: Path, out_dir: Path) -> List[Path]:
    """
    Extract all embedded icon frames from .ico into PNG files using Pillow.
    Produces: out_dir/<stem>_frame_000.png, etc.
    """
    ico_path = Path(ico_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not ico_path.exists():
        raise FileNotFoundError(f"ICO not found: {ico_path}")

    img = Image.open(ico_path)
    frames = []
    
    try:
        idx = 0
        while True:
            img.seek(idx)
            frame_path = out_dir / f"{ico_path.stem}_frame_{idx:03d}.png"
            # Ensure RGBA for saving
            frame_img = img.copy()
            if frame_img.mode != "RGBA":
                frame_img = frame_img.convert("RGBA")
            frame_img.save(frame_path, "PNG")
            frames.append(frame_path)
            idx += 1
    except EOFError:
        pass

    return frames


def rebuild_ico_from_pngs(png_frames: List[Path], dst_ico: Path) -> Path:
    """
    Rebuild an .ico from multiple PNG frames using Pillow.
    """
    dst_ico = Path(dst_ico)
    dst_ico.parent.mkdir(parents=True, exist_ok=True)

    if not png_frames:
        raise RuntimeError("No PNG frames supplied to rebuild ICO.")

    images = []
    for p in png_frames:
        img = Image.open(p)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        images.append(img)

    if images:
        images[0].save(dst_ico, format="ICO", append_images=images[1:])
        
    return dst_ico
