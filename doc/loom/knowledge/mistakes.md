# Mistakes & Lessons Learned

> Record mistakes made during development and how to avoid them.
> A summary of the current tree: correct a section in place with `replace-section`.
>
> Format: Describe what went wrong, why, and how to avoid it next time.

## Media kit merge mistakes

ffmpeg 9 ignored the `-color_trc` and `-color_primaries` output flags once frame properties were set (fixed with a `setparams` bt709 filter; motion also used the BT.601 matrix); a manifest merge that kept "the kind not recaptured" dropped entries (now merged on origin); docs and code cited README sections by name and broke when sections moved (guarded by `tests/test_docs_contracts.py`). Prevention rules: [mistakes/media-kit-merge](mistakes/media-kit-merge.md).

## Capture engine and postkit mistakes

`grep -q` into a pipe under `pipefail` misreported an encoder; Pillow's `verify()` and `open()` miss `SyntaxError`, broken zlib streams and decompression bombs; the guides described behaviour the code lacks. Prevention rules: [mistakes/capture-and-postkit](mistakes/capture-and-postkit.md).

## Gate and contract mistakes

Contracts frozen with `cwd` at the repository root fail on the system python; a seed `uv_build` bound warned on every build. Prevention rules: [mistakes/loom-gates](mistakes/loom-gates.md).
