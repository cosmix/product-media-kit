"""export-broll: layout, sidecars, INDEX/CATALOG, library merge, idempotence, conflicts, refusals."""

import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest
from tools.export_broll import export

KIT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                reason="ffmpeg and ffprobe are needed")

CREDIT = ("## 02_street\n\n- Title: Street at dusk\n- Channel: A Filmer\n- URL: https://example.test/v\n"
          "- Licence: Creative Commons Attribution (CC BY)\n- Range used: 0:05-0:09\n")


def make_clip(path: Path, rate: int = 10, seconds: int = 3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc=size=160x90:rate={rate}:duration={seconds}", "-pix_fmt", "yuv420p", str(path)],
                   check=True)


def make_project(root: Path, slug: str = "acme") -> Path:
    root.mkdir(parents=True)
    (root / "project.json").write_text(json.dumps({"slug": slug}))
    omni = root / "broll/gen/omni"
    make_clip(omni / "harbor.mp4")
    (omni / "harbor.json").write_text(json.dumps({"model": "omni", "prompt": "A harbor.\nNo people.",
                                                  "mode": "text"}))
    (omni / "unrendered.json").write_text("{}")  # metadata without a clip
    make_clip(omni / ".other.tmp.mp4")  # an unfinished render
    make_clip(root / "broll/candidates/02_street.mp4")
    make_clip(root / "broll/candidates/01_harbor.mp4")  # normalised copy of a generated clip: no credit
    (root / "broll/CREDITS.md").write_text("# Credits\n\n" + CREDIT)
    return root


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return make_project(tmp_path / "proj")


def test_layout_sidecars_index_and_catalog(project: Path, tmp_path: Path) -> None:
    dest = tmp_path / "lib"

    ids = export(project, dest)

    assert ids == ["02_street", "harbor"]
    folder = dest / "acme"
    assert sorted(p.name for p in folder.iterdir()) == [
        "02_street-contact.png", "02_street.json", "02_street.mp4",
        "INDEX.md", "harbor-contact.png", "harbor.json", "harbor.mp4"]
    assert (folder / "harbor.mp4").read_bytes() == (project / "broll/gen/omni/harbor.mp4").read_bytes()
    assert (folder / "harbor-contact.png").read_bytes()[:4] == b"\x89PNG"
    gen = json.loads((folder / "harbor.json").read_text())
    assert (gen["project"], gen["kind"], gen["model"], gen["mode"]) == ("acme", "generated", "omni", "text")
    assert (gen["width"], gen["height"], gen["fps"], gen["duration"]) == (160, 90, 10.0, 3.0)
    assert len(gen["sha256"]) == 64 and gen["exported_at"].endswith("Z")
    stock = json.loads((folder / "02_street.json").read_text())
    assert stock["kind"] == "stock" and stock["credit"]["Channel"] == "A Filmer"
    index = (folder / "INDEX.md").read_text()
    assert "![harbor contact sheet](harbor-contact.png)" in index
    assert "> A harbor.\n> No people." in index
    assert "Generated, no attribution needed" in index
    assert "Title: Street at dusk" in index and "URL: https://example.test/v" in index
    catalog = json.loads((dest / "catalog.json").read_text())
    assert [e["id"] for e in catalog["projects"]["acme"]] == ["02_street", "harbor"]
    assert "acme/harbor.mp4" in (dest / "CATALOG.md").read_text()


def test_the_contact_sheet_tiles_four_by_three(project: Path, tmp_path: Path) -> None:
    export(project, tmp_path / "lib", only=["harbor"])

    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                            str(tmp_path / "lib/acme/harbor-contact.png")], check=False, capture_output=True, text=True)
    width, height = map(int, probe.stdout.strip().split(","))
    assert width == 4 * 480 + 5 * 4 and height > 3 * 200  # 4 columns of 480 px frames, 3 rows of 16:9


def test_rerun_is_idempotent(project: Path, tmp_path: Path) -> None:
    dest = tmp_path / "lib"
    export(project, dest)
    files = [p for p in (dest / "acme").iterdir()]
    before = {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in files}
    catalog = (dest / "catalog.json").read_text()

    export(project, dest)

    assert {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in (dest / "acme").iterdir()
            if p.name != "INDEX.md"} == {k: v for k, v in before.items() if k != "INDEX.md"}
    assert (dest / "catalog.json").read_text() == catalog


def test_second_project_merges_into_the_catalog(project: Path, tmp_path: Path) -> None:
    dest = tmp_path / "lib"
    export(project, dest)
    other = make_project(tmp_path / "other", slug="beta")

    export(other, dest)
    export(project, dest, only=["harbor"])  # a narrowed re-export keeps its other clips and the other project

    catalog = json.loads((dest / "catalog.json").read_text())["projects"]
    assert sorted(catalog) == ["acme", "beta"]
    assert [e["id"] for e in catalog["acme"]] == ["02_street", "harbor"]
    assert "## beta" in (dest / "CATALOG.md").read_text() and "## acme" in (dest / "CATALOG.md").read_text()


