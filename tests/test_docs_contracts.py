"""Contract tests for the guides: every command, flag, module, link and section they name resolves
in the kit, the pinned README section map holds, and no stale name survives."""

import ast
import re
from functools import cache
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "HUMAN.md",
    "claude-project.md",
    "guides/capture.md",
    "guides/blog.md",
    "guides/video.md",
    "claude-skills/begin/SKILL.md",
    ".claude/skills/install/SKILL.md",
)
MODULE_ROOTS = tuple(KIT / p for p in ("fixtures/web", "fixtures/tui/src", "post/src", "edit", "motion", "music"))
SCRIPT_DIRS = tuple(KIT / p for p in ("", "edit", "motion", "music", "narration", "post", "fixtures/web", "fixtures/tui"))
SHELL_SCRIPTS = ("setup.sh", "install.sh", "system-deps.sh", "inflate.sh")
WRAPPERS = {"configure.sh": "tools/project_settings.py", "export.sh": "tools/export_project.py"}  # exec argparse
PACKAGES = ("webcap", "tuicap", "postkit", "editkit")
STALE = re.compile(
    r"product-video-[k]it|product-blog-[k]it|Product (Video|Blog) [K]it|edit/out/[i]ntro|post\.[j]son|[o]pen_scene"
    r"|key_marks|STILL_T|\.postkit\.json"
)
README_MAP = {
    "What you make": ["The stack"],
    "How the kit is used": [],
    "For the human": [],
    "Requirements": [],
    "Setup": ["Install into a project", "System packages", "Self-tests", "Running on macOS", "Sharing a project"],
    "The team": ["Rules that make the team work", "Good briefs"],
    "Kickoff": [],
    "Reuse between media": [],
    "Pipeline and folder map": [],
    "Engine and project files": [],
    "Code that needs your product": [],
    "Outputs": [],
    "Brand": ["`BRAND.md` and `brand/`", "The brand skill", "The checker"],
    "Design system": ["`design.json`", "Fonts by family", "Who reads what", "Legibility"],
    "Editorial rules": [],
    "Project records": [
        "`NOTES.md`: the decision log",
        "`HANDBOOK.md`: the project's own handbook",
        "Rejected styles",
        "`claims.md` and `scenarios.md`",
    ],
    "Mistakes and pitfalls": [],
    "Licences and credits": [],
}
FENCE = re.compile(r"^ *```(?:bash|sh)\s*\n(.*?)^ *```", re.MULTILINE | re.DOTALL)
ANY_FENCE = re.compile(r"^ *```.*?^ *```[ \t]*$", re.MULTILINE | re.DOTALL)
INLINE = re.compile(r"`([^`\n]+)`")
UV_RUN = re.compile(r"^uv run(?: --\S+)* (?P<rest>.*)$")
FLAG = re.compile(r"(?<![^\s\[(|])(--?[A-Za-z][\w-]*)")
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)\)")
SECTION_REF = re.compile(
    r"`?(?P<file>README(?:\.md)?|guides/\w+\.md)`?(?:\]\([^)\s]*\))?,? "
    r"\(?(?P<names>\\?\"[^\"\\\n]+\\?\"(?:,? (?:and |or )?\\?\"[^\"\\\n]+\\?\")*)"
)


def guides() -> list[Path]:
    paths = {KIT / p for p in REQUIRED} | set((KIT / "guides").glob("*.md"))
    return sorted(p for p in paths if p.is_file())


def prose(text: str) -> str:
    """The text with every fenced code block removed."""
    return ANY_FENCE.sub("", text)


def commands(text: str) -> list[str]:
    """Simple commands in fenced bash blocks (continuations joined, comments dropped) and inline
    code spans that start a command."""
    found = []
    for block in FENCE.findall(text):
        for line in block.replace("\\\n", " ").splitlines():
            line = line.split(" #", 1)[0].strip().removeprefix("$ ")
            found += [" ".join(part.split()) for part in re.split(r"&&|\|\||;|\||\(|\)", line)]
    for span in INLINE.findall(prose(text)):
        if span.startswith(("uv run ", "./")):
            found.append(" ".join(span.split()))
    return [c for c in found if c]


