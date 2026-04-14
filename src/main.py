"""
Command line runner for the Music Recommender Simulation.

"""

from recommender import load_songs, recommend_songs


def run_profile(name, user_prefs, songs):
    print("\n" + "=" * 60)
    print(f"🎧 USER PROFILE: {name}")
    print("=" * 60)

    recommendations = recommend_songs(user_prefs, songs, k=5)

    for i, (song, score, reasons) in enumerate(recommendations, start=1):
        print(f"\n#{i} 🎵 {song['title']} — {song['artist']}")
        print(f"Score: {score:.2f}")

        print("Why this fits:")
        for r in reasons:
            print(f"  • {r}")

    print("\n")


def main() -> None:
    songs = load_songs("data/songs.csv")

    # =====================================================
    # NORMAL USERS
    # =====================================================

    chill_lofi = {
        "favorite_genre": "lofi",
        "mood_context": ["focused", "relaxed", "late-night"],
        "target_energy_range": (0.35, 0.60),
        "target_valence": 0.65,
        "target_acousticness": 0.75,
        "likes_acoustic": True,
    }

    high_energy_pop = {
        "favorite_genre": "pop",
        "mood_context": ["energetic", "happy"],
        "target_energy_range": (0.75, 0.95),
        "target_valence": 0.85,
        "target_acousticness": 0.20,
        "likes_acoustic": False,
    }

    deep_intense_rock = {
        "favorite_genre": "rock",
        "mood_context": ["intense", "moody"],
        "target_energy_range": (0.65, 0.90),
        "target_valence": 0.30,
        "target_acousticness": 0.25,
        "likes_acoustic": False,
    }

    # =====================================================
    # EDGE CASE USERS
    # =====================================================

    ultra_specific_listener = {
        "favorite_genre": "lofi",
        "mood_context": ["focused"],
        "target_energy_range": (0.50, 0.52),  # extremely narrow
        "target_valence": 0.60,
        "target_acousticness": 0.80,
        "likes_acoustic": True,
    }

    neutral_listener = {
        "favorite_genre": "pop",
        "mood_context": [],
        "target_energy_range": (0.0, 1.0),  # accepts everything
        "target_valence": 0.50,
        "target_acousticness": 0.50,
        "likes_acoustic": True,
    }

    # =====================================================
    # ADVERSARIAL USERS (LOGIC STRESS TESTS)
    # =====================================================

    conflicting_emotions = {
        "favorite_genre": "rock",
        "mood_context": ["sad"],
        "target_energy_range": (0.85, 0.95),  # sad but extremely energetic
        "target_valence": 0.20,
        "target_acousticness": 0.80,
        "likes_acoustic": True,
    }

    acoustic_club_paradox = {
        "favorite_genre": "lofi",
        "mood_context": ["energetic"],
        "target_energy_range": (0.80, 1.00),
        "target_valence": 0.90,
        "target_acousticness": 0.95,  # acoustic but party energy
        "likes_acoustic": True,
    }

    # RUN ALL SIMULATIONS

    profiles = {
        "Chill Lofi": chill_lofi,
        "High Energy Pop": high_energy_pop,
        "Deep Intense Rock": deep_intense_rock,
        "Ultra Specific Listener (Edge Case)": ultra_specific_listener,
        "Neutral Listener (Edge Case)": neutral_listener,
        "Conflicting Emotions (Adversarial)": conflicting_emotions,
        "Acoustic Club Paradox (Adversarial)": acoustic_club_paradox,
    }

    for name, profile in profiles.items():
        run_profile(name, profile, songs)


if __name__ == "__main__":
    main()