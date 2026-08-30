"""The debate — the desk's only LLM decision point, and the last gate before an opening.

Where it runs
-------------
`review_open()` is called from `desk.py` **only on an opening decision**, after the
deterministic layers have already done their work: `signal.py` decided *whether* the surface is
worth selling, `execution.py` picked the strikes, `execution.size()` picked a contract count and
`risk.evaluate()` approved it. Exits, portfolio gates and sizing never touch this module — they
stay pure Python, which is exactly the split Alpaca recommends for agentic trading systems and
the reason a hallucination here cannot become a loss there. In practice this is a handful of
calls a day, not one per 15-minute cron tick.

Why the LLM cannot increase risk — by construction, not by prompt
-----------------------------------------------------------------
`review_open()` receives `cap_contracts`, a number the Risk Officer already blessed. The final
size is::

    contracts = max(0, min(int(desk_head_says), cap_contracts))

so the debate is a **monotonically non-increasing** function of risk: it can cut the size, it
can veto, it can do nothing. There is no argument, jailbreak or hallucination that makes that
expression return more than `cap_contracts`, because the model's number never reaches
`execution.open_trade()` un-clamped. Same for vetoes: `risk.evaluate()` runs *before* this and
a `False` there means `desk.py` never calls us at all. The model is a filter downstream of the
gate, never a party to it.

Failure is a stand-down, never an approval
------------------------------------------
Every failure mode — a provider outage, a hung socket, a truncated JSON body, a model that
argues without citing the signal, an ensemble that splits 1-1-1 — resolves to
`approved=False` with the reason recorded. We run on a 15-minute cron, so the whole debate
carries a wall-clock budget (`DESK_DEBATE_BUDGET_S`, default 90s) enforced with hard per-seat
deadlines; blowing the budget stands the desk down rather than delaying the next tick.

Kill switch
-----------
`DESK_DEBATE=off` bypasses the seats entirely and passes the deterministic decision straight
through (journalled as `debate_disabled`). Default is `required`: no working LLM layer means no
new positions, which is the safe direction and keeps the journal honest.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any

from dotenv import load_dotenv

from . import seats
from .seats import Argument, DeskDecision, QuantBallot, SeatClient

load_dotenv()          # so this module works standalone, not only via `desk.py` -> `config.py`

DEFAULT_BUDGET_S = 90.0
QUANT_SHARE = 0.35      # fraction of the budget the ensemble may spend (it runs in parallel)
ARGUER_SHARE = 0.30     # Bull and Bear run SEQUENTIALLY: Bear rebuts Bull (see _run_arguers)
MIN_SEAT_TIMEOUT = 5.0
# Above this text overlap Bull and Bear are saying the same thing and the debate is decorative.
DEGENERATE_SIMILARITY = 0.80


# --------------------------------------------------------------------------- wiring

@dataclass
class DeskClients:
    """The transports for one debate. Inject fakes in tests; `build()` reads the environment."""

    quant: list[tuple[str, SeatClient]] = field(default_factory=list)
    arguer: SeatClient | None = None

    @classmethod
    def build(cls) -> DeskClients:
        """Construct real provider clients from env. Raises `seats.SeatError` if unconfigured."""
        # `.get(k, default)` does not fire the default when the var is present-but-empty, which is
        # exactly how an unset GitHub Actions repo variable arrives. Treat "" as absent.
        base = os.environ.get("FEATHERLESS_BASE_URL", "").strip() or "https://api.featherless.ai/v1"
        key = os.environ.get("FEATHERLESS_API_KEY", "").strip()
        models = [m.strip() for m in os.environ.get("FEATHERLESS_MODELS", "").split(",")
                  if m.strip()][:seats.MAX_QUANT_MODELS]
        if not key or not models:
            raise seats.SeatError("featherless not configured (FEATHERLESS_API_KEY/MODELS)")
        # Bull / Bear / Desk Head share one model. Defaults to the first ensemble member so a
        # single FEATHERLESS_MODELS is enough to boot; override for a stronger arguer.
        arguer_model = os.environ.get("FEATHERLESS_ARGUER_MODEL", "").strip() or models[0]
        return cls(
            quant=[(m, seats.FeatherlessSeatClient(model=m, base_url=base, api_key=key))
                   for m in models],
            arguer=seats.FeatherlessSeatClient(model=arguer_model, base_url=base, api_key=key),
        )


def is_enabled() -> bool:
    """`DESK_DEBATE=off` disables the LLM layer; anything else (default) requires it."""
    return os.environ.get("DESK_DEBATE", "required").strip().lower() not in {"off", "0", "false"}


def _budget_s() -> float:
    try:
        return max(10.0, float(os.environ.get("DESK_DEBATE_BUDGET_S", DEFAULT_BUDGET_S)))
    except ValueError:
        return DEFAULT_BUDGET_S


class _Clock:
    """Wall-clock budget for the whole debate, sliced into per-seat deadlines."""

    def __init__(self, total: float) -> None:
        self.total = total
        self.t0 = time.monotonic()

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.t0

    def remaining(self) -> float:
        return max(0.0, self.total - self.elapsed)

    def slice_(self, share: float) -> float:
        """Timeout for the next stage: its share of the total, capped by what is actually left."""
        return max(0.0, min(self.total * share, self.remaining()))

    def seat_timeout(self, share: float | None = None) -> float:
        """Per-seat deadline: never below `MIN_SEAT_TIMEOUT`, never above the total budget.

        The floor keeps a stage that starts late from getting a 0.2s deadline it cannot meet;
        the ceiling keeps the floor from silently overriding a deliberately small budget.
        """
        want = self.remaining() if share is None else self.slice_(share)
        return max(min(MIN_SEAT_TIMEOUT, self.total), want)


# --------------------------------------------------------------------------- result

@dataclass
class DebateOutcome:
    """What `desk.py` acts on. `approved=False` always means: do not open this trade."""

    approved: bool
    reason: str                       # machine-readable stand-down / approval code
    contracts: int                    # ALREADY clamped to cap_contracts. Safe to trade.
    cap_contracts: int
    thesis: str
    prediction: dict | None = None
    quant_verdict: str = ""
    elapsed_s: float = 0.0
    transcript: list[dict] = field(default_factory=list)
    started_at: str = ""

    def to_record(self) -> dict:
        """Journal-ready dict: fully JSON-serializable, every seat's intervention included."""
        return {
            "approved": self.approved, "reason": self.reason, "contracts": self.contracts,
            "cap_contracts": self.cap_contracts, "quant_verdict": self.quant_verdict,
            "thesis": self.thesis, "prediction": self.prediction,
            "elapsed_s": round(self.elapsed_s, 2), "started_at": self.started_at,
            "transcript": self.transcript,
        }


