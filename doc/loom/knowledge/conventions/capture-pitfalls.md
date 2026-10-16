# Capture Pitfalls

> Capture pitfalls that shaped the engines, web and TUI capture notes

## Pitfalls that apply to stills and clips

Authoritative table: README "Mistakes and pitfalls"; the rows below shaped the engines.

| Area | What went wrong | Rule |
| --- | --- | --- |
| Claims | A script or post described what the PRD planned and the code shipped something else | Verify every claim against the code; the code wins and the human decides the wording |
| Review | A capture teammate reported a still as fine; the box was on the wrong element | The lead Reads every image itself |
| Team | Agents reported on an old brief while a newer one sat in their inbox | Check whether the agent is running or idle and read file timestamps before re-sending |
| Files | A capture overwritten in place was read half-written | Write to a temporary name and rename atomically |
| Fixtures | Implausible or contradictory fixture data was found after capture | Review the fixture data for sense before capturing anything |
| Fixtures | A tmux socket under a long fixture path could not be created (Unix socket paths hold about 104-108 bytes) | Keep `TMUX_TMPDIR` short; `tmux_server` refuses a longer path |
| Web | A selector stopped matching after a product change | Prefer roles, labels and visible text over generated class names; recapture only that scenario |
| Web | In mock mode a toast or debounced field never appears in the still | Advance the page timers with `shooter.page.clock.run_for(ms)` before the shot |
| Web | Mock mode stops with `KeyError` for a scenario | Give `World` a scene for every SHOTS and CLIPS scenario |
| Reuse | A post linked clips captured under the video profile and showed their posters | Recapture those clips with `--for both` |
| Brand | A defect from downstream repair | Fix at the source; never repair the output downstream |

## Web and TUI capture notes

- Web: the mock is an aiohttp app serving the real built frontend (`PRODUCT_WEB_DIST`) and implementing the API from the frontend's own schema; show only what the real UI renders, and record a real quirk as a bug in the product's tracker instead of faking it. Live mode (`BASE_URL` or `PRODUCT_URL`) captures a running product in real time. A live-mode `Director` still installs the page's fake clock on its first step.
- TUI: the real binary runs in a pty at a fixed grid; pyte interprets output; skia draws with the mono font from `design.json` or the system monospace; a TUI that talks to a daemon needs a stand-in daemon in `fixtures/tui/`; build the workspace with the product's init command in `prepare()`; run config UIs with `HOME` at a scratch home; CLI shots run read-only against `PRODUCT_REPO`; isolate tmux with a short `TMUX_TMPDIR`.
