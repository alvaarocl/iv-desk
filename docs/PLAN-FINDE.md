# Plan del fin de semana — sáb 29 → lunes 31 (go-live 15:30 CEST)

> **Para el agente de Ángel:** tus tareas son la sección **ÁNGEL (A1–A8)**. Cada una tiene un
> issue en GitHub etiquetado `finde` y asignado a `aaangelmartin` — trabaja de ahí:
> `gh issue list --assignee @me --label finde`. Rama sugerida: `lane/senal-finde` desde `main`.
> Las de Álvaro (B1–B8) son para contexto, no las toques.

---

## Estado de partida

`main` está mergeado y verde: **116 tests**, `ruff` limpio, el loop corre end-to-end contra Alpaca
vía CLI en `dry_run`. Todo el código de las dos lanes está integrado. Lo que falta **no es código
nuevo**, es calibración con datos reales + probar la mesa LLM + ops + entrega.

### Decisiones cerradas (no re-litigar)
- **#16 → frecuencia > tamaño:** `risk_per_trade` fijo 0.5% NAV toda la semana (sin rampa),
  `max_positions=8`, menos selectivo. Muchos trades pequeños alimentan Technology/Creativity/
  Presentation aunque el P&L sea plano.
- **Ventana de P&L:** snapshot jueves 3 sep EOD. 4 sesiones (31 ago, 1–3 sep).
- **Cuenta:** los $200k del dashboard son buying power; `portfolio_value` = $100k, OK.
- **Arranque lunes escalonado:** 15:30 primera posición en la cuenta de **testing**, ~16:15 CEST
  arrancar UC3M con el ciclo ya verificado en vivo.
- **Anthropic descartado** (no gastamos de bolsillo). **La mesa LLM va 100% Featherless** (cupón
  `ALPACA26`, $25). Bull/Bear/Desk Head pasan de `AnthropicSeatClient` a `FeatherlessSeatClient`.
- **Dashboard: dentro**, versión mínima el domingo (tarea de Álvaro).
- **Vídeo:** guion Ángel, grabación + montaje Álvaro.

---

## ÁNGEL — señal, mesa LLM, entrega

### A1 · Backtest con keys reales · P0 · bloquea A2 · issue
`uv run python -m backtest.replay --days 60 --symbols SPY,QQQ,IWM` con el `.env` de testing.
Sacar la tabla del embudo: sesiones → `sell_premium` → `structure` → `credit_ok` → `size_ok` →
`risk_ok` → P&L aproximado. Commitear el output como exhibit (`backtest/RESULTS.md`).
**Salida:** o dispara ~1–3 trades/semana/subyacente (rama A), o no dispara (rama B → narrativa
"la mesa que sabe cuándo NO operar"). Avanza **#5**.

### A2 · Fijar parámetros de calibración · P0 · issue
Con la tabla de A1, ajustar en `agent/config.py`: `vrp_ratio_min`, `short_delta`,
`min_credit_frac`, `gex_min`. Commit **con la evidencia al lado** (el propio `config.py` dice
"change them there, with evidence"). Confirmar que `max_positions=8` a 0.5% no revienta
`max_portfolio_risk=0.10`. Cierra **#6, #7, #10**.

### A3 · Mesa LLM 100% Featherless · P0 · el diferenciador · issue
Refactor en `agent/seats.py` / `agent/debate.py`: Bull/Bear/Desk Head dejan de usar
`AnthropicSeatClient` y pasan a `FeatherlessSeatClient` (ya existe, cumple el `SeatClient`
protocol — swap de constructor, no reescritura). Opcional: env `DESK_DEBATE_PROVIDER`.
Elegir modelos: 3 ids para el ensemble Quant + 1 para argumentación, con buen JSON-following.
Borrar `ANTHROPIC_MODEL` y el import lazy de `anthropic` en `seats.py`. Cierra **#13**.

### A4 · Probar el debate end-to-end con Featherless real · P0 · issue
Forzar una señal que pase los gates (o fixture) y correr `debate.review_open` con las keys reales.
Confirmar transcript completo + tesis falsable en `data/journal.jsonl` con `approved` y el veredicto
de cada asiento. Medir el reloj real vs `DESK_DEBATE_BUDGET_S=90`. Verificar que el coste cabe en
los $25 del cupón; si aprieta, ensemble a 1 modelo (cut-list de `PLAN.md`).

### A5 · Decisiones de señal pendientes · P1 · issue
- **#12 fade_trend:** ya en `False` (stand down en tendencia). Confirmar + escribir el porqué en
  `docs/strategy-spec.md` (coherencia: no predecimos dirección). Cerrar #12.
- **`BLACKOUT` en `calendar.py`:** 2h bloquea la mañana del 1 y del 3 sep hasta ~12:00 ET. Con
  "frecuencia > tamaño" duele. Decidir 2h vs ~75 min y escribirlo (media de decisión conjunta D1).
