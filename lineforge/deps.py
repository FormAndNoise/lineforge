import sys
from pathlib import Path
from .utils import which


def resource_path(rel: str) -> Path:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / rel
    return Path(__file__).resolve().parent.parent / rel


def find_vpipe() -> str | None:
    bundled = resource_path("bin/vpipe-cli.exe")
    if bundled.exists():
        return str(bundled)
    return which("vpipe-cli") or which("vpipe-cli.exe")


def find_all_deps() -> dict:
    return {
        "vpipe-cli": find_vpipe(),
    }
