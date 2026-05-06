#!/usr/bin/env python3
"""
master_voice.py — Voice recording mastering CLI

Effects chain:
  1. Noise reduction  (noisereduce)
  2. High-pass filter (pedalboard)
  3. Parametric EQ    (pedalboard)
  4. Compression      (pedalboard)
  5. Limiter          (pedalboard)
  6. Loudness norm    (pyloudnorm → −16 LUFS target)

Output: processed audio file + before/after spectrograms.
"""

import argparse
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import soundfile as sf
import noisereduce as nr
from pedalboard.io import AudioFile as PedalboardAudioFile
import pyloudnorm as pyln
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pedalboard import (
    Pedalboard,
    HighpassFilter,
    LowShelfFilter,
    PeakFilter,
    HighShelfFilter,
    Compressor,
    Limiter,
)

warnings.filterwarnings("ignore", category=UserWarning)


# ── helpers ──────────────────────────────────────────────────────────────────

def load_audio(path: str) -> tuple[np.ndarray, int]:
    """Load audio as float32 (channels, samples).
    Tries pedalboard first; falls back to ffmpeg for formats libsndfile can't decode."""
    import subprocess, tempfile

    try:
        with PedalboardAudioFile(path) as f:
            audio = f.read(f.frames)
            sr = int(f.samplerate)
        return audio, sr
    except Exception:
        pass

    # ffmpeg fallback — converts to a temp WAV and reads that
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", path, tmp.name],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg could not decode {Path(path).name}:\n"
                + result.stderr.decode(errors="replace").strip().splitlines()[-1]
            )
        audio, sr = sf.read(tmp.name, dtype="float32", always_2d=True)
        return audio.T, sr
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def save_audio(path: str, audio: np.ndarray, sr: int) -> None:
    sf.write(path, audio.T, sr, subtype="PCM_24")


def lufs(audio: np.ndarray, sr: int) -> float:
    meter = pyln.Meter(sr)
    # pyloudnorm expects (samples, channels)
    return meter.integrated_loudness(audio.T)


def normalize_loudness(audio: np.ndarray, sr: int, target_lufs: float) -> np.ndarray:
    current = lufs(audio, sr)
    if not np.isfinite(current):
        print("  [warn] could not measure loudness — skipping normalization")
        return audio
    gain_db = target_lufs - current
    gain_linear = 10 ** (gain_db / 20)
    return audio * gain_linear


def noise_sample_frames(audio: np.ndarray, sr: int,
                        start_s: float, end_s: float) -> np.ndarray:
    """Extract a noise profile slice (channels, samples)."""
    s = max(0, int(start_s * sr))
    e = min(audio.shape[1], int(end_s * sr))
    if s >= e:
        raise ValueError(
            f"Noise sample range {start_s}–{end_s}s is invalid for this file."
        )
    return audio[:, s:e]


def plot_spectrogram(ax: plt.Axes, audio: np.ndarray, sr: int,
                     title: str, fmax: float = 8000) -> None:
    mono = audio.mean(axis=0)
    ax.specgram(mono, Fs=sr, NFFT=1024, noverlap=512,
                cmap="inferno", vmin=-100, vmax=0)
    ax.set_ylim(0, fmax)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")


def save_spectrograms(before: np.ndarray, after: np.ndarray,
                      sr: int, out_path: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), tight_layout=True)
    plot_spectrogram(axes[0], before, sr, "Before — original")
    plot_spectrogram(axes[1], after,  sr, "After — mastered")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ── processing stages ────────────────────────────────────────────────────────

def apply_noise_reduction(audio: np.ndarray, sr: int,
                           noise_start: float, noise_end: float,
                           prop_decrease: float) -> np.ndarray:
    profile = noise_sample_frames(audio, sr, noise_start, noise_end)
    out = np.zeros_like(audio)
    for ch in range(audio.shape[0]):
        out[ch] = nr.reduce_noise(
            y=audio[ch],
            sr=sr,
            y_noise=profile[ch],
            prop_decrease=prop_decrease,
            stationary=False,
        )
    return out


