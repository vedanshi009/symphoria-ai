# src/evaluator_agent.py

from typing import List, Dict, Any, Union
from collections import defaultdict
from src.planner_agent import RecommendationPlan


class EvaluatorAgent:
    """
    Evaluates how good a generated playlist is.

    Think of this as a "grading system" that checks:
    - Did we follow artist limits?
    - Does energy flow feel smooth?
    - Does it match user mood?
    - Is the output logically valid?

    Returns a report used for retry/improvement.

    Songs arrive as plain dicts from PlaylistBuilder (which receives them
    from recommend_songs() in recommender.py). All field access therefore
    uses dict.get() rather than attribute access.
    """

    def _get(self, song: Union[Dict, Any], key: str, default=None):
        """Safe field reader — works for both dicts and Song dataclass objects."""
        if isinstance(song, dict):
            return song.get(key, default)
        return getattr(song, key, default)

    def evaluate(
        self,
        playlist: List[Union[Dict, Any]],
        plan: RecommendationPlan,
        user_prefs: Dict[str, Any],
    ) -> Dict[str, Any]:

        issues: List[str] = []

        # If playlist is empty, nothing to evaluate
        if not playlist:
            return {
                "pass": False,
                "score": 0.0,
                "diversity_score": 0.0,
                "energy_variance": 0.0,
                "mood_match_score": 0.0,
                "issues": ["empty playlist"],
                "recommendation": "regenerate playlist with relaxed constraints",
            }

        # ===================================================
        # 1. DIVERSITY CHECK (avoid same artist spam)
        # ===================================================
        artist_counts = defaultdict(int)

        for song in playlist:
            artist = self._get(song, "artist", "unknown")
            artist_counts[artist] += 1

        total_songs = len(playlist)
        unique_artists = len(artist_counts)

        # measure how varied the playlist is
        diversity_score = unique_artists / total_songs

        # penalty if any artist exceeds allowed limit
        repetition_penalty = 0
        for artist, count in artist_counts.items():
            if count > plan.max_artists:
                repetition_penalty += (count - plan.max_artists)
                issues.append(
                    f"{artist} exceeds max_artists limit ({count})"
                )

        # reduce diversity score if repetition is too high
        diversity_score = max(0.0, diversity_score - (0.1 * repetition_penalty))

        # ===================================================
        # 2. ENERGY VARIANCE (is playlist too flat or chaotic?)
        # ===================================================
        energies = [self._get(song, "energy", 0.5) for song in playlist]

        mean_energy = sum(energies) / len(energies)

        # variance = how spread out energy values are
        variance = sum((e - mean_energy) ** 2 for e in energies) / len(energies)

        energy_variance = variance 

        # interpret variance quality
        if energy_variance < 0.005:
            issues.append("energy is too flat (boring playlist)")
        elif energy_variance > 0.08:
            issues.append("energy is too chaotic (no smooth flow)")

        # we want a "balanced" variance around a target value
        target_var = 0.04
        energy_score = 1.0 - min(
            1.0, abs(energy_variance - target_var) / 0.1
        )

        # ===================================================
        # 3. MOOD MATCHING (does playlist match user intent?)
        # ===================================================
        mood_context = set(user_prefs.get("mood_context", []))

        if not mood_context:
            # no info means neutral score
            mood_match_score = 0.5
            issues.append("no mood context provided")
        else:
            matches = 0

            # count how many songs match desired mood
            for song in playlist:
                song_mood = self._get(song, "mood")

                if song_mood in mood_context:
                    matches += 1
                elif any(song_mood in m for m in mood_context):
                    matches += 0.5

            mood_match_score = matches / len(playlist)

            if mood_match_score < 0.5:
                issues.append("playlist does not match user mood well")

        # ===================================================
        # 4. CONSTRAINT CHECKS (final safety validation)
        # ===================================================
        constraint_issues = []

        # ensure artist constraints are not broken
        if any(count > plan.max_artists for count in artist_counts.values()):
            constraint_issues.append("max_artists constraint violated")

        issues.extend(constraint_issues)

        # ===================================================
        # 5. FINAL SCORE (weighted grading system)
        # ===================================================
        score = (
            0.4 * diversity_score +
            0.3 * energy_score +
            0.3 * mood_match_score
        )

        # clamp score between 0 and 1
        score = max(0.0, min(1.0, score))

        # ===================================================
        # 6. PASS / FAIL DECISION
        # ===================================================
        passed = score >= 0.7 and len(constraint_issues) == 0

        recommendation = (
            "playlist looks good"
            if passed
            else "retry with adjusted constraints or improved diversity"
        )

        return {
            "pass": passed,
            "score": score,
            "diversity_score": diversity_score,
            "energy_variance": energy_variance,
            "mood_match_score": mood_match_score,
            "issues": issues,
            "recommendation": recommendation,
        }