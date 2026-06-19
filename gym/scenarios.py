"""Scenario mode: long, multi-step, deliberately-chosen practice.

Scenarios are NOT in the FSRS due-queue — a 15-30 min exercise doesn't fit a
3-day-interval rep. Instead we track completion + a soft staleness hint, and
solving one nudges the FSRS state of every skill it links to (a free "Good"),
so deliberate practice still feeds the memory model.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json

from .cards import Card
from .srs import SRS, STATE_DIR

STATE_FILE = STATE_DIR / "scenario_state.json"


def now() -> datetime:
    return datetime.now(timezone.utc)


def scenarios(bank: list[Card]) -> list[Card]:
    return [c for c in bank if c.type == "scenario"]


class ScenarioTracker:
    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self._state: dict[str, dict] = {}  # skill_id -> {"last_done": iso, "times_done": int}
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            self._state = json.loads(self.state_file.read_text())

    def save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self._state, indent=2))

    def last_done(self, skill_id: str) -> datetime | None:
        entry = self._state.get(skill_id)
        if not entry:
            return None
        return datetime.fromisoformat(entry["last_done"])

    def times_done(self, skill_id: str) -> int:
        return self._state.get(skill_id, {}).get("times_done", 0)

    def staleness_days(self, skill_id: str) -> int | None:
        """Days since last solved, or None if never attempted."""
        last = self.last_done(skill_id)
        if last is None:
            return None
        return (now() - last).days

    def mark_solved(self, card: Card, srs: SRS) -> None:
        """Record completion and nudge every linked skill's FSRS state."""
        entry = self._state.get(card.skill_id, {"times_done": 0})
        entry["times_done"] = entry.get("times_done", 0) + 1
        entry["last_done"] = now().isoformat()
        self._state[card.skill_id] = entry
        self.save()
        srs.nudge(list(card.skills))
