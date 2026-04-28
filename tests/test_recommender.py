from src.recommender import Song, UserProfile, Recommender, score_song


def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


# --------------------------------------------------
# TEST 1 — recommendation ordering
# --------------------------------------------------
def test_recommend_returns_songs_sorted_by_score():
    user = {
    "favorite_genre": "pop",
    "mood_context": ["happy"],
    "target_energy_range": (0.7, 0.9),
    "likes_acoustic": False,
}

    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2

    # Expect pop + happy song ranked first
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


# --------------------------------------------------
# TEST 2 — scoring explanation exists
# --------------------------------------------------
def test_score_song_returns_reasoning():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )

    rec = make_small_recommender()
    song = rec.songs[0]

    # Convert user → scoring format
    user_dict = {
        "favorite_genre": user.favorite_genre,
        "mood_context": [user.favorite_mood],
        "target_energy_range": (
            max(0.0, user.target_energy - 0.15),
            min(1.0, user.target_energy + 0.15),
        ),
        "target_valence": 0.5,
        "target_acousticness": 0.5,
        "likes_acoustic": user.likes_acoustic,
    }

    score, reasons = score_song(user_dict, song.__dict__)

    assert isinstance(score, float)
    assert isinstance(reasons, list)
    assert len(reasons) > 0