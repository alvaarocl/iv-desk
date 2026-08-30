# Guion del vídeo demo (issue #36)

**Duración objetivo: 2:30–2:50.** Para Álvaro: grabar desde el lunes, montar domingo/lunes.
Instrucciones de rodaje en español; **la locución va en inglés** (la entrega es en inglés — igual
que `docs/write-up.md`). Si prefieres narrar en español, subtitula en inglés.

**Tesis del vídeo:** el P&L de 4 sesiones es una lotería de varianza y no lo vendemos. Vendemos
**el agente decidiendo solo**, y el plano que gana es **el momento en que la mesa se niega a
operar**. Ese plano va en el minuto 1:20, no al final.

---

## Antes de grabar — capturar el material

Todo el metraje sale del journal. Nada de mockups: si no está en `data/journal.jsonl`, no se graba.

```bash
# Terminal a 1920x1080, fuente grande (18–20 pt), tema oscuro, prompt corto (PS1='$ ').
# 1) La señal más reciente de un subyacente
grep '"event": "signal"' data/journal.jsonl | tail -1 | python -m json.tool

# 2) EL PLANO CLAVE — un stand-down con su motivo (probar los cuatro)
grep '"stand_down": "vrp"'   data/journal.jsonl | tail -1 | python -m json.tool
grep '"stand_down": "gex"'   data/journal.jsonl | tail -1 | python -m json.tool
grep '"stand_down": "trend"' data/journal.jsonl | tail -1 | python -m json.tool

# 3) Un rechazo del Risk Officer con el gate que lo bloqueó
grep '"event": "rejected"' data/journal.jsonl | tail -1 | python -m json.tool

# 4) Un debate completo (transcript de los cuatro asientos)
grep '"event": "debate"' data/journal.jsonl | tail -1 | python -m json.tool

# 5) Una apertura y una salida
grep '"event": "opened"' data/journal.jsonl | tail -1 | python -m json.tool
grep '"event": "exit"'   data/journal.jsonl | tail -1 | python -m json.tool
```

**Si el lunes/martes no hay ningún stand-down natural grabable:** genéralo en la **cuenta de
testing** (`PA3TQHQKM5AD`, nunca en la de competición) subiendo `vrp_ratio_min` en
`data/params.json` y corriendo `uv run python -m agent.desk` en `dry_run`. Es el mismo código y el
mismo journal; solo estás forzando el umbral. **Devuelve `params.json` a su valor al terminar.**

Clips extra que hacen falta:
- Scroll lento por `agent/risk.py` (cabe entero en pantalla: es corto, y eso es parte del mensaje).
- La línea del clamp en `agent/debate.py` (`contracts = max(0, min(int(head.contracts), cap))`).
- El run verde de GitHub Actions (*IV Desk loop*) con el paso **Verify CLI version**.
- El dashboard de Alpaca de `PA39HSCQE8S3`: equity + posiciones + activity log.

---

## Guion, plano a plano

### 0:00–0:20 · Gancho — por qué esto no es "multiagente + RSI"

**Pantalla:** título sobre negro 2 s (`IV Desk — an options desk that knows when not to trade`), y
corte inmediato a la terminal con el JSON del punto (2): un `signal` con `"stand_down": "vrp"`
visible. **Empezar por el no-trade es deliberado.**

> **VO (EN):** "Most trading agents are a multi-agent wrapper around a moving average. This one
> doesn't predict price at all. It sells overpriced volatility on SPY, QQQ and IWM — and most of
> the time, it decides not to trade. Every one of those refusals is on the record, with a reason."

### 0:20–0:55 · La señal — VRP y gamma de dealers

**Pantalla:** dividir en dos. Izquierda, el docstring de `agent/signal.py` (las tres puertas:
`vrp`, `gex`, `trend`). Derecha, el JSON del `signal` del punto (1) con el cursor resaltando
`vrp_ratio`, `gex_norm`, `gex_state`, `regime`, `notes`.

