"""lane/ejecucion — the four bugs that had to be fixed before going live (issues #1, #2, #22, #3)."""

from __future__ import annotations

import pytest

from agent import execution as ex

# ---------- issue #2: exit-manager units ----------

def _mk_trade(entry_credit_ps: float, width_ps: float = 4.0, contracts: int = 1,
              expiration: str = "2026-09-10") -> ex.Trade:
    # `expiration` deliberately outside the 31 Aug - 4 Sep competition window: `manage_exits`
    # reads the real wall clock (agent/execution.py:395) and force-closes on expiry day
    # regardless of P&L thresholds, so a trade dated "today" during the live event would make
    # these threshold tests fail on exactly the days the desk is actually trading — as
    # "2026-09-03" did the moment 3 Sep arrived for real.
    return ex.Trade(
        id="t1", underlying="SPY", structure="iron_condor", expiration=expiration,
        legs=[
            {"symbol": "SPY260903P00769000", "side": "sell", "ratio_qty": "1",
             "position_intent": "sell_to_open"},
            {"symbol": "SPY260903P00765000", "side": "buy", "ratio_qty": "1",
             "position_intent": "buy_to_open"},
        ],
        contracts=contracts, entry_credit=entry_credit_ps * 100, width=width_ps,
        max_loss=(width_ps - entry_credit_ps) * 100 * contracts, thesis="x",
        opened_at="2026-09-02T10:00:00-04:00", status="open",
    )


@pytest.mark.parametrize(
    ("debit_ps", "expected"),
    [(0.60, "take_profit"),   # credit 1.20 -> take at 0.60
     (1.00, None),            # between take and stop -> hold
     (2.40, "stop")],         # >= 2x credit -> stop
)
def test_exit_thresholds_compare_like_units(monkeypatch, params, debit_ps, expected):
    trade = _mk_trade(1.20)
    monkeypatch.setattr(ex, "_load_all", lambda: [trade])
    monkeypatch.setattr(ex, "_rewrite", lambda t: None)
    monkeypatch.setattr(ex, "_combo_cost_to_close", lambda t, chain: debit_ps * 100)
    monkeypatch.setattr(ex.md, "option_chain_snapshot", lambda *a, **k: {})

    actions = ex.manage_exits(params, mode="dry_run")

    if expected is None:
        assert actions == []
    else:
        assert actions and actions[0]["reason"] == expected


def test_pnl_matches_credit_minus_debit_in_dollars(monkeypatch, params):
    trade = _mk_trade(1.20, contracts=3)
    monkeypatch.setattr(ex, "_load_all", lambda: [trade])
    monkeypatch.setattr(ex, "_rewrite", lambda t: None)
    monkeypatch.setattr(ex, "_combo_cost_to_close", lambda t, chain: 0.50 * 100)
    monkeypatch.setattr(ex.md, "option_chain_snapshot", lambda *a, **k: {})

    actions = ex.manage_exits(params, mode="dry_run")

    # (1.20 - 0.50) * 100 * 3 contracts = 210
    assert actions[0]["pnl"] == pytest.approx(210.0)


# ---------- issue #1: signed limit price ----------

def test_entry_limit_is_negative_for_a_credit_structure(monkeypatch):
    captured = {}

    def fake_submit(legs, qty, limit_price, *, client_order_id=None, tif="day"):
        captured["limit_price"] = limit_price
        return {"id": "o1", "status": "filled", "filled_avg_price": str(-limit_price)}

    monkeypatch.setattr(ex.broker, "submit_mleg", fake_submit)
    monkeypatch.setattr(ex.broker, "get_order", lambda **k: None)
    monkeypatch.setattr(ex, "_await_fill", lambda oid: {"status": "filled",
                                                        "filled_avg_price": "-1.10"})
    monkeypatch.setattr(ex, "_append", lambda t: None)

    sig = type("S", (), {"underlying": "SPY", "expiration": "2026-09-03",
                         "structure": "iron_condor"})()
    sel = {"legs": _mk_trade(1.20).legs, "credit": 1.20, "width": 4.0, "strikes": {}}
    ex.open_trade(sig, sel, contracts=1, thesis="x", mode="live")

    assert captured["limit_price"] < 0


