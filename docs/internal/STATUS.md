# Estado del proyecto

Última actualización: **30 ago 2026** (domingo tarde). Este archivo se actualiza a mano.
Plan del fin de semana en [`PLAN-FINDE.md`](PLAN-FINDE.md).

---

## Dónde estamos

**Todo lo técnico está hecho y en `main`**: 116 tests, `ruff` limpio, loop end-to-end
por el CLI. Además de eso, ya hecho este finde:

- **Calibrado con backtest real** (60 sesiones Alpaca): `vrp_ratio_min 1.05`, `gex_min 0.03`.
  11 trades / 174 sesiones, +$484 held-to-expiry. Es **rama B** — la señal dispara poco. Detalle
  en [`../../backtest/RESULTS.md`](../../backtest/RESULTS.md).
- **Mesa LLM probada en vivo contra Featherless** — transcript real, dentro del budget, coste
  trivial. Modelos verificados y puestos en las variables de GitHub.
- **CI verificado**: `workflow_dispatch` en `dry_run` contra UC3M pasa (instala CLI v0.0.14,
  autentica como `PA39HSCQE8S3`, no coloca nada, persiste el journal).
- **Dashboard en vivo** (inglés): https://alvaarocl.github.io/iv-desk/
- **Vídeo de la entrega listo**: `video/out/IVDESK-UC3M.mp4` (visuales Remotion + voz). Master mudo
  en `iv-desk-presentation.mp4`. Se re-renderiza el jueves con los números reales.
- Ventana de P&L confirmada en Discord · secrets/vars puestos · cuenta UC3M verificada ($100k, L3, cero histórico).

**Tareas de Álvaro: cerradas.** Ángel cierra las suyas (código ya en `main`). Queda pulir un par de
cosas, el go-live del lunes, y la entrega del viernes.

---

## Reglas oficiales (guidelines de Alpaca, recibidas 29 ago)

Datos del concurso verificados en [`REGLAS-HACKATHON.md`](../REGLAS-HACKATHON.md). Todas las fechas con
hora CEST y ET en [`CALENDARIO.md`](../CALENDARIO.md).

- **Criterios de jurado: CUATRO** — P&L Performance · Technology Implementation · Creativity &
  Originality · Presentation & Execution (~25% cada uno). **Social Engagement es un premio aparte**,
  no un eje del rubro → el P&L pesa **~25%, no ~20%**.
- **Premio: $5.000** (1º $2.500 · 2º $1.500 · 3º $1.000). Algunas fuentes dicen $6.000 contando dos
  premios sociales de $500. **No usar la cifra de $6.300 que arrastraba `CLAUDE.md`** (ya corregida
  allí y en `PLAN.md`).
