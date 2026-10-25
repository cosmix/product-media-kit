"""A steady beat and bar grid measured from audio, for music with no score to read it from (a
Lyria take). Lyria does not follow a tempo asked for in the prompt, so the grid always comes from
the sound: qc.tempo_estimate gives a first period, a comb over the onset strength refines period
and phase, a line through the onsets nearest each beat fixes both, and the beat phase whose hits
carry the most low-band attack (kick, bass) is taken as the downbeat. 4/4 is assumed.

    grid = measure(x)                 # x: 48 kHz stereo float
    grid.bpm, grid.downbeats(0, 30)   # downbeat times (s) within [0, 30]
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d, uniform_filter1d

from .library import SR
from .qc import HOP, onset_strength, onsets, tempo_estimate

# onset_strength frame k is the log-spectral flux between 2048-sample windows k and k+1 (HOP
# apart). A log spectrum jumps as soon as an attack enters a window, so an attack at t peaks at
# frame k = (t - LAG) / HOP: about one window length late, 45 ms measured on click tracks at
# 96-143 BPM (lyria.py --selftest checks the phase to 20 ms).
LAG = 0.045
SNAP = 0.04  # an onset this close to a predicted beat belongs to it (s)


@dataclass(frozen=True)
class BeatGrid:
    period: float    # seconds per beat
    downbeat: float  # one downbeat (s); every fourth beat from it is another

    @property
    def bpm(self) -> float:
        return 60.0 / self.period

    def _every(self, step: float, lo: float, hi: float) -> np.ndarray:
        k0 = np.ceil((lo - self.downbeat) / step - 1e-9)
        k1 = np.floor((hi - self.downbeat) / step + 1e-9)
        return self.downbeat + np.arange(k0, k1 + 1) * step

    def beats(self, lo: float, hi: float) -> np.ndarray:
        """Beat times (s) within [lo, hi]."""
        return self._every(self.period, lo, hi)

    def downbeats(self, lo: float, hi: float) -> np.ndarray:
        """Downbeat (bar accent) times (s) within [lo, hi]."""
        return self._every(4 * self.period, lo, hi)


def _comb(strength: np.ndarray, times: np.ndarray, period: float) -> tuple[float, float]:
    """(score, phase): the phase whose beats sit on the most onset strength at this period."""
    phases = np.arange(0.0, period, HOP / 2)
    grid = phases[:, None] + np.arange(int(times[-1] / period) + 1)[None, :] * period
    score = np.interp(grid, times, strength, right=0.0).sum(axis=1)
    best = int(np.argmax(score))
    return float(score[best]) / grid.shape[1], float(phases[best])


def _line_fit(x: np.ndarray, period: float, phase: float) -> tuple[float, float]:
    """(period, phase) from a least-squares line through the onsets nearest each predicted beat."""
    hits = onsets(x) + LAG
    duration = len(x) / SR
    for _ in range(2):
        beats = np.arange(phase, duration, period)
        nearest = np.abs(hits[None, :] - beats[:, None]).argmin(axis=1)
        near = np.abs(hits[nearest] - beats) < SNAP
        if near.sum() < 8:
            break
        index = np.flatnonzero(near).astype(float)
        period, phase = np.polyfit(index, hits[nearest[near]], 1)
    return float(period), float(phase)


def _accents(x: np.ndarray, beats: np.ndarray, strength: np.ndarray, times: np.ndarray) -> np.ndarray:
    """Per beat: full-band onset strength plus low-band (< 150 Hz) energy rise, each in units of its spread."""
    sos = signal.butter(4, 150, "low", fs=SR, output="sos")
    hop = int(HOP * SR)
    low = uniform_filter1d(signal.sosfilt(sos, x.mean(axis=1)) ** 2, 2 * hop)[::hop]
    rise = np.maximum(0.0, np.diff(np.log10(low + 1e-10), prepend=np.log10(low[0] + 1e-10)))
    width = int(2 * SNAP / HOP) + 1
    full = np.interp(beats, times, maximum_filter1d(strength, width))
    bass = np.interp(beats, np.arange(len(rise)) * HOP, maximum_filter1d(rise, width))
    return full / (full.std() + 1e-12) + bass / (bass.std() + 1e-12)


def measure(x: np.ndarray) -> BeatGrid:
    """The grid of a 48 kHz stereo signal at least a few bars long."""
    strength = np.maximum(onset_strength(x), 0.0)
    times = np.arange(len(strength)) * HOP + LAG
    guess = 60.0 / tempo_estimate(x)
    candidates = guess * (1.0 + np.linspace(-0.025, 0.025, 101))
    scored = [(*_comb(strength, times, p), p) for p in candidates]
    _, phase, period = max(scored)
    period, phase = _line_fit(x, period, phase)
    phase %= period
    beats = np.arange(phase, len(x) / SR, period)
    accent = _accents(x, beats, strength, times)
    bar_phase = int(np.argmax([accent[m::4].mean() for m in range(4)]))
    return BeatGrid(period=period, downbeat=float(beats[bar_phase]))
