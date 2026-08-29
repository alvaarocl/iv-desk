"""The seats at the desk — the only place in the repo where an LLM is called.

Four personas, two providers:

* **Quant** — an ensemble of open models served by Featherless (OpenAI-compatible endpoint).
  Each model gets the same ballot and votes independently; `consensus()` needs a strict
  majority or the seat abstains.
* **Bull / Bear** — Anthropic (`claude-sonnet-5`). Argue the direction of the underlying and
  are *required* to cite concrete `Signal` fields; an argument that cites nothing (or cites
  invented fields) is discarded as unusable, not accepted at face value.
* **Desk Head** — Anthropic. Picks the final size and writes a falsifiable prediction.

Design rules that hold for every seat in this module:

1. **Transport is injected.** Every seat takes a `SeatClient` (anything with `.complete()`),
   so `tests/test_debate.py` runs the whole desk against doubles with no network and no keys.
2. **Bad output is abstention, never approval.** Unparseable JSON, a missing field, an
   out-of-range number and a transport error all raise `SeatError`, which the orchestrator in
   `debate.py` turns into "do not trade". There is no code path where garbage means "yes".
3. **No seat here can widen risk.** These functions only *report* what the model said. The
   clamping to the Risk Officer's cap happens in `debate.py`, in plain Python, after the fact.
4. **Bounded cost.** Small `max_tokens` per seat, compact prompts (the option chain is never
   sent), one bounded SDK retry.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

# Bull / Bear / Desk Head. Note: `claude-sonnet-5` rejects `temperature`/`top_p`/`top_k`
# with a 400 — determinism is bought with the prompt, not with sampling params.
ANTHROPIC_MODEL = os.environ.get("DESK_DEBATE_ANTHROPIC_MODEL", "claude-sonnet-5")

MAX_QUANT_MODELS = 3          # keeps the $25 Featherless coupon bounded
QUANT_MAX_TOKENS = 400
ARGUER_MAX_TOKENS = 700
DESK_HEAD_MAX_TOKENS = 900


class SeatError(RuntimeError):
    """A seat produced nothing usable — transport failure, timeout, or invalid output.

    Always treated as an abstention upstream. Never as approval.
    """


class SeatClient(Protocol):
    """Minimal transport contract. Real providers and test doubles both satisfy it."""

    def complete(self, *, system: str, user: str, max_tokens: int, timeout: float) -> str:
        ...


# --------------------------------------------------------------------------- transports

@dataclass
class AnthropicSeatClient:
    """Bull / Bear / Desk Head. Lazy import so the module stays importable without the SDK."""

    model: str = ANTHROPIC_MODEL
    api_key: str | None = None
    effort: str = "low"           # output_config.effort — cost lever, GA on claude-sonnet-5
    max_retries: int = 1
    _client: Any = field(default=None, repr=False)

    def complete(self, *, system: str, user: str, max_tokens: int, timeout: float) -> str:
        try:
            import anthropic
        except ImportError as e:                                  # pragma: no cover
            raise SeatError(f"anthropic sdk unavailable: {e}") from e
        if self._client is None:
            key = self.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            if not key:
                raise SeatError("ANTHROPIC_API_KEY not set")
            self._client = anthropic.Anthropic(api_key=key, max_retries=self.max_retries)
        try:
            msg = self._client.with_options(timeout=timeout).messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": self.effort},
            )
        except Exception as e:  # every transport error becomes exactly one abstention
            raise SeatError(f"{self.model}: {type(e).__name__}: {e}") from e
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


@dataclass
class FeatherlessSeatClient:
    """One member of the Quant ensemble. Featherless speaks the OpenAI chat-completions API."""

    model: str
    base_url: str
    api_key: str
    max_retries: int = 1

    def complete(self, *, system: str, user: str, max_tokens: int, timeout: float) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:                                  # pragma: no cover
            raise SeatError(f"openai sdk unavailable: {e}") from e
        try:
            client = OpenAI(base_url=self.base_url, api_key=self.api_key,
                            timeout=timeout, max_retries=self.max_retries)
            r = client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.0,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
            )
        except Exception as e:  # every transport error becomes exactly one abstention
            raise SeatError(f"{self.model}: {type(e).__name__}: {e}") from e
        return (r.choices[0].message.content or "") if r.choices else ""


# --------------------------------------------------------------------------- parsing

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_json_object(raw: str) -> dict:
    """Tolerant JSON extraction. Anything that is not a JSON object raises `SeatError`.

    Handles the three things models actually do: clean JSON, a ```json fence, and prose
    wrapped around an object. Everything else is an abstention.
    """
    if not raw or not raw.strip():
        raise SeatError("empty response")
    text = raw.strip()
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    obj: Any
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise SeatError("no json object in response") from None
        try:
            obj = json.loads(text[start:end + 1])
        except json.JSONDecodeError as e:
            raise SeatError(f"unparseable json: {e}") from None
    if not isinstance(obj, dict):
        raise SeatError("json root is not an object")
    return obj


def _str_field(obj: dict, key: str, *, allowed: set[str] | None = None) -> str:
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip():
        raise SeatError(f"missing or empty field {key!r}")
    v = v.strip()
    if allowed is not None and v.lower() not in allowed:
        raise SeatError(f"field {key!r} = {v!r} not in {sorted(allowed)}")
    return v


def _float_field(obj: dict, key: str) -> float:
    v = obj.get(key)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise SeatError(f"field {key!r} is not a number")
    return float(v)


# --------------------------------------------------------------------------- signal facts

def signal_facts(signal: Any) -> dict:
    """Serializable view of a `Signal`, minus the option chain (too big, and not needed)."""
    raw = vars(signal) if hasattr(signal, "__dict__") else dict(signal)
    return {k: v for k, v in raw.items() if k != "chain"}


def _facts_block(signal: Any) -> str:
    return json.dumps(signal_facts(signal), indent=2, default=str, sort_keys=True)


def _trade_block(signal: Any, selection: dict, cap_contracts: int) -> str:
    return json.dumps({
        "underlying": getattr(signal, "underlying", "?"),
        "structure": getattr(signal, "structure", "?"),
        "expiration": getattr(signal, "expiration", "?"),
        "strikes": selection.get("strikes"),
        "credit_per_contract": round(float(selection.get("credit", 0.0)), 2),
        "width": selection.get("width"),
        "risk_officer_cap_contracts": cap_contracts,
    }, indent=2, default=str, sort_keys=True)


# --------------------------------------------------------------------------- Quant seat

QUANT_SYSTEM = (
    "You are a quantitative options analyst on a systematic volatility-selling desk. "
    "A deterministic Python signal layer has already selected a structure and strikes. "
    "Your only job is to confirm or reject that selection on the evidence given. "
    "You do NOT size trades and you cannot change the strikes. "
    "Answer with a single JSON object and nothing else:\n"
    '{"vote": "confirm" | "reject", "structure": "<the structure you believe is right>", '
    '"confidence": <0..1>, "reason": "<one sentence, cite numbers>"}\n'
    "Vote 'reject' if the volatility risk premium looks like a measurement artifact, if the "
    "dealer gamma read does not support a short-premium trade, or if the credit is too thin "
    "for the width. When in doubt, reject: standing down is free, a broken short strike is not."
)


@dataclass
class QuantBallot:
    model: str
    ok: bool
    vote: str = ""            # confirm | reject
    structure: str = ""
    confidence: float = 0.0
    reason: str = ""
    error: str = ""
    raw: str = ""

    def to_record(self) -> dict:
        return {"seat": "quant", "model": self.model, "ok": self.ok, "vote": self.vote,
                "structure": self.structure, "confidence": round(self.confidence, 3),
                "reason": self.reason, "error": self.error, "raw": self.raw[:600]}


def quant_prompt(signal: Any, selection: dict, cap_contracts: int) -> str:
    return (f"SIGNAL (deterministic, computed from the option surface):\n{_facts_block(signal)}\n\n"
            f"PROPOSED TRADE:\n{_trade_block(signal, selection, cap_contracts)}\n\n"
            "Confirm or reject. JSON only.")


def quant_ballot(client: SeatClient, model: str, signal: Any, selection: dict,
                 cap_contracts: int, timeout: float) -> QuantBallot:
    """Run one ensemble member. Never raises — a failure is a ballot with `ok=False`."""
    raw = ""
    try:
        raw = client.complete(system=QUANT_SYSTEM,
                              user=quant_prompt(signal, selection, cap_contracts),
                              max_tokens=QUANT_MAX_TOKENS, timeout=timeout)
        obj = parse_json_object(raw)
        vote = _str_field(obj, "vote", allowed={"confirm", "reject"}).lower()
        structure = _str_field(obj, "structure")
        conf = _float_field(obj, "confidence") if "confidence" in obj else 0.5
        if not 0.0 <= conf <= 1.0:
            raise SeatError(f"confidence {conf} out of range")
        return QuantBallot(model=model, ok=True, vote=vote, structure=structure, confidence=conf,
                           reason=str(obj.get("reason", ""))[:400], raw=raw)
    except SeatError as e:
        return QuantBallot(model=model, ok=False, error=str(e)[:300], raw=raw)
    except Exception as e:  # noqa: BLE001 - any seat failure must degrade to abstention
        return QuantBallot(model=model, ok=False, error=f"{type(e).__name__}: {e}"[:300], raw=raw)


def consensus(ballots: list[QuantBallot], n_models: int, expected_structure: str) -> tuple[str, str]:
    """Strict-majority vote over the ensemble. -> (verdict, reason).

    verdict is one of `confirm`, `reject`, `no_consensus`. The majority is computed over the
    number of models *dispatched*, not over the ones that answered: if two of three models time
    out, the survivor cannot carry the vote. A majority that confirms a structure other than
    the one the deterministic layer selected is not consensus either — the desk only trades the
    structure `signal.py` picked, so a disagreement there is a stand-down.
    """
    required = n_models // 2 + 1
    valid = [b for b in ballots if b.ok]
    confirms = [b for b in valid if b.vote == "confirm"]
    rejects = [b for b in valid if b.vote == "reject"]
    if len(rejects) >= required:
        return "reject", f"{len(rejects)}/{n_models} models reject the setup"
    if len(confirms) >= required:
        on_structure = [b for b in confirms if b.structure.strip().lower() == expected_structure]
        if len(on_structure) < required:
            return "no_consensus", (
                f"{len(confirms)}/{n_models} confirm but only {len(on_structure)} agree on "
                f"{expected_structure}")
        return "confirm", f"{len(confirms)}/{n_models} models confirm {expected_structure}"
    return "no_consensus", (
        f"{len(confirms)} confirm / {len(rejects)} reject / {len(ballots) - len(valid)} "
        f"unusable, need {required} of {n_models}")


# --------------------------------------------------------------------------- Bull / Bear

_ARGUER_SYSTEM = (
    "You are the ROLE seat on a systematic options desk, arguing the direction of the "
    "underlying over the life of a short-dated trade. You are NOT deciding whether to trade and "
    "you have no say over size — you supply one side of the argument, honestly and briefly.\n"
    "Hard requirement: every claim must be anchored to the numeric SIGNAL fields you are given. "
    "Cite the exact field names you used in `cited_fields`; at least two, and only names that "
    "actually exist in the SIGNAL object. Do not invent data you were not given — you have no "
    "price chart, no news feed and no positioning data beyond these fields.\n"
    "Answer with a single JSON object and nothing else:\n"
    '{"argument": "<3-5 sentences>", "cited_fields": ["field", "field"], '
    '"confidence": <0..1>, "key_risk": "<the strongest point against your own case>"}'
)

BULL_SYSTEM = _ARGUER_SYSTEM.replace("ROLE", "Bull")
BEAR_SYSTEM = _ARGUER_SYSTEM.replace("ROLE", "Bear")


@dataclass
class Argument:
    role: str                 # bull | bear
    ok: bool
    argument: str = ""
    cited_fields: list[str] = field(default_factory=list)
    confidence: float = 0.0
    key_risk: str = ""
    error: str = ""
    raw: str = ""

    def to_record(self) -> dict:
        return {"seat": self.role, "ok": self.ok, "argument": self.argument,
                "cited_fields": self.cited_fields, "confidence": round(self.confidence, 3),
                "key_risk": self.key_risk, "error": self.error, "raw": self.raw[:600]}


def arguer_prompt(signal: Any, selection: dict, cap_contracts: int) -> str:
    facts = signal_facts(signal)
    return (f"SIGNAL fields you may cite: {sorted(facts)}\n\n"
            f"SIGNAL:\n{json.dumps(facts, indent=2, default=str, sort_keys=True)}\n\n"
            f"PROPOSED TRADE:\n{_trade_block(signal, selection, cap_contracts)}\n\n"
            "Make your case. JSON only.")


def argue(client: SeatClient, role: str, signal: Any, selection: dict, cap_contracts: int,
          timeout: float) -> Argument:
    """Run the Bull or Bear seat. Never raises; `ok=False` means the seat is unusable.

    An argument that cites fewer than two real `Signal` fields is rejected: the whole point of
    this seat is that it reasons over the surface we measured, not over vibes.
    """
    system = BULL_SYSTEM if role == "bull" else BEAR_SYSTEM
    allowed = set(signal_facts(signal))
    raw = ""
    try:
        raw = client.complete(system=system,
                              user=arguer_prompt(signal, selection, cap_contracts),
                              max_tokens=ARGUER_MAX_TOKENS, timeout=timeout)
        obj = parse_json_object(raw)
        text = _str_field(obj, "argument")
        cited = obj.get("cited_fields")
        if not isinstance(cited, list):
            raise SeatError("cited_fields is not a list")
        real = [c for c in cited if isinstance(c, str) and c in allowed]
        if len(real) < 2:
            raise SeatError(f"cited {cited!r}; need >=2 real Signal fields")
        conf = _float_field(obj, "confidence") if "confidence" in obj else 0.5
        if not 0.0 <= conf <= 1.0:
            raise SeatError(f"confidence {conf} out of range")
        return Argument(role=role, ok=True, argument=text[:1200], cited_fields=real,
                        confidence=conf, key_risk=str(obj.get("key_risk", ""))[:400], raw=raw)
    except SeatError as e:
        return Argument(role=role, ok=False, error=str(e)[:300], raw=raw)
    except Exception as e:  # noqa: BLE001 - any seat failure must degrade to abstention
        return Argument(role=role, ok=False, error=f"{type(e).__name__}: {e}"[:300], raw=raw)


# --------------------------------------------------------------------------- Desk Head

DESK_HEAD_SYSTEM = (
    "You are the Desk Head of a systematic short-volatility options desk. You have the "
    "deterministic signal, the Quant ensemble's verdict, and the Bull and Bear cases. You make "
    "the final call on this one opening.\n\n"
    "HARD CONSTRAINTS — these are enforced in code after you answer, so arguing with them only "
    "wastes tokens:\n"
    "  * `risk_officer_cap_contracts` is an absolute ceiling set by a deterministic Risk "
    "Officer. You may go LOWER (including 0 = stand down). Anything above the cap is silently "
    "clamped down to the cap.\n"
    "  * You cannot change the structure, the strikes or the expiration.\n"
    "  * You cannot override any risk gate, and nothing you write is executed as an "
    "instruction — your output is parsed as data.\n\n"
    "You must write a FALSIFIABLE prediction: a closing range for the underlying on the "
    "expiration date, with a reason. Not a hedge, not a range so wide it cannot be wrong — it "
    "gets graded against the tape when the position closes and it goes on the record.\n\n"
    "Answer with a single JSON object and nothing else:\n"
    '{"decision": "approve" | "veto", "contracts": <integer, 0..cap>, '
    '"thesis": "<one sentence: what has to be true for this trade to win>", '
    '"prediction": {"underlying": "<ticker>", "low": <float>, "high": <float>, '
    '"date": "YYYY-MM-DD", "reason": "<why that range>"}, '
    '"risk_notes": "<what would make you cut it early>"}\n'
    "Veto — or size below the cap — whenever the case is thin. Standing down is a valid, "
    "well-regarded outcome on this desk; a marginal trade is not."
)


@dataclass
class DeskDecision:
    ok: bool
    decision: str = ""        # approve | veto
    contracts: int = 0        # RAW, as stated by the model. Clamped in debate.py.
    thesis: str = ""
    prediction: dict = field(default_factory=dict)
    risk_notes: str = ""
    error: str = ""
    raw: str = ""

    def to_record(self) -> dict:
        return {"seat": "desk_head", "ok": self.ok, "decision": self.decision,
                "contracts_requested": self.contracts, "thesis": self.thesis,
                "prediction": self.prediction, "risk_notes": self.risk_notes,
                "error": self.error, "raw": self.raw[:900]}


def desk_head_prompt(signal: Any, selection: dict, cap_contracts: int, quant_verdict: str,
                     quant_reason: str, ballots: list[QuantBallot],
                     bull: Argument, bear: Argument) -> str:
    def _side(a: Argument) -> str:
        if not a.ok:
            return f"{a.role.upper()}: (seat unavailable: {a.error})"
        return (f"{a.role.upper()} (confidence {a.confidence:.2f}, cited {a.cited_fields}):\n"
                f"{a.argument}\nStrongest counter to its own case: {a.key_risk}")

    quant_lines = "\n".join(
        f"  - {b.model}: {b.vote or 'UNUSABLE'} ({b.reason or b.error})" for b in ballots)
    return (
        f"SIGNAL:\n{_facts_block(signal)}\n\n"
        f"PROPOSED TRADE:\n{_trade_block(signal, selection, cap_contracts)}\n\n"
        f"QUANT ENSEMBLE: {quant_verdict} — {quant_reason}\n{quant_lines}\n\n"
        f"{_side(bull)}\n\n{_side(bear)}\n\n"
        f"The Risk Officer's cap is {cap_contracts} contract(s). Decide. JSON only."
    )


def desk_head(client: SeatClient, signal: Any, selection: dict, cap_contracts: int,
              quant_verdict: str, quant_reason: str, ballots: list[QuantBallot],
              bull: Argument, bear: Argument, timeout: float) -> DeskDecision:
    """Run the Desk Head seat. Never raises; `ok=False` is an abstention.

    Validates the falsifiable prediction: a range that is inverted, non-numeric or nowhere near
    the spot we measured is not a prediction, so it does not earn a trade. A missing or
    unparseable date is filled deterministically with the trade's expiration rather than
    rejected — the date is ours to know, unlike the range.
    """
    raw = ""
    try:
        raw = client.complete(
            system=DESK_HEAD_SYSTEM,
            user=desk_head_prompt(signal, selection, cap_contracts, quant_verdict, quant_reason,
                                  ballots, bull, bear),
            max_tokens=DESK_HEAD_MAX_TOKENS, timeout=timeout)
        obj = parse_json_object(raw)
        decision = _str_field(obj, "decision", allowed={"approve", "veto"}).lower()
        thesis = _str_field(obj, "thesis")
        contracts = obj.get("contracts", 0)
        if isinstance(contracts, bool) or not isinstance(contracts, (int, float)):
            raise SeatError("contracts is not a number")
        contracts = int(contracts)
        pred = _validate_prediction(obj.get("prediction"), signal) if decision == "approve" else {}
        return DeskDecision(ok=True, decision=decision, contracts=contracts, thesis=thesis[:600],
                            prediction=pred, risk_notes=str(obj.get("risk_notes", ""))[:400],
                            raw=raw)
    except SeatError as e:
        return DeskDecision(ok=False, error=str(e)[:300], raw=raw)
    except Exception as e:  # noqa: BLE001 - any seat failure must degrade to abstention
        return DeskDecision(ok=False, error=f"{type(e).__name__}: {e}"[:300], raw=raw)


def _validate_prediction(pred: Any, signal: Any) -> dict:
    if not isinstance(pred, dict):
        raise SeatError("prediction is missing or not an object")
    low, high = _float_field(pred, "low"), _float_field(pred, "high")
    if not low < high:
        raise SeatError(f"prediction range [{low}, {high}] is not ordered")
    spot = float(getattr(signal, "spot", 0.0) or 0.0)
    if spot > 0 and not (0.5 * spot <= low and high <= 1.5 * spot):
        raise SeatError(f"prediction range [{low}, {high}] implausible vs spot {spot}")
    date = pred.get("date")
    expiration = str(getattr(signal, "expiration", ""))
    if not (isinstance(date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date.strip())):
        date = expiration                     # deterministic fill; the date is ours, not the LLM's
    return {"underlying": str(getattr(signal, "underlying", "")),
            "low": round(low, 2), "high": round(high, 2), "date": str(date).strip(),
            "expiration": expiration, "reason": str(pred.get("reason", ""))[:400],
            "graded": False}
