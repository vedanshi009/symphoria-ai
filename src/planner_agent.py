"""
Planner agent that converts structured intent into a recommendation strategy.
It decides how the system should search, not which songs to pick.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class RecommendationPlan:
    """
    Strategy produced by the planner and consumed by downstream components.
    """

    mode: str
    weights: Dict[str, float]
    diversity_required: bool
    energy_curve: bool
    max_artists: int
    adjusted_user_prefs: Dict[str, Any]
    confidence: float
    reason: str
    energy_curve_style: str = "none"  # "low_to_high" | "high_to_low" | "none"


class PlannerAgent:
    """
    Chooses recommendation strategy based on intent clarity and energy signals.
    """

    def __init__(self):
        self.ambiguity_threshold = 0.4

    def create_plan(
        self,
        intent: Dict[str, Any],
        user_prefs: Dict[str, Any]
    ) -> RecommendationPlan:

        confidence = intent.get("confidence", 1.0)
        ambiguity = intent.get("ambiguity", False)

        if confidence < self.ambiguity_threshold or ambiguity:
            return self._balanced_plan(user_prefs, confidence)

        energy = intent.get("energy", 0.5)

        if energy > 0.7:
            return self._high_energy_plan(user_prefs, confidence)

        return self._focused_plan(user_prefs, confidence)

    def _balanced_plan(self, user_prefs: Dict[str, Any],
                       confidence: float) -> RecommendationPlan:

        adjusted = dict(user_prefs)

        low, high = adjusted.get("target_energy_range", (0.4, 0.6))
        adjusted["target_energy_range"] = (
            max(0.0, low - 0.1),
            min(1.0, high + 0.1),
        )

        return RecommendationPlan(
            mode="balanced",
            weights={
                "mood": 0.4,
                "energy": 0.3,
                "genre": 0.3,
            },
            diversity_required=True,
            energy_curve=True,
            max_artists=2,
            adjusted_user_prefs=adjusted,
            confidence=confidence,
            reason="intent ambiguity detected; broaden exploration without altering scoring logic",
        )

    def _focused_plan(self, user_prefs: Dict[str, Any],
                      confidence: float) -> RecommendationPlan:

        return RecommendationPlan(
            mode="focused",
            weights={
                "mood": 0.6,
                "energy": 0.25,
                "genre": 0.15,
            },
            diversity_required=False,
            energy_curve=True,
            max_artists=1,
            adjusted_user_prefs=dict(user_prefs),
            confidence=confidence,
            reason="high confidence intent; prioritize direct matching",
        )

    def _high_energy_plan(self, user_prefs: Dict[str, Any],
                          confidence: float) -> RecommendationPlan:

        adjusted = dict(user_prefs)

        # Soft control signal for scoring engine
        adjusted["acoustic_bias_strength"] = 0.5

        return RecommendationPlan(
            mode="exploration",
            weights={
                "mood": 0.3,
                "energy": 0.5,
                "genre": 0.2,
            },
            diversity_required=True,
            energy_curve=False,
            max_artists=3,
            adjusted_user_prefs=adjusted,
            confidence=confidence,
            reason="high energy intent; reduce acoustic dominance without mutating user preferences",
        )