def apply_effects_chain(
    audio: np.ndarray,
    sr: int,
    hp_cutoff: float,
    low_shelf_gain: float,
    low_shelf_freq: float,
    mid_cut_gain: float,
    mid_cut_freq: float,
    mid_cut_q: float,
    presence_gain: float,
    presence_freq: float,
    presence_q: float,
    air_gain: float,
    air_freq: float,
    comp_threshold: float,
    comp_ratio: float,
    comp_attack: float,
    comp_release: float,
    limiter_threshold: float,
) -> np.ndarray:
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=hp_cutoff),

        # Tighten low end
        LowShelfFilter(
            cutoff_frequency_hz=low_shelf_freq,
            gain_db=low_shelf_gain,
        ),

        # Cut boxy/nasal mud
        PeakFilter(
            cutoff_frequency_hz=mid_cut_freq,
            gain_db=mid_cut_gain,
            q=mid_cut_q,
        ),

        # Presence / clarity boost
        PeakFilter(
            cutoff_frequency_hz=presence_freq,
            gain_db=presence_gain,
            q=presence_q,
        ),

        # Air
        HighShelfFilter(
            cutoff_frequency_hz=air_freq,
            gain_db=air_gain,
        ),

        Compressor(
            threshold_db=comp_threshold,
            ratio=comp_ratio,
            attack_ms=comp_attack,
            release_ms=comp_release,
        ),

        Limiter(threshold_db=limiter_threshold, release_ms=50.0),
    ])

    # pedalboard expects (channels, samples) float32
    return board(audio, sr)


# ── public API ───────────────────────────────────────────────────────────────

