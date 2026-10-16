# Music

> scorekit: sample libraries, score, instruments, mix, qc, render

## scorekit (music/)

One uv project (package name `scorekit`; Python >= 3.12; numpy, scipy, soundfile, soxr, pyloudnorm, matplotlib, `pedalboard`). `uv run render.py [--out out] [--seed 7] [--qc] [--excerpt A B]` composes the cue with the project's `<project>/music/arrangement.py` (`compose(seed)` returns a `scorekit.score.Score`) and writes `music/out/soundtrack.wav`, `music/out/stems/*.wav` (48 kHz, 24-bit, sample-aligned) and `manifest.json` (tempo, bar grid, section starts, `sample_libraries`: the libraries the score used, which `edit/editkit/credit_data.music_samples()` reads to credit Salamander only when used). `--excerpt` writes a slice for the audio judge. `uv run render.py --selftest` renders eight bars of synthesized C major, no samples needed. The edit reads `music/out/soundtrack.wav` and `music/out/stems/`; a video without music has neither.

Modules in `music/scorekit/`:
- `library.py`: indexes the sample libraries (Salamander Grand Piano as sfz, VSCO-2 CE folders) into zones (sample, MIDI pitch, velocity band, round-robin index). `setup.sh` downloads VSCO-2 CE, and Salamander only when `project.json` `piano` is `salamander`, into `music/samples/` (not installed, not committed); `music/CREDITS.md` records the licences.
- `sampler.py`: repitch, envelope, sustain extension, stereo placement. `instruments.py`: `STEMS` (piano, strings, mallets, bass, percussion, synth, winds), `piano_library()` (`project.json` `piano` through `tools/project_settings`) and the `registry()` of instruments; `piano` plays VSCO's Upright Nr1 unless `piano_library()` is `salamander`.
- `score.py`: `Score`, per-instrument timing jitter and lag. `timing.py`: `Grid` (the bar grid) and `narration_windows()` read from `narration/timeline.json`, so cues land on the narration's clock.
- `theory.py` (chords and voicings), `parts.py` (ostinati, pulses, bass, melody, strings), `drums.py`, `percussion.py` (VSCO one-shots plus synthesized pieces), `synth.py` (pluck, sub bass, kick, clap, riser).
- `mix.py`: synthetic room and hall impulse responses, stem buses and loudness through `pedalboard`, with mid dips that keep 1-4 kHz open for the narrator. `qc.py`: spectrograms, loudness curves, onset density, tempo estimate, centroid and click hunting, for review without ears.
