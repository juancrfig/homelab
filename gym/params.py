"""Parametrizer (PRD §7, §8.2): fill {{slots}} fresh each review.

The skill is fixed (card identity / SRS key); the surface (path, user, port…) is
reshuffled per review so you can't memorize one exact command string. Rules only,
no LLM yet (v1, PRD §13).
"""
from __future__ import annotations
import random

from .cards import Card, SLOT_RE


def _fill(text: str, values: dict[str, str]) -> str:
    return SLOT_RE.sub(lambda m: values[m.group(1)], text)


def render_card(card: Card, rng: random.Random) -> dict:
    """Pick one value per slot and render the card into display-ready strings."""
    values = {slot: rng.choice(options)
              for slot, options in card.param_generator.items()}
    return {
        "skill_id": card.skill_id,
        "type": card.type,
        "domain": card.domain,
        "prompt": _fill(card.template, values),
        "criteria": _fill(card.success_criteria, values),
        "ref_commands": _fill(card.ref_commands, values),
        "ref_why": _fill(card.ref_why, values),
    }
