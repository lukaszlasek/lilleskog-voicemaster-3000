"""
presets.py — Recording type presets for Voice Master.

Each preset configures the full effects chain. Keys map 1:1 to
process_audio() keyword arguments plus display-only fields.
"""

PRESETS: dict[str, dict] = {
    "studio": {
        # display
        "label":       "Studio mic",
        "description": "Clean close-mic, quiet room",
        "nr_label":    "No NR",
        # noise reduction
        "skip_noise_reduction": True,
        "noise_reduction": 0.0,
        "noise_start":     0.0,
        "noise_end":       0.5,
        # EQ
        "hp_cutoff":       80.0,
        "low_shelf_gain": -2.0,   "low_shelf_freq": 200.0,
        "mid_cut_gain":   -2.0,   "mid_cut_freq":   350.0,  "mid_cut_q": 1.2,
        "presence_gain":   2.0,   "presence_freq": 5000.0,  "presence_q": 0.8,
        "air_gain":        2.0,   "air_freq":     12000.0,
        # dynamics
        "comp_threshold": -18.0,  "comp_ratio": 3.0,
        "comp_attack":      8.0,  "comp_release": 120.0,
        "limiter_threshold": -1.0,
        # loudness
        "target_lufs": -16.0,
    },

    "headset": {
        "label":       "Headset / Earbuds",
        "description": "Close mic with background hiss",
        "nr_label":    "Moderate NR",
        "skip_noise_reduction": False,
        "noise_reduction": 0.65,
        "noise_start":     0.0,
        "noise_end":       0.5,
        "hp_cutoff":       80.0,
        "low_shelf_gain": -4.0,   "low_shelf_freq": 200.0,
        "mid_cut_gain":   -5.0,   "mid_cut_freq":   500.0,  "mid_cut_q": 1.0,
        "presence_gain":   3.5,   "presence_freq": 3500.0,  "presence_q": 0.8,
        "air_gain":        1.5,   "air_freq":     10000.0,
        "comp_threshold": -20.0,  "comp_ratio": 3.5,
        "comp_attack":      6.0,  "comp_release": 100.0,
        "limiter_threshold": -1.0,
        "target_lufs": -16.0,
    },

    "room": {
        "label":       "Room recording",
        "description": "One person, typical indoor space",
        "nr_label":    "Low NR",
        "skip_noise_reduction": False,
        "noise_reduction": 0.40,
        "noise_start":     0.0,
        "noise_end":       0.5,
        "hp_cutoff":       80.0,
        "low_shelf_gain": -3.0,   "low_shelf_freq": 200.0,
        "mid_cut_gain":   -3.0,   "mid_cut_freq":   400.0,  "mid_cut_q": 1.0,
        "presence_gain":   2.5,   "presence_freq": 4000.0,  "presence_q": 0.8,
        "air_gain":        1.5,   "air_freq":     10000.0,
        "comp_threshold": -18.0,  "comp_ratio": 3.0,
        "comp_attack":      8.0,  "comp_release": 120.0,
        "limiter_threshold": -1.0,
        "target_lufs": -16.0,
    },

    "interview": {
        "label":       "Interview",
        "description": "Two people, one mic or separate mics",
        "nr_label":    "Low NR",
        "skip_noise_reduction": False,
        "noise_reduction": 0.50,
        "noise_start":     0.0,
        "noise_end":       0.5,
        "hp_cutoff":       80.0,
        "low_shelf_gain": -3.0,   "low_shelf_freq": 180.0,
        "mid_cut_gain":   -2.5,   "mid_cut_freq":   380.0,  "mid_cut_q": 0.9,
        "presence_gain":   2.0,   "presence_freq": 4000.0,  "presence_q": 0.8,
        "air_gain":        1.5,   "air_freq":     10000.0,
        "comp_threshold": -22.0,  "comp_ratio": 2.5,
        "comp_attack":     10.0,  "comp_release": 150.0,
        "limiter_threshold": -1.0,
        "target_lufs": -16.0,
    },

    "multi": {
        "label":       "Multiple speakers",
        "description": "Panel, roundtable, group discussion",
        "nr_label":    "Moderate NR",
        "skip_noise_reduction": False,
        "noise_reduction": 0.55,
        "noise_start":     0.0,
        "noise_end":       0.5,
        "hp_cutoff":       80.0,
        "low_shelf_gain": -2.0,   "low_shelf_freq": 180.0,
        "mid_cut_gain":   -2.0,   "mid_cut_freq":   400.0,  "mid_cut_q": 0.8,
        "presence_gain":   2.0,   "presence_freq": 4000.0,  "presence_q": 0.7,
        "air_gain":        1.0,   "air_freq":     10000.0,
        "comp_threshold": -22.0,  "comp_ratio": 2.0,
        "comp_attack":     12.0,  "comp_release": 180.0,
        "limiter_threshold": -1.0,
        "target_lufs": -16.0,
    },

    "zoom": {
        "label":       "Zoom / Remote call",
        "description": "Video call recording, codec-compressed",
        "nr_label":    "Low NR",
        "skip_noise_reduction": False,
        "noise_reduction": 0.25,
        "noise_start":     0.0,
        "noise_end":       0.5,
        "hp_cutoff":       80.0,
        "low_shelf_gain": -1.5,   "low_shelf_freq": 200.0,
        "mid_cut_gain":   -2.0,   "mid_cut_freq":   400.0,  "mid_cut_q": 0.8,
        "presence_gain":   4.0,   "presence_freq": 3500.0,  "presence_q": 0.7,
        "air_gain":        3.5,   "air_freq":      8000.0,
        "comp_threshold": -24.0,  "comp_ratio": 2.0,
        "comp_attack":     12.0,  "comp_release": 160.0,
        "limiter_threshold": -1.0,
        "target_lufs": -16.0,
    },

    "phone": {
        "label":       "Phone / Mobile",
        "description": "Telephony recording, narrow bandwidth",
        "nr_label":    "High NR",
        "skip_noise_reduction": False,
        "noise_reduction": 0.80,
        "noise_start":     0.0,
        "noise_end":       0.5,
        "hp_cutoff":      120.0,
        "low_shelf_gain": -6.0,   "low_shelf_freq": 300.0,
        "mid_cut_gain":   -3.0,   "mid_cut_freq":   500.0,  "mid_cut_q": 1.0,
        "presence_gain":   4.0,   "presence_freq": 3000.0,  "presence_q": 0.7,
        "air_gain":        2.5,   "air_freq":      7000.0,
        "comp_threshold": -18.0,  "comp_ratio": 4.0,
        "comp_attack":      5.0,  "comp_release":  80.0,
        "limiter_threshold": -1.0,
        "target_lufs": -16.0,
    },

    "outdoor": {
        "label":       "Outdoor",
        "description": "Outside recording, wind and ambient noise",
        "nr_label":    "High NR",
        "skip_noise_reduction": False,
        "noise_reduction": 0.88,
        "noise_start":     0.0,
        "noise_end":       0.5,
        "hp_cutoff":      150.0,
        "low_shelf_gain": -7.0,   "low_shelf_freq": 300.0,
        "mid_cut_gain":   -3.0,   "mid_cut_freq":   450.0,  "mid_cut_q": 1.0,
        "presence_gain":   4.0,   "presence_freq": 4000.0,  "presence_q": 0.7,
        "air_gain":        2.0,   "air_freq":     10000.0,
        "comp_threshold": -18.0,  "comp_ratio": 3.5,
        "comp_attack":      7.0,  "comp_release": 100.0,
        "limiter_threshold": -1.0,
        "target_lufs": -16.0,
    },
}

DEFAULT_PRESET = "room"

# Keys that map directly to process_audio() kwargs
AUDIO_KEYS = {
    "skip_noise_reduction", "noise_reduction", "noise_start", "noise_end",
    "hp_cutoff", "low_shelf_gain", "low_shelf_freq",
    "mid_cut_gain", "mid_cut_freq", "mid_cut_q",
    "presence_gain", "presence_freq", "presence_q",
    "air_gain", "air_freq",
    "comp_threshold", "comp_ratio", "comp_attack", "comp_release",
    "limiter_threshold", "target_lufs",
}


def audio_params(preset_name: str) -> dict:
    """Return only the kwargs needed by process_audio() for a given preset."""
    p = PRESETS.get(preset_name, PRESETS[DEFAULT_PRESET])
    return {k: v for k, v in p.items() if k in AUDIO_KEYS}
