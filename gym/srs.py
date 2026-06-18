"""SRS (PRD §12): FSRS keyed on skill_id. State = local progress, separate from card bank.

Card bank = content (git-tracked). State = your reps (gitignored). Clean split.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json

from fsrs import Scheduler, Card as FSRSCard, Rating

STATE_DIR = Path(__file__).resolve().parent.parent / "state"
STATE_FILE = STATE_DIR / "srs_state.json"

RATING = {
    "again": Rating.Again,
    "hard": Rating.Hard,
    "good": Rating.Good,
    "easy": Rating.Easy,
}


def now() -> datetime:
    return datetime.now(timezone.utc)


class SRS:
    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self.scheduler = Scheduler()
        self._states: dict[str, dict] = {}   # skill_id -> FSRSCard.to_dict()
        self._history: dict[str, int] = {}   # skill_id -> review count
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            blob = json.loads(self.state_file.read_text())
            self._states = blob.get("states", {})
            self._history = blob.get("history", {})

    def save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(
            {"states": self._states, "history": self._history}, indent=2))

    def _card(self, skill_id: str) -> FSRSCard:
        if skill_id in self._states:
            return FSRSCard.from_dict(self._states[skill_id])
        return FSRSCard()  # new card: due now

    EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

    def seen(self, skill_id: str) -> bool:
        return skill_id in self._states

    def due_at(self, skill_id: str) -> datetime:
        # unseen card = brand new = due now (sort it first via epoch)
        if not self.seen(skill_id):
            return self.EPOCH
        return self._card(skill_id).due

    def is_due(self, skill_id: str, at: datetime | None = None) -> bool:
        if not self.seen(skill_id):
            return True
        return self.due_at(skill_id) <= (at or now())

    def reviews(self, skill_id: str) -> int:
        return self._history.get(skill_id, 0)

    def grade(self, skill_id: str, rating_key: str) -> datetime:
        """Apply grade, persist, return next due. rating_key in again|hard|good|easy."""
        card = self._card(skill_id)
        card, _log = self.scheduler.review_card(card, RATING[rating_key])
        self._states[skill_id] = card.to_dict()
        self._history[skill_id] = self._history.get(skill_id, 0) + 1
        self.save()
        return card.due


def next_due(srs: SRS, skill_ids: list[str], at: datetime | None = None) -> str | None:
    """Pick next card to show: due ones first (earliest due), keyed on skill_id (PRD §5)."""
    at = at or now()
    due = [s for s in skill_ids if srs.is_due(s, at)]
    if not due:
        return None
    due.sort(key=lambda s: (srs.due_at(s), srs.reviews(s)))
    return due[0]
