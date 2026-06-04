# External Tool Commands Reference

## ImageMagick (`magick`)

### Preprocess Stage
```bash
magick input.png \
  -background white -alpha remove -alpha off \
  -colorspace Gray \
  [-negate] \
  [-threshold N%] \
  [-median N] \
  [-blur 0xN] \
  [-auto-level] \
  [-contrast-stretch N%xN%] \
  png:output.png
```

### Trace Stage (PNG → PBM)
```bash
magick input.png \
  -background white -alpha remove -alpha off \
  -colorspace Gray \
  [-negate] \
  -threshold N% \
  pbm:output.pbm
```

## Potrace

### Trace Stage (PBM → SVG)
```bash
potrace input.pbm \
  -s \
  -o output.svg \
  --turdsize N \
  [--flat]
```
- `-s`: output SVG
- `--turdsize`: min speck size to keep
- `--flat`: (optional) reduce curve smoothing

## Inkscape

### Export Stage
```bash
inkscape input.svg \
  --export-type=png|svg|pdf|eps \
  --export-filename=output.png|svg|pdf|eps \
  --export-width=N \
  [--export-area-drawing]
```

## Dependency Requirements

| Stage | Tools Required | Notes |
|-------|---------------|-------|
| Preprocess | None (Pillow) or ImageMagick | Pillow fallback available |
| Pad | None (PIL) | Pure Python, no external tools |
| Trace | ImageMagick + potrace | PBM intermediate format required |
| Export | Inkscape | SVG/PDF/EPS output |