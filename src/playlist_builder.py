# src/playlist_builder.py

from typing import List, Tuple, Dict, Any
from collections import defaultdict
from src.planner_agent import RecommendationPlan


class PlaylistBuilder:
    """
    Builds a playlist from already-ranked songs.

    What this class does:
    - picks songs greedily (top-down from ranked list)
    - limits repeated artists
    - optionally reshapes energy flow (low → high pattern)

    Important: does NOT change ranking scores.

    Input: ranked_songs is List[Tuple[Dict, float, List[str]]] as produced
           by recommend_songs() in recommender.py — each element is
           (song_dict, score, reasons).
    """

    def build(
        self,
        ranked_songs: List[Tuple[Dict[str, Any], float, Any]],
        plan: RecommendationPlan,
        k: int = 12,
    ) -> List[Dict[str, Any]]:

        selected: List[Dict[str, Any]] = []
        artist_count = defaultdict(int)

        # Helper: safely read a field from a song dict
        def get_field(song: Dict, key: str, default=None):
            return song.get(key, default)

        # STEP 1: unpack tuples and pick songs while enforcing artist limits
        for item in ranked_songs:
            # ranked_songs elements are (song_dict, score, reasons)
            song = item[0]

            artist = get_field(song, "artist")

            # skip if this artist already appears too many times
            if artist_count[artist] >= plan.max_artists:
                continue

            selected.append(song)
            artist_count[artist] += 1

            # stop once we have enough songs
            if len(selected) >= k:
                break

        # STEP 1B: fallback if constraints were too strict
        # ensures we still return k songs even if diversity blocks too many
        if len(selected) < k:
            for item in ranked_songs:
                song = item[0]
                if song not in selected:
                    selected.append(song)
                if len(selected) >= k:
                    break

        # STEP 2: optional energy curve shaping
        # this changes ORDER only, not which songs are chosen
        if plan.energy_curve and len(selected) > 2:

            # helper: extract energy value safely from dict
            def energy(song: Dict) -> float:
                return song.get("energy", 0.0)

            # sort songs from low energy to high energy
            sorted_songs = sorted(selected, key=energy)

            n = len(sorted_songs)

            # split into 3 energy groups
            low_band = sorted_songs[: n // 3]
            mid_band = sorted_songs[n // 3 : 2 * n // 3]
            high_band = sorted_songs[2 * n // 3 :]

            # build playlist with energy flow pattern
            # idea: smooth listening experience instead of random order
            pattern = []
            i = j = k_idx = 0

            while len(pattern) < n:

                if i < len(low_band):
                    pattern.append(low_band[i])
                    i += 1

                if len(pattern) >= n:
                    break

                if j < len(mid_band):
                    pattern.append(mid_band[j])
                    j += 1

                if len(pattern) >= n:
                    break

                if k_idx < len(high_band):
                    pattern.append(high_band[k_idx])
                    k_idx += 1

            selected = pattern

        # STEP 3: final safety trim (never exceed k)
        return selected[:k]