def test_sha_conflict_is_reported_without_force_and_replaced_with_it(project: Path, tmp_path: Path) -> None:
    dest = tmp_path / "lib"
    export(project, dest)
    make_clip(project / "broll/gen/omni/harbor.mp4", rate=12)
    exported = (dest / "acme/harbor.mp4").read_bytes()

    with pytest.raises(SystemExit) as caught:
        export(project, dest)
    assert "harbor" in str(caught.value) and "--force" in str(caught.value)
    assert (dest / "acme/harbor.mp4").read_bytes() == exported

    export(project, dest, force=True)
    assert (dest / "acme/harbor.mp4").read_bytes() == (project / "broll/gen/omni/harbor.mp4").read_bytes()
    assert json.loads((dest / "acme/harbor.json").read_text())["fps"] == 12.0


def test_unknown_only_id_and_refusals(project: Path, tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="unknown clip id: nope"):
        export(project, tmp_path / "lib", only=["nope"])
    with pytest.raises(SystemExit, match="outside the project"):
        export(project, project / "out")
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "project.json").write_text('{"slug": "e"}')
    with pytest.raises(SystemExit, match="nothing to export"):
        export(empty, tmp_path / "lib")
    assert not (tmp_path / "lib").exists()


def test_temp_files_and_uncredited_candidates_are_skipped(project: Path, tmp_path: Path) -> None:
    export(project, tmp_path / "lib")

    names = {p.name for p in (tmp_path / "lib/acme").iterdir()}
    assert not any("tmp" in n or n.startswith(".") or "01_harbor" in n for n in names)


def test_tar_holds_the_project_folder_and_catalog_and_refuses_an_existing_file(project: Path, tmp_path: Path) -> None:
    tar = tmp_path / "out" / "lib.tar.gz"

    export(project, tmp_path / "lib", tar=tar)

    with tarfile.open(tar) as archive:
        names = archive.getnames()
    assert "acme/harbor.mp4" in names and "catalog.json" in names and "CATALOG.md" in names
    with pytest.raises(SystemExit, match="already exists"):
        export(project, tmp_path / "lib2", tar=tar)
    assert not (tmp_path / "lib2").exists()


def test_cli_wrapper_runs_in_the_project(tmp_path: Path) -> None:
    project = make_project(tmp_path / "proj")
    (project / "tools").mkdir()
    shutil.copy2(KIT / "tools/export_broll.py", project / "tools/export_broll.py")
    shutil.copy2(KIT / "export-broll.sh", project / "export-broll.sh")

    proc = subprocess.run([shutil.which("bash") or "/bin/bash", str(project / "export-broll.sh"),
                           str(tmp_path / "lib"), "--only", "harbor"], check=False, capture_output=True, text=True,
                          env={**os.environ})

    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "lib/acme/harbor.mp4").is_file()
    assert not (tmp_path / "lib/acme/02_street.mp4").exists()


def test_generated_clip_without_a_sidecar_is_exported_with_the_shots_prompt(project: Path, tmp_path: Path,
                                                                            capsys: pytest.CaptureFixture) -> None:
    omni = project / "broll/gen/omni"
    make_clip(omni / "orphan.mp4")
    make_clip(omni / "nowhere.mp4")
    (project / "broll/gen/shots.json").write_text(json.dumps(
        [{"id": "orphan", "prompt": "An orphan shot.", "mode": "text", "images": ["a.png"]}]))

    ids = export(project, tmp_path / "lib")

    assert {"orphan", "nowhere"} <= set(ids)
    err = capsys.readouterr().err
    assert "note: orphan.mp4: orphan.json is missing" in err and "note: nowhere.mp4" in err
    orphan = json.loads((tmp_path / "lib/acme/orphan.json").read_text())
    assert (orphan["prompt"], orphan["mode"], orphan["images"], orphan["meta_source"]) == (
        "An orphan shot.", "text", ["a.png"], "shots.json")
    assert json.loads((tmp_path / "lib/acme/nowhere.json").read_text())["meta_source"] == "missing"
    assert "> An orphan shot." in (tmp_path / "lib/acme/INDEX.md").read_text()


def test_corrupt_sidecar_is_a_note_not_an_abort(project: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    (project / "broll/gen/omni/harbor.json").write_text("{not json")
    (project / "broll/gen/shots.json").write_text(json.dumps([{"id": "harbor", "prompt": "From shots."}]))
    make_clip(project / "broll/gen/omni/bad name.mp4")

    ids = export(project, tmp_path / "lib")

    assert "harbor" in ids and "bad name" not in ids
    err = capsys.readouterr().err
    assert "harbor.json is unreadable" in err and "bad name.mp4: skipped" in err
    side = json.loads((tmp_path / "lib/acme/harbor.json").read_text())
    assert side["prompt"] == "From shots." and side["meta_source"] == "shots.json"


def test_generated_id_colliding_with_a_credited_candidate_keeps_both(project: Path, tmp_path: Path) -> None:
    make_clip(project / "broll/gen/omni/02_street.mp4", rate=12)
    (project / "broll/gen/omni/02_street.json").write_text(json.dumps({"model": "omni", "prompt": "Gen street."}))

    ids = export(project, tmp_path / "lib")

    assert ids == ["02_street", "harbor", "stock-02_street"]
    folder = tmp_path / "lib/acme"
    assert json.loads((folder / "02_street.json").read_text())["kind"] == "generated"
    stock = json.loads((folder / "stock-02_street.json").read_text())
    assert stock["kind"] == "stock" and stock["credit"]["Channel"] == "A Filmer"
