"""Linux Practice Gym — Textual TUI. Core loop (PRD §5) + peek penalty (PRD §9).

Run:  python -m gym.app   (or  ./gym-run)

The tool is the SCHEDULER + PROMPTER. You act in a SEPARATE real terminal,
self-check against the criteria, then grade. Tool never grades doing-cards (PRD §8).
"""
from __future__ import annotations
import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Label, Static

from .cards import load_bank
from .params import render_card
from .srs import SRS, next_due


class Gym(App):
    CSS = """
    Screen { align: center top; }
    #wrap { width: 100%; max-width: 100; padding: 1 2; }
    #meta { color: $text-muted; }
    .h { text-style: bold; color: $accent; margin-top: 1; }
    #prompt { padding: 1 2; border: round $primary; }
    #criteria { padding: 1 2; border: round $warning; color: $text; }
    #ref { padding: 1 2; border: round $success; display: none; }
    #ref.shown { display: block; }
    #peeknote { color: $error; text-style: bold; display: none; }
    #peeknote.shown { display: block; }
    #grades { margin-top: 1; height: auto; }
    Button { margin: 0 1; }
    #empty { padding: 2; color: $text-muted; }
    """

    BINDINGS = [
        Binding("r", "reveal", "Reveal solution"),
        Binding("1", "grade('again')", "Again"),
        Binding("2", "grade('hard')", "Hard"),
        Binding("3", "grade('good')", "Good"),
        Binding("4", "grade('easy')", "Easy"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, seed: int | None = None):
        super().__init__()
        self.bank = load_bank()
        self.by_id = {c.skill_id: c for c in self.bank}
        self.srs = SRS()
        self.rng = random.Random(seed)
        self.current = None       # rendered card dict
        self.peeked = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll(id="wrap"):
            yield Label("", id="meta")
            yield Label("TASK", classes="h")
            yield Static("", id="prompt")
            yield Label("SUCCESS CRITERIA (self-check)", classes="h")
            yield Static("", id="criteria")
            yield Static("", id="peeknote")
            yield Label("REFERENCE SOLUTION", classes="h", id="refh")
            yield Static("", id="ref")
            with Horizontal(id="grades"):
                yield Button("Reveal (r)", id="reveal", variant="primary")
                yield Button("Again (1)", id="again", variant="error")
                yield Button("Hard (2)", id="hard", variant="warning")
                yield Button("Good (3)", id="good", variant="success")
                yield Button("Easy (4)", id="easy", variant="success")
            yield Static("", id="empty")
        yield Footer()

    def on_mount(self) -> None:
        self.load_next()

    # ---- loop ----
    def load_next(self) -> None:
        sid = next_due(self.srs, list(self.by_id))
        self.peeked = False
        self.query_one("#ref").remove_class("shown")
        self.query_one("#peeknote").remove_class("shown")
        self.query_one("#refh").display = True

        if sid is None:
            self._show_empty()
            return

        self.current = render_card(self.by_id[sid], self.rng)
        c = self.current
        n = self.srs.reviews(sid)
        self.query_one("#meta", Label).update(
            f"[{c['type']}] {c['domain']}  ·  skill: {sid}  ·  reps: {n}")
        self.query_one("#prompt", Static).update(c["prompt"])
        self.query_one("#criteria", Static).update(c["criteria"])
        ref = c["ref_commands"].rstrip()
        why = c["ref_why"]
        self.query_one("#ref", Static).update(f"$ {ref}\n\nwhy: {why}")
        self._set_grade_buttons(enabled=True, allow_easy=True)
        self.query_one("#empty", Static).update("")

    def _show_empty(self) -> None:
        self.current = None
        # earliest upcoming due across all skills
        nxt = min((self.srs.due_at(s) for s in self.by_id), default=None)
        for wid in ("#prompt", "#criteria", "#ref", "#peeknote"):
            self.query_one(wid, Static).update("")
        self.query_one("#meta", Label).update("All caught up.")
        self.query_one("#refh").display = False
        self._set_grade_buttons(enabled=False, allow_easy=False)
        self.query_one("#reveal", Button).disabled = True
        when = nxt.astimezone().strftime("%Y-%m-%d %H:%M") if nxt else "—"
        self.query_one("#empty", Static).update(
            f"No cards due. Next due: {when}\nClose with q. Come back later.")

    def _set_grade_buttons(self, enabled: bool, allow_easy: bool) -> None:
        self.query_one("#reveal", Button).disabled = not enabled
        self.query_one("#again", Button).disabled = not enabled
        self.query_one("#hard", Button).disabled = not enabled
        self.query_one("#good", Button).disabled = not (enabled and allow_easy)
        self.query_one("#easy", Button).disabled = not (enabled and allow_easy)

    # ---- actions ----
    def action_reveal(self) -> None:
        if self.current is None:
            return
        self.query_one("#ref").add_class("shown")
        # peek BEFORE grading = penalty (PRD §9): lock out Good/Easy
        if not self.peeked:
            self.peeked = True
            self.query_one("#peeknote", Static).update(
                "Peeked before grading -> penalty. Only Again / Hard allowed.")
            self.query_one("#peeknote").add_class("shown")
            self.query_one("#good", Button).disabled = True
            self.query_one("#easy", Button).disabled = True

    def action_grade(self, rating: str) -> None:
        if self.current is None:
            return
        if self.peeked and rating in ("good", "easy"):
            return  # blocked by penalty
        self.srs.grade(self.current["skill_id"], rating)
        self.load_next()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "reveal":
            self.action_reveal()
        elif bid in ("again", "hard", "good", "easy"):
            self.action_grade(bid)


def main() -> None:
    Gym().run()


if __name__ == "__main__":
    main()
