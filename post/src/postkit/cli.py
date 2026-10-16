"""postkit build | check | add | selftest [--root DIR]."""

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from postkit import selftest
from postkit.add import AddError, add
from postkit.assemble import BuildError, build
from postkit.check import check, report

DEFAULT_ROOT = Path(__file__).resolve().parents[3]  # post/src/postkit/cli.py -> the project root
REVISION_RE = re.compile(r"v([1-9]\d*)")


def _revision(text: str) -> int:
    m = REVISION_RE.fullmatch(text)
    if not m:
        raise argparse.ArgumentTypeError(f"{text!r}: expected vN, for example v2")
    return int(m[1])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="postkit", description="Assemble a blog post from the captures.")
    sub = parser.add_subparsers(dest="command", required=True, metavar="{build,check,add,selftest}")
    root = argparse.ArgumentParser(add_help=False)
    root.add_argument("--root", type=Path, default=DEFAULT_ROOT, help=f"the project root (default: {DEFAULT_ROOT})")
    text = "write outputs/blog/<stage>-<slug>-v<N>.md and outputs/blog/images/ from post/draft.md and the captures"
    cmd = sub.add_parser("build", parents=[root], help=text, description=text)
    cmd.add_argument("--final", action="store_true", help="write a final-<slug>-v<N>.md (default: draft)")
    which = cmd.add_mutually_exclusive_group()
    which.add_argument("--next", action="store_true", help="write the revision after the latest of the stage")
    which.add_argument("--revision", type=_revision, metavar="vN", help="write this revision")
    text = "check the built posts: links, alt text, image sizes"
    cmd = sub.add_parser("check", parents=[root], help=text, description=text)
    cmd.add_argument("--file", type=Path, help="check this post (default: the latest draft and the latest final)")
    text = "add a PNG, a video frame or a video segment to captures/<source>/ (motion, broll, video)"
    cmd = sub.add_parser("add", parents=[root], help=text, description=text)
    cmd.add_argument("ref", help="<source>/<scenario>/<label>")
    cmd.add_argument("file", type=Path, help="a PNG, or a video with --at or --from/--to")
    cmd.add_argument("--at", type=float, metavar="T", help="grab the frame at T seconds")
    cmd.add_argument("--from", dest="start", type=float, metavar="T", help="segment start, seconds")
    cmd.add_argument("--to", dest="end", type=float, metavar="T", help="segment end, seconds")
    sub.add_parser("selftest", help="build and check a made-up project in a temporary folder")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "build":
        return _build(args)
    if args.command == "check":
        return 1 if report(check(args.root, args.file)) else 0
    if args.command == "add":
        return _add(args)
    return selftest.run()


def _build(args: argparse.Namespace) -> int:
    try:
        result = build(args.root, final=args.final, revision=args.revision, next_rev=args.next)
    except BuildError as e:
        print(f"postkit build: cannot build the post:\n{e}", file=sys.stderr)
        return 1
    for path in result.written:
        print(path)
    for path in result.removed:
        print(f"removed {path}")
    return 0


def _add(args: argparse.Namespace) -> int:
    try:
        written = add(args.root, args.ref, args.file, at=args.at, start=args.start, end=args.end)
    except AddError as e:
        print(f"postkit add: {e}", file=sys.stderr)
        return 1
    for path in written:
        print(path)
    return 0
