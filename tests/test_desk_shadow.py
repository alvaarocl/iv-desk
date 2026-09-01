"""The shadow debate — `desk._maybe_shadow_debate`.

When VRP is rich but GEX vetoes a trade, the desk exercises the LLM desk anyway in
observation-only mode, so the journal has a real transcript against real market data even on a
day the risk gates never let a genuine opening through. These tests cover the gate that decides
*whether* it fires, and the two safety properties that make it inert: it never calls
`ex.open_trade` and it never mutates the portfolio state it was handed.
"""

from __future__ import annotations

import pytest

from agent import debate, desk, journal, risk
from agent.config import Params

STAMP = "2026-09-02T10:00:00-04:00"  # matches conftest's spy_chain expiration (2026-09-03, 1 DTE)


def _signal(**over) -> desk.sg.Signal:
    base = dict(
        underlying="SPY", spot=775.0, sell_premium=False, structure="none", bias="neutral",
        regime="chop", expiration="2026-09-03", vrp=0.03, vrp_ratio=1.35, atm_iv=0.16,
        rv_hat=0.12, gex=-2.0e7, gex_sign=-1, gex_norm=-0.40, gex_state=-1, skew=0.01,
        stand_down="gex", notes="stand down [gex]", chain={},
    )
    base.update(over)
    return desk.sg.Signal(**base)


def _pf() -> risk.PortfolioState:
    return risk.PortfolioState(nav=100_000.0, peak_nav=100_000.0, open_risk=1234.0,
                               n_positions=2, net_delta=0.05, day_pnl=-10.0)


@pytest.fixture
def wide_params() -> Params:
    """conftest's spy_chain is built 4 wide (769/765, 781/785) — the real Params default
    (width_spy=2.0) would not match any strike in it."""
    return Params(width_spy=4.0)


@pytest.fixture(autouse=True)
def _isolate_journal(tmp_path, monkeypatch):
    """Never let a test read or write the repo's real data/journal.jsonl.

    `desk.py` does `from .journal import JOURNAL`, which binds a SEPARATE name in desk's own
    namespace — patching `desk.JOURNAL` alone leaves `journal.append()` (the function actually
    doing the write, imported into desk.py by reference) still pointed at the real path. Both
    names have to move together or `_shadow_seen_today`'s reads and `append()`'s writes land in
    two different files, and — as a first draft of this fixture proved the hard way — the real
    one gets polluted with test data.
    """
    fake = tmp_path / "journal.jsonl"
    monkeypatch.setattr(desk, "JOURNAL", fake)
    monkeypatch.setattr(journal, "JOURNAL", fake)


@pytest.fixture
def stub_review_open(monkeypatch):
    """Replace the real (networked) debate with a call-counting stub."""
    calls: list[dict] = []

    def fake(signal, selection, cap, thesis, **kw):
        calls.append({"signal": signal, "selection": selection, "cap": cap, "thesis": thesis,
                     **kw})
        return debate.DebateOutcome(approved=True, reason="approved", contracts=cap,
                                    cap_contracts=cap, thesis=thesis, shadow=kw.get("shadow", False))

    monkeypatch.setattr(desk.debate, "review_open", fake)
    return calls


# ---------- fires only on a real GEX veto ----------


@pytest.mark.parametrize("stand_down", ["", "vrp", "trend", "data", "expiration"])
def test_never_fires_on_anything_but_gex(stand_down, stub_review_open, wide_params,
                                          spy_chain, oi_all_liquid):
    s = _signal(stand_down=stand_down, chain=spy_chain)
    desk._maybe_shadow_debate("SPY", s, {"oi": oi_all_liquid}, wide_params, _pf(), 1.0, STAMP)
    assert stub_review_open == []


def test_fires_on_a_genuine_gex_veto(stub_review_open, wide_params, spy_chain, oi_all_liquid):
    s = _signal(chain=spy_chain)
    desk._maybe_shadow_debate("SPY", s, {"oi": oi_all_liquid}, wide_params, _pf(), 1.0, STAMP)

    assert len(stub_review_open) == 1
    call = stub_review_open[0]
    assert call["shadow"] is True
    assert call["cap"] >= 1
    # chop + neutral -> iron_condor, per _fallback_structure and today's real tape
    assert call["signal"].structure == "iron_condor"
    # the facts shown to the seats must stay honest about the veto
    assert call["signal"].stand_down == "gex"
    assert call["signal"].sell_premium is False


# ---------- dedupe: at most once per underlying per day ----------


def test_does_not_repeat_the_same_underlying_same_day(stub_review_open, wide_params,
                                                        spy_chain, oi_all_liquid, tmp_path):
    journal = tmp_path / "journal.jsonl"
    journal.write_text(
        '{"ts": "2026-09-02T09:00:00-04:00", "event": "debate", "underlying": "SPY", '
        '"shadow": true, "approved": true}\n', encoding="utf-8")
    s = _signal(chain=spy_chain)
    desk._maybe_shadow_debate("SPY", s, {"oi": oi_all_liquid}, wide_params, _pf(), 1.0, STAMP)
    assert stub_review_open == []