- **#25 asignación temprana:** el código ya detecta equity inesperado y se planta. Escribir en
  `strategy-spec.md` que el riesgo se acepta (ex-div de SPY fuera de la ventana). Cerrar #25.
- **#26:** ya arreglado + `tests/test_marketdata_bars.py` lo cubre. Solo cerrar el issue.
- **#11, #14:** código mergeado. Verificar acceptance y cerrar.

### A6 · Write-up desde el código · P1 · #18 · issue
Reescribir `docs/write-up.md` con lo que existe de verdad — cada afirmación verificable abriendo un
fichero. Marcar "[Resultados: rellenar jueves]". **Quitar toda mención a Anthropic y MCP.** Frase de
arquitectura: "coincide con lo que Alpaca publica como buena práctica" (ver `REGLAS-HACKATHON.md`).
Cierra **#18**.

### A7 · Cierre de docs e issues · P1/P2 · issue
- **#19:** ✅ ventana de P&L confirmada en Discord (29 ago) — snapshot jueves 3 EOD, expiraciones ≤ 3 sep. Cerrar #19.
  Verificar premio ($5.000) y "4 criterios" corregidos en todos los docs. Cerrar #19.
- **#24:** `docs/RUNBOOK.md` ya fusionado. Verificar que el checklist de arranque dice "mesa
  Featherless", no Anthropic. Cerrar #24.
- Quitar `anthropic` de `pyproject.toml` una vez A3 está hecho (termina #15).

### A8 · Guion del vídeo · P1 · entregar a Álvaro el domingo · issue
2–3 min. Estructura en `docs/SUBMISSION.md`. Foco: el agente decidiendo solo — el debate, la tesis,
**el momento en que se niega a operar**. No el P&L.

---

## ÁLVARO — ejecución, ops, dashboard, grabación (contexto, no tocar)

- **B1** Verificar cuenta UC3M `PA39HSCQE8S3` ($100k, nivel 3, cero histórico).
- **B2** Secrets + variables en GitHub (keys UC3M, Featherless; `ALPACA_ACCOUNT_ID`,
  `FEATHERLESS_MODELS`, `DESK_MODE`). Editar workflow: quitar `ANTHROPIC_API_KEY`, añadir
  `DESK_DEBATE`/`DESK_DEBATE_BUDGET_S`.
- **B3** `workflow_dispatch` en `dry_run` contra UC3M → confirma CLI + auth + `account=PA39HSCQE8S3`.
- **B4** ✅ hecho — `tests/test_exit_manager_replay.py` (trayectorias take/stop/expiry + lifecycle live).
- **B5** Fix de drift en `.env.example`.
- **B6** Dashboard mínimo (`dashboard/index.html` estático leyendo `data/`).
- **B7** Setup de grabación (OBS, planos).
- **B8** Vigilancia en vivo (lunes).

---

## Decisiones conjuntas — call de ~30 min (sáb noche / dom mañana)

| # | Decisión | Depende de |
|---|---|---|
| D1 | `BLACKOUT` 2h vs 75 min | backtest A1 (cuántos trades pierde) |
| D2 | Rama A (calibrar y operar) vs rama B (operar poco + narrativa) | A1 |
| D3 | Modelos Featherless finales (3 + 1) y presupuesto del cupón | A3, A4 |
| D4 | Procedimiento escalonado exacto del lunes, quién al teclado a las 15:30 | — |

---

## Checkpoint domingo noche — gate antes del lunes

Todo cierto en `main`:
- [ ] `uv run pytest -q` verde.
- [ ] `uv run ruff check agent/ tests/ backtest/` limpio.
- [ ] `workflow_dispatch` en `dry_run` desde GitHub contra UC3M: instala CLI, autentica,
      loguea `account=PA39HSCQE8S3`, coloca nada, persiste el journal.
- [ ] El debate produce un transcript real (Featherless) con tesis en `data/journal.jsonl`.
- [ ] `backtest/` con la tabla del embudo commiteada; `config.py` con los parámetros calibrados + evidencia.
- [ ] `docs/write-up.md` sin nada que no exista (ni Anthropic ni MCP).
- [ ] Dashboard desplegado (o cortado explícitamente y anotado).
- [ ] Los 13 issues de Ángel cerrados o con estado claro.

Cut-list si el gate no pasa: dashboard → reflexión nocturna → ensemble a 1 modelo → Bull/Bear a
solo Desk Head → skew.

---

## Orden de construcción

**Sábado, en paralelo:**
- Ángel: **A1 → A2** (cadena crítica).
- Álvaro: B1 → B2 → B3, luego B4 ✅.

**Sábado noche:** D1–D4.

**Domingo, en paralelo:**
- Ángel: **A3 → A4 → A6 → A5/A7 → A8**.
- Álvaro: B6 → B5 → B7.

**Domingo noche:** merge de las dos ramas a `main`, checkpoint gate.

**Lunes:** B8 + arranque escalonado.
