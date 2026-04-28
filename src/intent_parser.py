import re
from typing import Optional

ENERGY_SIGNALS = {
    "chill": 0.25, "mellow": 0.2, "calm": 0.2, "relaxed": 0.25,
    "focus": 0.4, "study": 0.35,
    "upbeat": 0.7, "energetic": 0.8, "hype": 0.9,
}

VALENCE_SIGNALS = {
    "happy": 0.8, "sad": 0.2, "dark": 0.2,
}

MOOD_SIGNALS = {
    "chill": "chill",
    "relaxed": "relaxed",
    "focus": "focused",
    "study": "focused",
    "happy": "happy",
    "sad": "sad",
    "energetic": "energetic",
    "hype": "energetic",
    "gym": "energetic",
    "party": "energetic",
}

GENRE_SIGNALS = {
    "lofi": ["lofi", "lo-fi"],
    "pop": ["pop"],
    "rock": ["rock"],
    "edm": ["edm", "dance"],
}

ACOUSTIC_SIGNALS = {
    "acoustic": 0.8,
    "electronic": 0.2,
}


def _energy_to_range(e: float):
    return (round(max(0.0, e - 0.15), 2), round(min(1.0, e + 0.15), 2))


def parse_intent(text: str) -> dict:
    text = text.lower()

    # ---------------- defaults ----------------
    # Ensuring all keys required by score_song are initialized
    intent = {
        "target_energy_range": (0.4, 0.6),
        "target_valence": 0.5,
        "target_acousticness": 0.5,
        "mood_context": [],
        "favorite_genre": None,
        "likes_acoustic": False,
        "ambiguity": False,
        "confidence": 0.0,
    }

    signals = 0

    # ---------------- genre detection ----------------
    for genre, keywords in GENRE_SIGNALS.items():
        if any(k in text for k in keywords):
            intent["favorite_genre"] = genre
            signals += 1
            break  # Stop at first genre match to keep favorite_genre a single string

    # ---------------- mood ----------------
    for k, mood in MOOD_SIGNALS.items():
        if k in text and mood not in intent["mood_context"]:
            intent["mood_context"].append(mood)
            signals += 1

    # ---------------- energy ----------------
    energy_val = None
    for k, v in ENERGY_SIGNALS.items():
        if k in text:
            energy_val = v
            signals += 1
            break

    if energy_val is not None:
        intent["target_energy_range"] = _energy_to_range(energy_val)

    # ---------------- valence ----------------
    for k, v in VALENCE_SIGNALS.items():
        if k in text:
            intent["target_valence"] = v
            signals += 1
            break

    # ---------------- acoustic ----------------
    for k, v in ACOUSTIC_SIGNALS.items():
        if k in text:
            intent["target_acousticness"] = v
            intent["likes_acoustic"] = v > 0.7
            signals += 1
            break

    # ---------------- confidence ----------------
    # Scale confidence based on signals found, capped at 0.95
    intent["confidence"] = min(0.95, signals * 0.25)

    # ---------------- ambiguity ----------------
    # Check for conflicting signals (e.g., "sad" mood with high energy requirements)
    if "sad" in intent["mood_context"] and intent["target_energy_range"][1] > 0.7:
        intent["ambiguity"] = True
    
    # Also mark as ambiguous if no signals were found at all
    if signals == 0:
        intent["ambiguity"] = True

    return intent