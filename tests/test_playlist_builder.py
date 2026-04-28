from src.playlist_builder import PlaylistBuilder
from src.planner_agent import RecommendationPlan


def make_plan():
    return RecommendationPlan(
        mode="focused",
        weights={},
        diversity_required=False,
        energy_curve=True,
        max_artists=1,
        adjusted_user_prefs={},
        confidence=1.0,
        reason="test",
    )


def make_ranked_songs():
    return [
        ({"title": "A", "artist": "X", "energy": 0.2}, 0.9, []),
        ({"title": "B", "artist": "X", "energy": 0.8}, 0.8, []),
        ({"title": "C", "artist": "Y", "energy": 0.5}, 0.7, []),
        ({"title": "D", "artist": "Z", "energy": 0.6}, 0.6, []),
    ]


def test_artist_limit_respected():
    builder = PlaylistBuilder()
    playlist = builder.build(make_ranked_songs(), make_plan(), k=3)

    artists = [s["artist"] for s in playlist]
    assert artists.count("X") == 1


def test_fallback_fills_playlist():
    builder = PlaylistBuilder()

    plan = make_plan()
    plan.max_artists = 0  # impossible constraint

    playlist = builder.build(make_ranked_songs(), plan, k=3)

    assert len(playlist) == 3


def test_energy_curve_reorders_playlist():
    builder = PlaylistBuilder()

    playlist = builder.build(make_ranked_songs(), make_plan(), k=4)

    energies = [s["energy"] for s in playlist]

    assert energies != sorted(energies, reverse=True)