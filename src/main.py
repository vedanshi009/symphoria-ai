"""
File: src/main.py
Agentic Music Recommender Runner

Pipeline order:
  parse_intent → PlannerAgent → recommend_songs → PlaylistBuilder
      → EvaluatorAgent (loop) → CuratorAgent → print output

With 90 songs in the dataset:
  - Score all 90 every iteration (no pre-filtering ceiling)
  - PlaylistBuilder selects k=10 with artist diversity constraints
  - Up to 3 self-correction iterations before curator runs
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.recommender import load_songs, recommend_songs
from src.intent_parser import parse_intent
from src.planner_agent import PlannerAgent
from src.playlist_builder import PlaylistBuilder
from src.evaluator_agent import EvaluatorAgent
from src.curator_agent import CuratorAgent

# ------------------------------------------------------------------
# K VALUES  (90-song dataset)
#
# SCORE_K  = how many scored songs to keep before builder sees them
#            → use all songs (None = no ceiling); the builder's own
#              artist-limit + greedy selection does the real trimming
#
# PLAYLIST_K = final playlist length
#            → 10 songs is enough to show diversity, energy arc, and
#              mood matching without padding with mediocre picks
# ------------------------------------------------------------------
SCORE_K    = 90   # pass everything scored to the builder
PLAYLIST_K = 10   # final playlist length


def _build_user_prefs(intent: dict, genre_hint: str = "lofi") -> dict:
    """
    Merges the intent parser output with any profile-level fields
    that the parser cannot infer from free text alone.

    favorite_genre: intent_parser leaves this None intentionally;
                    caller injects it from the user's stored profile
                    (or a sensible default for the demo).
    """
    prefs = dict(intent)
    if prefs.get("favorite_genre") is None:
        prefs["favorite_genre"] = genre_hint
    return prefs


def run_agent_system(user_input: str, favorite_genre: str = "lofi"):

    print("\n" + "=" * 70)
    print("🎧 AGENTIC MUSIC CURATION SYSTEM")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Load Data
    # ------------------------------------------------------------------
    songs = load_songs("data/songs.csv")

    # ------------------------------------------------------------------
    # Initialize Agents
    # ------------------------------------------------------------------
    planner   = PlannerAgent()
    builder   = PlaylistBuilder()
    evaluator = EvaluatorAgent()
    curator   = CuratorAgent()

    # ------------------------------------------------------------------
    # STEP 1 — Intent Parsing
    # ------------------------------------------------------------------
    intent = parse_intent(user_input)

    favorite_genre = intent.get("favorite_genre")

    if favorite_genre is None:
        favorite_genre = "pop"  # neutral fallback

    user_prefs = intent
    user_prefs["favorite_genre"] = favorite_genre
    user_prefs = _build_user_prefs(intent, genre_hint=favorite_genre)

    # Print only the scoring-relevant keys — pipeline metadata
    # (context, arc_type, bpm_range, ambiguity, conflicts, etc.)
    # is useful for debugging but clutters normal output.
    SCORING_KEYS = [
        "target_energy_range", "target_valence", "target_acousticness",
        "mood_context", "favorite_genre", "likes_acoustic",
    ]
    print("\n🧠 Intent Parsed")
    for k in SCORING_KEYS:
        v = user_prefs.get(k)
        # Round floats and float-tuples to 2 decimal places for readability
        if isinstance(v, float):
            v = round(v, 2)
        elif isinstance(v, tuple):
            v = tuple(round(x, 2) for x in v)
        print(f"  {k}: {v}")
    # Surface ambiguity warnings if present — these are actionable
    if user_prefs.get("ambiguity"):
        print(f"  ⚠️  conflicts: {user_prefs.get('conflicts', [])}")

    # ------------------------------------------------------------------
    # STEP 2 — Planning
    #   arg 1 = intent (confidence, ambiguity, energy signal for mode)
    #   arg 2 = user_prefs (the full scoring-compatible dict)
    # ------------------------------------------------------------------
    plan = planner.create_plan(intent, user_prefs)

    print(f"\n📋 Plan: mode={plan.mode} | confidence={plan.confidence:.2f}")
    print(f"   reason: {plan.reason}")

    # ------------------------------------------------------------------
    # STEP 3-4 — Iterative Score → Build → Evaluate loop
    #
    # Re-scores on every iteration so that planner adjustments
    # (e.g. widened energy range) actually affect which songs surface.
    # ------------------------------------------------------------------
    MAX_ITER = 3
    evaluation_report = {}
    playlist = []

    for iteration in range(MAX_ITER):

        print(f"\n🔁 Iteration {iteration + 1} — scoring with adjusted prefs")

        # Score all songs against current adjusted prefs
        ranked_songs = recommend_songs(
            plan.adjusted_user_prefs,
            songs,
            k=SCORE_K
        )

        # Build playlist from ranked candidates
        playlist = builder.build(ranked_songs, plan, k=PLAYLIST_K)

        # Evaluate
        evaluation_report = evaluator.evaluate(
            playlist,
            plan,
            plan.adjusted_user_prefs
        )

        score_str = f"{evaluation_report.get('score', 0):.2f}"
        passed = evaluation_report.get("pass", False)
        issues = evaluation_report.get("issues", [])

        print(f"   Score: {score_str} | Pass: {passed}")
        if issues:
            print(f"   Issues: {', '.join(issues)}")

        if passed:
            print("✅ Evaluation passed")
            break

        if iteration < MAX_ITER - 1:
            # Re-plan with feedback: intent stays fixed, prefs evolve
            print("⚙️  Refining plan...")
            plan = planner.refine_plan(
            plan,
            evaluation_report)

    # ------------------------------------------------------------------
    # STEP 5 — Curator Layer
    # ------------------------------------------------------------------
    curated_output = curator.curate(
        playlist,
        plan,
        evaluation_report,
        plan.adjusted_user_prefs
    )

    # ------------------------------------------------------------------
    # STEP 6 — Output
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("🎼 FINAL PLAYLIST")
    print("=" * 70)

    print(f"\n📀 {curated_output['playlist_name']}")
    print(f"🌊 Arc: {curated_output['emotional_arc']}")
    print(f"\n{curated_output['summary']}")

    print("\nTracklist:")
    for i, song in enumerate(curated_output["song_explanations"], 1):
        print(f"\n  {i:02d}. {song['title']} — {song['artist']}")
        print(f"      Role : {song['role_in_playlist']}")
        print(f"      Why  : {song['why_this_song']}")

    print(f"\n📝 {curated_output['final_note']}")


def main():

    print("\n🎧 AGENTIC MUSIC RECOMMENDER")
    print("Type a mood (or 'exit' to quit)\n")

    while True:
        user_input = input("👉 Enter request: ")

        if user_input.lower() == "exit":
            break

        run_agent_system(user_input)
if __name__ == "__main__":
    main()