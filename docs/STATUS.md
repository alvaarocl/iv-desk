# Estado del proyecto

Última actualización: **30 ago 2026** (domingo, lane `lane/senal-finde`). Este archivo se actualiza a
mano según avanza el trabajo. Plan del fin de semana en [`PLAN-FINDE.md`](PLAN-FINDE.md).

---

## Dónde estamos, en tres líneas

**`main` está mergeado y verde: 100 tests, `ruff` limpio, y el loop corre end-to-end contra Alpaca
por el CLI en `dry_run`.** Las dos lanes (señal y ejecución) están integradas: **no falta código
nuevo**. Lo que falta es **calibrar con datos reales, probar la mesa Featherless en vivo, ops y
entrega**.

---

## Reglas oficiales (guidelines de Alpaca, recibidas 29 ago)

Datos del concurso verificados en [`REGLAS-HACKATHON.md`](REGLAS-HACKATHON.md). Todas las fechas con
hora CEST y ET en [`CALENDARIO.md`](CALENDARIO.md).

- **Criterios de jurado: CUATRO** — P&L Performance · Technology Implementation · Creativity &
  Originality · Presentation & Execution (~25% cada uno). **Social Engagement es un premio aparte**,
  no un eje del rubro → el P&L pesa **~25%, no ~20%**.
- **Premio: $5.000** (1º $2.500 · 2º $1.500 · 3º $1.000). Algunas fuentes dicen $6.000 contando dos
  premios sociales de $500. **No usar la cifra de $6.300 que arrastraba `CLAUDE.md`** (ya corregida
  allí y en `PLAN.md`).
- **Ventana de scoring de P&L:** lunes **31 ago 9:30 ET (15:30 CEST) → snapshot de equity a cierre del
  jueves 3 sep (22:00 CEST)**. Cuentan 4 sesiones: lun 31, mar 1, mié 2, jue 3.
  **El viernes 4 NO cuenta para P&L.**
  > ⚠️ **PENDIENTE — ACCIÓN HUMANA: preguntarlo en el Discord del hackathon.** Viene de las
  > guidelines privadas y **no es verificable públicamente**. Toda la política de expiraciones
  > (≤ 3 sep) depende de ello. Mientras no haya respuesta, **se trata el jueves como confirmado**
  > (es la opción conservadora). No cambiarlo sin respuesta. → issue #19
- Se juzga por **equity total de la cuenta** (no caja) + creatividad, autonomía y robustez del workflow.
  No hay Sharpe/Sortino/drawdown como métrica, solo equity. Sin scoreboard en vivo.
- **La UI NO es obligatoria.** *"We are primarily evaluating the autonomous agent workflow and its
  trading performance."* → el dashboard es **opcional**.
- El agente debe **empezar a operar el lunes 31 a las 9:30 ET desde la cuenta de competición**.
  Los trades en la cuenta de testing no puntúan.
- **Transporte:** vale MCP o CLI. **Decidido y ya construido: la ejecución va por el CLI de Alpaca.**
- **Trabajo pre-evento permitido pero hay que declararlo** en el README. ✅ hecho.
- Repo privado durante el hackathon; público el 4 sep.

---

## Qué está hecho y verde en `main`