> **VO (EN):** "The signal is deterministic Python, and it reads the option surface, not the price
> chart. Implied volatility over a Yang-Zhang realized-vol forecast gives the volatility risk
> premium — a ratio, so it means the same thing in a six-percent tape and a twenty-percent one.
> Dealer gamma, computed from open interest, decides whether that premium is safe to sell, with a
> dead zone around zero because the open-interest data is two days old. Three gates. Any one of
> them can stand the desk down, and each writes the reason it did."

### 0:55–1:20 · La mesa debate — tesis falsable

**Pantalla:** el JSON del `debate` del punto (4), haciendo scroll despacio por el `transcript`.
Pausar sobre: los tres `quant` con su `vote` y `reason` → el `bull` y el `bear` con
`cited_fields` → el `desk_head` con `thesis` y `prediction` (`low`, `high`, `date`).

> **VO (EN):** "Only then does the LLM desk get a say — four seats, all running open models on
> Featherless. A three-model Quant ensemble votes, and needs a strict majority of the models we
> dispatched, not of the ones that answered. Bull and Bear argue the direction, and an argument
> that doesn't cite at least two real fields from the signal is thrown away as unusable. The Desk
> Head sizes the trade and writes a falsifiable prediction: a closing range, on a date, that gets
> checked against the tape."

### 1:20–2:00 · **El no-trade — el corazón del vídeo**

**Pantalla, en tres cortes rápidos:**
1. El `rejected` del punto (3) con el `reason` en grande — idealmente `macro event blackout` (el
   desk plantándose antes de un ISM) o `portfolio delta band`.
2. El `debate` con `"approved": false` y un `reason` tipo `quant_reject:` / `desk_head_veto`.
3. Corte a `agent/debate.py`, a la línea del clamp, y a `agent/risk.py` entero en pantalla.

> **VO (EN):** "This is the part we're proudest of. Here the desk stood down before an ISM print,
> because the risk officer blacks out new positions around macro releases. Here the quant ensemble
> refused a setup the deterministic layer had already approved. Both are in the journal, with the
> exact gate that blocked them and the numbers behind it.
>
> And the language model can never make this worse. The final size is one line: the minimum of what
> the Desk Head asked for and the cap the risk officer already set. The debate can trim, or veto,
> or do nothing. It cannot widen a limit, resize a trade, or override an exit — that's structural,
> not a prompt. If a model times out, returns broken JSON, or the provider goes down, the result is
> a stand-down. There is no code path where garbage means yes."

### 2:00–2:30 · Ejecución real y cierre

**Pantalla:** el `opened` del punto (5) con `strikes`/`contracts`/`thesis` → corte al run de Actions
con **Verify CLI version** y el paso del loop → corte al dashboard de Alpaca de `PA39HSCQE8S3` con
la curva de equity y las posiciones → corte al `exit` con `reason` y `pnl`.

> **VO (EN):** "When the desk does trade, it goes out as a single four-leg iron condor through the
> official Alpaca CLI — every trading call in the loop shells out to it — and comes back through a
> deterministic exit manager: fifty percent of the credit, two times the credit, or close on
> expiry day. It runs itself on a fifteen-minute cron, reconciling against Alpaca as the source of
> truth on every tick.
>
> Four sessions of P&L is a coin flip. An agent that documents every trade it didn't take isn't.
> The journal is in the repo — go check us against it."

**Cierre:** tarjeta final 3 s con `github.com/alvaarocl/iv-desk` · `PA39HSCQE8S3` · `IV Desk`.

---

## Notas de montaje

- **Sin música por encima de la voz.** Un lecho muy bajo entre 0:00–0:20 y en el cierre, si acaso.
- Zoom o resaltado sobre la clave JSON de la que habla la locución. El espectador tiene 4 segundos
  por plano: si tiene que buscar el campo, se pierde.
- **Nada de metraje de stock ni animaciones de "IA".** Terminal, código y el dashboard de Alpaca.
- No enseñar `.env`, claves ni el `account_number` de la cuenta de testing. `PA39HSCQE8S3` sí puede
  salir: va en el formulario de la entrega.
- Si sobran segundos, el primer recorte es el bloque 2:00–2:30 (ejecución), no el no-trade.
- Subir a YouTube **no listado** y pegar el enlace en `docs/SUBMISSION.md` (entregable #5).
