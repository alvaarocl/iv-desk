"""Day-0 probe 3: does paper `mleg` accept a 4-leg iron condor? If not, fall back to 2x verticals.

Run:  uv run python probes/03_multileg_order.py
Places orders on the FRESH PAPER account, then cancels them. Market must be open (or use limit far from mid).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

KEY = os.environ["ALPACA_API_KEY"]
SEC = os.environ["ALPACA_SECRET_KEY"]
UNDERLYING = "SPY"


def pick_condor_legs(trading, opt, stock):
    """Return 4 OCC symbols: short put, long put (lower), short call, long call (higher)."""
    from alpaca.data.requests import OptionChainRequest, StockLatestTradeRequest

    spot = stock.get_stock_latest_trade(StockLatestTradeRequest(symbol_or_symbols=UNDERLYING))[
        UNDERLYING
    ].price
    chain = opt.get_option_chain(
        OptionChainRequest(
            underlying_symbol=UNDERLYING,
            strike_price_gte=spot * 0.90,
            strike_price_lte=spot * 1.10,
        )
    )
    puts, calls = {}, {}
    for sym, snap in chain.items():
        # OCC symbol: ...YYMMDD[C/P]00000000 — parse type + strike
        body = sym[len(UNDERLYING) :]
        cp = body[6]
        strike = int(body[7:]) / 1000
        (puts if cp == "P" else calls)[strike] = sym
    sp = max(k for k in puts if k < spot * 0.97)
    lp = max(k for k in puts if k < sp)
    sc = min(k for k in calls if k > spot * 1.03)
    lc = min(k for k in calls if k > sc)
    return puts[sp], puts[lp], calls[sc], calls[lc]


def main() -> None:
    from alpaca.data.historical.option import OptionHistoricalDataClient
    from alpaca.data.historical.stock import StockHistoricalDataClient
    from alpaca.trading.client import TradingClient
    from alpaca.trading.enums import OrderClass, OrderSide, OrderType, TimeInForce
    from alpaca.trading.requests import LimitOrderRequest, OptionLegRequest

    trading = TradingClient(KEY, SEC, paper=True)
    opt = OptionHistoricalDataClient(KEY, SEC)
    stock = StockHistoricalDataClient(KEY, SEC)

    short_put, long_put, short_call, long_call = pick_condor_legs(trading, opt, stock)
    print("legs:", short_put, long_put, short_call, long_call)

    legs = [
        OptionLegRequest(symbol=short_put, side=OrderSide.SELL, ratio_qty=1),
        OptionLegRequest(symbol=long_put, side=OrderSide.BUY, ratio_qty=1),
        OptionLegRequest(symbol=short_call, side=OrderSide.SELL, ratio_qty=1),
        OptionLegRequest(symbol=long_call, side=OrderSide.BUY, ratio_qty=1),
    ]

    # A limit price well below any real credit so it rests without filling; we just want the accept/reject.
    order = LimitOrderRequest(
        qty=1,
        limit_price=0.05,
        order_class=OrderClass.MLEG,
        time_in_force=TimeInForce.DAY,
        type=OrderType.LIMIT,
        legs=legs,
    )
    try:
        resp = trading.submit_order(order)
        print("\n✅ 4-leg mleg ACCEPTED — id", resp.id, "status", resp.status)
        trading.cancel_order_by_id(resp.id)
        print("cancelled.")
    except Exception as e:  # noqa: BLE001
        print("\n❌ 4-leg mleg REJECTED:", repr(e))
        print("→ execution.py must emit two 2-leg verticals. Testing that path...")
        for pair, tag in [((legs[0], legs[1]), "put spread"), ((legs[2], legs[3]), "call spread")]:
            o = LimitOrderRequest(
                qty=1,
                limit_price=0.05,
                order_class=OrderClass.MLEG,
                time_in_force=TimeInForce.DAY,
                type=OrderType.LIMIT,
                legs=list(pair),
            )
            r = trading.submit_order(o)
            print(f"  ✅ {tag} accepted — {r.id}")
            trading.cancel_order_by_id(r.id)


if __name__ == "__main__":
    main()