- **Ventana de scoring de P&L (✅ confirmada en Discord, 29 ago):** lun **31 ago 09:30 ET → vie 4 sep
  09:30 ET**, con el **snapshot de equity al cierre del jueves 3 sep**. Cuentan 4 sesiones (31, 1, 2,
  3). Las posiciones que expiran el **viernes 4 quedan excluidas** de la medición → operaciones de
  competición con expiración ≤ 3 sep. Ver la cita literal en [`REGLAS-HACKATHON.md`](../REGLAS-HACKATHON.md).
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
| `agent/signal.py` | VRP ratio (Yang-Zhang + EWMA vs IV ATM), GEX normalizado con zona muerta, régimen ADX/EMA, skew, y **`stand_down` con el gate que bloquea**. ✅ **calibrado** con el backtest real (#6, #7, #10). |
| `agent/execution.py` | Selección de strikes (condor y vertical) con gates de liquidez, sizing, exit manager determinista (50% TP / 2× stop / cierre en expiración), `client_order_id` idempotente, `reconcile`. ✅ |
| `agent/risk.py` | Risk Officer: todos los gates, sin discrecionalidad. `evaluate()` entrada única. ✅ |
| `agent/calendar.py` | Calendario macro verificado (#17) + **blackout asimétrico 2 h antes / 45 min después** (#33). ✅ |
| `agent/seats.py` / `agent/debate.py` | **La mesa, 100% Featherless** (#31): Quant ensemble ×3 con mayoría estricta, Bull/Bear obligados a citar campos reales, Desk Head con predicción falsable validada. Clamp al cap del Risk Officer. Kill switch `DESK_DEBATE=off`. ✅ **cableada en `desk.py`**. |
| `agent/desk.py` | Loop completo: guardarraíl de cuenta → reconcile → salidas → gates de cartera → señal → debate → apertura → journal. ✅ end-to-end en `dry_run`. |
| `agent/journal.py` | Journal append-only + curva de equity + hook de grading de predicciones. ✅ |
| `backtest/replay.py` | Harness de replay. ✅ **corrido con datos reales** → `../../backtest/RESULTS.md`. |
| Tests | **116 tests**, `ruff` limpio. La mesa se testea con dobles inyectados: sin red y sin claves. Harness de replay del exit manager incluido. ✅ |
| `.github/workflows/desk.yml` | Cron cada 15 min en horario de mercado + `workflow_dispatch`; instala y **verifica la versión** del CLI (pin `0.0.14`). ✅ |
| Probes Día 0 | Los 3 pasaron. `../../probes/RESULTS.md`. ✅ |
| `docs/write-up.md` | Reescrito desde el código (#34/#18): sin Anthropic, sin MCP, cada afirmación con su fichero. 🔶 solo faltan los números del jueves. |
| `docs/RUNBOOK.md`, `docs/CALENDARIO.md` | ✅ hechos. **Leer el runbook los dos antes del lunes.** |
| `video/` | Proyecto Remotion (8 escenas, 60 fps, 3:12) + `NARRATION.md`. Vídeo final con voz: `video/out/IVDESK-UC3M.mp4`. ✅ v1 |
| `dashboard/` | Página estática en inglés, desplegada en GitHub Pages, lee `data/` en vivo. ✅ |

---

## Qué falta

### Antes del lunes — casi todo hecho

| Tarea | Quién | Estado |
|---|---|---|
| Calibrar con datos reales (`vrp_ratio_min`, `gex_min`, …) con evidencia | Álvaro (hecho por Ángel) | ✅ `../../backtest/RESULTS.md` |
| Probar la mesa Featherless end-to-end con claves reales | Álvaro | ✅ transcript real, dentro del budget |
| Secrets + variables en GitHub (UC3M, Featherless, modelos, `DESK_MODE=dry_run`) | Álvaro | ✅ |
| `workflow_dispatch` en `dry_run` contra UC3M | Álvaro | ✅ pasa |
| Verificar cuenta UC3M ($100k, L3, cero histórico) | humano | ✅ |
| Harness de replay del exit manager | Álvaro | ✅ `tests/test_exit_manager_replay.py` |
| Ventana de P&L en Discord | humano | ✅ jueves 3 EOD, expiraciones ≤ 3 sep |
| **Cerrar #6, #7, #10, #29–#36** — código ya en `main`, es papeleo | Ángel | ⬜ |
| **Bull/Bear adversariales** — dieron argumentos idénticos en la prueba en vivo | Ángel | ⬜ (único con impacto real) |
| Setup de OBS para grabar el lunes (#40) | Álvaro | ⬜ |
| Confirmar en equipo: **vamos con rama B** | equipo | ⬜ (30 s) |

### Lunes 31 — go-live

Seguir `docs/RUNBOOK.md`. 15:00 checklist · 15:30 primera posición en **testing** · ~16:15
`DESK_MODE=live` para UC3M · vigilar cada run de 15 min · grabar clips · post social #1.

### Jueves 3 (tras el cierre, 22:00 CEST) — el cuello de botella

- Capturas de UC3M (equity, posiciones, activity log) → **fijar el número de P&L**.
- Re-render del vídeo: `video/src/data.ts` → `RESULTS.mode='live'` + bloque S7 de `NARRATION.md`
  → `npm run render` → re-grabar solo el audio de S7 → recomponer.
- Write-up final con los números reales (Ángel).

### Viernes 4 (17:00 CEST) — entregar

Subir vídeo a YouTube no listado → link en [`SUBMISSION.md`](SUBMISSION.md) · repo a público
(`gh repo edit --visibility public`, ese día) · formulario lablab (repo, vídeo, account ID
`PA39HSCQE8S3`, hasta 5 links sociales, título/descripción/tags) · post social final.

### Opcional / recortes

Deck / slides (las reglas no lo piden — el write-up + el vídeo cubren Presentation) · MCP ·
reflexión nocturna · ensemble a 1 modelo si el cupón aprieta.

---

## Deuda de documentación detectada (no arreglada en esta lane)

Ficheros fuera del alcance de `lane/senal-finde`. **El write-up y el runbook ya están limpios**;
estos son internos y no se entregan, pero conviene cerrarlos antes de hacer el repo público:

| Fichero | Qué arrastra |
|---|---|
| `docs/internal/game-plan.html` | Tabla de **cinco** criterios al ~20% con "Social Engagement" como eje. Son **cuatro al ~25%** |
| `docs/internal/estado.html` | Sección de MCP como pendiente y referencias a "Anthropic" en la mesa |
| `.env.example` | `ANTHROPIC_API_KEY` (B5) |
| `pyproject.toml` | Dependencia `anthropic` (#15, la quita Ángel con #31) |
| `CLAUDE.md`, `PLAN.md`, `CONTRIBUTING.md` | Tabla de módulos desactualizada (`broker.py` "REST", mesa "no cableada"), `ANTHROPIC_API_KEY` en la lista de claves |
| `README.md` | Menciona el MCP como descartado — correcto, pero revisar antes de publicar |

Premio ($5.000) y "cuatro criterios" **verificados correctos** en `CLAUDE.md`, `PLAN.md`,
`REGLAS-HACKATHON.md`, `CONCEPT.md`, `VIABILIDAD.md`, `estado.html` y este fichero. La única tabla
vieja que queda es la de `game-plan.html`.

---

## Decisiones cerradas

No revisar sin motivo. Fijadas por los probes de Día 0 (`../../probes/RESULTS.md`) y por las decisiones
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
| Ventana de P&L | **lun 31 ago 9:30 ET / 15:30 CEST → snapshot equity cierre jue 3 sep 16:00 ET / 22:00 CEST** (4 sesiones) — ✅ confirmada en Discord 29 ago; expiraciones de competición ≤ 3 sep |
| Fin de submissions (lablab) | **4 sep 2026, 15:00 UTC = 17:00 CEST = 11:00 ET** |
| Expiraciones de competición | ≤ 3 sep |
| Premio | **$5.000** (1º $2.500 · 2º $1.500 · 3º $1.000) |
| Criterios de jurado | **4**, ~25% cada uno. Social Engagement es premio aparte |
