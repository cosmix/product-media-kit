"""Credits for the video description, from the same data as the on-screen credits.

Usage: uv run credits.py [--final] [--revision vN]
  -> outputs/<stage>-<slug>-v<N>-credits.txt, stage draft unless --final, N the latest mp4 of that
  stage unless --revision
"""

import argparse

from editkit import credit_data as cd
from editkit.assets import ROOT
from editkit.outputs import output_path, read_slug, revision_arg
from editkit.project import edl

OUTPUTS = ROOT / "outputs"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true", help="write the final-stage file (default draft)")
    ap.add_argument("--revision", type=revision_arg, metavar="vN", help="attach to this revision instead of the latest mp4")
    a = ap.parse_args()
    lines = [cd.title(), ""] if cd.title() else []
    if broll := cd.broll(list(getattr(edl(), "BROLL_CLIPS", []))):
        lines += ["B-roll (Creative Commons Attribution):"]
        lines += [f"- \"{c.title}\", {c.by}, {c.url} ({c.licence})" for c in broll] + [""]
    if samples := cd.music_samples():
        lines += ["Music: original score, with samples from"]
        lines += [f"- {c.title}, {c.by} ({c.licence}) {c.url}".rstrip() for c in samples]
    lines += [f"{label}: {text}" for label, text in cd.extra_rows()]
    out = output_path(OUTPUTS, read_slug(ROOT), "final" if a.final else "draft", "txt",
                      primary_ext="mp4", suffix="credits", revision=a.revision)
    out.write_text("\n".join(lines) + "\n")
    if lines:
        print(f"wrote {out}")
    else:
        print(f"nothing to credit (no music, b-roll or credits.json rows): wrote an empty {out}")


if __name__ == "__main__":
    main()