def _stand_down(reason: str, cap: int, thesis: str, clock: _Clock, started: str,
                transcript: list[dict], quant_verdict: str = "") -> DebateOutcome:
    return DebateOutcome(approved=False, reason=reason, contracts=0, cap_contracts=cap,
                         thesis=thesis, quant_verdict=quant_verdict, elapsed_s=clock.elapsed,
                         transcript=transcript, started_at=started)


# --------------------------------------------------------------------------- entry point

def review_open(
    signal: Any,
    selection: dict,
    cap_contracts: int,
    base_thesis: str = "",
    *,
    clients: DeskClients | None = None,
    budget_s: float | None = None,
) -> DebateOutcome:
    """Run the four-seat debate over one proposed opening. Never raises.

    This is the **only** entry point `desk.py` needs, and it is safe to call unconditionally:
    it degrades to a stand-down on any failure and to a pass-through when `DESK_DEBATE=off`.

    Args:
        signal: the `signal.Signal` for this underlying. Read via `vars()`, so any dataclass
            with the same fields works; the option `chain` is stripped before it reaches a
            prompt. New `Signal` fields become citable by the Bull/Bear seats automatically.
        selection: the dict from `execution.select_condor` / `select_vertical`
            (`legs`, `credit`, `width`, `strikes`).
        cap_contracts: **the hard ceiling from the deterministic layer** — the size
            `execution.size()` produced and `risk.evaluate()` approved. The returned
            `contracts` is guaranteed to be an int in `[0, cap_contracts]`.
        base_thesis: the deterministic thesis `desk.py` already built. Used verbatim when the
            debate is disabled, and as the fallback if the Desk Head writes an empty one.

    Returns:
        `DebateOutcome`. Trade only if `.approved` is True, with `.contracts` (never
        `cap_contracts`) and `.thesis`. Append `.to_record()` to the journal either way —
        a documented stand-down is the artifact this desk is judged on.

    Kwargs:
        clients: inject `DeskClients` with test doubles. Built from env when omitted.
        budget_s: wall-clock ceiling for the whole debate. Defaults to `DESK_DEBATE_BUDGET_S`.
    """
    started = datetime.now(UTC).isoformat()
    clock = _Clock(budget_s if budget_s is not None else _budget_s())
    cap = max(0, int(cap_contracts))
    transcript: list[dict] = []

    if not is_enabled():
        return DebateOutcome(approved=cap >= 1, reason="debate_disabled", contracts=cap,
                             cap_contracts=cap, thesis=base_thesis, elapsed_s=clock.elapsed,
                             transcript=[{"seat": "system", "note": "DESK_DEBATE=off"}],
                             started_at=started)
    if cap < 1:
        return _stand_down("cap_is_zero", cap, base_thesis, clock, started, transcript)

    if clients is None:
        try:
            clients = DeskClients.build()
        except seats.SeatError as e:
            return _stand_down(f"debate_unavailable: {e}", cap, base_thesis, clock, started,
                               [{"seat": "system", "error": str(e)}])
    if not clients.quant or clients.arguer is None:
        return _stand_down("debate_unavailable: seats not wired", cap, base_thesis, clock,
                           started, transcript)

    structure = str(getattr(signal, "structure", "")).strip().lower()

    # --- seat 1: Quant ensemble (parallel, majority or abstain) ---------------------------
    q_timeout = clock.seat_timeout(QUANT_SHARE)
    ballots = _run_quant(clients.quant, signal, selection, cap, q_timeout)
    transcript.extend(b.to_record() for b in ballots)
    verdict, q_reason = seats.consensus(ballots, len(clients.quant), structure)
    transcript.append({"seat": "quant_ensemble", "verdict": verdict, "reason": q_reason,
                       "models": len(clients.quant)})
    if verdict != "confirm":
        return _stand_down(f"quant_{verdict}: {q_reason}", cap, base_thesis, clock, started,
                           transcript, verdict)

    # --- seats 2 & 3: Bull and Bear (parallel, must cite the signal) ----------------------
    a_timeout = clock.seat_timeout(ARGUER_SHARE)
    bull, bear = _run_arguers(clients.arguer, signal, selection, cap, a_timeout)
    similarity = adversarial_ratio(bull, bear)
    transcript.extend([bull.to_record(), bear.to_record(),
                       {"seat": "debate_quality", "ok": True,
                        "bull_bear_similarity": round(similarity, 3),
                        "adversarial": similarity < DEGENERATE_SIMILARITY}])
    if not (bull.ok and bear.ok):
        bad = ", ".join(f"{a.role}: {a.error}" for a in (bull, bear) if not a.ok)
        return _stand_down(f"debate_incomplete: {bad}", cap, base_thesis, clock, started,
                           transcript, verdict)

    # --- seat 4: Desk Head (final size, always <= cap; falsifiable thesis) ----------------
    d_timeout = clock.seat_timeout()
    head = _collect(_spawn(lambda: seats.desk_head(
        clients.arguer, signal, selection, cap, verdict, q_reason, ballots, bull, bear,
        d_timeout)), d_timeout, lambda err: DeskDecision(ok=False, error=err))
    transcript.append(head.to_record())

    if not head.ok:
        return _stand_down(f"desk_head_unusable: {head.error}", cap, base_thesis, clock, started,
                           transcript, verdict)
    if head.decision != "approve":
        return _stand_down("desk_head_veto", cap, base_thesis, clock, started, transcript, verdict)

    # THE clamp. Nothing above this line can widen risk; nothing below it can either.
    contracts = max(0, min(int(head.contracts), cap))
    if contracts < 1:
        return _stand_down("desk_head_sized_to_zero", cap, base_thesis, clock, started,
                           transcript, verdict)
    if contracts < cap:
        transcript.append({"seat": "system", "note": f"desk head trimmed {cap} -> {contracts}"})
    if int(head.contracts) > cap:
        transcript.append({"seat": "system",
                           "note": f"requested {int(head.contracts)} > cap {cap}; clamped to cap"})

    return DebateOutcome(
        approved=True, reason="approved", contracts=contracts, cap_contracts=cap,
        thesis=head.thesis or base_thesis, prediction=head.prediction, quant_verdict=verdict,
        elapsed_s=clock.elapsed, transcript=transcript, started_at=started,
    )