@cache
def argparse_names(path: Path) -> tuple[frozenset[str], frozenset[str]]:
    """(option strings, sub-command names) an argparse script defines; ({}, {}) without argparse."""
    flags, subs = set(), set()
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = getattr(node.func, "attr", None)
        consts = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if name == "add_argument":
            flags |= {c for c in consts if c.startswith("-")}
        elif name == "add_parser" and consts:
            subs.add(consts[0])
    if flags:
        flags |= {"--help", "-h"}
    return frozenset(flags), frozenset(subs)


def module_file(module: str) -> Path | None:
    rel = Path(*module.split("."))
    for root in MODULE_ROOTS:
        for candidate in (root / rel.with_suffix(".py"), root / rel / "__init__.py", root / rel / "__main__.py"):
            if candidate.is_file():
                return candidate
    return None


def flag_problems(command: str, args: str, files: list[Path]) -> list[str]:
    known = set().union(*(argparse_names(f)[0] for f in files))
    if not known:
        return []
    return [f"no flag {flag}: {command}" for flag in sorted(set(FLAG.findall(args)) - known)]


def script_files(path: str) -> list[Path]:
    rel = path.replace(".claude/skills/", "claude-skills/").lstrip("./")
    return [d / rel for d in SCRIPT_DIRS if (d / rel).is_file()]


def uv_problems(command: str, rest: str) -> list[str]:
    words = rest.split(maxsplit=1) + [""]
    head, args = words[0], words[1]
    if head == "python" and args.startswith("-m "):
        module, _, args = args[3:].partition(" ")
        path = module_file(module)
        return flag_problems(command, args, [path]) if path else [f"no module {module}: {command}"]
    if head == "python":
        head, _, args = args.partition(" ")
        if not head.endswith(".py"):
            return []
    if head == "postkit":
        cli = KIT / "post/src/postkit/cli.py"
        sub = args.split(maxsplit=1)[0] if args.split() else ""
        if sub not in argparse_names(cli)[1]:
            return [f"postkit has no sub-command {sub!r}: {command}"]
        return flag_problems(command, args, [cli])
    if head == "tuicap":
        return flag_problems(command, args, [KIT / "fixtures/tui/src/tuicap/clips.py"])
    if head.endswith(".py") and not set("<$") & set(head):
        files = script_files(head)
        return flag_problems(command, args, files) if files else [f"no script {head}: {command}"]
    return []


def shell_problems(command: str) -> list[str]:
    script, _, args = command.partition(" ")
    name = script.removeprefix("./")
    if name in WRAPPERS:
        return flag_problems(command, args, [KIT / WRAPPERS[name]])
    if name not in SHELL_SCRIPTS:
        return []
    text = (KIT / name).read_text()
    flags = set(FLAG.findall(args)) - {"--help", "-h"}
    return [f"{name} has no flag {f}: {command}" for f in sorted(flags)
            if not re.search(rf"(?<![\w-]){re.escape(f)}(?![\w-])", text)]


def command_problems(command: str) -> list[str]:
    match = UV_RUN.match(command)
    if match:
        return uv_problems(command, match["rest"])
    return shell_problems(command) if command.startswith("./") else []


def slug(heading: str) -> str:
    """GitHub's anchor for a heading."""
    text = heading.strip().lower().replace("`", "")
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def headings(path: Path) -> list[tuple[int, str]]:
    return [(len(m[1]), m[2].strip()) for m in re.finditer(r"^(#{1,6}) +(.+)$", prose(path.read_text()), re.MULTILINE)]


