from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageOps, ImageFilter
from ..utils import run_cmd


def preprocess_pil(
    src: Path,
    dst: Path,
    grayscale: bool = True,
    auto_level: bool = True,
    contrast_stretch: bool = True,
    cs_black: float = 0.5,
    cs_white: float = 0.5,
    median: int = 1,
    blur: float = 0.0,
    negate: bool = False,
    mode: str = "none",
    threshold_pct: int = 45,
    quantize_levels: int = 16,
) -> Path:
    src = Path(src)
    dst = Path(dst)
    if not src.exists():
        raise FileNotFoundError(f"Source image not found: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    img = Image.open(src)
    
    if grayscale:
        img = img.convert("L")
    
    if negate:
        img = ImageOps.invert(img)
    
    if median and median > 0:
        img = img.filter(ImageFilter.MedianFilter(size=int(median)))
    
    if blur and blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=float(blur)))
    
    mode = (mode or "none").strip().lower()
    
    if mode == "threshold":
        threshold = int(255 * threshold_pct / 100)
        img = img.convert("L").point(lambda p: 255 if p > threshold else 0).convert("1")
    elif mode == "quantize":
        levels = max(2, min(256, int(quantize_levels)))
        img = img.convert("L")
        img = img.quantize(colors=levels, method=Image.Quantize.MEDIANCUT, kmeans=0)
        img = img.convert("L")  # quantize() returns palette mode (P); convert back for autocontrast
    
    if auto_level and mode != "threshold":
        img = ImageOps.autocontrast(img, cutoff=0)
    
    if contrast_stretch and mode != "threshold":
        low = int(255 * cs_black / 100)
        high = int(255 * cs_white / 100)
        img = ImageOps.autocontrast(img, cutoff=(low, high))
    
    img.save(dst, "PNG")
    return dst

