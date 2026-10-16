"""File helpers every capture output shares: atomic writes and PNG dimensions."""

from __future__ import annotations

from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def temp_path(path: Path) -> Path:
    """Where `path` is written before it is renamed into place: `name.tmp.ext`."""
    return path.with_name(f"{path.stem}.tmp{path.suffix}")


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = temp_path(path)
    partial.write_bytes(data)
    partial.replace(path)


def png_size(header: bytes) -> tuple[int, int]:
    """(width, height) from the first 24 bytes of a PNG file."""
    if header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise ValueError("not a PNG file")
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def png_file_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        return png_size(file.read(24))
