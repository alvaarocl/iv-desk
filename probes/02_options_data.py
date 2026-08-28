"""Day-0 probe 2: do Alpaca option snapshots carry greeks + IV, and can we get OI at scale?

Run:  uv run python probes/02_options_data.py
Needs ALPACA_API_KEY / ALPACA_SECRET_KEY in env or .env.
"""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv

load_dotenv()

KEY = os.environ["ALPACA_API_KEY"]
SEC = os.environ["ALPACA_SECRET_KEY"]

UNDERLYING = "SPY"
SPOT_BAND = 0.05  # +/- 5% of spot


def main() -> None:
    from alpaca.data.historical.option import OptionHistoricalDataClient
    from alpaca.data.historical.stock import StockHistoricalDataClient
    from alpaca.data.requests import OptionChainRequest, StockLatestTradeRequest
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import GetOptionContractsRequest

    stock = StockHistoricalDataClient(KEY, SEC)
    opt = OptionHistoricalDataClient(KEY, SEC)
    trading = TradingClient(KEY, SEC, paper=True)

    spot = stock.get_stock_latest_trade(StockLatestTradeRequest(symbol_or_symbols=UNDERLYING))[
        UNDERLYING
    ].price
    lo, hi = spot * (1 - SPOT_BAND), spot * (1 + SPOT_BAND)
    print(f"{UNDERLYING} spot ~ {spot:.2f}  band [{lo:.2f}, {hi:.2f}]")

    # ---- chain snapshot: greeks + IV? ----
    t0 = time.time()
    chain = opt.get_option_chain(
        OptionChainRequest(underlying_symbol=UNDERLYING, strike_price_gte=lo, strike_price_lte=hi)
    )
    print(f"\nchain snapshot: {len(chain)} contracts in {time.time() - t0:.2f}s")
    sample = next(iter(chain.values()))
    print("sample keys:", [a for a in dir(sample) if not a.startswith("_")])
    print("  greeks:", getattr(sample, "greeks", "MISSING"))
    print("  implied_volatility:", getattr(sample, "implied_volatility", "MISSING"))
    print("  latest_quote:", getattr(sample, "latest_quote", "MISSING"))

    # ---- open interest: on the snapshot or a separate call? ----
    print("\nOI on snapshot?", getattr(sample, "open_interest", "MISSING (need contracts endpoint)"))
    t0 = time.time()
    syms = list(chain.keys())[:100]
    got = 0
    req = GetOptionContractsRequest(underlying_symbols=[UNDERLYING], limit=100)
    contracts = trading.get_option_contracts(req)
    for c in contracts.option_contracts or []:
        if c.open_interest is not None:
            got += 1
    print(f"contracts endpoint: {got} with OI, first page in {time.time() - t0:.2f}s")
    print(f"\n~{len(syms)} contracts in band → estimate refresh cost accordingly.")


if __name__ == "__main__":
    main()
