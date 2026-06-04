import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, List

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".ico"}


def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def run_cmd(args: List[str]) -> None:
    """
    Run a subprocess command silently (no flashing console windows on Windows).
    Raises RuntimeError if the command fails.
    """
    run_cmd_out(args)


def run_cmd_out(args: List[str]) -> str:
    """
    Run a subprocess command silently and return its stdout as a string.
    Raises RuntimeError if the command fails.
    """
    return run_cmd_out_bytes(args).decode("utf-8", errors="replace")


def run_cmd_out_bytes(args: List[str]) -> bytes:
    """
    Run a subprocess command silently and return its stdout as bytes.
    Raises RuntimeError if the command fails.
    """
    creationflags = 0
    startupinfo = None

    if sys.platform.startswith("win"):
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    p = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
        startupinfo=startupinfo,
    )

    if p.returncode != 0:
        err = p.stderr.decode("utf-8", errors="replace") if p.stderr else p.stdout.decode("utf-8", errors="replace")
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(args)
            + "\n"
            + err
        )
        
    return p.stdout


def list_images(path: Path, recursive: bool = False) -> list[Path]:
    """
    Return supported image files for a file OR directory.
    """
    path = Path(path)

    if path.is_file():
        return [path] if path.suffix.lower() in IMG_EXTS else []

    if not path.exists() or not path.is_dir():
        return []

    if recursive:
        return sorted(
            p for p in path.rglob("*")
            if p.is_file() and p.suffix.lower() in IMG_EXTS
        )

    return sorted(
        p for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in IMG_EXTS
    )
