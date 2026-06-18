# Linux Practice Gym — v1

Daily spaced-repetition loop for the 80/20 Linux skills a DevOps engineer must own.
You act in a **real terminal**; the tool schedules, prompts, and tracks. Habit first (PRD §2).

## What this is (and isn't)

- **Is:** an SRS scheduler + prompter. Two card types: `doing` (run in shell, self-check) and `concept` (recall).
- **Isn't:** a grader for hands-on tasks. You self-grade against observable criteria (PRD §8). No nanny.

## Quick start

```bash
uv sync              # resolve + install deps into .venv
./gym-run            # or: uv run python -m gym.app  (or: uv run gym)
```

Open a **second terminal** next to it — that's your arena. Break things freely (PRD §10).

## The loop (PRD §5)

```
due card -> slots parametrized fresh -> shows TASK + SUCCESS CRITERIA
   -> you act in the real shell
   -> self-check against criteria
   -> (optional) Reveal solution  [peeking before grade = penalty]
   -> grade: Again(1) / Hard(2) / Good(3) / Easy(4)
   -> FSRS reschedules -> next card
```

Keys: `r` reveal · `1`–`4` grade · `q` quit.

**Peek penalty (PRD §9):** revealing the reference *before* grading locks out Good/Easy.
Peeking is not free.

**Anti-rote (PRD §7):** the skill is fixed (what FSRS tracks via `skill_id`); the surface
(path, user, port…) is reshuffled each review. You can't memorize one exact command string.

## Layout

```
gym/
  cards.py    load + validate YAML card bank
  params.py   fill {{slots}} from value lists (rules, no LLM yet)
  srs.py      FSRS engine + JSON state (keyed on skill_id)
  app.py      Textual TUI (the loop)
cards/        the card bank — the real product (PRD §15). 1 seed card so far.
state/        your reps. gitignored. delete to reset progress.
```

Card bank = content, git-tracked. State = your progress, local + gitignored. Clean split.

## Add / edit cards

One `*.yaml` per skill in `cards/`. Shape (PRD §11):

```yaml
skill_id: acl_readonly        # stable identity — what SRS tracks. NEVER rename casually.
domain: permissions/acl
type: doing                   # doing | concept
template: "Give user {{user}} read-only access to {{path}}."
param_generator:              # each slot -> list of solvable values
  user: [deploy, ci, web]
  path: [/etc/app, /srv/web]
success_criteria: "`getfacl {{path}}` shows `user:{{user}}:r--` and no write/execute."
reference_solution:
  commands: |
    setfacl -m u:{{user}}:r-- {{path}}
  why: "ACLs grant per-user perms beyond owner/group/other. r-- = read only."
```

Rules: every `{{slot}}` used must exist in `param_generator`. Keep value lists to options
that stay solvable + similar difficulty. `skill_id` is the SRS key — renaming = losing history.

## Seed cards

Currently **1** card: `acl_readonly` (permissions/ACL). The bank is the weight (PRD §15) —
cards are human-reviewed before entering it (PRD §8), so it grows deliberately. Next domains
to cover (PRD §14): octal perms · signals · systemd · grep · ss/ports · journald · du/disk ·
find/size · tar.

## Deferred (v2+, PRD §13)

AI content factory · AI concept grading · per-card verify scripts · container reset baked in ·
public multi-user SSH playground.

## Reset progress

```bash
rm -rf state/
```

