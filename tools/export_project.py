"""Compress a project with its media and source, excluding restorable dependencies.

Kept: source, settings, lockfiles, brand assets, captures/, outputs/ and every workstream's
media. Omitted: environments, caches, downloaded samples, build folders, capture self-tests,
machine-specific font resolution, Git history and local credentials. ./inflate.sh restores them.
"""

import argparse
import fnmatch
import os
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OMIT_NAMES = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
              ".ruff_cache", ".mypy_cache", ".cache", ".aws", ".DS_Store", ".envrc", ".netrc", ".npmrc"}
OMIT_GLOBS = ("*.pem", "*.key", "credentials*")  # key and credential files, matched against every path part
# project-relative paths, one glob per part; everything under them is omitted too
OMIT_PATHS = {"music/samples", "music/build", "edit/build", "post/build", "captures/*-selftest",
              "brand/fonts/resolved.json", "brand/fonts/.local",
              ".claude/settings.local.json", ".claude/projects", ".claude/debug"}


def under(rel, pattern):
    """`rel` is the path `pattern` names, or lies under it."""
    n = len(Path(pattern).parts)
    return len(rel.parts) >= n and Path(*rel.parts[:n]).match(pattern)


def omitted(rel):
    return (any(p in OMIT_NAMES or p == ".env" or
                (p.startswith(".env.") and p not in (".env.example", ".env.template"))
                for p in rel.parts) or
            any(fnmatch.fnmatch(p, g) for p in rel.parts for g in OMIT_GLOBS) or rel.suffix in (".pyc", ".pyo") or
            any(under(rel, p) for p in OMIT_PATHS))


def entries(root):
    for folder, dirs, files in os.walk(root, followlinks=False):
        base = Path(folder)
        dirs[:] = sorted(d for d in dirs if not omitted((base / d).relative_to(root)))
        for name in sorted(files + dirs):
            path = base / name
            rel = path.relative_to(root)
            if omitted(rel):
                continue
            if path.is_symlink():
                target = path.resolve()
                if not target.is_relative_to(root) or omitted(target.relative_to(root)):
                    raise ValueError(f"{rel}: symlink points outside the exported project; "
                                     "copy the project asset into the project before exporting")
                if not target.exists():
                    raise ValueError(f"{rel}: broken symlink")
            elif not path.is_file() and not path.is_dir():
                raise ValueError(f"{rel}: unsupported special file")
            yield path, rel


def _publish(temporary, output):
    """Move the finished archive to `output` without overwriting one created concurrently."""
    umask = os.umask(0)
    os.umask(umask)
    os.chmod(temporary, 0o666 & ~umask)  # mkstemp creates 0600; a shared archive follows the umask
    try:
        os.link(temporary, output)
    except OSError:  # no hard links on this filesystem: check, then replace (a narrow race remains)
        if output.exists():
            raise ValueError(f"{output} already exists; choose a new output path") from None
        os.replace(temporary, output)


def export(root, output):
    root, output = root.resolve(), output.absolute()
    if not root.is_dir() or not (root / "setup.sh").is_file():
        raise ValueError("project directory must contain setup.sh")
    if output.resolve().is_relative_to(root):
        raise ValueError("write the archive outside the project directory")
    if output.exists():
        raise ValueError(f"{output} already exists; choose a new output path")
    required = ("inflate.sh", "system-deps.sh", "configure.sh", "tools/project_settings.py",
                "tools/setup-samples.sh")
    if any(not (root / p).is_file() for p in required):
        raise ValueError("update this project with the current kit before exporting")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".export-", dir=output.parent)
    os.close(fd)
    try:
        with tarfile.open(temporary, "w:gz", compresslevel=9) as archive:
            for path, rel in entries(root):
                def portable_link(info):
                    if info.issym():
                        info.linkname = os.path.relpath(path.resolve(), path.parent)
                    return info
                archive.add(path, arcname=str(Path(root.name) / rel), recursive=False,
                            filter=portable_link)
        _publish(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", nargs="?", type=Path, default=ROOT)
    ap.add_argument("--output", type=Path, help="archive path outside the project (default: sibling .tar.gz)")
    args = ap.parse_args()
    root = args.project.resolve()
    output = args.output or root.with_name(root.name + ".tar.gz")
    try:
        print(export(root, output))
    except (OSError, ValueError, tarfile.TarError) as exc:
        ap.exit(1, f"export failed: {exc}\n")


if __name__ == "__main__":
    main()
