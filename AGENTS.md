# AGENTS.md — Pantograph

Modular batch image processing and vectorization pipeline using a native Rust engine (`vpipe-cli` / `vpipe`) and Python UI.

## Brand Identity & Standards
- **Product Name**: **Pantograph** (Repo: `pantograph`, Engine: `vpipe`)
- **Accent**: House Rust (`#D45500` / Dark: `#F07A2B`)
- **Job Line**: *"Raster in, clean vectors out. Batch line tracing with zero external dependencies."*
- **Symbol**: 24×24u, 1.75u stroke, mechanical parallelogram drafting linkage with 1 solid pivot pip.
- **Suite Context**: Form & Noise Atelier Loose Endorsed Family. Space Grotesk (Wordmarks), Inter (UI), IBM Plex Mono (CLI/Code).

## Core Architecture
- **Preprocessing**: Python Pillow for contrast, auto-level, median filter, threshold.
- **Engine (`vpipe-cli`)**: Compiled Rust engine for native tracing directly to SVG, PDF, or EPS.
- **No External Dependencies**: Zero reliance on ImageMagick, Potrace, or Inkscape binaries.

## Build & Test Commands
```powershell
.\build_release.ps1       # Compile Rust engine and package single-file EXE
cd lineforge_engine && cargo test # Test Rust engine
python main.py             # Run Python UI
```
