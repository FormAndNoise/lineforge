# LineForge

LineForge is a Windows‑only batch image processing pipeline that now uses a **native Rust engine** (`vpipe-cli`) for all heavy‑lifting. No external binaries such as ImageMagick, Potrace, or Inkscape are required.

## Building the project

```powershell
git clone https://github.com/aarik/lineforge.git
cd lineforge
# The Rust engine is built automatically as part of the Python install step,
# or you can build it manually:
#   cargo build --release
```

The compiled executable appears as `bin\vpipe-cli.exe` and is discovered automatically by the UI.

---

LineForge is a modular batch image processing pipeline for preparing raster artwork for vectorisation, icon refinement, and dataset clean‑up. It provides:

- **Image preprocessing** – performed with Python Pillow (no external tools).
- **Square padding / resizing**.
- **Raster → Vector tracing** – performed by the Rust `vpipe-cli` engine, outputting SVG, PDF, or EPS.
- **ICO round‑trip support** – extract, process, and rebuild ICOs using Pillow only.

---

## Supported Input

Formats:
- PNG
- JPG / JPEG
- WEBP
- BMP
- TIFF
- ICO (optional handling)

Input sources:
- Single file
- Folder
- Folder (recursive)

The UI displays:
```
Found: X inputs
```
If zero files are found, enable recursive mode when selecting a parent folder.

---

## Pipeline Stages

Each stage can be enabled or disabled independently.

### A) Preprocess
Uses **Pillow** for:
- Grayscale
- Auto‑level
- Contrast stretch
- Median filter
- Blur
- Negate
- Threshold (slider)

Outputs to `output/01_preprocessed`

---

### B) Pad
- Square resize
- Background: white / black / transparent
- Output format: PNG or JPG
- JPEG quality control

Outputs to `output/02_padded`

---

### C) Trace → Vector
Uses the **Rust engine (`vpipe-cli`)** to produce vector formats directly.
Options:
- Threshold cutoff
- Invert before threshold
- Turdsize
- Smooth toggle (default smooth, `--flat` disables)
- Output format: `svg`, `pdf`, or `eps`

Outputs to `output/03_vector`

---

### D) Export → Raster (optional)
If you need a raster export of the vector output, the Rust engine can also render PNGs directly. Select the desired export format in the UI.

---

## ICO Processing (Optional)
When enabled:
1. `.ico` files are extracted into PNG frames.
2. Frames are processed through the selected stages.
3. Processed frames are rebuilt into a new `.ico`.

Final icons land in `output/05_ico` and temporary extracted frames can be found in `output/_ico_frames`.

---

## Output Structure

```
output/
├── 01_preprocessed/
├── 02_padded/
├── 03_vector/          (SVG/PDF/EPS)
├── 04_export_png/      (optional PNG export)
├── 05_ico/            (if enabled)
└── _ico_frames/       (temporary)
```

---

## Dependencies

The only external requirement is the **Rust engine** bundled as `vpipe-cli.exe` (automatically built or provided in releases). All other processing is performed with the standard Python library and Pillow.

---

## Logs

Each run creates a timestamped log file in:

```
logs/
```

The UI provides shortcuts to:
- Open output folder
- Open last log
- Clear log