# --------------------------------------------------------------------------- stage runners

@dataclass
class _Task:
    """One seat running on a daemon thread, with a box for its result."""

    thread: threading.Thread
    box: dict


def _spawn(fn) -> _Task:
    """Start `fn` on a **daemon** thread.

    Daemon on purpose. Python cannot kill a thread, so a seat that hangs past its deadline is
    abandoned rather than stopped — and a non-daemon worker would then be re-joined at
    interpreter exit, turning a 90-second debate budget into however long the socket takes to
    give up. Daemon threads let the process exit on schedule; the real clients each carry their
    own transport timeout, so nothing leaks for long.
    """
    box: dict = {}

    def target() -> None:
        try:
            box["value"] = fn()
        except Exception as e:  # noqa: BLE001 - surfaced to the caller as an abstention
            box["error"] = e

    t = threading.Thread(target=target, daemon=True, name="iv-desk-seat")
    t.start()
    return _Task(thread=t, box=box)


def _collect(task: _Task, timeout: float, fallback):
    """Wait up to `timeout` for a seat. A blown deadline or a crash yields `fallback(msg)`."""
    task.thread.join(max(0.0, timeout))
    if task.thread.is_alive():
        return fallback(f"timeout after {timeout:.1f}s")
    if "error" in task.box:
        e = task.box["error"]
        return fallback(f"{type(e).__name__}: {e}")
    return task.box["value"]