| Componente | Estado |
|---|---|
| `agent/broker.py` | **Trading API por el CLI de Alpaca** (`alpaca api METHOD /path`): cuenta, clock, posiciones, órdenes, cancelaciones, `/v2/options/contracts`, `mleg`. `limit_price` firmado. ✅ |
| `agent/marketdata.py` | REST de market data (permitido para lecturas): snapshots con griegas + IV, open interest, barras diarias SIP. ✅ |
| `agent/signal.py` | VRP ratio (Yang-Zhang + EWMA vs IV ATM), GEX normalizado con zona muerta, régimen ADX/EMA, skew, y **`stand_down` con el gate que bloquea**. ✅ corre; **umbrales sin calibrar**. |
| `agent/execution.py` | Selección de strikes (condor y vertical) con gates de liquidez, sizing, exit manager determinista (50% TP / 2× stop / cierre en expiración), `client_order_id` idempotente, `reconcile`. ✅ |
| `agent/risk.py` | Risk Officer: todos los gates, sin discrecionalidad. `evaluate()` entrada única. ✅ |
| `agent/calendar.py` | Calendario macro verificado (#17) + **blackout asimétrico 2 h antes / 45 min después** (#33). ✅ |
| `agent/seats.py` / `agent/debate.py` | **La mesa, 100% Featherless** (#31): Quant ensemble ×3 con mayoría estricta, Bull/Bear obligados a citar campos reales, Desk Head con predicción falsable validada. Clamp al cap del Risk Officer. Kill switch `DESK_DEBATE=off`. ✅ **cableada en `desk.py`**. |
| `agent/desk.py` | Loop completo: guardarraíl de cuenta → reconcile → salidas → gates de cartera → señal → debate → apertura → journal. ✅ end-to-end en `dry_run`. |
| `agent/journal.py` | Journal append-only + curva de equity + hook de grading de predicciones. ✅ |
| `backtest/replay.py` | Harness de replay para calibrar. ✅ existe; **falta correrlo con keys reales**. |
| Tests | **100 tests**, `ruff` limpio. La mesa se testea con dobles inyectados: sin red y sin claves. ✅ |
| `.github/workflows/desk.yml` | Cron cada 15 min en horario de mercado + `workflow_dispatch`; instala y **verifica la versión** del CLI (pin `0.0.14`). ✅ |
| Probes Día 0 | Los 3 pasaron. `../probes/RESULTS.md`. ✅ |
| `docs/write-up.md` | Reescrito desde el código (#34/#18): sin Anthropic, sin MCP, cada afirmación con su fichero. ✅ solo faltan los números del jueves. |
| `docs/RUNBOOK.md`, `docs/CALENDARIO.md`, `docs/video-script.md` | ✅ hechos. Leer el runbook los dos antes del lunes. |

---

## Qué falta

### Bloquea el lunes

| Tarea | Quién | Issue |
|---|---|---|
| **Calibrar con datos reales**: correr `backtest.replay` con las keys de testing, sacar la tabla del embudo y fijar `vrp_ratio_min`, `gex_min`, `short_delta`, `min_credit_frac` en `agent/config.py` con la evidencia al lado | Ángel | #5, #6, #7, #10 |
| **Probar la mesa Featherless end-to-end** con claves reales: transcript completo en `data/journal.jsonl`, reloj real vs `DESK_DEBATE_BUDGET_S=90`, coste dentro de los $25 del cupón | Ángel | A4 |
| Secrets y variables en GitHub con las keys de `PA39HSCQE8S3` (+ `FEATHERLESS_MODELS`, `ALPACA_ACCOUNT_ID`, `DESK_MODE`) | Álvaro | B2 |
| `workflow_dispatch` en `dry_run` contra UC3M: confirma CLI + auth + `account=PA39HSCQE8S3` | Álvaro | B3 |
| Verificar la cuenta UC3M `PA39HSCQE8S3` ($100k, nivel 3, cero histórico) | humano | B1 |
| **Probar el exit manager sobre una posición real** en la cuenta de testing. `tests/test_exit_manager_replay.py` (B4) todavía **no está en esta rama**: confirmar que llega a `main` en el merge del domingo | Álvaro | B4 |
| **Preguntar en Discord la ventana de P&L** | humano | #19 |
| Limpiar `data/` de la sesión de testing antes del lunes (o asumirlo y anotarlo) | humano | RUNBOOK |

### Entrega (viernes 4, 17:00 CEST)

| Tarea | Estado |
|---|---|
| Rellenar los `[Results: ...]` del write-up con los números del jueves | ⬜ jueves 3 tras el cierre |
| Grabar y montar el vídeo — guion en [`video-script.md`](video-script.md) | ⬜ Álvaro, clips desde el lunes |
| Deck / slides + cover image | ⬜ |
| Capturas post-cierre del jueves (equity, posiciones, activity log) | ⬜ |
| Repo a público + formulario de lablab | ⬜ viernes 4 |
| Posts sociales (premio aparte) | ⬜ |

### Opcional / lista de recortes

Dashboard mínimo (B6) · reflexión nocturna · ensemble a 1 modelo si el cupón aprieta · skew.

---

## Deuda de documentación detectada (no arreglada en esta lane)

Ficheros fuera del alcance de `lane/senal-finde`. **El write-up y el runbook ya están limpios**;
estos son internos y no se entregan, pero conviene cerrarlos antes de hacer el repo público:

| Fichero | Qué arrastra |
|---|---|
| `docs/game-plan.html` | Tabla de **cinco** criterios al ~20% con "Social Engagement" como eje. Son **cuatro al ~25%** |
| `docs/estado.html` | Sección de MCP como pendiente y referencias a "Anthropic" en la mesa |
| `.env.example` | `ANTHROPIC_API_KEY` (B5) |
| `pyproject.toml` | Dependencia `anthropic` (#15, la quita Ángel con #31) |
| `CLAUDE.md`, `PLAN.md`, `CONTRIBUTING.md` | Tabla de módulos desactualizada (`broker.py` "REST", mesa "no cableada"), `ANTHROPIC_API_KEY` en la lista de claves |
| `README.md` | Menciona el MCP como descartado — correcto, pero revisar antes de publicar |

Premio ($5.000) y "cuatro criterios" **verificados correctos** en `CLAUDE.md`, `PLAN.md`,
`REGLAS-HACKATHON.md`, `CONCEPT.md`, `VIABILIDAD.md`, `estado.html` y este fichero. La única tabla
vieja que queda es la de `game-plan.html`.

---

## Decisiones cerradas

No revisar sin motivo. Fijadas por los probes de Día 0 (`../probes/RESULTS.md`) y por las decisiones
del finde (`PLAN-FINDE.md`).

- **Estructura:** iron condor como una sola orden `mleg` de 4 patas. Confirmado en paper.
- **Feed de datos de opciones:** `feed=indicative` (OPRA es de pago; indicative va ~2s fresco).
- **Griegas + IV:** de los snapshots de Alpaca. Sin motor de Black-Scholes propio.
- **Open interest:** solo en `/v2/options/contracts`, T-2. Vale para el GEX (régimen, aproximado).
- **DTE:** 1–3 días. 0DTE solo con stops más anchos y nunca después de las 14:00 ET.
- **Transporte:** **CLI de Alpaca** para toda la Trading API. REST solo para market data. Hecho.
- **Mesa LLM: 100% Featherless.** Anthropic descartado (no gastamos de bolsillo). Cupón `ALPACA26`.
- **Universo:** SPY, QQQ, IWM. Los tres tienen expiración diaria toda la semana.
- **Frecuencia > tamaño (#16):** `risk_per_trade` 0.5% del NAV plano toda la semana, `max_positions=8`.
- **Sin sleeve satélite direccional (#14):** el desk vende premium o se planta. Código borrado.
- **No fadear tendencia (#12):** `fade_trend=False` → stand down en tape con tendencia.
- **Blackout asimétrico (#33):** 2 h antes de un dato macro, 45 min después.
- **Expiraciones de competición:** ≤ 3 sep.
- **Dashboard:** opcional, solo si sobra tiempo el domingo.

## Decisiones abiertas

- **Calibración de umbrales.** `vrp_ratio_min`, `gex_min`, `short_delta`, `min_credit_frac` y el ancho
  de las alas siguen siendo **provisionales** (`agent/config.py` lo dice explícitamente). Salen del
  backtest, no de una opinión.
- **Rama A vs rama B.** Si tras calibrar dispara ~1–3 trades/semana/subyacente → operar normal. Si no
  dispara → narrativa "la mesa que sabe cuándo NO operar" y aflojar lo justo para tener trades.
- **Modelos Featherless finales** (3 para el ensemble + 1 para argumentar) y presupuesto del cupón.

---

## Datos clave

| | |
|---|---|
| Cuenta de **testing** | "Paper Trading" `PA3TQHQKM5AD` — $100.000, nivel 3. **Todo el desarrollo va aquí.** |
| Cuenta de **competición** | "PAPER UC3M" `PA39HSCQE8S3` — $100.000, nivel 3, intacta. **Primera orden: lun 31 ago 9:30 ET. No tocar antes.** Sus API keys solo en los secrets de GitHub. |
| Repo | github.com/alvaarocl/iv-desk — **privado hasta el 4 sep**, luego público (obligatorio) |
| Cupón Featherless | `ALPACA26` — $25, redimir en featherless.ai |
| Ventana de P&L | **lun 31 ago 9:30 ET / 15:30 CEST → snapshot equity cierre jue 3 sep 16:00 ET / 22:00 CEST** (4 sesiones) — ⚠️ pendiente de confirmar en Discord (#19) |
| Fin de submissions (lablab) | **4 sep 2026, 15:00 UTC = 17:00 CEST = 11:00 ET** |
| Expiraciones de competición | ≤ 3 sep |
| Premio | **$5.000** (1º $2.500 · 2º $1.500 · 3º $1.000) |
| Criterios de jurado | **4**, ~25% cada uno. Social Engagement es premio aparte |