def anchors(path: Path) -> set[str]:
    seen: dict[str, int] = {}
    out = set()
    for _, text in headings(path):
        base = slug(text)
        n = seen.get(base, 0)
        out.add(base if n == 0 else f"{base}-{n}")
        seen[base] = n + 1
    return out


def heading_matches(ref: str, path: Path) -> bool:
    want = ref.replace("`", "").strip().lower()
    for _, text in headings(path):
        have = text.replace("`", "").strip().lower()
        if have == want or have.startswith(want + ":"):
            return True
    return False


def rel(path: Path) -> str:
    return str(path.relative_to(KIT))


@pytest.mark.parametrize("name", REQUIRED)
def test_guide_exists(name: str) -> None:
    assert (KIT / name).is_file(), f"{name} missing"


def test_kit_root_has_no_claude_md() -> None:
    assert not (KIT / "CLAUDE.md").exists(), "the kit root's CLAUDE.md is gone: claude-project.md is installed as CLAUDE.md"
    assert (KIT / "doc/mac_port_testing.md").is_file()
    assert not (KIT / "mac_port_testing.md").exists()


def test_commands_resolve() -> None:
    problems, checked = [], 0
    for path in guides():
        for command in commands(path.read_text()):
            checked += bool(UV_RUN.match(command) or command.startswith("./"))
            problems += [f"{rel(path)}: {p}" for p in command_problems(command)]
    assert checked > 20, f"only {checked} commands found in the guides"
    assert not problems, "\n".join(problems)


def test_dotted_names_resolve() -> None:
    problems = []
    pattern = re.compile(rf"`((?:{'|'.join(PACKAGES)})(?:\.[A-Za-z_]\w*)+)")
    for path in guides():
        for name in sorted(set(pattern.findall(path.read_text()))):
            problem = dotted_problem(name)
            if problem:
                problems.append(f"{rel(path)}: {problem}")
    assert not problems, "\n".join(problems)


def dotted_problem(name: str) -> str | None:
    parts = name.split(".")
    for i in range(len(parts), 0, -1):
        path = module_file(".".join(parts[:i]))
        if path is not None:
            return member_problem(name, path, parts[i:])
    return f"no module for {name}"


def member_problem(name: str, path: Path, rest: list[str]) -> str | None:
    if not rest:
        return None
    body = ast.parse(path.read_text()).body
    node = next((n for n in body if rest[0] in defined_names(n)), None)
    if node is None:
        return f"{name}: {rel(path)} defines no {rest[0]}"
    is_class = len(rest) > 1 and isinstance(node, ast.ClassDef)
    if is_class and not any(rest[1] in defined_names(n) for n in node.body):
        return f"{name}: class {rest[0]} has no {rest[1]}"
    return None


