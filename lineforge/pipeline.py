from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, List, Callable, Optional

from .utils import list_images
from .deps import find_vpipe
from .settings import Settings
from .stages.preprocess import preprocess_pil
from .stages.pad import pad_square
from .stages.trace import trace_to_svg
from .stages.icon import split_ico_to_pngs, rebuild_ico_from_pngs


class PipelineResult:
    def __init__(self):
        self.total_files = 0
        self.processed_files = 0
        self.failed_files: List[str] = []
        self.total_bytes = 0
        self.stage_stats: Dict[str, int] = {}


_cancel_event: threading.Event = threading.Event()


def _choose_last_raster_dir(output_root: Path, s: Settings) -> Path:
    if s.do_export and (output_root / s.output_dir_export).exists():
        return output_root / s.output_dir_export
    if s.do_pad and (output_root / s.output_dir_pad).exists():
        return output_root / s.output_dir_pad
    if s.do_preprocess and (output_root / s.output_dir_preprocess).exists():
        return output_root / s.output_dir_preprocess
    return output_root


def _get_output_dir(output_root: Path, stage: str, s: Settings) -> Path:
    dir_map = {
        "preprocess": s.output_dir_preprocess,
        "pad": s.output_dir_pad,
        "trace": s.output_dir_svg,
        "export": s.output_dir_export,
    }
    return output_root / dir_map.get(stage, f"04_{stage}")


