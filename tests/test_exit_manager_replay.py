"""Exit-manager lifecycle — driven through price trajectories, with no market (issue #23, B4).

`test_execution.py` checks the take/stop/expiry thresholds in isolation. This drives a position
through a *sequence* of prices across simulated time and asserts:

- the right reason fires at the right step and **exactly once** (a closed trade is never re-closed);
- `expiry_close` still fires on a run *after* 15:45 ET, i.e. when the 15:30/15:45 tick was skipped;
- in `live` mode the close order is submitted, the trade sits `pending_close`, and `reconcile`
  finalizes it once the broker reports the fill;
- the whole path runs through the real `_combo_cost_to_close` on a synthetic chain, not only a stub.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from agent import execution as ex

ET = ZoneInfo("America/New_York")


# --------------------------------------------------------------------------- helpers

def _condor(credit_ps: float, *, contracts: int = 1, expiration: str = "2026-09-03") -> ex.Trade:
    legs = [
        {"symbol": "SPY260903P00769000", "side": "sell", "ratio_qty": "1",
         "position_intent": "sell_to_open"},
        {"symbol": "SPY260903P00765000", "side": "buy", "ratio_qty": "1",
         "position_intent": "buy_to_open"},
        {"symbol": "SPY260903C00781000", "side": "sell", "ratio_qty": "1",
         "position_intent": "sell_to_open"},
        {"symbol": "SPY260903C00785000", "side": "buy", "ratio_qty": "1",
         "position_intent": "buy_to_open"},
    ]
    return ex.Trade(
        id=f"SPY-{expiration}", underlying="SPY", structure="iron_condor", expiration=expiration,
        legs=legs, contracts=contracts, entry_credit=credit_ps * 100, width=4.0,
        max_loss=(4.0 - credit_ps) * 100 * contracts, thesis="x",
        opened_at="2026-09-02T10:00:00-04:00", status="open", client_order_id=f"SPY-{expiration}",
    )


def _chain_for_combo(debit_ps_per_lot: float) -> dict:
    """A 4-leg chain whose buy-back combo cost equals `debit_ps_per_lot` dollars per 1-lot.

    combo_ps = (short_p - long_p) + (short_c - long_c) = 2*short - 2*long, then x100 in the code.
    Fix the long legs at a small floor and solve the short mid to hit the target.
    """
    long_mid = 0.05
    short_mid = debit_ps_per_lot / 100 / 2 + long_mid
    q = lambda m: {"latestQuote": {"bp": max(m - 0.005, 0.01), "ap": m + 0.005}}
    return {
        "SPY260903P00769000": q(short_mid),
        "SPY260903P00765000": q(long_mid),
        "SPY260903C00781000": q(short_mid),
        "SPY260903C00785000": q(long_mid),
    }


class _Replay:
    """Drives `manage_exits` through a list of debits and a controllable clock."""

    def __init__(self, monkeypatch, trade: ex.Trade, when: datetime):
        self._trades = [trade]
        self._debit = None
        self._now = when
        monkeypatch.setattr(ex, "_load_all", lambda: list(self._trades))
        monkeypatch.setattr(ex, "_rewrite", self._store)
        monkeypatch.setattr(ex, "_append", self._store)
        monkeypatch.setattr(ex.md, "option_chain_snapshot",
                            lambda *a, **k: _chain_for_combo(self._debit))

        replay = self

        class _Clock:
            @staticmethod
            def now(tz=None):
                return replay._now

        monkeypatch.setattr(ex, "datetime", _Clock)

    def _store(self, t: ex.Trade) -> None:
        self._trades = [t if x.id == t.id else x for x in self._trades]

    @property
    def trade(self) -> ex.Trade:
        return self._trades[0]

    def step(self, debit_ps_per_lot: float, params, *, mode: str = "dry_run",
             at: datetime | None = None):
        self._debit = debit_ps_per_lot
        if at is not None:
            self._now = at
        return ex.manage_exits(params, mode)


NON_EXPIRY = datetime(2026, 9, 2, 12, 0, tzinfo=ET)
EXPIRY_1530 = datetime(2026, 9, 3, 15, 30, tzinfo=ET)
EXPIRY_1551 = datetime(2026, 9, 3, 15, 51, tzinfo=ET)   # 15:30/15:45 ticks were skipped


# --------------------------------------------------------------------------- trajectories

def test_take_profit_fires_once_along_a_falling_debit(monkeypatch, params):
    r = _Replay(monkeypatch, _condor(1.20), NON_EXPIRY)
    take = 1.20 * (1 - params.take_profit_frac) * 100        # $60 per lot

    assert r.step(110.0, params) == []                       # above take, hold
    assert r.step(90.0, params) == []
    acts = r.step(take - 5, params)                          # crosses -> take_profit
    assert acts and acts[0]["reason"] == "take_profit"
    assert r.trade.status == "closed"
    assert r.trade.pnl == pytest.approx(1.20 * 100 - (take - 5))

    assert r.step(10.0, params) == []                        # already closed -> no second close


def test_stop_fires_when_debit_doubles_the_credit(monkeypatch, params):
    r = _Replay(monkeypatch, _condor(1.20), NON_EXPIRY)
    stop = 1.20 * params.stop_multiple * 100                 # $240 per lot

    assert r.step(150.0, params) == []
    acts = r.step(stop + 10, params)
    assert acts[0]["reason"] == "stop"
    assert r.trade.pnl == pytest.approx(1.20 * 100 - (stop + 10))


def test_mid_debit_on_a_non_expiry_day_just_holds(monkeypatch, params):
    r = _Replay(monkeypatch, _condor(1.20), NON_EXPIRY)
    for _ in range(5):
        assert r.step(100.0, params) == []                  # between take and stop, not expiry
    assert r.trade.status == "open"


def test_expiry_close_fires_at_1530_on_expiration_day(monkeypatch, params):
    r = _Replay(monkeypatch, _condor(1.20), NON_EXPIRY)
    assert r.step(100.0, params) == []                       # 2 Sep noon: hold
    acts = r.step(100.0, params, at=EXPIRY_1530)             # 3 Sep 15:30: close
    assert acts[0]["reason"] == "expiry_close"
    assert r.trade.status == "closed"


def test_expiry_close_still_fires_after_a_skipped_1545_run(monkeypatch, params):
    r = _Replay(monkeypatch, _condor(1.20), EXPIRY_1551)
    acts = r.step(105.0, params)
    assert acts[0]["reason"] == "expiry_close"               # 15:30 window is >=, not ==


# --------------------------------------------------------------------------- live lifecycle

def test_live_close_goes_pending_then_reconcile_finalizes(monkeypatch, params):
    r = _Replay(monkeypatch, _condor(1.20), NON_EXPIRY)

    submitted = {}
    monkeypatch.setattr(ex.broker, "submit_mleg",
                        lambda *a, **k: submitted.update(k) or {"id": "x1"})
    monkeypatch.setattr(ex, "_await_fill", lambda oid: {"status": "new"})   # not filled yet

    acts = r.step(40.0, params, mode="live")                 # take_profit territory
    assert acts[0]["reason"] == "take_profit" and acts[0].get("pending") is True
    assert r.trade.status == "pending_close"
    assert submitted["client_order_id"].endswith("-x")

    # next loop: reconcile sees the fill
    monkeypatch.setattr(ex.broker, "get_order",
                        lambda **k: {"status": "filled", "filled_avg_price": "0.40"})
    monkeypatch.setattr(ex, "_load_active", lambda: [r.trade])
    monkeypatch.setattr(ex, "_unexpected_equity_positions", list)
    evts = ex.reconcile("live")
    assert any(e.get("resolved") == "exit_filled" for e in evts)
    assert r.trade.status == "closed"
    assert r.trade.pnl == pytest.approx(1.20 * 100 - 0.40 * 100)


def test_combo_cost_runs_through_the_real_chain(params):
    """No stub on _combo_cost_to_close: the 4-leg synthetic chain must value to ~$100/lot."""
    t = _condor(1.20)
    chain = _chain_for_combo(100.0)
    assert ex._combo_cost_to_close(t, chain) == pytest.approx(100.0, abs=3.0)