def defined_names(node: ast.stmt) -> set[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    if isinstance(node, ast.Assign):
        return {t.id for t in node.targets if isinstance(t, ast.Name)}
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return {node.target.id}
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return {(a.asname or a.name).split(".")[0] for a in node.names}
    return set()


def test_links_resolve() -> None:
    problems = []
    for path in guides():
        for target in LINK.findall(prose(path.read_text())):
            if re.match(r"[a-z]+:", target):
                continue
            file_part, _, anchor = target.partition("#")
            dest = (path.parent / file_part).resolve() if file_part else path
            if not dest.exists():
                problems.append(f"{rel(path)}: link to missing {target}")
            elif anchor and dest.suffix == ".md" and anchor not in anchors(dest):
                problems.append(f"{rel(path)}: no heading for #{anchor} in {rel(dest)}")
    assert not problems, "\n".join(problems)


def test_section_references_resolve() -> None:
    """`README "X"` and `guides/<g>.md, "X"` name a heading of that file (skipped while the file is absent)."""
    problems = []
    for path in guides():
        for m in SECTION_REF.finditer(path.read_text()):
            target = KIT / ("README.md" if m["file"].startswith("README") else m["file"])
            if not target.is_file():
                continue
            for name in re.findall(r"\"([^\"\\]+)\\?\"", m["names"]):
                if not heading_matches(name, target):
                    problems.append(f"{rel(path)}: {rel(target)} has no section \"{name}\"")
    assert not problems, "\n".join(problems)


def test_code_section_references_resolve() -> None:
    """Every `(README.md, "X")` or `(guides/<g>.md, "X")` citation in the kit's code names a real heading."""
    problems, checked = [], 0
    for path in sorted(p for pattern in ("*.py", "*.sh") for p in KIT.rglob(pattern)
                       if not {".venv", "node_modules", ".git", "tests"} & set(p.relative_to(KIT).parts)):
        for m in SECTION_REF.finditer(path.read_text()):
            target = KIT / ("README.md" if m["file"].startswith("README") else m["file"])
            for name in re.findall(r"\\?\"([^\"\\]+)\\?\"", m["names"]):
                checked += 1
                if not target.is_file() or not heading_matches(name, target):
                    problems.append(f"{rel(path)}: {rel(target)} has no section \"{name}\"")
    assert checked > 20, f"only {checked} citations found in the code"
    assert not problems, "\n".join(problems)


def test_readme_section_map() -> None:
    found = headings(KIT / "README.md")
    h2 = [text for level, text in found if level == 2 and text != "Contents"]
    assert h2 == list(README_MAP), f"README H2 headings {h2} differ from the pinned map"
    current, h3 = None, {}
    for level, text in found:
        if level == 2:
            current = text
        elif level == 3 and current in README_MAP:
            h3.setdefault(current, []).append(text)
    for section, subs in README_MAP.items():
        assert h3.get(section, []) == subs, f"README \"{section}\" subsections {h3.get(section)} != {subs}"


@pytest.mark.parametrize(("name", "sections"), [
    ("guides/capture.md", ["Web capture", "TUI capture", "Manifests", "Profiles"]),
    ("guides/blog.md", ["Roles", "The post", "`draft.md` and `shot:` references",
                        "`images.json`: image treatment", "Building and checking", "`postkit add`",
                        "Review and QA", "Blog editorial rules", "Blog mistakes"]),
])
def test_guide_sections(name: str, sections: list[str]) -> None:
    have = [text for _, text in headings(KIT / name)]
    missing = [s for s in sections if s not in have]
    assert not missing, f"{name} lacks {missing}"


def test_no_stale_names() -> None:
    problems = [
        f"{rel(path)}:{n}: {line.strip()}"
        for path in guides()
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if STALE.search(line)
    ]
    assert not problems, "\n".join(problems)


def test_fences_name_a_language() -> None:
    problems = []
    for path in guides():
        inside = False
        for n, line in enumerate(path.read_text().splitlines(), 1):
            fence = line.lstrip()
            if not fence.startswith("```"):
                continue
            if not inside and fence == "```":
                problems.append(f"{rel(path)}:{n}: fence without a language")
            inside = not inside
    assert not problems, "\n".join(problems)


def check_skill_frontmatter(path: str, name: str, triggers: tuple[str, ...]) -> None:
    front = (KIT / path).read_text().split("---", 2)[1]
    assert re.search(rf"^name: {name}$", front, re.MULTILINE), front
    description = re.search(r"^description: (.+)$", front, re.MULTILINE)
    assert description, front
    for trigger in triggers:
        assert trigger in description[1], f"description lacks {trigger!r}"


def test_begin_skill_frontmatter() -> None:
    check_skill_frontmatter(
        "claude-skills/begin/SKILL.md", "begin", ("/begin", "let's make a video", "write a blog post", "start the project")
    )


def test_install_skill_frontmatter() -> None:
    check_skill_frontmatter(
        ".claude/skills/install/SKILL.md", "install", ("/install", "install the kit", "set up a project", "new project")
    )