def run_all(
    input_path: Path,
    output_root: Path,
    s: Settings,
    log: Callable[[str], None],
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> PipelineResult:
    global _cancel_event
    _cancel_event.clear()
    result = PipelineResult()

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    files = list_images(input_path, recursive=s.input_recursive)
    if not files:
        raise RuntimeError(
            "No supported images found.\n"
            "If your images are inside subfolders, enable: Include subfolders (recursive)."
        )

    result.total_files = len(files)


    ico_map: Dict[str, Dict[str, object]] = {}
    if s.handle_ico:
        expanded: List[Path] = []
        ico_files = [p for p in files if p.suffix.lower() == ".ico"]
        other_files = [p for p in files if p.suffix.lower() != ".ico"]

        if ico_files:
            log(f"\n[ICO] Extracting frames from {len(ico_files)} icon(s)...\n")
            ico_stage_dir = output_root / "_ico_frames"
            ico_stage_dir.mkdir(parents=True, exist_ok=True)

            for ico in ico_files:
                if _cancel_event.is_set():
                    log("  CANCELLED\n")
                    return result
                frame_dir = ico_stage_dir / ico.stem
                frames = split_ico_to_pngs(ico, frame_dir)
                if not frames:
                    log(f"  WARN: no frames extracted from {ico.name}\n")
                    continue
                ico_map[ico.stem] = {"src": ico, "frames": frames}
                expanded.extend(frames)
                log(f"  {ico.name}: {len(frames)} frame(s)\n")

        files = other_files + expanded

    if not files:
        raise RuntimeError("No images to process after ICO extraction. (Were the ICOs valid?)")

    def emit_progress(current: int, total: int):
        if progress_callback:
            progress_callback(current, total)

    if s.do_preprocess:
        d1 = output_root / _get_output_dir(output_root, "preprocess", s)
        d1.mkdir(parents=True, exist_ok=True)

        log(f"\n[A] Preprocess -> {d1}\n")
        count = 0
        for i, src in enumerate(files, 1):
            if _cancel_event.is_set():
                log("  CANCELLED\n")
                return result
            dst = d1 / (src.stem + ".png")
            if s.skip_existing and dst.exists():
                log(f"  [{i}/{len(files)}] {src.name} (skipped, exists)\n")
                emit_progress(i, len(files))
                continue
            try:
                log(f"  [{i}/{len(files)}] {src.name}\n")
                preprocess_pil(
                    src, dst,
                    s.grayscale, s.auto_level, s.contrast_stretch,
                    s.cs_black, s.cs_white, s.median, s.blur,
                    s.negate,
                    s.preprocess_mode, s.threshold_pct, s.quantize_levels
                )
                count += 1
            except Exception as e:
                log(f"  ERROR: {src.name}: {e}\n")
                result.failed_files.append(src.name)
            emit_progress(i, len(files))
        result.stage_stats["preprocess"] = count
        files = list_images(d1, recursive=False)

    if s.do_pad:
        d2 = output_root / _get_output_dir(output_root, "pad", s)
        d2.mkdir(parents=True, exist_ok=True)
        log(f"\n[B] Pad -> {d2}\n")
        count = 0
        for i, src in enumerate(files, 1):
            if _cancel_event.is_set():
                log("  CANCELLED\n")
                return result
            out_base = d2 / src.stem
            if s.skip_existing and out_base.with_suffix(".png" if s.pad_out_fmt == "png" else ".jpg").exists():
                log(f"  [{i}/{len(files)}] {src.name} (skipped, exists)\n")
                emit_progress(i, len(files))
                continue
            try:
                log(f"  [{i}/{len(files)}] {src.name}\n")
                pad_square(src, out_base, s.pad_size, s.pad_bg, s.pad_out_fmt, s.jpeg_quality)
                count += 1
            except Exception as e:
                log(f"  ERROR: {src.name}: {e}\n")
                result.failed_files.append(src.name)
            emit_progress(i, len(files))
        result.stage_stats["pad"] = count
        files = list_images(d2, recursive=False)

    if s.do_trace:
        vpipe = find_vpipe()
        if not vpipe:
            if s.strict_mode:
                raise RuntimeError("vpipe-cli (LineForge Engine) not found in bin/.")
            log("  WARN: vpipe-cli not found - skipping Trace stage\n")
            s.do_trace = False
        else:
            d3 = output_root / _get_output_dir(output_root, "trace", s)
            d3.mkdir(parents=True, exist_ok=True)
            log(f"\n[C] Trace -> {d3}\n")
            count = 0
            for i, src in enumerate(files, 1):
                if _cancel_event.is_set():
                    log("  CANCELLED\n")
                    return result
                dst = d3 / (src.stem + ".svg")
                if s.skip_existing and dst.exists():
                    log(f"  [{i}/{len(files)}] {src.name} (skipped, exists)\n")
                    emit_progress(i, len(files))
                    continue
                try:
                    log(f"  [{i}/{len(files)}] {src.name}\n")
                    out_fmt = s.export_format if s.do_export and s.export_format in ("svg", "pdf", "eps") else "svg"
                    dst = d3 / (src.stem + f".{out_fmt}")
                    trace_to_svg(
                        vpipe, src, dst,
                        s.trace_cutoff_pct, s.trace_invert,
                        s.potrace_turdsize, s.potrace_smooth,
                        out_fmt
                    )
                    count += 1
                except Exception as e:
                    log(f"  ERROR: {src.name}: {e}\n")
                    result.failed_files.append(src.name)
                emit_progress(i, len(files))
            result.stage_stats["trace"] = count
            files = sorted(d3.glob("*.svg"))

    if s.do_export and not s.do_trace:
        log("  WARN: LineForge Engine directly exports from raster.\n")
        log("  Please enable 'Vectorize (Trace)' to generate PDF/EPS.\n")
        log("  Standalone SVG export is no longer supported without Inkscape.\n")

    if s.handle_ico and ico_map:
        src_raster_dir = _choose_last_raster_dir(output_root, s)
        out_ico_dir = output_root / "05_ico"
        out_ico_dir.mkdir(parents=True, exist_ok=True)

        log(f"\n[ICO] Rebuilding icons -> {out_ico_dir}\n")

        for stem, info in ico_map.items():
            if _cancel_event.is_set():
                log("  CANCELLED\n")
                return result
            frames: List[Path] = info["frames"]
            processed_frames = []

            for fr in frames:
                cand_png = src_raster_dir / (Path(fr).stem + ".png")
                cand_jpg = src_raster_dir / (Path(fr).stem + ".jpg")
                if cand_png.exists():
                    processed_frames.append(cand_png)
                elif cand_jpg.exists():
                    processed_frames.append(cand_jpg)

            if not processed_frames:
                log(f"  WARN: No processed frames found for {stem}.ico (skipping)\n")
                continue

            dst_ico = out_ico_dir / f"{stem}.ico"
            rebuild_ico_from_pngs(processed_frames, dst_ico)
            log(f"  OK: {dst_ico.name} ({len(processed_frames)} frame(s))\n")

    result.processed_files = sum(result.stage_stats.values())
    return result


def cancel_pipeline():
    global _cancel_event
    _cancel_event.set()


def is_cancelled() -> bool:
    return _cancel_event.is_set()