"""Entry point: `gym` launches the TUI, `gym refill` tops up the LLM variant pool
(Phase 2 — stub for now)."""
from __future__ import annotations
import sys


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "refill":
        print("gym refill: not implemented yet (Phase 2 — cloud-API rephraser pool).")
        return
    from .app import Gym
    Gym().run()


if __name__ == "__main__":
    main()
