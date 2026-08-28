# Day-0 Probes

Run these the moment you have a funded fresh paper account + API keys in `.env`.
They de-risk the three things that can sink the project. Record output in `RESULTS.md`.

## 0. Install the Alpaca CLI

The official CLI is `github.com/alpacahq/cli` (binary name `alpaca`).

- **Homebrew (mac/Linux):** `brew install alpacahq/tap/cli`
- **Go:** `go install github.com/alpacahq/cli/cmd/alpaca@latest`
- **Windows:** download the latest Windows binary from https://github.com/alpacahq/cli/releases,
  put `alpaca.exe` on PATH. (No Go / Homebrew needed.)

Then:
```
alpaca version
alpaca doctor
```

## 1. CLI smoke — `01_cli_smoke.sh`

Auth works, account is the fresh one with $100k, options level is 3, an option chain query returns data.

## 2. Options data — `02_options_data.py`

- Snapshot endpoint returns **greeks + implied volatility** per contract.
- Per-contract endpoint returns **open interest**.
- Time a full ±5%-of-spot OI sweep for one underlying → is a 2×/day GEX refresh feasible under rate limits?

## 3. Multi-leg order — `03_multileg_order.py`

- Submit a **4-leg iron condor** via `order_class: mleg` on paper. Does it accept 4 legs?
- If not: submit it as **two 2-leg vertical credit spreads**. Confirm that path works.
- Cancel everything after. **This decides the structure builder in `agent/execution.py`.**

## Decision gates

| Probe result | Consequence |
|---|---|
| Snapshot has no greeks/IV | Compute greeks via Black-Scholes in `agent/surface.py` from mid + risk-free rate |
| OI sweep too slow / rate-limited | Narrow GEX strike window to ±3%, refresh once/day |
| `mleg` rejects 4 legs | Structure builder emits paired verticals instead of condors |
| Options level < 3 | Re-open account / request upgrade before anything else |
