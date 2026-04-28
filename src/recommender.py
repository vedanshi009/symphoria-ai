#File: src/recommender.py
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
import csv


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    Object-oriented recommender used by tests and agent pipeline.
    """

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _normalize_user(self, user):
        """
        Allows both dictionary user profiles and UserProfile objects.
        """
        if isinstance(user, dict):
            return user
        if isinstance(user, UserProfile):
            return user.__dict__
        return None

    def recommend(self, user, k: int = 5) -> List[Song]:
        """
        Scores all songs and returns top-k results.
        """

        scored = []

        user_dict = self._normalize_user(user)

        # If already a dict (agent pipeline)
        if isinstance(user_dict, dict):
            user_prefs = user_dict

        # If coming from UserProfile (unit tests)
        else:
            user_prefs = {
                "favorite_genre": user.favorite_genre,
                "mood_context": [user.favorite_mood],
                "target_energy_range": (
                    max(0.0, user.target_energy - 0.15),
                    min(1.0, user.target_energy + 0.15)
                ),
                "target_valence": 0.5,
                "target_acousticness": 0.5,
                "likes_acoustic": user.likes_acoustic
            }

        # Score every song
        for song in self.songs:
            # Convert Song → Dict (since score_song expects dict)
            song_dict = song if isinstance(song, dict) else song.__dict__

            score, _ = score_song(user_prefs, song_dict)
            scored.append((song, score))

        # Sort by score (descending)
        ranked = sorted(scored, key=lambda x: x[1], reverse=True)

        return [song for song, _ in ranked[:k]]


def load_songs(csv_path: str) -> List[Dict[str, Any]]:
    """
    Loads songs from CSV and prepares them for the scoring engine.

    Converts all numeric audio features into proper types so
    scoring math can be applied directly.
    """

    print(f"Loading songs from {csv_path}...")

    songs: List[Dict[str, Any]] = []

    # The system uses these as FLOAT features for similarity scoring
    FLOAT_FIELDS = {
        "energy",
        "valence",
        "danceability",
        "acousticness"
    }

    # BPM is used for tempo penalty logic → integer preferred
    INT_FIELDS = {
        "tempo_bpm"
    }

    # Everything else stays categorical/string
    try:
        with open(csv_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                song: Dict[str, Any] = {}

                for key, value in row.items():

                    if value is None:
                        song[key] = None
                        continue

                    if isinstance(value, str):
                        value = value.strip()

                    # ID → int (useful for tracking but not scoring)
                    if key == "id":
                        try:
                            song[key] = int(value)
                        except ValueError:
                            song[key] = None

                    # Float features → core of vibe similarity layer
                    elif key in FLOAT_FIELDS:
                        try:
                            song[key] = float(value)
                        except ValueError:
                            song[key] = None

                    # BPM → integer for tempo penalty logic
                    elif key in INT_FIELDS:
                        try:
                            song[key] = int(float(value))
                        except ValueError:
                            song[key] = None

                    # Strings → used for mood, genre, artist logic
                    else:
                        song[key] = value

                # --------------------------------------------------
                # Row validation: drop any song that is missing a
                # field score_song() will do math on.  A None in
                # energy/valence/danceability/acousticness/tempo_bpm
                # causes a TypeError inside range_distance(); better
                # to skip the row loudly than crash silently later.
                # --------------------------------------------------
                REQUIRED_NUMERIC = {
                    "energy", "valence", "danceability",
                    "acousticness", "tempo_bpm"
                }
                if any(song.get(f) is None for f in REQUIRED_NUMERIC):
                    missing = [f for f in REQUIRED_NUMERIC if song.get(f) is None]
                    label = song.get("title") or song.get("id") or "unknown"
                    print(f"  ⚠️  Skipping '{label}' — missing/unparseable fields: {missing}")
                    continue

                songs.append(song)

    except FileNotFoundError:
        print(f"File not found: {csv_path}")
    except Exception as e:
        print(f"Error loading songs: {e}")

    print(f"Loaded {len(songs)} songs 🎵 ready for scoring engine")
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.

    Returns:
        (score, reasons)
    """

    reasons: List[str] = []
    score = 0.0

    # -----------------------------
    # CONSTANTS (Algorithm Recipe)
    # -----------------------------
    MOOD_FAMILIES = {
        "chill": {"relaxed", "focused", "late-night"},
        "happy": {"energetic"},
        "moody": {"intense"},
    }

    GENRE_NEIGHBORS = {
        "lofi": {"ambient", "bedroom pop"},
        "pop": {"indie pop"},
        "rock": {"indie rock"},
    }

    # Helper: find mood family
    def get_mood_family(mood: str):
        for family, moods in MOOD_FAMILIES.items():
            if mood in moods:
                return family
        return None

    # -----------------------------
    # USER INPUT
    # -----------------------------
    energy_min, energy_max = user_prefs.get("target_energy_range", (0.4, 0.6))
    target_valence = user_prefs.get("target_valence", 0.5)
    target_acousticness = user_prefs.get("target_acousticness", 0.5)
    mood_context = set(user_prefs.get("mood_context", []))
    favorite_genre = user_prefs.get("favorite_genre", "")
    likes_acoustic = user_prefs.get("likes_acoustic", False)

    # ==========================================================
    # LAYER 1 — VIBE SIMILARITY (MAX 0.50)
    # ==========================================================

    def range_distance(value, low, high):
        if low <= value <= high:
            return 0.0
        if value < low:
            return low - value
        return value - high

    # ---- Energy (0.22)
    energy_distance = range_distance(song["energy"], energy_min, energy_max)
    energy_similarity = 0.22 * (1 - min(1, energy_distance))
    score += energy_similarity
    reasons.append(f"energy alignment (+{energy_similarity:.2f})")

    # ---- Acousticness (0.18)
    acoustic_distance = abs(song["acousticness"] - target_acousticness)
    acoustic_similarity = 0.18 * (1 - min(1, acoustic_distance))
    score += acoustic_similarity
    reasons.append(f"acoustic texture match (+{acoustic_similarity:.2f})")

    # Acoustic preference boost
    if likes_acoustic and song["acousticness"] > 0.6:
        score += 0.03
        reasons.append("acoustic preference boost (+0.03)")

    # ---- Valence (0.10)
    valence_distance = abs(song["valence"] - target_valence)
    valence_similarity = 0.10 * (1 - min(1, valence_distance))
    score += valence_similarity
    reasons.append(f"emotional tone similarity (+{valence_similarity:.2f})")

    # ==========================================================
    # LAYER 2 — MOOD MATCH (MAX 0.25)
    # ==========================================================

    song_mood = song["mood"]

    if song_mood in mood_context:
        score += 0.25
        reasons.append("direct mood match (+0.25)")
    else:
        # Family-to-family comparison
        song_family = get_mood_family(song_mood)
        user_families = {get_mood_family(m) for m in mood_context}

        if song_family and song_family in user_families:
            score += 0.12
            reasons.append("mood family match (+0.12)")

    # ==========================================================
    # LAYER 3 — GENRE CONTEXT (MAX 0.15)
    # ==========================================================

    song_genre = song["genre"]

    if song_genre == favorite_genre:
        score += 0.10
        reasons.append("favorite genre match (+0.10)")
    elif favorite_genre in GENRE_NEIGHBORS and \
         song_genre in GENRE_NEIGHBORS[favorite_genre]:
        score += 0.05
        reasons.append("adjacent genre match (+0.05)")

    # ==========================================================
    # LAYER 4 — SECONDARY VIBE REFINEMENT (MAX 0.10)
    # ==========================================================

    expected_energy = (energy_min + energy_max) / 2
    expected_danceability = 0.3 + (expected_energy * 0.6)

    dance_distance = abs(expected_danceability - song["danceability"])
    dance_score = 0.10 * (1 - min(1, dance_distance))

    score += dance_score
    reasons.append(f"rhythm alignment (+{dance_score:.2f})")


    # ==========================================================
    # PENALTIES (MULTIPLICATIVE)
    # ==========================================================

    # Smooth tempo penalty instead of binary rule (fix #7)
    expected_bpm = 60 + (expected_energy * 100)
    tempo_diff = abs(song["tempo_bpm"] - expected_bpm)

    tempo_penalty = max(0.85, 1 - (tempo_diff / 200))
    if tempo_penalty < 1:
        score *= tempo_penalty
        reasons.append(f"tempo consistency penalty (×{tempo_penalty:.2f})")

    # ==========================================================
    # SCORE NORMALIZATION 
    # ==========================================================
    # Expands separation between good and great songs

    score = score ** 1.15

    # Clamp final result
    score = max(0.0, min(1.0, score))

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 30) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    Steps:
    1. Score every song using score_song()
    2. Attach score + reasons
    3. Sort songs by score (descending)
    4. Return top-k results

    Returns:
        List of (song_dict, score, explanation)
    """
    scored_songs = []

    # ----------------------------------------------------------
    # 1. SCORE EVERY SONG 
    # ----------------------------------------------------------
    for song in songs:
        score, reasons = score_song(user_prefs, song)

        scored_songs.append((
            song,
            score,
            reasons  
        ))

    # ----------------------------------------------------------
    # 2. SORT BY SCORE (DESCENDING)
    # ----------------------------------------------------------

    ranked_songs = sorted(
        scored_songs,
        key=lambda x: x[1],
        reverse=True
    )

    # ----------------------------------------------------------
    # 3. RETURN TOP-K
    # ----------------------------------------------------------
    return ranked_songs[:k]