"""
curator_agent.py


Current LLM role: generates playlist name, emotional arc, and summary
from the final scored playlist.

Future improvements:
- Natural language explanations per song ("why this song fits your mood")
  instead of the current template-based _simple_reason()
- Dynamic prompt adjustment based on evaluation score — if score < 0.7,
  ask the LLM to acknowledge the trade-offs in the summary
- Multi-turn conversation: let the user refine ("more energetic", "fewer
  vocals") and re-run the agentic loop with updated intent
"""


import json
import threading
from typing import List, Dict, Any

try:
    from langchain_ollama import ChatOllama
    HAS_LLM = True
except ImportError:
    ChatOllama = None
    HAS_LLM = False


class CuratorAgent:

    """
    CuratorAgent:
    - ALWAYS works without LLM
    - Uses deterministic logic as primary system
    - LLM is optional future enhancement layer
    """
    
    LLM_TIMEOUT_SECONDS = 15

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def curate(
        self,
        playlist: List[Any],
        plan,
        evaluation_report: Dict[str, Any],
        user_prefs: Dict[str, Any],
    ) -> Dict[str, Any]:

        passed = evaluation_report.get("pass", False)

        song_explanations = []
        energy_curve      = []

        for i, song in enumerate(playlist):
            energy = self._get(song, "energy", 0.5)
            energy_curve.append(round(energy, 2))

            song_explanations.append({
                "title": self._get(song, "title", "Unknown"),
                "artist": self._get(song, "artist", "Unknown"),
                "why_this_song": self._simple_reason(song),
                "role_in_playlist": self._role(i, len(playlist), energy),
            })

        # fallback naming signals
        moods = [self._get(s, "mood", "") for s in playlist]
        genres = [self._get(s, "genre", "") for s in playlist]

        top_mood = max(set(moods), key=moods.count) if moods else "mixed"
        top_genre = max(set(genres), key=genres.count) if genres else "mixed"

        # -------------------------------------------------
        # ORNAMENTAL LLM CALL (NOT REQUIRED)
        # -------------------------------------------------
        playlist_name, emotional_arc, summary = self._call_llm(
            plan=plan,
            evaluation_report=evaluation_report,
            user_prefs=user_prefs,
            energy_curve=energy_curve,
            fallback_name=f"{top_mood.title()} {top_genre.title()} Mix",
        )

        final_note = (
            "Curated successfully with strong coherence across constraints."
            if passed
            else "Playlist generated under constraint trade-offs."
        )

        return {
            "playlist_name": playlist_name,
            "emotional_arc": emotional_arc,
            "summary": summary,
            "song_explanations": song_explanations,
            "final_note": final_note,
        }

    # -------------------------------------------------
    # OPTIONAL LLM (SAFE ORNAMENT)
    # -------------------------------------------------
    def _call_llm(self, **kwargs):
        fallback_name = kwargs.get("fallback_name", "Untitled Mix")

        # If LLM is not installed → skip immediately
        if not HAS_LLM:
            return (fallback_name, "", "")

        result = {"data": None, "error": None}

        def _run():
            try:
                llm = ChatOllama(model=self.model, temperature=0.4)
                prompt = f"""
You are a music curator.

Return JSON:
{{"playlist_name": "...", "emotional_arc": "...", "summary": "..."}}

Context:
{json.dumps(kwargs, indent=2)}
"""
                response = llm.invoke(prompt)
                result["data"] = response.content
            except Exception as e:
                result["error"] = str(e)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=self.LLM_TIMEOUT_SECONDS)

        if thread.is_alive() or result["error"]:
            return (fallback_name, "", "")

        try:
            text = result["data"]
            start = text.find("{")
            end = text.rfind("}") + 1
            data = json.loads(text[start:end])

            return (
                data.get("playlist_name", fallback_name),
                data.get("emotional_arc", ""),
                data.get("summary", ""),
            )
        except:
            return (fallback_name, "", "")

    # -------------------------------------------------
    # HELPERS
    # -------------------------------------------------
    def _get(self, song, key, default=None):
        if isinstance(song, dict):
            return song.get(key, default)
        return getattr(song, key, default)

    def _simple_reason(self, song):
        return (
            f"{self._get(song,'genre')} supports mood "
            f"{self._get(song,'mood')} with energy "
            f"{self._get(song,'energy',0.5):.2f}"
        )

    def _role(self, idx, total, energy):
        if idx == 0:
            return "intro"
        if idx == total - 1:
            return "outro"
        if energy > 0.7:
            return "peak"
        return "transition"