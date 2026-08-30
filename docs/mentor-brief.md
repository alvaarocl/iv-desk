# Brief para el mentor

Mensaje corto para explicarle a un mentor del hackathon qué presentamos y sacarle consejo.
Abajo, en inglés (para enviar) y en español (para nosotros). El detalle completo está en
[`DOSSIER.md`](DOSSIER.md).

---

## English (to send)

**What we're building — IV Desk**

An autonomous options desk for the hackathon. It behaves like an insurance company for the stock
market: it sells defined-risk premium (iron condors, 1–3 DTE) on SPY/QQQ/IWM, but **only** when two
deterministic signals agree — (1) implied vol is rich relative to a realized-vol forecast (positive
VRP, gated on a *ratio* not an absolute), and (2) dealer gamma positioning (normalized GEX from T-2
open interest) says the tape should be range-bound. Everything that can lose money — signal, strike
selection, sizing, exits, risk gates — is pure deterministic Python with 116 tests. On top sits a
4-seat LLM "desk" (Quant ensemble ×3 + adversarial Bull/Bear + Desk Head), all on open models via
Featherless, that debates each *already-approved* trade and writes a falsifiable prediction. **The
LLM can only trim or veto, never increase risk — that's one clamped line.** Trading API goes through
the Alpaca CLI; runs every 15 min on GitHub Actions cron; every decision (including every "stand
down, here's the gate that blocked it") is logged to a public append-only journal.

**Where we think we stand.** We're not chasing the P&L axis — 4 sessions is a variance lottery, and
our backtest on 60 real sessions shows the VRP signal is thin in the 2026 tape (IV/RV median 0.90),
so we expect **0–4 trades** all week. Our frame is "a desk that knows when *not* to trade, and
proves it." We're betting on Technology (deep, real Alpaca stack usage + robustness) and Creativity
(the vol-surface + gamma signal, not another indicator on price).

**Where we'd value your read:**

1. Is "a disciplined desk that mostly stands down" a defensible frame with judges, or are we
   rationalizing a signal that barely fires? Would you widen the universe / add a second premium
   structure to guarantee more debate transcripts, or hold the line?
2. For the Technology axis — is CLI + options greeks/IV + GEX + 4-leg `mleg` + full test suite
   "deep enough," or do judges expect an MCP server too?
3. Does the LLM debate need to *visibly change outcomes* to score on Creativity, or is a bounded
   critic layer + falsifiable prediction ledger enough?
4. Go-live is Monday from a fresh $100k account with a loop that's unit-tested but never run
   end-to-end in a live open. Anything you'd insist we de-risk first?
5. Presentation priority given no UI is required: video, live dashboard, or slide deck — where does
   the marginal hour go?

---

## Español (para nosotros)

**Qué estamos construyendo — IV Desk**

Una mesa de opciones autónoma para el hackathon. Se comporta como una aseguradora para la bolsa:
vende prima de riesgo definido (iron condors, 1–3 días a vencimiento) sobre SPY/QQQ/IWM, pero
**solo** cuando dos señales deterministas coinciden — (1) la volatilidad implícita está cara
respecto a una previsión de volatilidad realizada (VRP positivo, con un gate que es un *ratio*, no
un valor absoluto), y (2) el posicionamiento de gamma de los dealers (GEX normalizado a partir de
open interest con retraso T-2) dice que el mercado debería quedarse en rango. Todo lo que puede
perder dinero — señal, selección de strikes, sizing, salidas, gates de riesgo — es Python
determinista puro con 116 tests. Encima hay una "mesa" LLM de 4 asientos (ensemble Quant ×3 + Bull/
Bear adversariales + Jefe de Mesa), todos sobre modelos abiertos vía Featherless, que debate cada
operación *ya aprobada* y escribe una predicción falsable. **El LLM solo puede recortar o vetar,
nunca aumentar el riesgo — es una línea con un clamp.** La Trading API va por el CLI de Alpaca;
corre cada 15 min en un cron de GitHub Actions; cada decisión (incluida cada "me planto, y este es
el gate que lo bloqueó") se registra en un journal público append-only.

**Dónde creemos que estamos.** No perseguimos el eje de P&L — 4 sesiones son una lotería de
varianza, y nuestro backtest sobre 60 sesiones reales muestra que la señal VRP es delgada en el
mercado de 2026 (IV/RV mediana 0.90), así que esperamos **0–4 operaciones** en toda la semana.
Nuestro enfoque es "una mesa que sabe cuándo *no* operar, y lo demuestra". Apostamos por Technology
(uso profundo y real del stack de Alpaca + robustez) y Creativity (la señal de superficie de
volatilidad + gamma, no otro indicador sobre el precio).

**Dónde nos vendría bien tu lectura:**

1. ¿"Una mesa disciplinada que casi siempre se planta" es un enfoque defendible ante el jurado, o
   estamos racionalizando una señal que apenas dispara? ¿Ampliarías el universo / añadirías una
   segunda estructura de prima para garantizar más transcripts de debate, o mantendrías la línea?
2. Para el eje de Technology — ¿CLI + griegas/IV de opciones + GEX + `mleg` de 4 patas + suite de
   tests completa es "suficientemente profundo", o el jurado espera también un servidor MCP?
3. ¿El debate LLM necesita *cambiar visiblemente los resultados* para puntuar en Creativity, o
   basta con una capa de crítica acotada + un registro de predicciones falsables?
4. El go-live es el lunes desde una cuenta nueva de $100k con un loop que está testeado por
   unidades pero nunca se ha corrido end-to-end en un mercado abierto en vivo. ¿Algo que
   insistirías en de-riesgar antes?
5. Prioridad de presentación dado que la UI no es obligatoria: vídeo, dashboard en vivo o deck de
   slides — ¿dónde va la hora marginal?