def test_submit_mleg_rejects_zero_limit():
    with pytest.raises(ValueError, match="non-zero"):
        ex.broker.submit_mleg([], 1, 0.0)


# ---------- issue #22: liquidity gate / no silent zero ----------

def test_mid_never_falls_back_to_zero():
    assert ex._mid_ps({"latestQuote": {"bp": 1.0, "ap": 1.2}}) == pytest.approx(1.1)
    assert ex._mid_ps({"latestQuote": {"bp": 1.0, "ap": 0.0}}) is None
    assert ex._mid_ps({"latestTrade": {"p": 1.5}}) is None      # no two-sided quote -> None


def test_illiquid_strike_is_excluded(spy_chain, oi_all_liquid, params):
    rows = ex._by_type_delta(spy_chain, "P", oi_all_liquid, params.min_oi if hasattr(params, "min_oi")
                             else ex.MIN_OI, ex.MAX_SPREAD_FRAC)
    syms = {r[2] for r in rows}
    assert "SPY260903P00760000" not in syms          # one-sided quote -> filtered
    assert "SPY260903P00769000" in syms


def test_low_oi_strike_is_excluded(spy_chain, params):
    oi = {"SPY260903P00769000": 100, "SPY260903P00765000": 4000}     # short put below the floor
    rows = ex._by_type_delta(spy_chain, "P", oi, ex.MIN_OI, ex.MAX_SPREAD_FRAC)
    assert "SPY260903P00769000" not in {r[2] for r in rows}


def test_condor_credit_is_positive_and_bounded(spy_chain, oi_all_liquid, params):
    sel = ex.select_condor(spy_chain, short_delta=0.18, width=4.0, oi=oi_all_liquid, params=params)
    assert sel is not None
    assert 0 < sel["credit"] < sel["width"]


# ---------- issue #3: asynchronous fills ----------

def test_unfilled_entry_stays_pending(monkeypatch):
    monkeypatch.setattr(ex.broker, "get_order", lambda **k: None)

    def _new_order(*a, **k):
        return {"id": "o9", "status": "new"}

    monkeypatch.setattr(ex.broker, "submit_mleg", _new_order)
    monkeypatch.setattr(ex, "_await_fill", lambda oid: {"status": "new"})
    monkeypatch.setattr(ex, "_append", lambda t: None)

    sig = type("S", (), {"underlying": "QQQ", "expiration": "2026-09-03",
                         "structure": "iron_condor"})()
    sel = {"legs": _mk_trade(1.0).legs, "credit": 1.0, "width": 4.0, "strikes": {}}
    t = ex.open_trade(sig, sel, contracts=1, thesis="x", mode="live")

    assert t.status == "pending_open"


def test_duplicate_client_order_id_is_not_resubmitted(monkeypatch):
    calls = []
    monkeypatch.setattr(ex.broker, "get_order", lambda **k: {"id": "existing", "status": "new"})
    monkeypatch.setattr(ex.broker, "submit_mleg",
                        lambda *a, **k: calls.append(1) or {"id": "x"})
    monkeypatch.setattr(ex, "_append", lambda t: None)

    sig = type("S", (), {"underlying": "SPY", "expiration": "2026-09-03",
                         "structure": "iron_condor"})()
    sel = {"legs": _mk_trade(1.0).legs, "credit": 1.0, "width": 4.0, "strikes": {}}
    ex.open_trade(sig, sel, contracts=1, thesis="x", mode="live")

    assert calls == []


def test_reconcile_flags_unexpected_equity(monkeypatch):
    monkeypatch.setattr(ex, "_load_active", list)
    monkeypatch.setattr(ex.broker, "positions", lambda: [
        {"symbol": "SPY", "asset_class": "us_equity", "qty": "100", "market_value": "77000"},
    ])
    events = ex.reconcile(mode="dry_run")
    assert any(e.get("alert") == "unexpected_equity_position" for e in events)
    assert ex.has_unexpected_equity() is True
