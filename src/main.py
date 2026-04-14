"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv") 

    # Starter example profile
    user_prefs = {
    "favorite_genre": "lofi",
    "mood_context": ["focused", "relaxed", "late-night"], #variaibility for mood context
    "target_energy_range": (0.35, 0.60),
    "target_valence": 0.65,
    "target_acousticness": 0.75,
    "likes_acoustic": True
}

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\n🎧 Top recommendations:\n")
    print("=" * 50)
    for i, rec in enumerate(recommendations, start=1):
        song, score, reasons = rec   # reasons is LIST

        print(f"\n#{i} 🎵 {song['title']} — {song['artist']}")
        print(f"Score: {score:.2f}")
        print("-" * 50)

        print("Why this fits your vibe:")
        for r in reasons:
            print(f"  • {r}")

        print("-" * 50)

    print("\n✨ End of recommendations\n")


if __name__ == "__main__":
    main()
