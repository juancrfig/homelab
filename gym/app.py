"""Linux Practice Gym — Textual TUI.

Two modes, one engine:
  - DRILL  (default): FSRS due-queue over recall/command cards. Self-graded,
    interleaved across types/topics, clear-all-due. Peek penalty applies.
  - SCENARIO (key 's'): deliberately-chosen, long, multi-step practice. NOT in
    the due-queue. Marking one solved nudges the FSRS state of every skill it
    links to.

The tool is the SCHEDULER + PROMPTER. You act in a SEPARATE real terminal,
self-check against the criteria, then grade. Tool never grades for you.

Run:  gym   (installed console script, or `./gym-run` in dev)
"""
from __future__ import annotations
import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header, Label, Static

from .cards import load_bank
from .params import render_card
from .scenarios import ScenarioTracker, scenarios as scenario_cards
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
    #scenmeta { color: $text-muted; margin-top: 1; }
    #scensteps { padding: 1 2; border: round $primary; display: none; }
    #scensteps.shown { display: block; }
    """

    BINDINGS = [
        Binding("r", "reveal", "Reveal solution"),
        Binding("1", "grade('again')", "Again"),
        Binding("2", "grade('hard')", "Hard"),
        Binding("3", "grade('good')", "Good"),
        Binding("4", "grade('easy')", "Easy"),
        Binding("s", "toggle_scenario", "Scenario mode"),
        Binding("n", "next_scenario", "Next scenario", show=False),
        Binding("m", "mark_solved", "Mark solved", show=False),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, seed: int | None = None):
        super().__init__()
        self.bank = load_bank()
        self.drill_by_id = {c.skill_id: c for c in self.bank if c.type in ("recall", "command")}
        self.scenarios = scenario_cards(self.bank)
        self.srs = SRS()
        self.scenario_tracker = ScenarioTracker()
        self.rng = random.Random(seed)
        # interleaving: shuffle so ties (same due date, e.g. all-new cards) don't
        # group by topic/type — FSRS still owns strict due-date ordering.
        self._drill_order = list(self.drill_by_id)
        self.rng.shuffle(self._drill_order)
        self.current = None       # rendered card dict (drill mode)
        self.peeked = False
        self.mode = "drill"       # drill | scenario
        self.scenario_idx = 0
        self.scenario_peeked = False

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
            yield Label("", id="scenmeta")
            yield Static("", id="scensteps")
            with Horizontal(id="grades"):
                yield Button("Reveal (r)", id="reveal", variant="primary")
                yield Button("Again (1)", id="again", variant="error")
                yield Button("Hard (2)", id="hard", variant="warning")
                yield Button("Good (3)", id="good", variant="success")
                yield Button("Easy (4)", id="easy", variant="success")
                yield Button("Mark solved (m)", id="solved", variant="success")
                yield Button("Next scenario (n)", id="next_scen", variant="primary")
            yield Static("", id="empty")
        yield Footer()

    def on_mount(self) -> None:
        self.load_next()

    # ---- mode switching ----
    def action_toggle_scenario(self) -> None:
        self.mode = "scenario" if self.mode == "drill" else "drill"
        if self.mode == "scenario":
            self.scenario_idx = 0
            self.scenario_peeked = False
            self._render_scenario()
        else:
            self.load_next()

    def action_next_scenario(self) -> None:
        if self.mode != "scenario" or not self.scenarios:
            return
        self.scenario_idx = (self.scenario_idx + 1) % len(self.scenarios)
        self.scenario_peeked = False
        self._render_scenario()

    # ---- drill loop ----
    def load_next(self) -> None:
        self._set_scenario_widgets(visible=False)
        sid = next_due(self.srs, self._drill_order)
        self.peeked = False
        self.query_one("#ref").remove_class("shown")
        self.query_one("#peeknote").remove_class("shown")
        self.query_one("#refh").display = True

        if sid is None:
            self._show_empty()
            return

        self.current = render_card(self.drill_by_id[sid], self.rng, self.srs)
        c = self.current
        n = self.srs.reviews(sid)
        self.query_one("#meta", Label).update(
            f"[{c['type']}] {c['topic']}  ·  skill: {sid}  ·  reps: {n}")
        self.query_one("#prompt", Static).update(c["prompt"])
        self.query_one("#criteria", Static).update(c["criteria"])
        ref = c["ref_commands"].rstrip()
        why = c["ref_why"]
        self.query_one("#ref", Static).update(f"$ {ref}\n\nwhy: {why}")
        self._set_grade_buttons(enabled=True, allow_easy=True)
        self.query_one("#empty", Static).update("")

    def _show_empty(self) -> None:
        self.current = None
        nxt = min((self.srs.due_at(s) for s in self.drill_by_id), default=None)
        for wid in ("#prompt", "#criteria", "#ref", "#peeknote"):
            self.query_one(wid, Static).update("")
        self.query_one("#meta", Label).update("All caught up.")
        self.query_one("#refh").display = False
        self._set_grade_buttons(enabled=False, allow_easy=False)
        self.query_one("#reveal", Button).disabled = True
        when = nxt.astimezone().strftime("%Y-%m-%d %H:%M") if nxt else "—"
        self.query_one("#empty", Static).update(
            f"No cards due. Next due: {when}\n"
            f"Press 's' for scenario practice, or close with q.")

    def _set_grade_buttons(self, enabled: bool, allow_easy: bool) -> None:
        self.query_one("#reveal", Button).disabled = not enabled
        self.query_one("#again", Button).disabled = not enabled
        self.query_one("#hard", Button).disabled = not enabled
        self.query_one("#good", Button).disabled = not (enabled and allow_easy)
        self.query_one("#easy", Button).disabled = not (enabled and allow_easy)

    # ---- scenario mode ----
    def _set_scenario_widgets(self, visible: bool) -> None:
        self.query_one("#scenmeta", Label).display = visible
        self.query_one("#solved", Button).display = visible
        self.query_one("#next_scen", Button).display = visible
        if not visible:
            self.query_one("#scensteps").remove_class("shown")

    def _render_scenario(self) -> None:
        if not self.scenarios:
            self.query_one("#meta", Label).update("No scenarios in the bank yet.")
            return
        self.query_one("#ref").remove_class("shown")
        self.query_one("#peeknote").remove_class("shown")
        self._set_scenario_widgets(visible=True)
        card = self.scenarios[self.scenario_idx]
        times = self.scenario_tracker.times_done(card.skill_id)
        stale = self.scenario_tracker.staleness_days(card.skill_id)
        stale_note = "never attempted" if stale is None else f"last solved {stale}d ago"
        self.query_one("#meta", Label).update(
            f"[scenario] {card.topic}  ·  {card.skill_id}  ·  "
            f"done {times}x  ·  {stale_note}")
        self.query_one("#prompt", Static).update(
            f"({self.scenario_idx + 1}/{len(self.scenarios)}) press 'n' for another scenario")
        steps_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(card.steps))
        self.query_one("#scensteps", Static).update(steps_text)
        self.query_one("#scensteps").add_class("shown")
        v = card.variants[0]
        self.query_one("#criteria", Static).update(v.success_criteria)
        self.query_one("#ref", Static).update(f"$ {v.ref_commands.rstrip()}\n\nwhy: {v.ref_why}")
        self.query_one("#scenmeta", Label).update(f"linked skills: {', '.join(card.skills)}")
        self._set_grade_buttons(enabled=False, allow_easy=False)
        self.query_one("#reveal", Button).disabled = False
        self.query_one("#solved", Button).disabled = False
        self.query_one("#empty", Static).update("")

    def action_mark_solved(self) -> None:
        if self.mode != "scenario" or not self.scenarios:
            return
        card = self.scenarios[self.scenario_idx]
        self.scenario_tracker.mark_solved(card, self.srs)
        self._render_scenario()

    # ---- actions ----
    def action_reveal(self) -> None:
        if self.mode == "scenario":
            self.query_one("#ref").add_class("shown")
            return
        if self.current is None:
            return
        self.query_one("#ref").add_class("shown")
        # peek BEFORE grading = penalty: lock out Good/Easy
        if not self.peeked:
            self.peeked = True
            self.query_one("#peeknote", Static).update(
                "Peeked before grading -> penalty. Only Again / Hard allowed.")
            self.query_one("#peeknote").add_class("shown")
            self.query_one("#good", Button).disabled = True
            self.query_one("#easy", Button).disabled = True

    def action_grade(self, rating: str) -> None:
        if self.mode != "drill" or self.current is None:
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
        elif bid == "solved":
            self.action_mark_solved()
        elif bid == "next_scen":
            self.action_next_scenario()


def main() -> None:
    Gym().run()


if __name__ == "__main__":
    main()
