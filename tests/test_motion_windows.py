"""The recreated third-party windows in motion/ (lib/slack_ui.py, lib/linear_ui.py,
lib/github_pages.py, their content modules, reference/ and the demo), and the README and guides
that describe them, carry no names or text from a project that used them: every name a video
shows comes from the project's own scene.

The names are checked by SHA-256 digests of lowercase word tokens and token pairs, so the kit
holds no copy of them. A file is tokenised whole, so a pair split by a line break is found, and
each hit is reported at its line. render.py --demo is the visual check (guides/video.md, "Motion
graphics")."""

import hashlib
import itertools
import re
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
MOTION = KIT / "motion"
SKIP = {".venv", "out", "__pycache__"}
TEXT = (".py", ".md", ".sh", ".txt", ".toml", ".json")
# lowercase tokens and token pairs that name a product, company, person or record of one project
FORBIDDEN = frozenset({
    "2ff8ddd61f5e0a0c72ad9390b7c448e32b5055707f1be2e65a361b24f2a180ce",
    "84e2cdb7a166d1671bc5e2abc1e78b59777dd1f863d3c5b05d09c2dd088444c2",
    "0c95c7ece1ce1a9750275ef1c6d7ad6b278f70d66592207783ffe7d58474cc01",
    "9fd09dc33545f9cc19b81ebd0b98c4fd8c66ed1e34de89f4c9a81e6b26dc0d54",
    "a58f0473fb4c182db5a53fe978863b6eaa6552b5c694769ae3965d25bb11be76",
    "7fb35d4777487797615cfa7c57724a47ba99152485600ccdb98e3871a6d05b21",
    "3200fd68851394579ab07eab38217e30e8cbecf1a8027296f01bda78788f8e12",
    "1b162807be261ea4c990313fd752d31542a0fdede70a20538e246467dcd7f2b9",
    "11820fddaddfdf34b0b683fcca38c813b540095e546d0637c5e716d19ad6f83a",
    "22f166336865fe63d0aadddb22c6a81742189df9bd66cd8498a2786fd619276c",
    "87e4f20ef9ba6d6ff8cd1ae62c376d630ae5cd3784d15e7b3b2751b474d9c2af",
    "10788083e2956e7e59e0587224036b57dfd6e780ced1f9b8147472f5526e26f1",
    "88bfa1b7f844b8cb1fbc9087eb182e4a501154d255058499823afc468ce357b6",
    "3c41e7be861caa79d7a5dc7aedaa1d7736b4f8412b858ea85cd13eab89d86bbb",
    "728347f22c75c20bbce96235fde092d637ce2465e6dc79014a2f52b5233df333",
})
# a listed word the README and guides use in its everyday sense (Gemini billing); motion/ may not
DOC_OK = frozenset({"billing"})
# citations of one project's records: a row, a claim number, a dated or numbered review round
RECORDS = re.compile(r"scenarios\.md\W+rows?\s*\d|claims\.md\W+#\s*\d|NOTES\.md\W+(?:round|\d{4}-\d\d)", re.IGNORECASE)


def scanned_files() -> list[Path]:
    """Every text file under motion/, plus README.md and guides/*.md."""
    motion = (p for p in MOTION.rglob("*") if p.is_file() and p.suffix in TEXT
              and not SKIP & set(p.relative_to(MOTION).parts))
    return sorted([*motion, KIT / "README.md", *(KIT / "guides").glob("*.md")])


def hits(text: str, digests: frozenset[str] = FORBIDDEN) -> list[tuple[int, str]]:
    """(line, token or token pair) for each token and token pair of `text` whose digest is in
    `digests`; a pair is reported at its first token's line, whatever lies between the two."""
    tokens = [(m.group(), text.count("\n", 0, m.start()) + 1) for m in re.finditer(r"[a-z0-9]+", text.lower())]
    grams = [(line, tok) for tok, line in tokens]
    grams += [(l1, f"{t1} {t2}") for (t1, l1), (t2, _) in itertools.pairwise(tokens)]
    return sorted((line, g) for line, g in grams if hashlib.sha256(g.encode()).hexdigest() in digests)


def test_scanner_finds_a_listed_token_and_pair() -> None:
    listed = frozenset(hashlib.sha256(s.encode()).hexdigest() for s in ("acme", "jane doe"))
    assert hits("Posted by Jane  Doe for ACME-42.", listed) == [(1, "acme"), (1, "jane doe")]
    assert hits("Posted by Jane for the team.", listed) == []


def test_scanner_finds_a_pair_across_a_line_break() -> None:
    listed = frozenset(hashlib.sha256(s.encode()).hexdigest() for s in ("acme", "jane doe"))
    assert hits("intro\nPosted by Jane\n  Doe today.", listed) == [(2, "jane doe")]
    assert hits("Posted by Jane\n\nfor the team.", listed) == []


def test_scan_covers_the_windows_and_their_docs() -> None:
    names = {p.relative_to(KIT).as_posix() for p in scanned_files()}
    for need in ("motion/lib/slack_ui.py", "motion/lib/linear_ui.py", "motion/lib/github_pages.py", "motion/lib/demo.py",
                 "motion/reference/slack.md", "motion/reference/linear.md", "motion/reference/github.md",
                 "README.md", "guides/video.md"):
        assert need in names, f"{need} missing from the scan"


def test_kit_names_no_project() -> None:
    problems = []
    for path in scanned_files():
        text = path.read_text()
        ok = frozenset() if MOTION in path.parents else DOC_OK
        found = [(n, g) for n, g in hits(text) if g not in ok]
        found += [(text.count("\n", 0, m.start()) + 1, m.group()) for m in RECORDS.finditer(text)]
        problems += [f"{path.relative_to(KIT)}:{line}: {g}" for line, g in sorted(found)]
    assert not problems, "project-specific names in the kit:\n" + "\n".join(problems)
