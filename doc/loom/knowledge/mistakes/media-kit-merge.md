# Media Kit Merge

> ffmpeg colour tags, manifest merge on origin, docs citing sections by name

## ffmpeg dropped the colour output flags

**What happened**: clips from webcap, tuicap and motion carried no bt709 transfer or primaries tags, so players guessed. The `-color_trc` and `-color_primaries` output flags were present in every command. Motion's opaque H.264 had also converted with the BT.601 matrix.
**Why**: with ffmpeg 9, properties set on a frame override the output colour flags, and frames decoded or piped in carry their own (unspecified) properties. The flags were silently ignored while the command exited 0.
**Prevention**: tag frames with a `setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv` filter in every encode that produces an H.264 deliverable (`fixtures/web/webcap/encode.py`, `fixtures/tui/src/tuicap/encode.py`, `motion/lib/encode.py`, `edit/render.py`); convert RGB to YUV with the bt709 matrix; check a result with `ffprobe -show_streams` for `color_transfer`, `color_primaries` and `color_space`.
**Fix**: the `setparams` filter in webcap, tuicap and motion, and the bt709 matrix in motion.

## The manifest merge that kept "the kind not recaptured" dropped entries

**What happened**: a run kept "the kind it did not recapture" (still or clip) and replaced everything else of the scenario, which dropped entries. Stills a director took inside a clip (`still()`) vanished from the manifest when SHOTS stills were recaptured, and the reverse.
**Why**: the rule was "stills versus clips", but a clip scenario also produces stills (origin `clip`), so the file-type split did not match where an entry came from.
**Prevention**: merge on `origin` (`shots` or `clip`): `manifest.update(..., origins=...)` replaces the scenario's entries of the origins a run captured and keeps every other entry. Each engine has a test that a run keeps the origin it did not recapture (`test_run_keeps_the_origin_it_did_not_recapture` in `fixtures/tui/tests/test_tuicap.py`).
**Fix**: every entry carries `origin`; both `manifest.update` functions merge by scenario and origin.

## Docs and code cited README sections by name and broke when sections moved

**What happened**: engine error messages, guides and skills pointed at README sections by heading ("README, Web capture"); a restructure moved or renamed headings and the pointers went stale without any check noticing.
**Why**: a section name is a link with no resolver.
**Prevention**: cite a guide section only by a name that `tests/test_docs_contracts.py` resolves: it checks that every command, flag, module, link and section reference in the guides exists, pins the README section map, rejects stale names, and requires a language on every fence. Change a heading and the test says which citation to move.
**Fix**: the contract test, and citations pointing at `guides/capture.md`, `guides/video.md` and `guides/blog.md` sections.