def process_audio(
    input_path: str,
    output_path: str,
    spec_path: str | None = None,
    *,
    preset_label: str = "Custom",
    noise_start: float = 0.0,
    noise_end: float = 0.5,
    noise_reduction: float = 0.85,
    skip_noise_reduction: bool = False,
    hp_cutoff: float = 80.0,
    low_shelf_gain: float = -3.0,
    low_shelf_freq: float = 200.0,
    mid_cut_gain: float = -3.0,
    mid_cut_freq: float = 400.0,
    mid_cut_q: float = 1.0,
    presence_gain: float = 2.5,
    presence_freq: float = 4000.0,
    presence_q: float = 0.8,
    air_gain: float = 1.5,
    air_freq: float = 10000.0,
    comp_threshold: float = -18.0,
    comp_ratio: float = 3.0,
    comp_attack: float = 8.0,
    comp_release: float = 120.0,
    limiter_threshold: float = -1.0,
    target_lufs: float = -16.0,
    on_status=None,
) -> dict:
    """
    Run the full mastering pipeline and return a metadata dict.

    on_status(step, status, detail, params) where:
      step   — one of 'load'|'noise'|'effects'|'loudness'|'spectro'
      status — 'running'|'done'|'skipped'|'error'
      detail — short human-readable summary (shown by default in UI)
      params — dict of technical key/value pairs (shown in accordion)
    """
    def emit(step, status, detail="", params=None):
        if on_status:
            on_status(step, status, detail, params or {})

    emit("load", "running")
    audio_in, sr = load_audio(input_path)
    duration = audio_in.shape[1] / sr
    channels = audio_in.shape[0]
    input_lufs_val = lufs(audio_in, sr)
    sr_str = f"{sr / 1000:.1f}".rstrip("0").rstrip(".") + " kHz"
    ch_str = "mono" if channels == 1 else "stereo" if channels == 2 else f"{channels}ch"
    emit("load", "done",
         f"{ch_str} · {sr_str} · {duration:.1f}s · {input_lufs_val:.1f} LUFS",
         params={
             "Channels":       ch_str,
             "Sample rate":    f"{sr:,} Hz",
             "Duration":       f"{duration:.2f} s",
             "Input loudness": f"{input_lufs_val:.2f} LUFS",
             "Format":         Path(input_path).suffix.upper().lstrip(".") or "WAV",
         })

    original = audio_in.copy()

    if not skip_noise_reduction:
        emit("noise", "running")
        audio = apply_noise_reduction(audio_in, sr, noise_start, noise_end, noise_reduction)
        emit("noise", "done", "",
             params={
                 "Preset":        preset_label,
                 "Strength":      f"{noise_reduction:.0%}",
                 "Noise sample":  f"{noise_start} – {noise_end} s",
                 "Algorithm":     "Spectral gating",
                 "Stationary":    "No",
             })
    else:
        audio = audio_in
        emit("noise", "skipped", "skipped",
             params={"Preset": preset_label, "Reason": "Clean recording — NR disabled"})

    emit("effects", "running")
    audio = apply_effects_chain(
        audio, sr,
        hp_cutoff=hp_cutoff,
        low_shelf_gain=low_shelf_gain,
        low_shelf_freq=low_shelf_freq,
        mid_cut_gain=mid_cut_gain,
        mid_cut_freq=mid_cut_freq,
        mid_cut_q=mid_cut_q,
        presence_gain=presence_gain,
        presence_freq=presence_freq,
        presence_q=presence_q,
        air_gain=air_gain,
        air_freq=air_freq,
        comp_threshold=comp_threshold,
        comp_ratio=comp_ratio,
        comp_attack=comp_attack,
        comp_release=comp_release,
        limiter_threshold=limiter_threshold,
    )
    emit("effects", "done", "",
         params={
             "HP cutoff":     f"{hp_cutoff} Hz",
             "Low shelf":     f"{low_shelf_gain:+.1f} dB @ {low_shelf_freq:.0f} Hz",
             "Mid cut":       f"{mid_cut_gain:+.1f} dB @ {mid_cut_freq:.0f} Hz · Q {mid_cut_q}",
             "Presence":      f"{presence_gain:+.1f} dB @ {presence_freq:.0f} Hz · Q {presence_q}",
             "Air":           f"{air_gain:+.1f} dB @ {air_freq:.0f} Hz",
             "Comp threshold": f"{comp_threshold} dB",
             "Comp ratio":    f"{comp_ratio}:1",
             "Comp attack":   f"{comp_attack} ms",
             "Comp release":  f"{comp_release} ms",
             "Limiter":       f"{limiter_threshold} dBFS",
         })

    emit("loudness", "running")
    pre_norm_lufs = lufs(audio, sr)
    audio = normalize_loudness(audio, sr, target_lufs)
    output_lufs_val = lufs(audio, sr)
    gain_applied = output_lufs_val - pre_norm_lufs
    emit("loudness", "done", f"{output_lufs_val:.1f} LUFS",
         params={
             "Target":        f"{target_lufs} LUFS",
             "Pre-norm":      f"{pre_norm_lufs:.2f} LUFS",
             "Output":        f"{output_lufs_val:.2f} LUFS",
             "Gain applied":  f"{gain_applied:+.2f} dB",
             "Standard":      "EBU R128 / ITU-R BS.1770-4",
         })

    save_audio(output_path, audio, sr)

    if spec_path:
        emit("spectro", "running")
        save_spectrograms(original, audio, sr, spec_path)
        emit("spectro", "done", "",
             params={
                 "File":       Path(spec_path).name,
                 "Resolution": "1800 × 600 px",
                 "Colourmap":  "Inferno",
                 "NFFT":       "1024",
                 "Overlap":    "512",
             })

    return {
        "channels":    channels,
        "sample_rate": sr,
        "duration":    duration,
        "input_lufs":  input_lufs_val,
        "output_lufs": output_lufs_val,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="master_voice",
        description="Master a voice recording to broadcast-ready quality.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # I/O
    p.add_argument("input", help="Input audio file (WAV, FLAC, MP3, AIFF, …)")
    p.add_argument("-o", "--output", default=None,
                   help="Output file path (default: <input>_mastered.wav)")
    p.add_argument("--spectrogram", default=None,
                   help="Spectrogram PNG path (default: <input>_spectrogram.png)")
    p.add_argument("--no-spectrogram", action="store_true",
                   help="Skip spectrogram generation")

    # Noise reduction
    nr_g = p.add_argument_group("Noise reduction")
    nr_g.add_argument("--noise-start", type=float, default=0.0, metavar="S",
                      help="Noise profile sample start (seconds)")
    nr_g.add_argument("--noise-end", type=float, default=0.5, metavar="S",
                      help="Noise profile sample end (seconds)")
    nr_g.add_argument("--noise-reduction", type=float, default=0.85, metavar="0–1",
                      help="Proportion of noise to remove (0=none, 1=full)")
    nr_g.add_argument("--skip-noise-reduction", action="store_true",
                      help="Bypass noise reduction entirely")

    # EQ
    eq_g = p.add_argument_group("Equalisation")
    eq_g.add_argument("--hp-cutoff", type=float, default=80.0, metavar="HZ",
                      help="High-pass filter cutoff (removes rumble/handling noise)")
    eq_g.add_argument("--low-shelf-gain", type=float, default=-3.0, metavar="DB",
                      help="Low shelf gain at --low-shelf-freq")
    eq_g.add_argument("--low-shelf-freq", type=float, default=200.0, metavar="HZ",
                      help="Low shelf frequency (tighten low-mid body)")
    eq_g.add_argument("--mid-cut-gain", type=float, default=-3.0, metavar="DB",
                      help="Parametric mid cut gain (negative = cut)")
    eq_g.add_argument("--mid-cut-freq", type=float, default=400.0, metavar="HZ",
                      help="Parametric mid cut centre frequency (boxiness)")
    eq_g.add_argument("--mid-cut-q", type=float, default=1.0, metavar="Q",
                      help="Parametric mid cut Q / bandwidth")
    eq_g.add_argument("--presence-gain", type=float, default=2.5, metavar="DB",
                      help="Presence boost gain")
    eq_g.add_argument("--presence-freq", type=float, default=4000.0, metavar="HZ",
                      help="Presence boost centre frequency")
    eq_g.add_argument("--presence-q", type=float, default=0.8, metavar="Q",
                      help="Presence boost Q")
    eq_g.add_argument("--air-gain", type=float, default=1.5, metavar="DB",
                      help="High shelf (air) gain")
    eq_g.add_argument("--air-freq", type=float, default=10000.0, metavar="HZ",
                      help="High shelf (air) frequency")

    # Compression
    comp_g = p.add_argument_group("Compression")
    comp_g.add_argument("--comp-threshold", type=float, default=-18.0, metavar="DB",
                        help="Compressor threshold")
    comp_g.add_argument("--comp-ratio", type=float, default=3.0, metavar="X:1",
                        help="Compressor ratio")
    comp_g.add_argument("--comp-attack", type=float, default=8.0, metavar="MS",
                        help="Compressor attack time (ms)")
    comp_g.add_argument("--comp-release", type=float, default=120.0, metavar="MS",
                        help="Compressor release time (ms)")
    # Limiter & loudness
    lim_g = p.add_argument_group("Limiter & loudness")
    lim_g.add_argument("--limiter-threshold", type=float, default=-1.0, metavar="DB",
                       help="True-peak limiter ceiling")
    lim_g.add_argument("--target-lufs", type=float, default=-16.0, metavar="LUFS",
                       help="Integrated loudness target (−16 LUFS = podcast/streaming)")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"Error: file not found — {input_path}")

    stem = input_path.stem
    parent = input_path.parent

    output_path = Path(args.output) if args.output else parent / f"{stem}_mastered.wav"
    spec_path   = (Path(args.spectrogram) if args.spectrogram
                   else parent / f"{stem}_spectrogram.png")

    print(f"\n  input   : {input_path}")
    print(f"  output  : {output_path}")
    if not args.no_spectrogram:
        print(f"  spectro : {spec_path}")
    print()

    # ── load ─────────────────────────────────────────────────────────────────
    print("  [1/6] Loading …")
    audio_in, sr = load_audio(str(input_path))
    duration = audio_in.shape[1] / sr
    print(f"        {audio_in.shape[0]}ch  {sr} Hz  {duration:.1f}s  "
          f"({lufs(audio_in, sr):.1f} LUFS)")

    original = audio_in.copy()

    # ── noise reduction ───────────────────────────────────────────────────────
    if not args.skip_noise_reduction:
        print(f"  [2/6] Noise reduction  "
              f"(sample {args.noise_start}–{args.noise_end}s, "
              f"prop={args.noise_reduction}) …")
        audio = apply_noise_reduction(
            audio_in, sr,
            args.noise_start, args.noise_end,
            args.noise_reduction,
        )
    else:
        print("  [2/6] Noise reduction  SKIPPED")
        audio = audio_in

    # ── EQ + compression + limiting ───────────────────────────────────────────
    print("  [3/6] EQ …")
    print("  [4/6] Compression …")
    print("  [5/6] Limiting …")
    audio = apply_effects_chain(
        audio, sr,
        hp_cutoff=args.hp_cutoff,
        low_shelf_gain=args.low_shelf_gain,
        low_shelf_freq=args.low_shelf_freq,
        mid_cut_gain=args.mid_cut_gain,
        mid_cut_freq=args.mid_cut_freq,
        mid_cut_q=args.mid_cut_q,
        presence_gain=args.presence_gain,
        presence_freq=args.presence_freq,
        presence_q=args.presence_q,
        air_gain=args.air_gain,
        air_freq=args.air_freq,
        comp_threshold=args.comp_threshold,
        comp_ratio=args.comp_ratio,
        comp_attack=args.comp_attack,
        comp_release=args.comp_release,
        limiter_threshold=args.limiter_threshold,
    )

    # ── loudness normalisation ────────────────────────────────────────────────
    print(f"  [6/6] Loudness normalisation → {args.target_lufs} LUFS …")
    audio = normalize_loudness(audio, sr, args.target_lufs)
    final_lufs = lufs(audio, sr)
    print(f"        output loudness: {final_lufs:.1f} LUFS")

    # ── save audio ────────────────────────────────────────────────────────────
    save_audio(str(output_path), audio, sr)
    print(f"\n  Saved: {output_path}")

    # ── spectrograms ──────────────────────────────────────────────────────────
    if not args.no_spectrogram:
        print("  Generating spectrograms …")
        save_spectrograms(original, audio, sr, str(spec_path))
        print(f"  Saved: {spec_path}")

    print("\n  Done.\n")


if __name__ == "__main__":
    main()
