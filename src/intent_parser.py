"""
intent_parser.py

Converts raw natural language user input into structured intent JSON
that the Planner agent can act on.

Layer 1: keyword matching (always runs)
Layer 2: context inference (fills gaps)
Layer 3: LLM fallback (only if confidence < 0.4)

Output keys are aligned with the user_prefs contract expected by
score_song() in recommender.py:
    - target_energy_range  (tuple, not a scalar)
    - target_valence       (not "valence")
    - target_acousticness  (not "acousticness")
    - mood_context         (list, not a single "mood" string)
    - favorite_genre       (str, may be None until caller fills it)
    - likes_acoustic       (bool)
"""

import re
from typing import Optional

# ----------------------------------------------------------
# SIGNAL DICTIONARIES
# ----------------------------------------------------------

ENERGY_SIGNALS = {
    "chill": 0.25, "mellow": 0.2, "calm": 0.2, "relaxed": 0.25,
    "soft": 0.2, "quiet": 0.15, "peaceful": 0.15, "sleepy": 0.1,
    "gentle": 0.2, "easy": 0.3, "low-key": 0.25,
    "upbeat": 0.7, "energetic": 0.8, "hype": 0.9, "pump": 0.85,
    "workout": 0.85, "intense": 0.9, "fast": 0.75, "dance": 0.8,
    "focus": 0.4, "study": 0.35, "work": 0.4, "concentrate": 0.35,
}

VALENCE_SIGNALS = {
    "happy": 0.8, "uplifting": 0.85, "positive": 0.75, "fun": 0.8,
    "sad": 0.2, "melancholy": 0.25, "dark": 0.2, "gloomy": 0.15,
    "bittersweet": 0.45, "nostalgic": 0.4,
    "angry": 0.3, "aggressive": 0.25,
}

MOOD_SIGNALS = {
    "sad": "sad", "melancholy": "sad", "gloomy": "sad",
    "happy": "happy", "joyful": "happy", "fun": "happy",
    "focused": "focused", "study": "focused", "concentrate": "focused",
    "relaxed": "relaxed", "chill": "relaxed", "calm": "relaxed",
    "energetic": "energetic", "hype": "energetic", "pump": "energetic",
    "intense": "intense", "angry": "intense", "aggressive": "intense",
    "late-night": "late-night", "night": "late-night",
}

CONTEXT_SIGNALS = {
    "studying": "studying", "study": "studying", "homework": "studying",
    "working": "working", "office": "working",
    "commute": "commute", "driving": "commute", "road trip": "commute",
    "workout": "workout", "gym": "workout", "run": "workout",
    "sleeping": "sleep", "sleep": "sleep", "falling asleep": "sleep",
    "party": "social", "friends": "social", "dinner": "social",
}

ACOUSTIC_SIGNALS = {
    "acoustic": 0.8, "unplugged": 0.8, "live": 0.7, "raw": 0.75,
    "electronic": 0.1, "synth": 0.1, "edm": 0.05, "produced": 0.15,
}

ARC_SIGNALS = {
    "wind down": "wind-down", "cool down": "wind-down",
    "build up": "build", "warm up": "build", "start slow": "build",
    "same vibe": "flat", "consistent": "flat",
    "mix it up": "peak-valley", "varied": "peak-valley",
}

# Context defaults use a scalar energy value; we convert it to a
# ±0.15 range when building the output so score_song gets a tuple.
CONTEXT_DEFAULTS = {
    "studying":  {"energy": 0.35, "target_valence": 0.55, "arc_type": "flat"},
    "workout":   {"energy": 0.82, "target_valence": 0.70, "arc_type": "build"},
    "sleep":     {"energy": 0.12, "target_valence": 0.45, "arc_type": "wind-down"},
    "social":    {"energy": 0.65, "target_valence": 0.78, "arc_type": "peak-valley"},
    "commute":   {"energy": 0.55, "target_valence": 0.60, "arc_type": "flat"},
    "working":   {"energy": 0.40, "target_valence": 0.55, "arc_type": "flat"},
}

# Energy range half-width applied when converting scalar → range
_ENERGY_HALF_WIDTH = 0.15


def _energy_to_range(energy: float) -> tuple:
    """Convert a scalar energy value to the (min, max) range score_song expects."""
    return (
        max(0.0, energy - _ENERGY_HALF_WIDTH),
        min(1.0, energy + _ENERGY_HALF_WIDTH),
    )


# ----------------------------------------------------------
# CORE PARSER
# ----------------------------------------------------------

def parse_intent(user_input: str) -> dict:
    """
    Main entry point. Takes raw text, returns structured intent dict
    whose keys are directly usable as user_prefs by score_song().

    Returns:
        {
            # --- score_song compatible keys ---
            "target_energy_range": tuple(float, float),
            "target_valence":      float,
            "target_acousticness": float,
            "mood_context":        list[str],   # one or more moods
            "favorite_genre":      None,        # caller must inject from profile
            "likes_acoustic":      bool,

            # --- planner / pipeline metadata ---
            "context":             str or None,
            "arc_type":            str,
            "bpm_range":           tuple or None,
            "duration_minutes":    int or None,
            "ambiguity":           bool,
            "confidence":          float,
        }
    """
    text = user_input.lower().strip()
    intent = _keyword_pass(text)
    intent = _fill_gaps_from_context(intent)
    intent = _detect_conflicts(intent)
    return intent


