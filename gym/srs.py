"""SRS: FSRS keyed on skill_id. State = local progress, separate from card bank.

Card bank = content (git-tracked). State = your reps (gitignored). Clean split.

Also tracks per-skill variant exposure counts (which wording you've seen how many
times) so the picker can favor the least-shown variant of a due skill — a pure
within-skill tie-break that never competes with FSRS's own due-date scheduling.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json

from fsrs import Scheduler, Card as FSRSCard, Rating

STATE_DIR = Path.home() / ".local" / "share" / "linux-gym"
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
        self._states: dict[str, dict] = {}     # skill_id -> FSRSCard.to_dict()
        self._history: dict[str, int] = {}      # skill_id -> review count
        self._exposure: dict[str, list[int]] = {}  # skill_id -> [count per variant idx]
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            blob = json.loads(self.state_file.read_text())
            self._states = blob.get("states", {})
            self._history = blob.get("history", {})
            self._exposure = blob.get("exposure", {})

    def save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(
            {"states": self._states, "history": self._history, "exposure": self._exposure},
            indent=2))

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

    def nudge(self, skill_ids: list[str]) -> None:
        """Apply a soft 'good' to every skill a solved scenario touched, so long
        deliberate practice still feeds the memory model without being a scheduled
        card itself."""
        for skill_id in skill_ids:
            self.grade(skill_id, "good")

    # ---- variant exposure (within-skill wording tie-break) ----
    def variant_counts(self, skill_id: str, n_variants: int) -> list[int]:
        counts = self._exposure.get(skill_id, [])
        if len(counts) < n_variants:
            counts = counts + [0] * (n_variants - len(counts))
        return counts[:n_variants]

    def pick_variant(self, skill_id: str, n_variants: int) -> int:
        """Index of the least-shown variant; ties broken by lowest index."""
        counts = self.variant_counts(skill_id, n_variants)
        return min(range(n_variants), key=lambda i: counts[i])

    def record_variant_shown(self, skill_id: str, idx: int, n_variants: int) -> None:
        counts = self.variant_counts(skill_id, n_variants)
        counts[idx] += 1
        self._exposure[skill_id] = counts
        self.save()


def next_due(srs: SRS, skill_ids: list[str], at: datetime | None = None) -> str | None:
    """Pick next card to show: due ones first (earliest due), keyed on skill_id."""
    at = at or now()
    due = [s for s in skill_ids if srs.is_due(s, at)]
    if not due:
        return None
    due.sort(key=lambda s: (srs.due_at(s), srs.reviews(s)))
    return due[0]
