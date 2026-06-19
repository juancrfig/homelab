"""Card bank loader + validation.

One `*.yaml` per skill under `cards/<topic>/`. The bank is the real product;
this module just loads it and fails loud on malformed cards so a bad card never
enters the loop silently.

Schema (frozen — see plan):
  skill_id, topic, type (recall|command|scenario), param_generator,
  variants: [{template, success_criteria, reference_solution{commands,why}}, ...]
Scenario cards additionally carry: steps (list[str]), skills (list[skill_id]).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re

import yaml

CARDS_DIR = Path(__file__).resolve().parent.parent / "cards"

VALID_TYPES = {"recall", "command", "scenario"}
SLOT_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


@dataclass(frozen=True)
class Variant:
    template: str
    success_criteria: str
    ref_commands: str
    ref_why: str


@dataclass(frozen=True)
class Card:
    skill_id: str          # stable SRS identity — never rename casually
    topic: str
    type: str              # recall | command | scenario
    param_generator: dict[str, list[str]]
    variants: tuple[Variant, ...]
    steps: tuple[str, ...] = field(default_factory=tuple)   # scenario only
    skills: tuple[str, ...] = field(default_factory=tuple)  # scenario only: linked skill_ids to nudge

    def slots(self) -> set[str]:
        """Every {{slot}} referenced across every variant's templated fields."""
        out: set[str] = set()
        for v in self.variants:
            text = " ".join((v.template, v.success_criteria, v.ref_commands, v.ref_why))
            out |= set(SLOT_RE.findall(text))
        return out


def _variant_from_dict(data: dict, source: str, idx: int) -> Variant:
    def req(key: str):
        if key not in data:
            raise ValueError(f"{source}: variant[{idx}] missing required field '{key}'")
        return data[key]

    ref = req("reference_solution")
    if not isinstance(ref, dict) or "commands" not in ref or "why" not in ref:
        raise ValueError(f"{source}: variant[{idx}].reference_solution needs 'commands' and 'why'")

    return Variant(
        template=str(req("template")),
        success_criteria=str(req("success_criteria")),
        ref_commands=str(ref["commands"]),
        ref_why=str(ref["why"]),
    )


def _card_from_dict(data: dict, source: str) -> Card:
    def req(key: str):
        if key not in data:
            raise ValueError(f"{source}: missing required field '{key}'")
        return data[key]

    raw_variants = data.get("variants")
    if not raw_variants:
        raise ValueError(f"{source}: missing required field 'variants' (non-empty list)")
    if not isinstance(raw_variants, list):
        raise ValueError(f"{source}: 'variants' must be a list")
    variants = tuple(_variant_from_dict(v, source, i) for i, v in enumerate(raw_variants))

    card = Card(
        skill_id=str(req("skill_id")),
        topic=str(req("topic")),
        type=str(req("type")),
        param_generator=data.get("param_generator") or {},
        variants=variants,
        steps=tuple(str(s) for s in data.get("steps", [])),
        skills=tuple(str(s) for s in data.get("skills", [])),
    )
    _validate(card, source)
    return card


def _validate(card: Card, source: str) -> None:
    if card.type not in VALID_TYPES:
        raise ValueError(f"{source}: type '{card.type}' not in {VALID_TYPES}")
    if not isinstance(card.param_generator, dict):
        raise ValueError(f"{source}: param_generator must be a mapping")
    if card.type == "scenario" and not card.skills:
        raise ValueError(f"{source}: scenario cards must list linked 'skills' to nudge on solve")
    # Anti-rote contract: every {{slot}} used must have values to fill it.
    missing = card.slots() - set(card.param_generator)
    if missing:
        raise ValueError(
            f"{source}: slots {sorted(missing)} used but absent from param_generator")
    for slot, values in card.param_generator.items():
        if not isinstance(values, list) or not values:
            raise ValueError(f"{source}: param_generator['{slot}'] must be a non-empty list")


def load_bank(cards_dir: Path = CARDS_DIR) -> list[Card]:
    """Load + validate every card under every topic dir. Raises on the first
    malformed card or duplicate skill_id."""
    files = sorted(cards_dir.glob("*/*.yaml")) + sorted(cards_dir.glob("*/*.yml"))
    files = [f for f in files if not f.name.startswith("_")]
    if not files:
        raise FileNotFoundError(f"no card files in {cards_dir}/<topic>/")
    bank: list[Card] = []
    seen: dict[str, str] = {}
    for f in files:
        data = yaml.safe_load(f.read_text())
        if not isinstance(data, dict):
            raise ValueError(f"{f.name}: top-level YAML must be a mapping")
        card = _card_from_dict(data, f"{f.parent.name}/{f.name}")
        if card.skill_id in seen:
            raise ValueError(
                f"{f.name}: duplicate skill_id '{card.skill_id}' (also in {seen[card.skill_id]})")
        seen[card.skill_id] = f.name
        bank.append(card)
    return bank
