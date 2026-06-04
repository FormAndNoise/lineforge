import os
import re

md_path = r"c:\Users\aguy\lineforge\cleanroomcode.md"
with open(md_path, "r", encoding="utf-8") as f:
    text = f.read()

# Pattern matches code blocks that start with a FILE: comment
pattern = re.compile(r'```rust\n// ============================================================\n// FILE: ([^\n]+)\n// ============================================================\n(.*?)\n```', re.DOTALL)

engine_dir = r"c:\Users\aguy\lineforge\lineforge_engine"
os.makedirs(os.path.join(engine_dir, "src"), exist_ok=True)

for match in pattern.finditer(text):
    filename = match.group(1).strip()
    if "(CLI binary)" in filename:
        filename = filename.replace("(CLI binary)", "").strip()
    code = match.group(2)
    filepath = os.path.join(engine_dir, filename)
    print(f"Writing {filepath}...")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)

cargo_toml = """[package]
name = "lineforge_engine"
version = "0.1.0"
edition = "2021"

[dependencies]
"""
with open(os.path.join(engine_dir, "Cargo.toml"), "w", encoding="utf-8") as f:
    f.write(cargo_toml)

print("Done extraction.")
