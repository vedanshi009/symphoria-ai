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

from langchain_ollama import ChatOllama


class CuratorAgent:

    # If Ollama doesn't respond within this many seconds, skip it
    # and use the deterministic fallback instead.
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
                "title":             self._get(song, "title",  "Unknown"),
                "artist":            self._get(song, "artist", "Unknown"),
                "why_this_song":     self._simple_reason(song, user_prefs),
                "role_in_playlist":  self._role(i, len(playlist), energy),
            })

        # Dominant mood + genre from the playlist (used in fallback name)
        moods  = [self._get(s, "mood",  "") for s in playlist]
        genres = [self._get(s, "genre", "") for s in playlist]
        top_mood  = max(set(moods),  key=moods.count)  if moods  else "mixed"
        top_genre = max(set(genres), key=genres.count) if genres else "mixed"

        playlist_snapshot = [
            {
                "title":  self._get(s, "title"),
                "genre":  self._get(s, "genre"),
                "mood":   self._get(s, "mood"),
                "energy": round(self._get(s, "energy", 0.5), 2),
            }
            for s in playlist
        ]

        prompt = f"""You are a music curator writing short liner notes.

Playlist info:
- Mode: {plan.mode}
- Mood context: {user_prefs.get("mood_context", [])}
- Energy curve: {sorted(energy_curve)}
- Eval score: {round(evaluation_report.get("score", 0), 2)} | passed: {passed}
- Songs: {json.dumps(playlist_snapshot)}

Write a playlist name (max 5 words), one-sentence emotional arc, two-sentence summary.
Tone: grounded, DJ-like, no poetry.

Return ONLY a JSON object — no markdown, no explanation, just the JSON:
{{"playlist_name": "...", "emotional_arc": "...", "summary": "..."}}"""

        playlist_name, emotional_arc, summary = self._call_llm_with_timeout(
            prompt,
            fallback_name=f"{top_mood.title()} {top_genre.title()} Mix",
        )

        final_note = (
            "Curated successfully with strong coherence across constraints."
            if passed else
            "Playlist generated under constraint trade-offs. "
            "Flow preserved despite evaluation limitations."
        )

        return {
            "playlist_name":     playlist_name,
            "emotional_arc":     emotional_arc,
            "summary":           summary,
            "song_explanations": song_explanations,
            "final_note":        final_note,
        }

    # ------------------------------------------------------------------
    # LLM call with timeout
    # ------------------------------------------------------------------

    def _call_llm_with_timeout(
        self,
        prompt: str,
        fallback_name: str = "Untitled Mix",
    ):
        """
        Runs the Ollama call in a background thread with a hard timeout.
        If Ollama doesn't respond in time, or isn't running at all,
        the pipeline gets a clean fallback instead of hanging forever.
        """
        result = {"data": None, "error": None}

        def _run():
            try:
                llm = ChatOllama(model=self.model, temperature=0.4)
                response = llm.invoke(prompt)
                result["data"] = response.content
            except Exception as e:
                result["error"] = str(e)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=self.LLM_TIMEOUT_SECONDS)

        if thread.is_alive():
            print(
                f"  ⚠️  Curator: Ollama did not respond within "
                f"{self.LLM_TIMEOUT_SECONDS}s — using fallback name."
            )
            return (fallback_name, "", "")

        if result["error"]:
            print(f"  ⚠️  Curator: Ollama error — {result['error']}")
            return (fallback_name, "", "")

        return self._parse_response(result["data"], fallback_name)

    def _parse_response(self, raw: str, fallback_name: str):
        """
        Parses the LLM response. Expects a JSON object but defensively
        handles markdown fences and leading/trailing prose that some
        models add even when told not to.
        """
        if not raw:
            return (fallback_name, "", "")

        text = raw.strip()

        # Strip markdown code fences if present
        if "```" in text:
            parts = text.split("```")
            text  = parts[1] if len(parts) > 1 else parts[0]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        # Find the JSON object boundaries even if surrounded by prose
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        try:
            data = json.loads(text)
            return (
                data.get("playlist_name", fallback_name),
                data.get("emotional_arc", ""),
                data.get("summary",       ""),
            )
        except json.JSONDecodeError:
            print("  ⚠️  Curator: Could not parse LLM JSON — using fallback.")
            return (fallback_name, "", "")

    # ------------------------------------------------------------------
    # Deterministic helpers
    # ------------------------------------------------------------------

    def _get(self, song, key, default=None):
        if isinstance(song, dict):
            return song.get(key, default)
        return getattr(song, key, default)

    def _simple_reason(self, song, prefs):
        genre  = self._get(song, "genre",  "unknown genre")
        mood   = self._get(song, "mood",   "unknown mood")
        energy = self._get(song, "energy", 0.0)
        return (
            f"{genre} aligns with listener preference and "
            f"{mood} supports the intended mood direction "
            f"at energy level {energy:.2f}."
        )

    def _role(self, idx, total, energy):
        if idx == 0:
            return "intro / setup"
        elif idx == total - 1:
            return "closing / resolution"
        elif energy > 0.7:
            return "peak energy segment"
        else:
            return "transition layer"