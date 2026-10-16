# Outputs And Reuse

> output names and revisions, twin outputs.py modules, manifest contract, reuse between media

## Output names and revisions

`<project>/project.json` is `{"slug": "<slug>", "media": [...]}`; `media` is an ordered subset of `["video", "blog"]`. Deliverables go to `outputs/` (video, flat) and `outputs/blog/` (the post, with `outputs/blog/images/`), named `<stage>-<slug>-v<N>[-<suffix>].<ext>` with stage `draft` or `final`:

```text
outputs/draft-<slug>-v<N>.mp4                    render.py --preview
outputs/final-<slug>-v<N>.mp4                    render.py
outputs/<stage>-<slug>-v<N>-range-<A>-<B>.mp4    render.py --range
outputs/draft-<slug>-v<N>-contact-<NN>.png       render.py --contact
outputs/<stage>-<slug>-v<N>.srt                  subs.py [--final]
outputs/<stage>-<slug>-v<N>-credits.txt          credits.py [--final]
outputs/final-<slug>-v<N>-share.mp4              render.py --share
outputs/blog/<stage>-<slug>-v<N>.md              postkit build [--final]
outputs/blog/images/<source>-<scenario>-<label>.<png|gif|webm>
```

Revisions are found by scanning the folder; there is no counter. A tool rewrites the latest revision of its stage (v1 when none); `--next` writes max+1; `--revision vN` names one. Numbering is per medium and per stage; the primary file has no suffix (video `.mp4`, blog `.md`), and companions (srt, credits, share, contact, range) attach to the latest primary of their stage. `outputs/` is committed: it is the deliverable. Intermediates stay put: `edit/out/mix.wav`, `edit/build/`, `motion/out/`, `music/out/`, `captures/`, `post/build/ledger.json`.

## Twin outputs modules

`edit/editkit/outputs.py` and `post/src/postkit/outputs.py` implement the same rules in two uv projects that cannot import each other. Change them together: `tests/test_outputs_agree.py` loads both by path and asserts they pick the same names and revisions on fixture trees; each package also tests its own copy (`edit/tests/test_outputs.py`, `post/tests/test_outputs.py`).

## Capture manifest contract

`captures/<source>/manifest.json` is `{"source": ..., "shots": [entry, ...]}`, sorted by id `<scenario>/<label>`, paths relative to the manifest's folder, written atomically. Sources: `web`, `tui` (written by the engines), `motion`, `broll`, `video` (written by `postkit add`). An entry has `id`, `kind` (`still` or `clip`), `origin` (`shots` or `clip`), `file`, `width`, `height`, `scale` (stills 2.0 from both engines; clips 2.0 for video and both, 1 for blog), `boxes` (`{name: [x, y, w, h]}` in image pixels). A clip adds `poster`, `duration`, `marks` and, by profile, `webm`, a GIF `file` (blog, both), `video` (mp4), `fps`, `cursor`, `cursor_space` (web), `grid`, `cell_px`, `padding_px` (tui) (video, both). Under the video profile alone `file` is the poster PNG. The label `clip` is reserved.

Merge rule: `update` replaces the scenario's entries of the origin a run captured and keeps the other origin and every other scenario, so a stills-only run never drops clip-derived stills and a clip run never drops SHOTS stills ([mistakes/media-kit-merge](../mistakes/media-kit-merge.md)).

## Reuse between media

- Shared records: `project.json`, `<project>/BRAND.md`, `brand/`, `design.json`, `<project>/claims.md` (every claim verified once against the code) and `<project>/scenarios.md` (one fixture story, one table with a Media column); the video script and the blog outline both take from them. Scenario, label and box names share one regex (`^[a-z0-9]+(-[a-z0-9]+)*$`) in both media.
- Capture once for both: with both media, `--for both` records one clip at scale 2 and 60 fps (`clip.mp4` for the edit) and derives the WebM and GIF for the post; one viewport serves both (1920x1080 when `media` includes video, else 1440x900; `VIEWPORT` in product.py wins).
- Video to blog: the draft links stills as `shot:web/<scenario>/<label>` (including `still()` frames a director took); motion renders, logo stills, b-roll and frames of a finished video enter through `postkit add motion|broll|video/<scenario>/<label> <file> [--at T | --from T --to T]`.
- Blog to video: the edit references `web:<scenario>` (clip) or `still:web/<scenario>/<label>`; a blog-only clip is a 30 fps WebM at scale 1, so recapture with `--for both` for the cut. `/mediatime` writes a reuse inventory into `<project>/NOTES.md` when a medium is added.
- Gap: a clip captured with `--for video` shows as a still in a post until recaptured with `--for both` ([concerns](../concerns.md)).
