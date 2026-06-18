"""Card bank loader + validation (PRD §11).

One `*.yaml` per skill in `cards/`. The bank is the real product (PRD §15);
this module just loads it and fails loud on malformed cards so a bad card never
enters the loop silently.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

import yaml

CARDS_DIR = Path(__file__).resolve().parent.parent / "cards"

VALID_TYPES = {"doing", "concept"}
SLOT_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


@dataclass(frozen=True)
class Card:
    skill_id: str          # stable SRS identity (PRD §11) — never rename casually
    domain: str
    type: str              # doing | concept
    template: str
    param_generator: dict[str, list[str]]
    success_criteria: str
    ref_commands: str
    ref_why: str

    def slots(self) -> set[str]:
        """Every {{slot}} referenced across the templated fields."""
        text = " ".join((self.template, self.success_criteria,
                          self.ref_commands, self.ref_why))
        return set(SLOT_RE.findall(text))


def _card_from_dict(data: dict, source: str) -> Card:
    def req(key: str):
        if key not in data:
            raise ValueError(f"{source}: missing required field '{key}'")
        return data[key]

    ref = req("reference_solution")
    if not isinstance(ref, dict) or "commands" not in ref or "why" not in ref:
        raise ValueError(f"{source}: reference_solution needs 'commands' and 'why'")

    card = Card(
        skill_id=str(req("skill_id")),
        domain=str(req("domain")),
        type=str(req("type")),
        template=str(req("template")),
        param_generator=req("param_generator") or {},
        success_criteria=str(req("success_criteria")),
        ref_commands=str(ref["commands"]),
        ref_why=str(ref["why"]),
    )
    _validate(card, source)
    return card


def _validate(card: Card, source: str) -> None:
    if card.type not in VALID_TYPES:
        raise ValueError(f"{source}: type '{card.type}' not in {VALID_TYPES}")
    if not isinstance(card.param_generator, dict):
        raise ValueError(f"{source}: param_generator must be a mapping")
    # Anti-rote contract (PRD §7): every {{slot}} used must have values to fill it.
    missing = card.slots() - set(card.param_generator)
    if missing:
        raise ValueError(
            f"{source}: slots {sorted(missing)} used but absent from param_generator")
    for slot, values in card.param_generator.items():
        if not isinstance(values, list) or not values:
            raise ValueError(f"{source}: param_generator['{slot}'] must be a non-empty list")


def load_bank(cards_dir: Path = CARDS_DIR) -> list[Card]:
    """Load + validate every card. Raises on the first malformed card or dup skill_id."""
    files = sorted(cards_dir.glob("*.yaml")) + sorted(cards_dir.glob("*.yml"))
    if not files:
        raise FileNotFoundError(f"no card files in {cards_dir}")
    bank: list[Card] = []
    seen: dict[str, str] = {}
    for f in files:
        data = yaml.safe_load(f.read_text())
        if not isinstance(data, dict):
            raise ValueError(f"{f.name}: top-level YAML must be a mapping")
        card = _card_from_dict(data, f.name)
        if card.skill_id in seen:
            raise ValueError(
                f"{f.name}: duplicate skill_id '{card.skill_id}' (also in {seen[card.skill_id]})")
        seen[card.skill_id] = f.name
        bank.append(card)
    return bank
