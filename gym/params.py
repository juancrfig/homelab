"""Parametrizer: fill {{slots}} fresh each review, and pick which variant to show.

The skill is fixed (card identity / SRS key); the surface (path, user, port…) is
reshuffled per review so you can't memorize one exact command string. Across
reviews of the same skill, the least-shown wording variant is favored so you cycle
through approved phrasings instead of repeating one — a pure tie-break, never a
scheduling decision (FSRS owns scheduling).
"""
from __future__ import annotations
import random

from .cards import Card, SLOT_RE
from .srs import SRS


def _fill(text: str, values: dict[str, str]) -> str:
    return SLOT_RE.sub(lambda m: values[m.group(1)], text)


def render_card(card: Card, rng: random.Random, srs: SRS) -> dict:
    """Pick the least-shown variant + fresh param values, render into display-ready
    strings, and record the exposure so the next rep favors a different wording."""
    idx = srs.pick_variant(card.skill_id, len(card.variants))
    srs.record_variant_shown(card.skill_id, idx, len(card.variants))
    variant = card.variants[idx]

    values = {slot: rng.choice(options)
              for slot, options in card.param_generator.items()}
    return {
        "skill_id": card.skill_id,
        "type": card.type,
        "topic": card.topic,
        "prompt": _fill(variant.template, values),
        "criteria": _fill(variant.success_criteria, values),
        "ref_commands": _fill(variant.ref_commands, values),
        "ref_why": _fill(variant.ref_why, values),
    }