def _run_quant(members: list[tuple[str, SeatClient]], signal: Any, selection: dict, cap: int,
               timeout: float) -> list[QuantBallot]:
    """Fan the same ballot out to every ensemble member at once, under one shared deadline."""
    running = [
        (model, _spawn(lambda c=client, m=model: seats.quant_ballot(
            c, m, signal, selection, cap, timeout)))
        for model, client in members
    ]
    deadline = time.monotonic() + timeout
    return [
        _collect(task, deadline - time.monotonic(),
                 lambda err, m=model: QuantBallot(model=m, ok=False, error=err))
        for model, task in running
    ]


def _run_arguers(client: SeatClient, signal: Any, selection: dict, cap: int,
                 timeout: float) -> tuple[Argument, Argument]:
    """Bull first, then Bear rebutting Bull. Sequential on purpose.

    Run in parallel the two seats answer the same question in isolation, and with one model at
    temperature 0 over near-identical prompts they return near-identical text — which is what
    the 30 Aug live test produced. A debate needs the second speaker to have heard the first.

    Each seat gets half the arguer budget. If Bull fails or times out, Bear still runs; it just
    argues into the void, which is no worse than the old behaviour.
    """
    half = max(timeout / 2, MIN_SEAT_TIMEOUT)
    deadline = time.monotonic() + timeout

    bull = _collect(_spawn(lambda: seats.argue(client, "bull", signal, selection, cap, half)),
                    min(half, deadline - time.monotonic()),
                    lambda err: Argument(role="bull", ok=False, error=err))

    left = deadline - time.monotonic()
    if left <= 0:
        return bull, Argument(role="bear", ok=False, error="arguer budget exhausted by bull")

    bear = _collect(
        _spawn(lambda: seats.argue(client, "bear", signal, selection, cap, min(half, left),
                                   opponent=bull if bull.ok else None)),
        min(half, left),
        lambda err: Argument(role="bear", ok=False, error=err))
    return bull, bear


def adversarial_ratio(bull: Argument, bear: Argument) -> float:
    """How different the two cases actually are, 0..1. 1.0 means identical text.

    A Bull and a Bear arguing opposite theses should never converge. When they do, the seat is
    broken rather than the market being unusually clear, so the number goes in the journal
    instead of being silently averaged away by the Desk Head.
    """
    if not (bull.ok and bear.ok):
        return 0.0
    return SequenceMatcher(None, bull.argument.lower(), bear.argument.lower()).ratio()


# --------------------------------------------------------------------------- debug helper

def _demo(outcome: DebateOutcome) -> str:                         # pragma: no cover
    return json.dumps(asdict(outcome), indent=2, default=str)
