"""Risk gates (issue #9) and the account guard (contamination guardrail)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from agent import broker, desk, risk

ET = ZoneInfo("America/New_York")


def _pf(**over):
    base = dict(nav=100_000.0, peak_nav=100_000.0, open_risk=0.0, n_positions=0,
               net_delta=0.0, day_pnl=0.0)
    base.update(over)
    return risk.PortfolioState(**base)


def _trade(**over):
    base = dict(underlying="SPY", structure="iron_condor", max_loss=400.0, net_delta=0.0,
               is_0dte=False, is_satellite=False)
    base.update(over)
    return risk.ProposedTrade(**base)


NOON = datetime(2026, 9, 2, 12, 0, tzinfo=ET)


def test_clean_trade_passes(params):
    ok, why = risk.evaluate(_trade(), _pf(), params, NOON)
    assert ok and why == "ok"


@pytest.mark.parametrize(
    ("trade_kw", "pf_kw", "frag"),
    [
        (dict(max_loss=3_000.0), {}, "per-trade"),
        (dict(max_loss=400.0), dict(open_risk=9_900.0), "portfolio risk"),
        ({}, dict(n_positions=99), "max concurrent"),
        ({}, dict(day_pnl=-3_500.0), "circuit breaker"),
        ({}, dict(nav=85_000.0), "drawdown"),
    ],
)
def test_each_gate_can_veto(params, trade_kw, pf_kw, frag):
    ok, why = risk.evaluate(_trade(**trade_kw), _pf(**pf_kw), params, NOON)
    assert not ok
    assert frag in why


def test_0dte_after_cutoff_is_blocked(params):
    late = datetime(2026, 9, 2, 15, 0, tzinfo=ET)
    ok, why = risk.evaluate(_trade(is_0dte=True), _pf(), params, late)
    assert not ok and "0DTE" in why


def test_size_multiplier_throttles_on_drawdown(params):
    assert risk.size_multiplier(_pf(), params) == 1.0
    assert risk.size_multiplier(_pf(nav=91_000.0), params) == 0.5      # 9% dd
    assert risk.size_multiplier(_pf(nav=87_000.0), params) == 0.0      # 13% dd


# ---------- account guard ----------

def test_live_mode_refuses_wrong_account(monkeypatch):
    monkeypatch.setattr(desk, "COMPETITION_ACCOUNT", "PA39HSCQE8S3")
    monkeypatch.setattr(broker, "account", lambda: {"account_number": "PA3TQHQKM5AD",
                                                    "equity": "100000"})
    with pytest.raises(broker.BrokerError, match="ACCOUNT MISMATCH"):
        desk._guard_account("live", NOON)


def test_competition_account_refused_before_window(monkeypatch):
    monkeypatch.setattr(desk, "COMPETITION_ACCOUNT", "PA39HSCQE8S3")
    monkeypatch.setattr(broker, "account", lambda: {"account_number": "PA39HSCQE8S3",
                                                    "equity": "100000"})
    early = datetime(2026, 8, 30, 12, 0, tzinfo=ET)
    with pytest.raises(broker.BrokerError, match="TOO EARLY"):
        desk._guard_account("dry_run", early)


def test_testing_account_dry_run_is_allowed(monkeypatch):
    monkeypatch.setattr(desk, "COMPETITION_ACCOUNT", "PA39HSCQE8S3")
    monkeypatch.setattr(broker, "account", lambda: {"account_number": "PA3TQHQKM5AD",
                                                    "equity": "100000"})
    acct = desk._guard_account("dry_run", NOON)
    assert acct["account_number"] == "PA3TQHQKM5AD"
