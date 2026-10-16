"""tools/genvideo.py with a fake client: request shapes, validation before any call, retry, metadata, frames."""

import base64
import importlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
JPG = b"\xff\xd8\xff\xe0" + b"0" * 32
A, B = "brand/hero.png", "brand/shots/b.jpg"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gv():
    """genvideo loaded by path; its usage_log and broll_frames, and a google.genai stub when the SDK
    is absent, live in sys.modules only while it loads."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "usage_log", load("usage_log", KIT / "tools" / "usage_log.py"))
        mp.setitem(sys.modules, "broll_frames", load("broll_frames", KIT / "tools" / "broll_frames.py"))
        try:
            importlib.import_module("google.genai")
        except ImportError:
            google = types.ModuleType("google")
            google.genai = types.ModuleType("google.genai")
            mp.setitem(sys.modules, "google", google)
            mp.setitem(sys.modules, "google.genai", google.genai)
        return load("genvideo", KIT / "tools" / "genvideo.py")


class Dump:
    def __init__(self, data):
        self.data = data

    def model_dump(self, **_):
        return self.data


class Interaction(Dump):
    def __init__(self):
        super().__init__({"id": "i1"})
        self.output_video = Dump({})
        self.output_video.data = base64.b64encode(b"video").decode()
        self.output_video.uri = None
        self.usage = None


def prompt_of(kw):
    return kw["input"] if isinstance(kw["input"], str) else kw["input"][-1]["text"]


class FakeClient:
    """Fails the first `fail` calls, and every call whose prompt is in `fail_on`."""

    def __init__(self, fail=0, fail_on=()):
        self.calls, self.fail, self.fail_on = [], fail, fail_on
        self.interactions = self

    def create(self, **kw):
        self.calls.append(kw)
        if len(self.calls) <= self.fail or prompt_of(kw) in self.fail_on:
            raise RuntimeError("503 unavailable")
        return Interaction()


@pytest.fixture
def project(tmp_path, monkeypatch, gv):
    root = (tmp_path / "proj").resolve()
    (root / "brand" / "shots").mkdir(parents=True)
    (root / A).write_bytes(PNG)
    (root / B).write_bytes(JPG)
    (root / "brand" / "fake.png").write_bytes(b"not an image")
    monkeypatch.setattr(gv, "PROJECT", root)
    monkeypatch.setattr(gv, "ROOT", root / "broll" / "gen")
    monkeypatch.setattr(gv.usage_log, "LOG", tmp_path / "usage.jsonl")
    monkeypatch.setattr(gv, "seconds", lambda _p: 1.0)
    return root


def render(gv, shot, client=None):
    client = client or FakeClient()
    return client, gv.run(client, shot, gv.validate(shot, [shot["id"]]))


def omni_dir(project):
    return project / "broll" / "gen" / "omni"


def test_text_only_request_is_unchanged(gv, project):
    client, (_, status) = render(gv, {"id": "t", "prompt": "a slow dolly"})
    assert status == "ok (attempt 1)"
    assert client.calls == [{"model": gv.MODEL, "input": "a slow dolly", "response_modalities": ["video"],
                             "response_format": gv.OMNI_FMT}]
    meta = json.loads((omni_dir(project) / "t.json").read_text())
    assert meta["task"] is None and "images" not in meta and "mode" not in meta


@pytest.mark.parametrize("mode,images,data,task", [
    ("first_frame", [A], [PNG], "image_to_video"),
    ("first_last", [B, A], [JPG, PNG], "image_to_video"),
    ("reference", [B, A], [JPG, PNG], "reference_to_video"),
])
def test_mode_sends_images_in_order_then_text(gv, project, mode, images, data, task):
    prompt = "see <IMAGE_REF_0> and <IMAGE_REF_1>" if mode == "reference" else "push in"
    client, (_, status) = render(gv, {"id": "s", "prompt": prompt, "images": images, "mode": mode})
    assert status == "ok (attempt 1)"
    kw = client.calls[0]
    *parts, text = kw["input"]
    assert text == {"type": "text", "text": prompt}
    assert [base64.b64decode(p["data"]) for p in parts] == data
    assert [p["mime_type"] for p in parts] == [{PNG: "image/png", JPG: "image/jpeg"}[d] for d in data]
    assert kw["generation_config"] == {"video_config": {"task": task}}


def test_metadata_records_images_mode_and_task(gv, project):
    render(gv, {"id": "m", "prompt": "p", "images": [A], "mode": "first_frame"})
    meta = json.loads((omni_dir(project) / "m.json").read_text())
    assert (meta["mode"], meta["task"], meta["attempts"]) == ("first_frame", "image_to_video", 1)
    assert meta["images"] == [{"path": A, "sha256": gv.hashlib.sha256(PNG).hexdigest()}]


@pytest.mark.parametrize("shot,message", [
    ({"id": "", "prompt": "p"}, "'id' must be"),
    ({"id": "a b", "prompt": "p"}, "'id' must be"),
    ({"id": 5, "prompt": "p"}, "'id' must be"),
    ({"prompt": "p"}, "'id' must be"),
    ({"id": "bad"}, "[bad] 'prompt' must be"),
    ({"id": "bad", "prompt": " "}, "[bad] 'prompt' must be"),
    ({"id": "bad", "prompt": ["p"]}, "[bad] 'prompt' must be"),
    ({"id": "bad", "prompt": "p", "images": A, "mode": "first_frame"}, "[bad] 'images' must be a list"),
    ({"id": "bad", "prompt": "p", "images": [1], "mode": "first_frame"}, "[bad] 'images' must be a list"),
    ({"id": "bad", "prompt": "p", "images": []}, "[bad] 'images' needs a 'mode'"),
    ({"id": "bad", "prompt": "p", "images": [A]}, "[bad] 'images' needs a 'mode'"),
    ({"id": "bad", "prompt": "p", "images": [A], "mode": "bogus"}, "[bad] 'images' needs a 'mode'"),
    ({"id": "bad", "prompt": "p", "images": [A], "mode": ["first_frame"]}, "[bad] 'images' needs a 'mode'"),
    ({"id": "bad", "prompt": "p", "mode": "first_frame"}, "[bad] mode 'first_frame' needs an 'images' list"),
    ({"id": "bad", "prompt": "p", "images": [], "mode": "first_frame"}, "[bad] mode first_frame takes 1"),
    ({"id": "bad", "prompt": "p", "images": [A, B], "mode": "first_frame"}, "[bad] mode first_frame takes 1"),
    ({"id": "bad", "prompt": "p", "images": [A], "mode": "first_last"}, "[bad] mode first_last takes 2"),
    ({"id": "bad", "prompt": "p", "images": [A] * 7, "mode": "reference"}, "[bad] mode reference takes 1 to 6"),
    ({"id": "bad", "prompt": "p", "images": ["brand/none.png"], "mode": "first_frame"}, "[bad] image not found"),
    ({"id": "bad", "prompt": "p", "images": ["brand"], "mode": "first_frame"}, "[bad] image not found"),
    ({"id": "bad", "prompt": "p", "images": ["brand/fake.png"], "mode": "first_frame"}, "not a png, jpeg or webp"),
    ({"id": "bad", "prompt": "p", "images": [A, B], "mode": "reference"}, "missing <IMAGE_REF_0>, <IMAGE_REF_1>"),
    ({"id": "bad", "prompt": "<IMAGE_REF_0> <IMAGE_REF_1>", "images": [A], "mode": "reference"},
     "[bad] the prompt names <IMAGE_REF_1>, but the shot has 1 image"),
    ({"id": "bad", "prompt": "<IMAGE_REF_0>", "images": [A], "mode": "first_frame"}, "reference mode only"),
    ({"id": "bad", "prompt": "<IMAGE_REF_0>"}, "reference mode only; this shot is text-only"),
])
def test_invalid_shot_raises_value_error_naming_it(gv, project, shot, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        gv.validate(shot, [shot.get("id")])


def test_non_object_shot_is_a_value_error(gv, project):
    with pytest.raises(ValueError, match=re.escape("a shot must be an object")):
        gv.validate("just a prompt", [None])


def test_duplicate_id_is_rejected(gv, project):
    with pytest.raises(ValueError, match=re.escape("[d] the id appears 2 times")):
        gv.validate({"id": "d", "prompt": "p"}, ["d", "x", "d"])


def test_image_size_is_checked_before_reading(gv, project, monkeypatch):
    monkeypatch.setattr(gv, "MAX_IMAGE_BYTES", 8)
    monkeypatch.setattr(Path, "open", lambda *_a, **_k: pytest.fail("read before the size check"))
    with pytest.raises(ValueError, match=re.escape("[big] brand/hero.png is 0.0 MB; the limit is")):
        gv.validate({"id": "big", "prompt": "p", "images": [A], "mode": "first_frame"}, ["big"])


def test_shot_total_size_cap(gv, project, monkeypatch):
    monkeypatch.setattr(gv, "MAX_SHOT_BYTES", len(PNG) + len(JPG) - 1)
    shot = {"id": "sum", "prompt": "p", "images": [A, B], "mode": "first_last"}
    with pytest.raises(ValueError, match=re.escape("[sum] brand/shots/b.jpg takes the shot's images past")):
        gv.validate(shot, ["sum"])


@pytest.mark.parametrize("how", ["dotdot", "absolute", "symlink"])
def test_image_outside_the_project_is_rejected(gv, project, how):
    outside = project.parent / "outside.png"
    outside.write_bytes(PNG)
    name = {"dotdot": "../outside.png", "absolute": str(outside), "symlink": "brand/link.png"}[how]
    if how == "symlink":
        (project / name).symlink_to(outside)
    shot = {"id": "esc", "prompt": "p", "images": [name], "mode": "first_frame"}
    with pytest.raises(ValueError, match=re.escape("[esc] image not found inside the project")):
        gv.validate(shot, ["esc"])


def test_failed_attempt_is_retried_once(gv, project):
    client, (_, status) = render(gv, {"id": "r", "prompt": "p"}, FakeClient(fail=1))
    assert status == "ok (attempt 2)" and len(client.calls) == 2
    assert json.loads((omni_dir(project) / "r.json").read_text())["attempts"] == 2


def test_two_failures_leave_no_files(gv, project):
    client, (_, status) = render(gv, {"id": "f", "prompt": "p"}, FakeClient(fail=2))
    assert status == "FAILED" and len(client.calls) == 2
    assert list(omni_dir(project).iterdir()) == []


def test_missing_ffprobe_gives_no_length(gv, monkeypatch):
    def no_ffprobe(*_a, **_k):
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr(gv.subprocess, "run", no_ffprobe)
    assert gv.seconds("clip.mp4") is None


def test_failure_after_the_call_is_not_retried(gv, project, monkeypatch):
    def broken(_path):
        raise OSError("disk gone")

    monkeypatch.setattr(gv, "seconds", broken)
    client, (_, status) = render(gv, {"id": "p", "prompt": "p"})
    assert status.startswith("FAILED after the paid call") and len(client.calls) == 1
    assert not (omni_dir(project) / "p.mp4").exists()


@pytest.fixture
def cli(gv, project, monkeypatch):
    """Run main() on a shot list (`failing`: prompts whose calls fail); returns the clients genai.Client() made."""
    made, fail_on = [], set()

    def client():
        made.append(FakeClient(fail_on=fail_on))
        return made[-1]

    monkeypatch.setattr(gv.genai, "Client", client, raising=False)

    def main(shots, *args, failing=()):
        fail_on.update(failing)
        (project / "broll" / "gen").mkdir(parents=True, exist_ok=True)
        (project / "broll" / "gen" / "shots.json").write_text(json.dumps(shots))
        monkeypatch.setattr(sys, "argv", ["genvideo.py", *args])
        gv.main()
        return made

    return main


def test_main_lists_every_error_before_making_a_client(cli):
    shots = [{"id": "ok", "prompt": "p"}, {"id": "bad", "prompt": ""}, {"id": "worse", "prompt": "p", "mode": "x"}]
    with pytest.raises(SystemExit) as exit_:
        cli(shots)
    assert exit_.value.code not in (0, None)
    assert "[bad] 'prompt' must be" in str(exit_.value.code) and "[worse] mode 'x'" in str(exit_.value.code)
    assert cli([]) == []


def test_main_unknown_only_id_exits(cli):
    with pytest.raises(SystemExit, match=re.escape("no shot nope")):
        cli([{"id": "a", "prompt": "p"}], "--only", "nope")


def test_main_skips_rendered_shots_without_validating(cli, project, capsys):
    omni_dir(project).mkdir(parents=True)
    (omni_dir(project) / "done.mp4").write_bytes(b"video")
    made = cli([{"id": "done", "prompt": "", "images": "x"}, {"id": "new", "prompt": "p"}])
    out = capsys.readouterr().out
    assert "done: skipped" in out and "new: ok (attempt 1)" in out
    assert [len(c.calls) for c in made] == [1]


def kid(*images, sid="kid"):
    return {"id": sid, "prompt": sid, "images": list(images), "mode": ["first_frame", "first_last"][len(images) - 1]}


@pytest.fixture
def frames(gv, monkeypatch):
    """broll_frames.extract writes PNG as <parent>@<at>.png; records (child, parent, at, the clip existed)."""
    calls = []

    def extract(sid, clip, at, folder, _length):
        calls.append((sid, clip.stem, at, clip.is_file()))
        folder.mkdir(parents=True, exist_ok=True)
        (out := folder / f"{clip.stem}@{at}.png").write_bytes(PNG)
        return out

    monkeypatch.setattr(gv.broll_frames, "extract", extract)
    return calls


@pytest.mark.parametrize("entry,message", [
    *((e, f"[kid] '{e}' is not frame:<shot id>, frame:<shot id>@last or frame:<shot id>@<seconds>")
      for e in ("frame:", "frame:mom@", "frame:mom@x", "frame:mom@-1", "frame:mom@1.", "frame:a b", "frame:mom@last@1")),
    ("frame:nope", "[kid] frame:nope@last: there is no shot nope in shots.json"),
    ("frame:kid@2", "[kid] frame:kid@2: a shot cannot use a frame of its own clip"),
])
def test_bad_frame_entry_is_rejected(gv, project, entry, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        gv.validate(kid(entry), ["mom", "kid"])


def test_rendered_parent_is_extracted_once_up_front(cli, gv, project, frames, capsys):
    omni_dir(project).mkdir(parents=True)
    (omni_dir(project) / "mom.mp4").write_bytes(b"video")
    made = cli([{"id": "mom", "prompt": "mom"}, kid("frame:mom@1.5", A)])
    assert frames == [("kid", "mom", "1.5", True)]
    sha = gv.hashlib.sha256(PNG).hexdigest()
    assert json.loads((omni_dir(project) / "kid.json").read_text())["images"] == [
        {"path": "broll/gen/frames/mom@1.5.png", "sha256": sha, "source": "frame:mom@1.5"}, {"path": A, "sha256": sha}]
    assert "kid: ok" in capsys.readouterr().out and [len(c.calls) for c in made] == [1]


def test_child_renders_after_its_parent(cli, project, frames, capsys):
    made = cli([kid("frame:mom"), {"id": "mom", "prompt": "mom"}, {"id": "solo", "prompt": "solo"}])
    prompts = [prompt_of(kw) for kw in made[0].calls]
    assert sorted(prompts) == ["kid", "mom", "solo"] and prompts.index("mom") < prompts.index("kid")
    assert frames == [("kid", "mom", "last", True)]
    assert json.loads((omni_dir(project) / "kid.json").read_text())["images"][0]["source"] == "frame:mom@last"
    assert "kid: ok (attempt 1)" in capsys.readouterr().out


def test_failed_parent_skips_the_child_without_a_call(cli, frames, capsys):
    made = cli([{"id": "mom", "prompt": "mom"}, kid("frame:mom"), {"id": "solo", "prompt": "solo"}], failing={"mom"})
    assert sorted(prompt_of(kw) for kw in made[0].calls) == ["mom", "mom", "solo"] and frames == []
    assert "kid: skipped: needs mom, which did not render" in (out := capsys.readouterr().out) and "solo: ok" in out


def test_failed_extraction_fails_the_child_without_a_call(cli, gv, project, monkeypatch, capsys):
    def broken(sid, *_a):
        raise ValueError(f"[{sid}] ffmpeg cannot read the last frame from mom's clip")

    monkeypatch.setattr(gv.broll_frames, "extract", broken)
    shots = [{"id": "mom", "prompt": "mom"}, kid("frame:mom")]
    omni_dir(project).mkdir(parents=True)
    (omni_dir(project) / "mom.mp4").write_bytes(b"video")
    with pytest.raises(SystemExit, match=re.escape("[kid] ffmpeg cannot read")):  # rendered: found up front
        cli(shots)
    (omni_dir(project) / "mom.mp4").unlink()
    assert [prompt_of(kw) for kw in cli(shots)[0].calls] == ["mom"]
    assert "kid: FAILED before the paid call: [kid] ffmpeg cannot read the last frame" in capsys.readouterr().out


@pytest.mark.parametrize("shots,args,message", [
    ([{"id": "mom", "prompt": "mom"}, kid("frame:mom")], ["--only", "kid"],
     "[kid] needs mom rendered first: run --only mom, or run without --only"),
    ([{"id": "mom", "prompt": ""}, kid("frame:mom")], [], "[kid] needs mom, whose entry in shots.json has errors"),
    ([kid("frame:b", sid="a"), kid("frame:c", sid="b"), kid("frame:a", sid="c")], [],
     "frame: entries form a cycle, each shot using a frame of the next: "),
])
def test_frame_graph_errors_stop_before_any_client(cli, frames, shots, args, message):
    with pytest.raises(SystemExit) as exit_:
        cli(shots, *args)
    text = str(exit_.value.code)
    assert message in text and frames == []
    if "cycle" in message:  # the chain follows the frame: references, from whichever shot it starts
        assert text.split(message)[1] in "a -> b -> c -> a -> b -> c -> a"


@pytest.mark.parametrize("args", [(), ("--only", "mom")])  # --only <parent> warns of children it skips
def test_stale_child_is_reported_not_rendered(cli, project, frames, capsys, args):
    omni_dir(project).mkdir(parents=True)
    (omni_dir(project) / "kid.mp4").write_bytes(b"video")
    made = cli([{"id": "mom", "prompt": "mom"}, kid("frame:mom")], *args)
    assert "kid: rendered from an earlier mom; delete broll/gen/omni/kid.mp4" in capsys.readouterr().out
    assert [prompt_of(kw) for kw in made[0].calls] == ["mom"]


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="needs ffmpeg and ffprobe")
def test_real_ffmpeg_picks_the_named_frames(gv, tmp_path, monkeypatch):
    monkeypatch.setattr(gv, "PROJECT", tmp_path)
    monkeypatch.setattr(gv, "ROOT", tmp_path / "broll" / "gen")
    clip = tmp_path / "broll" / "gen" / "omni" / "mom.mp4"
    clip.parent.mkdir(parents=True)
    colour = "color=s=64x36:r=30:c="  # red 1 s, lime 1 s, then one white frame: the true last frame
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"{colour}red:d=1", "-f", "lavfi", "-i",
                    f"{colour}lime:d=1", "-f", "lavfi", "-i", f"{colour}white,trim=end_frame=1", "-filter_complex",
                    "[0][1][2]concat=n=3:v=1:a=0", "-pix_fmt", "yuv420p", str(clip)], check=True)

    def rgb(data):
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                           input=data, capture_output=True, check=True)
        return tuple(round(c / 255) for c in r.stdout[:3])

    shot = {"id": "kid", "prompt": "<IMAGE_REF_0> <IMAGE_REF_1> <IMAGE_REF_2>", "mode": "reference"}
    images = gv.validate(shot | {"images": ["frame:mom", "frame:mom@0.5", "frame:mom@1.5"]}, ["mom", "kid"])
    assert [rgb(i["data"]) for i in images] == [(1, 1, 1), (1, 0, 0), (0, 1, 0)]
    assert [i["source"] for i in images] == ["frame:mom@last", "frame:mom@0.5", "frame:mom@1.5"]
    with pytest.raises(ValueError, match=re.escape("a frame at 9 s from mom's clip (the clip is 2.03 s long)")):
        gv.validate(kid("frame:mom@9"), ["mom", "kid"])
    frames = sorted(p.name for p in clip.parent.with_name("frames").iterdir())
    assert frames == ["mom@0.5.png", "mom@1.5.png", "mom@last.png"]  # no temporary file left behind
