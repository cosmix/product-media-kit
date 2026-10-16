"""Contract tests for the tuicap blog-capture surface."""

from __future__ import annotations

from tuicap.render import CELL_H, CELL_W, PAD, Geometry, Recording


def _png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def test_render_still_renders_state_at_time(tmp_path):
    from tuicap.render import render_still

    rec = Recording(
        cols=40,
        rows=10,
        events=[(0.0, b"first"), (2.0, b"\x1b[2J\x1b[Hsecond")],
        duration=3.0,
        inputs=[],
    )
    stills = {}
    for name, t in (("early", 1.0), ("early-again", 1.5), ("late", 2.5)):
        png = tmp_path / f"{name}.png"
        size = render_still(rec, png, t)
        assert tuple(size) == Geometry(40, 10).size
        data = png.read_bytes()
        assert _png_size(data) == Geometry(40, 10).size
        stills[name] = data

    assert stills["early"] == stills["early-again"]
    assert stills["early"] != stills["late"]
    assert not list(tmp_path.glob("*.tmp*"))


def test_cell_box_includes_padding():
    from tuicap.render import cell_box

    box = cell_box(Geometry(80, 24), 1, 2, 3, 10)
    assert box == [PAD + 2 * CELL_W, PAD + 1 * CELL_H, 8 * CELL_W, 2 * CELL_H]
    assert all(type(v) is int for v in box)
