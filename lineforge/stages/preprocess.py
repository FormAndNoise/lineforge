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
    
    if auto_level and mode != "threshold":
        img = ImageOps.autocontrast(img, cutoff=0)
    
    if contrast_stretch and mode != "threshold":
        low = int(255 * cs_black / 100)
        high = int(255 * cs_white / 100)
        img = ImageOps.autocontrast(img, cutoff=(low, high))
    
    img.save(dst, "PNG")
    return dst


def preprocess_magick(
    magick: str,
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
    mode: str = "none",               # "none" | "threshold" | "quantize"
    threshold_pct: int = 45,          # used when mode == "threshold"
    quantize_levels: int = 16,        # used when mode == "quantize"
) -> Path:
    """
    Preprocess an image using ImageMagick CLI (magick).
    Always writes a PNG to dst.

    Modes:
      - none: no hard threshold or quantize
      - threshold: brightness cutoff (2-tone B/W)
      - quantize: grayscale tone reduction (levels)
    """
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        raise FileNotFoundError(f"Source image not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    args: list[str] = [magick, str(src)]

    # Flatten alpha (avoid transparency artifacts downstream)
    args += ["-background", "white", "-alpha", "remove", "-alpha", "off"]

    # Strip metadata
    args += ["-strip"]

    # Work in grayscale when requested (also recommended for quantization)
    if grayscale:
        args += ["-colorspace", "Gray"]

    if auto_level:
        args += ["-auto-level"]

    if contrast_stretch:
        args += ["-contrast-stretch", f"{cs_black}%x{cs_white}%"]

    if int(median) > 0:
        args += ["-median", str(int(median))]

    if float(blur) > 0.0:
        args += ["-blur", f"0x{float(blur)}"]

    if negate:
        args += ["-negate"]

    # Mutually exclusive "finish" mode
    mode = (mode or "none").strip().lower()

    if mode == "threshold":
        tp = max(0, min(100, int(threshold_pct)))
        args += ["-threshold", f"{tp}%"]

    elif mode == "quantize":
        # Quantize grayscale to N levels.
        # Use -dither None so it doesn't introduce speckled noise.
        # -colors N reduces to N palette entries.
        levels = int(quantize_levels)
        if levels < 2:
            levels = 2
        if levels > 256:
            levels = 256

        # Ensure gray colorspace for predictable output
        args += ["-colorspace", "Gray"]
        args += ["-dither", "None"]
        args += ["-colors", str(levels)]

    elif mode == "none":
        pass
    else:
        raise ValueError(f"Unknown preprocess mode: {mode!r}")

    # Force PNG output
    args += [f"png:{dst}"]

    run_cmd(args)
    return dst