def _keyword_pass(text: str) -> dict:
    """Layer 1: scan for known signal words."""

    # Internal scalar energy; converted to range at the end
    _energy_scalar = None

    intent = {
        # score_song keys
        "target_energy_range": None,    # set at end of this function
        "target_valence": None,
        "target_acousticness": None,
        "mood_context": [],
        "favorite_genre": None,         # must be injected by caller from user profile
        "likes_acoustic": False,

        # pipeline metadata
        "context": None,
        "arc_type": "flat",
        "bpm_range": None,
        "duration_minutes": None,
        "ambiguity": False,
        "confidence": 0.0,
    }

    signals_found = 0

    # Energy (store scalar; convert to range at the end)
    for word, value in ENERGY_SIGNALS.items():
        if word in text:
            _energy_scalar = value
            signals_found += 1
            break

    # Valence → target_valence
    for word, value in VALENCE_SIGNALS.items():
        if word in text:
            intent["target_valence"] = value
            signals_found += 1
            break

    # Mood → mood_context list (single entry; layer 2 may append more)
    for word, mood in MOOD_SIGNALS.items():
        if word in text:
            if mood not in intent["mood_context"]:
                intent["mood_context"].append(mood)
            signals_found += 1
            break

    # Context
    for phrase, ctx in CONTEXT_SIGNALS.items():
        if phrase in text:
            intent["context"] = ctx
            signals_found += 1
            break

    # Acousticness → target_acousticness + likes_acoustic flag
    for word, value in ACOUSTIC_SIGNALS.items():
        if word in text:
            intent["target_acousticness"] = value
            intent["likes_acoustic"] = value >= 0.7   # high value = acoustic preference
            signals_found += 1
            break

    # Arc
    for phrase, arc in ARC_SIGNALS.items():
        if phrase in text:
            intent["arc_type"] = arc
            signals_found += 1
            break

    # BPM: e.g. "around 120 bpm"
    bpm_match = re.search(r'(\d{2,3})\s*bpm', text)
    if bpm_match:
        bpm = int(bpm_match.group(1))
        intent["bpm_range"] = (bpm - 10, bpm + 10)
        signals_found += 1

    # Duration: e.g. "30 minutes" or "1 hour"
    dur_match = re.search(r'(\d+)\s*(min|minute|hour)', text)
    if dur_match:
        n = int(dur_match.group(1))
        intent["duration_minutes"] = n * 60 if "hour" in dur_match.group(2) else n
        signals_found += 1

    # Convert scalar energy to range now that all signals are read
    if _energy_scalar is not None:
        intent["target_energy_range"] = _energy_to_range(_energy_scalar)

    # Confidence: keyword-only cap is 0.85
    intent["confidence"] = min(0.85, signals_found * 0.2)

    return intent


def _fill_gaps_from_context(intent: dict) -> dict:
    """Layer 2: infer missing values from context if available."""

    ctx = intent.get("context")
    if ctx and ctx in CONTEXT_DEFAULTS:
        defaults = CONTEXT_DEFAULTS[ctx]

        # Energy range
        if intent["target_energy_range"] is None and "energy" in defaults:
            intent["target_energy_range"] = _energy_to_range(defaults["energy"])
            intent["confidence"] = min(0.95, intent["confidence"] + 0.05)

        # Valence
        if intent["target_valence"] is None and "target_valence" in defaults:
            intent["target_valence"] = defaults["target_valence"]
            intent["confidence"] = min(0.95, intent["confidence"] + 0.05)

        # Arc
        if intent["arc_type"] == "flat" and "arc_type" in defaults:
            intent["arc_type"] = defaults["arc_type"]

    # Hard fallbacks for anything still None
    if intent["target_energy_range"] is None:
        intent["target_energy_range"] = _energy_to_range(0.5)

    if intent["target_valence"] is None:
        intent["target_valence"] = 0.5

    if intent["target_acousticness"] is None:
        intent["target_acousticness"] = 0.5

    # mood_context fallback: empty list is valid (evaluator handles it)
    # but score_song needs at least something to compare against
    # leave it empty — planner can decide whether to relax

    return intent


def _detect_conflicts(intent: dict) -> dict:
    """
    Detects meaningful conflicts in parsed intent.
    Sets ambiguity=True and logs the conflict type.

    Current checks:
    - sad mood + high energy (e.g. "sad but energetic")
    - acoustic preference + high energy (e.g. "acoustic party")
    """

    conflicts = []

    energy_mid = sum(intent["target_energy_range"]) / 2

    if "sad" in intent["mood_context"] and energy_mid > 0.65:
        conflicts.append("sad_high_energy")

    if intent["target_acousticness"] is not None:
        if intent["target_acousticness"] > 0.7 and energy_mid > 0.75:
            conflicts.append("acoustic_high_energy")

    if conflicts:
        intent["ambiguity"] = True
        intent["conflicts"] = conflicts
    else:
        intent["conflicts"] = []

    return intent


if __name__ == "__main__":
    tests = [
        "I want something sad but still energetic for studying",
        "chill lofi for late night focus",
        "acoustic workout music",
        "something dark and intense",
        "music for driving",
    ]
    for t in tests:
        print(f"\nInput: '{t}'")
        result = parse_intent(t)
        for k, v in result.items():
            print(f"  {k}: {v}")