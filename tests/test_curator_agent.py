from src.curator_agent import CuratorAgent


def make_playlist():
    return [
        {"title": "Song A", "artist": "Artist 1", "mood": "chill", "genre": "lofi", "energy": 0.3},
        {"title": "Song B", "artist": "Artist 2", "mood": "chill", "genre": "lofi", "energy": 0.6},
    ]


class DummyPlan:
    mode = "focused"


def test_curate_returns_required_fields():
    curator = CuratorAgent()

    result = curator.curate(
        playlist=make_playlist(),
        plan=DummyPlan(),
        evaluation_report={"pass": True, "score": 0.9},
        user_prefs={"mood_context": ["chill"]},
    )

    assert isinstance(result, dict)
    assert "playlist_name" in result
    assert "summary" in result
    assert "song_explanations" in result
    assert len(result["song_explanations"]) == 2


def test_song_explanations_have_roles():
    curator = CuratorAgent()

    result = curator.curate(
        make_playlist(),
        DummyPlan(),
        {"pass": False},
        {"mood_context": ["chill"]},
    )

    for song in result["song_explanations"]:
        assert "role_in_playlist" in song
        assert song["role_in_playlist"] in {
            "intro", "outro", "peak", "transition"
        }