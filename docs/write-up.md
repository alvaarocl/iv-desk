# IV Desk — One-Page Write-Up

> **Nota para nosotros (borrar antes de entregar).**
>
> **Regla: esto se escribe DESDE EL CÓDIGO, no desde el plan. Si el jueves algo no está construido,
> no aparece aquí.** Los jueces son **de Alpaca**: van a abrir el repo buscando exactamente las
> integraciones que afirmemos. Una promesa que no se puede verificar abriendo un fichero hunde el eje
> de Technology Implementation, que es donde más apretamos.
>
> Cada afirmación de abajo lleva entre paréntesis el fichero que la demuestra. **Antes de entregar:
> abrir cada uno de esos ficheros y comprobarlo.** Todo lo marcado `[[EN CONSTRUCCIÓN: …]]` se
> **reescribe con lo que exista** o **se borra entero** — no se entrega en presente. Las cifras van
> entre `[ ]` y se rellenan el jueves 3 después del cierre. Idioma de entrega: **inglés**.
> Issues relacionados: #18 (este doc) · #4 (CLI) · #13 (capa LLM) · #20 (MCP).

---

## What it is

IV Desk is an autonomous options trading desk. It does not trade price direction: it harvests the
**volatility risk premium** (VRP) on index ETFs — SPY, QQQ, IWM — gated by **dealer gamma
positioning** (GEX), and it trades defined-risk structures (iron condors and credit verticals,
1–3 DTE) as single 4-leg `order_class: mleg` orders.

It runs unattended on a dedicated Alpaca **paper** account on a 15-minute cron during regular trading
hours, and every decision it makes — including every decision **not** to trade — is written to an
append-only journal.

---

## The Day-0 probes: we measured before we built

Before writing the engine we ran three probes against the **live** market on 28 Aug and let the
results dictate the design (`probes/RESULTS.md`):

- **Greeks and IV come from Alpaca's option snapshots** → we ship no Black-Scholes engine at all.
- **OPRA is a paid tier we don't have; the free `indicative` feed measured ~2 s fresh** → good enough
  for 0–4 DTE credit spreads, so the whole design targets short-dated structures.
- **Open interest lives only on `/v2/options/contracts`, dated T-2** → GEX is explicitly a *regime*
  signal, never a precision input.
- **A 4-leg condor is accepted as one `mleg` order on paper at options level 3** → no
  paired-verticals fallback needed.

Every one of those findings is a design decision we can point at, not an assumption.

---

## Architecture: the LLM never touches the money path

The split is the point, and it is enforced structurally:

| Layer | Implementation | Where to verify |
|---|---|---|
| **Signal** — RV forecast (Yang-Zhang + EWMA) vs ATM implied vol → VRP; GEX from chain open interest; regime classifier; skew | Pure Python, deterministic | `agent/signal.py` |
| **Structure & sizing** — strike selection at a target short delta, contracts sized so max loss ≤ risk budget | Pure Python, deterministic | `agent/execution.py` |
| **Risk Officer** — every gate, **no discretion**. `evaluate()` is the single entry point and returns `(ok, reason)` | Pure Python, **no LLM ever calls into it** | `agent/risk.py` |
| **Trade management** — take profit at 50% of credit, stop at 2× credit, close before expiry | Pure Python, deterministic | `agent/execution.py` → `manage_exits()` |
| **Journal** — append-only JSONL of every signal, rejection, open and exit | — | `agent/journal.py` → `data/journal.jsonl` |
| **The desk (LLM)** — named seats that argue an open decision | **[[EN CONSTRUCCIÓN — issue #13. Describir aquí SOLO los asientos que existan el jueves y con qué modelos corren de verdad. Si no existe, borrar esta fila entera.]]** | |

Anything that can lose money — exits, gates, sizing — is deterministic Python. The LLM layer can
propose and argue; it **cannot** widen a risk limit, resize a trade, or veto an exit.

This mirrors, almost point for point, the architecture Alpaca itself publishes as good practice in
[*Building a Multi-Agent AI Trading System on Alpaca*](https://alpaca.markets/learn/building-a-multi-agent-ai-trading-system-on-alpaca):
specialised agents instead of one generalist prompt, a critic that validates against predefined
rules, a **deterministic Python risk guard with no LLM**, and position monitoring every 15 minutes.
We converged on it independently and then found their article confirming it.

---

## Risk gates (`agent/risk.py`)

Per-trade max loss ≤ [X]% NAV · portfolio open risk ≤ 10% NAV · ≤ [N] concurrent positions · net
portfolio delta band · −3% daily-loss circuit breaker · drawdown throttle at 8% (half size) and hard
halt at 12% (no new risk) · macro-event blackout ±2 h (`agent/calendar.py`) · no new 0DTE after
14:00 ET · early-assignment detection: any unexpected equity position puts the desk into exits-only.

Each gate returns a **reason string**, and that string is what lands in the journal. That is what
makes the log falsifiable rather than decorative.

---

## A falsifiable record, including the non-trades

`data/journal.jsonl` is the deliverable we are proudest of. It records, every 15 minutes:

- the full signal per underlying (VRP, GEX sign, regime, chosen structure),
- every `rejected` event **with the gate that rejected it**,
- every open, with the strikes and a written thesis,
- every exit, with the reason (`take_profit` / `stop` / `expiry_close`) and the realised P&L,
- the equity curve (`data/equity.csv`).

A desk that stands down before ISM with a documented reason is a better demonstration of autonomy
than one that got three condors right. The journal is what lets a judge check that claim instead of
believing it.

---

## Alpaca stack usage

- **Trading API** — account, clock, positions, orders, and 4-leg `order_class: mleg` condors.
  **[[EN CONSTRUCCIÓN — issue #4: hoy `agent/broker.py` es REST con `httpx`. Las reglas exigen
  Trading API + (MCP o CLI). Cuando la migración esté hecha, describir EXACTAMENTE qué comandos del
  CLI de Alpaca ejecuta el loop y desde qué fichero. Si el jueves sigue siendo REST, decirlo así, sin
  adornos.]]**
- **Options market data** — chain snapshots with greeks + implied vol (`feed=indicative`) and
  per-contract open interest from `/v2/options/contracts` (`agent/marketdata.py`).
- **Paper only.** Dedicated competition account, $100,000 starting balance, first order Mon 31 Aug
  09:30 ET, used for nothing before that. Account ID: **PA39HSCQE8S3**. Development and testing ran
  on a separate paper account (`PA3TQHQKM5AD`) — disclosed in the README.
- **[[MCP — issue #20. NO mencionarlo salvo que exista y se pueda abrir. Si no se construye, esta
  línea se borra.]]**

---

## Results — fill Thu 3 Sep after the close

Scoring window: Mon 31 Aug 09:30 ET → equity snapshot at Thu 3 Sep close. Four sessions.

- Sessions traded: [N] · trades closed: [N] · win rate [X]% · avg win $[X] · avg loss $[X].
- Ending equity: $[X] · return [X]% · max drawdown [X]% · [N] circuit-breaker triggers.
- Stand-downs: [N] sessions/loops with a documented `rejected` reason.
- Incidents encountered and resolved live: [N] — see `docs/RUNBOOK.md`.
- Prediction ledger: [X]/[N] theses resolved correct.

## Links

Repo: [URL] · Demo video: [URL] · **[[Dashboard — opcional (la UI no es obligatoria). Enlazar solo si existe.]]**