def test_a_different_underlying_the_same_day_still_fires(stub_review_open, wide_params,
                                                          spy_chain, oi_all_liquid, tmp_path):
    journal = tmp_path / "journal.jsonl"
    journal.write_text(
        '{"ts": "2026-09-02T09:00:00-04:00", "event": "debate", "underlying": "SPY", '
        '"shadow": true, "approved": true}\n', encoding="utf-8")
    s = _signal(underlying="QQQ", chain=spy_chain)
    desk._maybe_shadow_debate("QQQ", s, {"oi": oi_all_liquid}, wide_params, _pf(), 1.0, STAMP)
    assert len(stub_review_open) == 1


def test_the_same_underlying_the_next_day_fires_again(stub_review_open, wide_params,
                                                       spy_chain, oi_all_liquid, tmp_path):
    journal = tmp_path / "journal.jsonl"
    journal.write_text(
        '{"ts": "2026-09-01T09:00:00-04:00", "event": "debate", "underlying": "SPY", '
        '"shadow": true, "approved": true}\n', encoding="utf-8")
    s = _signal(chain=spy_chain)
    desk._maybe_shadow_debate("SPY", s, {"oi": oi_all_liquid}, wide_params, _pf(), 1.0, STAMP)
    assert len(stub_review_open) == 1


def test_a_real_non_shadow_debate_line_does_not_count_toward_the_dedupe(
        stub_review_open, wide_params, spy_chain, oi_all_liquid, tmp_path):
    """A real (non-shadow) debate for this underlying earlier today must not suppress the
    shadow debate — they answer different questions."""
    journal = tmp_path / "journal.jsonl"
    journal.write_text(
        '{"ts": "2026-09-02T09:00:00-04:00", "event": "debate", "underlying": "SPY", '
        '"shadow": false, "approved": false}\n', encoding="utf-8")
    s = _signal(chain=spy_chain)
    desk._maybe_shadow_debate("SPY", s, {"oi": oi_all_liquid}, wide_params, _pf(), 1.0, STAMP)
    assert len(stub_review_open) == 1


# ---------- the DESK_SHADOW_DEBATE kill switch ----------


def test_respects_its_own_off_switch(monkeypatch, stub_review_open, wide_params,
                                     spy_chain, oi_all_liquid):
    monkeypatch.setenv("DESK_SHADOW_DEBATE", "off")
    s = _signal(chain=spy_chain)
    desk._maybe_shadow_debate("SPY", s, {"oi": oi_all_liquid}, wide_params, _pf(), 1.0, STAMP)
    assert stub_review_open == []


# ---------- safe by construction: never opens, never mutates the book ----------


def test_never_calls_open_trade_even_when_the_stub_approves(monkeypatch, stub_review_open,
                                                             wide_params, spy_chain, oi_all_liquid):
    def _boom(*a, **k):
        raise AssertionError("shadow debate must never call ex.open_trade")

    monkeypatch.setattr(desk.ex, "open_trade", _boom)
    s = _signal(chain=spy_chain)
    desk._maybe_shadow_debate("SPY", s, {"oi": oi_all_liquid}, wide_params, _pf(), 1.0, STAMP)
    # got this far without the stub raising -> open_trade was never reached
    assert len(stub_review_open) == 1


def test_never_mutates_the_portfolio_state(stub_review_open, wide_params, spy_chain, oi_all_liquid):
    pf = _pf()
    before = (pf.n_positions, pf.open_risk, pf.net_delta, pf.day_pnl)
    s = _signal(chain=spy_chain)
    desk._maybe_shadow_debate("SPY", s, {"oi": oi_all_liquid}, wide_params, pf, 1.0, STAMP)
    after = (pf.n_positions, pf.open_risk, pf.net_delta, pf.day_pnl)
    assert before == after


# ---------- journaling ----------


def test_journals_the_debate_event_with_the_shadow_flag(stub_review_open, wide_params,
                                                         spy_chain, oi_all_liquid, tmp_path):
    s = _signal(chain=spy_chain)
    desk._maybe_shadow_debate("SPY", s, {"oi": oi_all_liquid}, wide_params, _pf(), 1.0, STAMP)

    lines = (tmp_path / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert '"event": "debate"' in lines[0]
    assert '"shadow": true' in lines[0]
    assert '"underlying": "SPY"' in lines[0]


def test_no_liquid_structure_is_a_silent_skip_not_an_error(stub_review_open, wide_params):
    """An empty chain means _pick returns None — nothing to shadow-debate, no crash."""
    s = _signal(chain={})
    desk._maybe_shadow_debate("SPY", s, {"oi": {}}, wide_params, _pf(), 1.0, STAMP)
    assert stub_review_open == []
