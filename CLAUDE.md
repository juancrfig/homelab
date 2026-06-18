# CLAUDE.md

Guidance for working in this repo. Read alongside `README.md` (user-facing) and the PRD
(vision; pasted into the kickoff conversation, not yet a file in the repo).

## What this is

**Linux Practice Gym** — a local, single-user spaced-repetition tool for the 80/20 Linux
skills a DevOps engineer needs. It is an **SRS scheduler + prompter**, not a grader. The
user acts in a *separate real terminal*, self-checks against observable criteria, then grades
Anki-style. v1 is local, hand-authored cards, no AI in the loop yet.

The card bank (`cards/*.yaml`) is the real product; the code is delivery (PRD §15).

## Architecture

```
gym/
  cards.py    Card dataclass + load_bank(): read/validate cards/*.yaml, fail loud
  params.py   render_card(): fill {{slots}} fresh each review (rules only, no LLM)
  srs.py      SRS class: FSRS engine + JSON state, keyed on skill_id
  app.py      Gym(Textual App): the core loop + peek penalty
cards/        the card bank (git-tracked content)
state/        FSRS progress JSON (gitignored; delete to reset)
gym-run       launcher → uv run python -m gym.app
pyproject.toml deps + the `gym` entry point (managed by uv)
```

Data flow: `load_bank()` → `next_due()` picks a due `skill_id` → `render_card()` fills slots
→ TUI shows task + criteria → user self-checks in their own shell → `SRS.grade()` reschedules.

## Key invariants (don't break these)

- **`skill_id` is the SRS identity.** FSRS schedules on it. Renaming a card's `skill_id`
  loses its review history. The YAML filename is incidental; `skill_id` is load-bearing.
- **Surface varies, skill is fixed (PRD §7).** Parametrization (`params.py`) must never
  change difficulty or solvability — only swap interchangeable values (paths, users, ports).
  It must not affect scheduling.
- **The tool never grades `doing` cards (PRD §8).** No auto-verification in v1. Self-grade only.
- **Peek-before-grade = penalty (PRD §9).** Revealing the reference before grading locks out
  Good/Easy (only Again/Hard remain). Enforced in `app.py` (`action_reveal`/`action_grade`).
- **Content/progress split.** `cards/` is git-tracked content; `state/` is local + gitignored.
- **Cards are human-reviewed before entering the bank.** Don't bulk-generate unreviewed cards.

## Card shape (PRD §11)

One `*.yaml` per skill in `cards/`. Required fields: `skill_id`, `domain`,
`type` (`doing`|`concept`), `template`, `param_generator` (slot → non-empty value list),
`success_criteria`, `reference_solution.{commands, why}`. `load_bank()` validates these and
rejects any `{{slot}}` used in a templated field that has no entry in `param_generator`.

## Running & checking

```bash
uv sync                              # install fsrs, textual, PyYAML into .venv
./gym-run                            # or: uv run python -m gym.app  (or: uv run gym)

# logic check without the TUI deps (only needs PyYAML):
uv run python -c "from gym.cards import load_bank; print([c.skill_id for c in load_bank()])"
uv run python -m py_compile gym/*.py
```

Deps are managed by `uv` via `pyproject.toml` (no `requirements.txt`). No test suite yet.
`srs.py`/`app.py` need `fsrs` + `textual` installed to import.

## Conventions

- Python 3, `from __future__ import annotations`, standard-lib + the three deps only.
- Relative imports within the `gym` package; run as a module (`-m gym.app`), never `gym/app.py`.
- Comments cite PRD sections (e.g. `(PRD §9)`) to tie code back to intent — keep that habit.

## Deferred to v2+ (PRD §13) — out of scope now

AI content factory · AI concept grading · per-card verify scripts · container-based reset ·
public multi-user SSH playground.
