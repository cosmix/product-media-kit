<!-- generated automatically on knowledge writes — do not edit by hand -->

# Knowledge Index

> Read this index first, then only what it points to: the section for your area in a tier-1 summary (`rg -n '^## ' <file>` lists them) and the tier-2 topics your task touches. A specific question is cheaper to pull than to read — `loom knowledge context --query "..."` returns the matching sections quoted.

## Tier 1 — Summaries

| File | Description | Lines |
| --- | --- | --- |
| [architecture.md](architecture.md) | High-level component relationships, data flow, module dependencies | 36 |
| [entry-points.md](entry-points.md) | Key files agents should read first | 30 |
| [patterns.md](patterns.md) | Architectural patterns discovered in the codebase | 48 |
| [conventions.md](conventions.md) | Coding conventions discovered in the codebase | 36 |
| [mistakes.md](mistakes.md) | Mistakes made and lessons learned - what to avoid | 18 |
| [stack.md](stack.md) | Dependencies, frameworks, and tooling used in the project | 29 |
| [concerns.md](concerns.md) | Technical debt, warnings, and issues to address | 24 |

## Tier 2 — Topics

### architecture

| Topic | Blurb | Lines |
| --- | --- | --- |
| [brand-and-design](architecture/brand-and-design.md) | design.json schema and its loaders, tools/fonts.py, brand skill, check.py | 29 |
| [broll](architecture/broll.md) | genvideo.py: Omni b-roll, image modes, frame: continuity, validation, retry | 27 |
| [edit](architecture/edit.md) | compositor, EDL asset refs, outputs naming, render, subs, credits and share copy | 24 |
| [kit-plumbing](architecture/kit-plumbing.md) | install.sh, setup.sh, system-deps.sh, configure/export/inflate, settings… | 51 |
| [motion](architecture/motion.md) | motion graphics renderer: scene modules, lib, encode, logo, manifest | 17 |
| [music](architecture/music.md) | scorekit: sample libraries, score, instruments, mix, qc, render | 14 |
| [narration](architecture/narration.md) | timeline.json the only clock, tts skill, listening judge, costs.py and… | 19 |
| [outputs-and-reuse](architecture/outputs-and-reuse.md) | output names and revisions, twin outputs.py modules, manifest contract, reuse… | 39 |
| [postkit](architecture/postkit.md) | postkit modules, build, check and add flow, treatments, ledger | 25 |
| [tuicap](architecture/tuicap.md) | tuicap modules, render pipeline, profiles, product.py contract, CLI, fallback… | 30 |
| [webcap](architecture/webcap.md) | webcap modules, profiles, product.py contract, mock and live modes, Director… | 46 |

### conventions

| Topic | Blurb | Lines |
| --- | --- | --- |
| [capture-pitfalls](conventions/capture-pitfalls.md) | Capture pitfalls that shaped the engines, web and TUI capture notes | 26 |
| [kit-workflow](conventions/kit-workflow.md) | Team roles, ownership rules, briefs, workflow phases, editorial rules for both… | 34 |

### mistakes

| Topic | Blurb | Lines |
| --- | --- | --- |
| [capture-and-postkit](mistakes/capture-and-postkit.md) | Pipefail grep, Pillow errors, guides ahead of code | 24 |
| [loom-gates](mistakes/loom-gates.md) | Contract cwd and uv_build bound: gate mistakes that apply to this repo's… | 17 |
| [media-kit-merge](mistakes/media-kit-merge.md) | ffmpeg colour tags, manifest merge on origin, docs citing sections by name | 31 |

### concerns

| Topic | Blurb | Lines |
| --- | --- | --- |
| [open-suggestions](concerns/open-suggestions.md) | Unimplemented reviewer suggestions and known gaps per package | 23 |
