#!/usr/bin/env bash
# Day-0 probe 1: Alpaca CLI auth + account + options level + an option chain query.
# Usage: set ALPACA_API_KEY / ALPACA_SECRET_KEY in env (or `source ../.env`), then: bash 01_cli_smoke.sh
set -euo pipefail

echo "== version =="
alpaca version

echo; echo "== doctor =="
alpaca doctor || true

echo; echo "== account (expect fresh acct, cash ~100000, options_trading_level 3) =="
alpaca account get --jq '{id, status, cash, portfolio_value, options_trading_level, options_approved_level}'

echo; echo "== clock =="
alpaca clock get

echo; echo "== option contracts for SPY (nearest expirations, calls near the money) =="
# Exact flags may differ by CLI version — check: alpaca option --help  /  alpaca data option --help
alpaca option list --underlying-symbol SPY --limit 5 --jq '.option_contracts[]? | {symbol, expiration_date, strike_price, type, open_interest}' \
  || alpaca data option chain --underlying SPY --jq 'keys[0:5]' \
  || echo "!! adjust option-chain command for this CLI version — see: alpaca option --help"

echo; echo "DONE — paste this output into RESULTS.md"
