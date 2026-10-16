"""Shared fixtures for the webcap tests."""

from __future__ import annotations

import struct
import zlib

import pytest


def _png(width: int, height: int) -> bytes:
    """A valid black RGB PNG of the given size."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    rows = b"".join(b"\x00" + b"\x00" * width * 3 for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(rows))
            + chunk(b"IEND", b""))


@pytest.fixture
def png():
    """png(width, height) -> the bytes of a PNG that size."""
    return _png
