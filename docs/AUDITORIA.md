# Auditoría técnica — 29 ago 2026 · estado al 30 ago

Revisión completa del repo en el commit `75b9af3` (~1.150 LOC de Python). Cada hallazgo lleva fichero y línea, y el issue donde se sigue.

**Cómo leer esto:** los P0 rompen la ventana de P&L y van antes del lunes 31 a las 09:30 ET. Los P1 afectan a robustez, que es un eje explícito del jurado. Los P2 son coherencia.

> Mantened este fichero vivo: si un PR arregla `execution.py:158`, que actualice también la entrada correspondiente aquí en el mismo commit.

---

## Estado al 30 ago (domingo)

**Los 8 P0 y los 9 P1 están cerrados en `main`.** El repo pasa a público el viernes; esta sección
es el resumen que verá un jurado. Detalle fichero-a-fichero en cada entrada de abajo (todas llevan
ya su marca ✅).

| Severidad | Nº | Estado |
|---|---|---|
| **P0** | 8 | ✅ **8/8 cerrados.** Ejecución por el CLI de Alpaca (#4), `limit_price` firmado (#1), exit manager en $/lote con replay harness (#2), `client_order_id` + `reconcile` contra Alpaca (#3), estrategia calibrada con 60 sesiones reales (#5/#6/#7), barras diarias paginadas (#26). |
| **P1** | 9 | ✅ **9/9 cerrados.** 116 tests + `ruff` limpio (#9), CLI pineado `v0.0.14` con verificación de versión (#8), capa LLM construida y **cableada en `desk.py:248`** (#13), gate de liquidez + `_mid()` sin caída silenciosa a 0 (#22), `net_delta` real (#11), umbral de GEX (#10), fade-trend resuelto por decisión (#12), runbook + contingencia de cron saltado (#23/#24). |
| **P2** | 5 | ✅ 4/5. Código muerto borrado (#14), calendario macro verificado (#17), asignación temprana mitigada y detectada por doble vía (#25). Sizing (#16) resuelto **por decisión humana**: 0.5% plano toda la semana, `max_positions=8` — ver [`VIABILIDAD.md`](VIABILIDAD.md) y `config.py:55-63`. Dependencias sin usar (#15): `anthropic`/`openai` fuera; quedan por barrer las restantes. |

Deuda de documentación pendiente de barrer antes del viernes: recuento de tests coherente en los
tres sitios (ahora **116**), `README.md` describe `dashboard/` como "Next.js" (es un `index.html`
estático) y `data/` con ficheros que aún no existen.

---

## Resumen (original — 29 ago)

| Severidad | Nº | Efecto si no se arregla |
|---|---|---|
| **P0** | 8 | O no operamos nada en 4 sesiones, o operamos con el signo del precio invertido. Y no cumplimos el requisito técnico del hackathon |
| **P1** | 9 | Estado inconsistente, cero tests, gates que son no-ops, créditos calculados sobre quotes fantasma, y el diferenciador (capa LLM) sin construir |
| **P2** | 5 | Docs que describen comportamiento inexistente, sizing incoherente con la postura de riesgo, y asignación temprana sin contemplar |

---

## P0 — bloqueantes

### 1. ~~El `limit_price` de entrada va con el signo invertido~~ ✅ RESUELTO (29 ago)
`execution.py:158`, `broker.py:99` · issue #1

> Arreglado: `execution.py:277` manda `limit_ps = -abs(credit_ps * 0.92)` (negativo = crédito), y
> `broker.py` rechaza un `limit_price` de cero con `ValueError` — el signo transporta la dirección,
> así que un cero es siempre un bug. Test: `test_execution.py` (límite negativo para un crédito,
> rechazo del cero).

En `order_class: mleg` el `limit_price` **va firmado**: positivo = débito, negativo = crédito (ver [`API-ALPACA.md`](API-ALPACA.md)). El código manda siempre positivo:

```python
broker.submit_mleg(t.legs, contracts, limit_price=max(credit * 0.92, 0.01))
```

Para un condor de crédito eso significa *"acepto pagar hasta $1.10 de débito"* por una estructura que debería pagarnos ~$1.20. La orden se vuelve marketable al instante y perdemos todo el control de precio.

**Por qué no lo cazó el probe:** en `probes/RESULTS.md` se mandó un condor *largo* (débito) a `limit_price: "0.01"`. Solo validamos la mitad de la convención que no vamos a usar.

El signo de **salida sí está bien** (`max(debit * 1.08, 0.01)` — recomprar es un débito).

### 2. ~~Bug de unidades en el exit manager~~ ✅ RESUELTO (29–30 ago)
`execution.py:170-186` · issue #2

> Arreglado: convención `_ps` (por acción) documentada en `execution.py:7`; `entry_credit` y los
> umbrales `take`/`stop` ahora están en la misma unidad. Cubierto por `tests/test_exit_manager_replay.py`
> (take-profit dispara una sola vez, stop a 2× crédito, cierre por expiración desde las 15:30 ET).

`entry_credit` está en **dólares** (`credit * 100`), pero `_combo_cost_to_close()` devuelve precio **por acción** (~1.20):

```python
take = credit * (1 - params.take_profit_frac)   # 120 * 0.5 = 60  (dólares)
if debit <= take:                                # 1.20 <= 60  → SIEMPRE cierto
```

Toda posición se marca como take-profit en el primer loop tras abrirse. El `pnl` calculado es fantasía. Coherente con que `STATUS.md` admita que el exit manager nunca se probó sobre una posición real.

### 3. ~~Se asume el fill y el estado vive en un `git push || true`~~ ✅ RESUELTO (29 ago)
`execution.py:151-160`, `.github/workflows/desk.yml:47` · issue #3

> Arreglado en tres frentes: `_client_order_id()` determinista por intención de trade
> (`execution.py:209`) → un re-run no duplica; `_await_fill()` (`execution.py:223`) no marca `open`
> hasta confirmar ejecución; `reconcile()` (`execution.py:298`) reconstruye el libro desde
> `broker.positions()`/`orders()` en cada arranque — Alpaca es la fuente de verdad, `trades.jsonl`
> es un journal. Y el `git push` del workflow ya no es best-effort: `desk.yml:93-97` hace
> `pull --rebase` y reintenta 3 veces, con `exit 1` si no lo consigue.

Tres problemas encadenados que producen **posiciones duplicadas o fantasma**:

- `open_trade()` escribe `status: "open"` justo después de mandar la orden, sin comprobar ejecución. Alpaca es explícito: *"All orders are simply 'requests'... el 200 solo confirma recepción, no ejecución."*
- `data/trades.jsonl` es la única fuente de verdad del libro y se persiste commiteándolo con push best-effort. Un push fallido → el siguiente run hace checkout de un `main` viejo, olvida la posición y **la vuelve a abrir**.
- **Cero `client_order_id`** en todo el repo. Nada impide un doble envío.

El repricing que promete `strategy-spec.md` ("reprice cada 30s, máx 3 pasos") no está implementado.

### 4. ~~No cumplimos el requisito técnico del hackathon~~ ✅ RESUELTO (29 ago)
`broker.py` completo · issue #4 · ver [`REGLAS-HACKATHON.md`](REGLAS-HACKATHON.md)

Las reglas exigen Trading API **+ MCP o CLI**. `broker.py` es REST puro; el CLI se instala en el workflow y no se usa jamás; el MCP no existe. **Es elegibilidad, no una mejora.**

> Arreglado (commit `30bbeb1`): `broker.py:38 _cli()` shell-out a `alpaca api METHOD /path` por
> `subprocess` para **toda** la Trading API (cuenta, clock, posiciones, órdenes, `mleg`, cancelaciones).
> `marketdata.py` sigue en REST `httpx`, que es la excepción permitida (solo lecturas de datos de
> mercado). El workflow instala y **verifica** el CLI pineado a `v0.0.14` (`desk.yml:69-74`).

### 5. ~~La estrategia probablemente no dispara nunca~~ ✅ CONFIRMADO Y CORREGIDO (29 ago)
issue #5 · `backtest/replay.py`

**El backtest confirmó la sospecha: con los parámetros anteriores, 0 trades en 180 sesiones-subyacente.**

| Gate | Supervivientes | |
|---|---|---|
| sesiones evaluadas | 180 | |
| VRP rico | 41 | mata el 77% |
| estructura construida | 41 | |
| `credit/width >= min_credit_frac` | **0** | **mata el 100% restante** |

**El gate de crédito era el letal, y era independientemente fatal:** apagando el VRP por completo
(`0.03 → 0.00`) los candidatos se triplican a 120 y **siguen saliendo 0 trades**. El
`credit/width` observado tuvo una mediana de 0.240 y un máximo de 0.310 — el umbral de 0.33 estaba
**por encima del techo geométrico** de la estructura. Ver la corrección al diagnóstico en la entrada 7.

Con los parámetros actuales: **57 trades**. Estrechar el ala sola no bastaba (4/2 → 2/1 con el
umbral viejo da solo 2 trades): hacían falta **las dos palancas**.

> ⚠️ **Esto es tape sintético, no mercado real.** Valida el pipeline y el argumento geométrico
> (que es analíticamente sólido), pero **el P&L de +$2.670 no es una previsión de nada**. La fila de
> `gex_min` es circular por construcción y no prueba nada. La corrida real necesita claves de Alpaca:
> `uv run python -m backtest.replay`.

**Dos avisos sobre la calibración nueva:**
- `gex_min = 0.10` tiene **muy poco margen**: subirlo a 0.30 devuelve el desk a cero trades. Necesita
  una lectura con datos reales antes del lunes.
- `min_credit_frac = 0.20` no está mordiendo ahora mismo (0.20 y 0.10 dan lo mismo), pero 0.30 baja a
  14 trades. Está bien colocado justo por debajo de la distribución, no por encima.

### 6. ~~El VRP está mal medido y su umbral es absoluto~~ ✅ RESUELTO (29 ago)
`signal.py` (`rv_forecast`, `build_signal`), `config.py:29` · issue #6

- **Comparamos magnitudes distintas:** IV de opciones a 1-3 días contra realizada histórica de 20 sesiones anualizada. Nuestro diagnóstico *"la vol está baja"* puede ser en buena parte un **artefacto de medición**.
- **`vrp_min = 0.03` es absoluto.** Con ATM IV al 8%, exige que la IV esté ~40% por encima de la RV. Calibrado mentalmente para un mundo de VIX 20. Debería ser un ratio: `IV / RV_hat >= 1.15`.
- Bug menor: en `yang_zhang_rv` los arrays `log_ho/log_lo/log_co` tienen longitud N y `log_oc/log_cc` longitud N-1; los `[-n:]` quedan desplazados un día.

### 7. ~~`min_credit_frac` × `width_spy` es inalcanzable~~ ✅ RESUELTO (29 ago) — y la causa no era la que creíamos
`config.py:30,33`, `desk.py:98` · issue #7

> **Corrección al diagnóstico original.** Esta entrada culpaba a la volatilidad baja. Es
> principalmente **geometría**: en un condor `credit/width ≈ 2 × |Δ| medio entre el strike corto y el
> largo`, porque se cobran las dos alas y solo una puede perder. Al estrechar el ala, la pata larga
> deja de ser un 5Δ y el ratio **sube**. Por eso el arreglo fue bajar el ancho (SPY/QQQ 4 → 2, IWM
> 2 → 1), no esperar a que suba la IV.


`0.33 × 4.0` exige **$1.33 de crédito en un condor de 4 puntos a 18Δ**. Con IV al 6-10% a 1-3 DTE eso recoge $0.30-0.60 → `cr_frac ≈ 0.10`. Rechazado siempre. **Es independiente del VRP**: aunque se arregle #6, este sigue bloqueando todo.

### 23. ~~`daily_bars` devuelve las barras más antiguas~~ ✅ RESUELTO (29 ago)
`agent/marketdata.py:31-36` · issue #26 · **encontrado por el backtest, verificado a mano**

`start` se calcula a 110 días naturales (~78 sesiones) pero `limit` es 60, y Alpaca devuelve en orden
**ascendente** — así que `limit` corta las barras **más nuevas**. La serie que alimenta `rv_forecast()`
**termina ~18 sesiones antes de hoy**.

El gate de VRP compara la IV de hoy contra la volatilidad realizada de hace casi un mes. No falla ni
avisa: devuelve un número plausible. **Invalidaba parcialmente la calibración de `vrp_ratio_min`.**

> Arreglado: `daily_bars` ahora pagina la ventana entera y devuelve la cola
> (`bars[-lookback_days:]`), con 3 tests de regresión. **Consecuencia importante:** el smoke run
> de la lane de ejecución que midió `rv_hat` en 15-27% contra una IV del 8-12% se hizo con este
> bug dentro *y* con el `yang_zhang` que duplicaba el gap overnight. **Esa medición no sirve para
> concluir nada sobre el VRP** — hay que repetirla con las dos correcciones dentro.

---

## P1 — robustez

### 8. ~~El CLI está pineado a `latest` de un binario en Alpha~~ ✅ RESUELTO (29 ago)
`.github/workflows/desk.yml:33-36` · issue #8

Se descarga `releases/latest` en cada ejecución del cron — 26 veces al día durante 4 días. El README de `alpacahq/cli` avisa: *"Do not depend on current behavior in production workflows."* Un release a mitad de semana rompe el loop en silencio.

> Arreglado: `desk.yml:26` pinea `ALPACA_CLI_VERSION: "0.0.14"`, se cachea por clave de versión, y
> `desk.yml:69-74` hace un assert duro (`exit 1`) si `alpaca version` no imprime exactamente ese pin.

### 9. ~~Cero tests~~ ✅ RESUELTO (29–30 ago)
issue #9

No existe `tests/`, hay **0 funciones `test_`**, y `pyproject.toml` declara `testpaths = ["agent", "tests"]`. `CONTRIBUTING.md` pide `pytest -q` antes de mergear: pasa vacío, siempre. Un solo test habría cazado #2.

> Arreglado: **116 tests** en 10 ficheros, `ruff` limpio, sin red y sin claves (la mesa se prueba
> con dobles inyectados). `test_debate.py` cubre el contrato de seguridad de la capa LLM (la
> inyección de prompt no puede subir el cap, el chain nunca llega al prompt, timeouts de proveedor);
> `test_exit_manager_replay.py` es el harness de replay del exit manager. Sigue sin haber un test
> end-to-end de `desk.run_once()` — asumido.

### 10. ~~GEX: solo se usa el signo, falta umbral~~ ✅ RESUELTO (29 ago)
`signal.py:210` · issue #10

`gex_sign = 1 if gex >= 0 else -1`. Un GEX de +$1M y uno de +$50Bn se tratan igual, sobre un dato con retraso T-2. `STATUS.md` lista "umbral de GEX" como parámetro a calibrar pero **no existe en `config.py`** (solo `gex_band`, que es la ventana de strikes).

### 11. ~~`net_delta` cableado a `0.0`~~ ✅ RESUELTO (29 ago)
`desk.py:78`, `desk.py:93` · issue #11

El gate de banda de delta de cartera de `risk.evaluate()` **nunca puede saltar**. `strategy-spec.md` lo vende como una de las protecciones de la mesa y en la práctica no existe.

### 12. ~~La lógica de "fade the trend" no está justificada~~ ✅ RESUELTO (29 ago)
`signal.py:137-146`, `signal.py:222-227` · issue #12

`classify_regime` invierte el sesgo a propósito: `trending_up → "bearish" → call_credit_spread`. Es decir, **vende calls por encima del mercado cuando el ADX dice que hay tendencia alcista**. Y las ramas de `bias` solo se alcanzan cuando `regime != "range"`, o sea justo cuando hay tendencia.

Vender primas contra la dirección del movimiento es la forma clásica de perder dinero con opciones cortas, y el único filtro es un signo de GEX ruidoso. **Es la línea más peligrosa del repo** y no aparece explicada en ningún doc.

Además `_adx()` (`signal.py:126`) devuelve un DX puntual, no un ADX suavizado — el umbral `> 22` no significa lo que dice la spec.

### 13. ~~La capa LLM no existe~~ ✅ CONSTRUIDA Y CABLEADA (29 ago)
`agent/seats.py`, `agent/debate.py` · issue #13

> Construida el 29 ago. La propiedad de seguridad es una línea (`debate.py:263`):
> `contracts = max(0, min(int(head.contracts), cap))`, donde `cap` es la `n` que ya aprobó
> `risk.evaluate()`. **El debate es una función monótona no creciente del riesgo**: puede recortar
> o vetar, nunca ampliar. Hay un test de inyección de prompt que lo comprueba.
> Los asientos corren en hilos *daemon* con `join(timeout)`, no en un `ThreadPoolExecutor`: su
> `__exit__` hace `shutdown(wait=True)` y volvía a esperar al asiento que acababas de descartar,
> convirtiendo un presupuesto de 90 s en un cuelgue de 30 s+ en un cron de 15 minutos.


Era **el diferenciador del proyecto** y estaba sin construir. Ya no: la mesa (Quant ensemble ×3 con
mayoría estricta, Bull/Bear adversariales, Desk Head con predicción falsable) corre 100% sobre
Featherless y está cableada en `desk.py:248`. `anthropic`/`openai` fuera de `pyproject.toml` (#31).

### 20. ~~Falta el gate de liquidez y `_mid()` devuelve 0.0 en silencio~~ ✅ RESUELTO (29 ago)
`execution.py:52-58`, `execution.py:71-92` · issue #22

`_mid()` cae a `t.get("p", 0.0)` cuando un contrato no tiene quote ni trade — pasa en strikes lejanos con `feed=indicative`. Ese **cero se propaga al crédito**, y de ahí al sizing y al `max_loss`. Puede inflar contratos o colar un trade con datos basura.

Y el gate de liquidez que exige `strategy-spec.md` (`OI > 500`, spread `< 10%` del mid, ambas patas) **no está implementado** en `select_condor()` ni en `select_vertical()`. El OI ya está en memoria para el GEX, así que el filtro es casi gratis.

> Arreglado: `_mid()` ya no cae a 0 en silencio (test `test_execution.py`: "mid never falls back to
> 0"); `select_condor()`/`select_vertical()` aplican `MIN_OI = 500` y `MAX_SPREAD_FRAC = 0.10` en
> ambas patas (`execution.py:33-34`).

### 21. ~~No hay plan si el cron se salta una ejecución~~ ✅ RESUELTO (29 ago)
`.github/workflows/desk.yml` · issue #23

Los `schedule:` de GitHub Actions son **best-effort**. Si no corre el run de las 15:45 ET, una posición en expiración se va a expiración con riesgo de pin y asignación. No hay kill switch documentado ni forma trivial de ver la última ejecución. **La robustez del workflow es un eje explícito del jurado** y ahora mismo no tenemos respuesta a la pregunta obvia.

> Arreglado: el cierre por expiración dispara en **cualquier** run desde las 15:30 ET, no solo a
> las 15:45 (`execution.py:411-412`); `reconcile()` en cada arranque resuelve el estado real; el
> `client_order_id` determinista impide que un re-run duplique. Kill switch (`DESK_MODE=exits_only`)
> y árbol de incidentes documentados en [`docs/RUNBOOK.md`](RUNBOOK.md). `timeout-minutes: 10` en el
> job para que un run colgado no bloquee la cola.

### 22. ~~No existe runbook para las sesiones en vivo~~ ✅ RESUELTO (29 ago)
issue #24 · **`docs/RUNBOOK.md` creado**

`PLAN.md` dice *"Watch every 15-min invocation"* pero no hay documento que diga qué mirar ni qué hacer cuando algo falla. La ventana empieza el lunes a las **15:30 CEST** — eso se escribe antes, no se improvisa.

---

## P2 — coherencia

### 14. ~~Código muerto: sleeve satélite y `conviction`~~ ✅ RESUELTO (29 ago)
`config.py:38`, `desk.py:93`, `signal.py:220`, `signal.py:229` · issue #14

- `satellite_frac` **nunca se lee**. `is_satellite` es siempre `False`. La rama `debit_spread` pone `sell = False`, con lo que `desk.py:85` la salta y `_pick()` ni tiene rama para ella. **El "modo adaptativo" que `CONCEPT.md` vende como mitigación del riesgo de baja volatilidad no está implementado** — y ese riesgo es exactamente el que se ha materializado.
- `conviction` se calcula y tiene 0 usos fuera de `signal.py`.

### 15. ~~Dependencias declaradas y no usadas~~ ✅ RESUELTO (30 ago) — esta entrada estaba desactualizada
`pyproject.toml` · issue #15

Esta entrada seguía sin marcar aunque el fix ya estaba hecho: `pyproject.toml` lleva desde el 30 ago con `alpaca-py`, `pandas`, `scipy`, `pydantic`, `rich` y `anthropic` fuera (comentario en el propio fichero: *"Removed 2026-08-30 (issue #15)"*). Verificado el 2 sep que las 5 dependencias declaradas hoy tienen import real: `httpx` (`marketdata.py`), `numpy` (`signal.py`), `python-dotenv` (`broker.py`/`config.py`/`debate.py`/`marketdata.py`), `openai` (`seats.py` — habla el API compatible de Featherless, no el SDK de OpenAI de pago) y `tzdata` (`ZoneInfo` en `calendar.py`/`desk.py`/`execution.py`). Nada declarado y sin usar.

### 16. El sizing no puede puntuar, pero sí puede perder — 🔄 REABIERTO Y REVERTIDO (31 ago)
`config.py:32` · issue #16

0.5% de $100k = $500/trade → **1 contrato** → ~$120 de crédito. Con 3 posiciones en 4 sesiones el mejor escenario posible es ~0.3% de retorno. Pero el max loss del condor son $280 y una rotura se come dos ganadores. **Cedemos el upside y conservamos el downside.** Ver [`VIABILIDAD.md`](VIABILIDAD.md).

> Resuelto por decisión de equipo (opción c de `VIABILIDAD.md`): **frecuencia > tamaño**.
> `risk_per_trade` 0.5% **plano toda la semana** (sin rampa lunes→martes), `max_positions` 6 → 8.
> Más trades pequeños de riesgo definido = más transcripts de debate y una curva de equity con
> textura, con el downside topado por `max_portfolio_risk` 0.10. No se persigue el eje de P&L
> (4 sesiones son una lotería de varianza); ver `config.py:55-63` y `backtest/RESULTS.md`.

> **Revertido el 31 ago tras la sesión 1.** La tesis "frecuencia > tamaño" dependía de que hubiera
> trades. El lunes dio **cero** — y no por la señal (SPY pasó todos los gates deterministas) sino
> porque `DESK_MODE` seguía en `dry_run`, el secret de Featherless daba 401 y el cron disparó 1 run
> de ~27. Con la tasa de disparo del 6,3% del backtest sobre las 9 sesiones-subyacente que quedan,
> la esperanza es ~0,6 trades: la frecuencia ya no está disponible como palanca.
> `risk_per_trade` **0.005 → 0.02** (~12 contratos, max_loss $1.872/trade). Los gates de entrada
> **no** se tocan: aflojar `vrp_ratio_min` o `gex_min` es como se revientan los libros de vol corta,
> y una cuenta en pérdidas puntúa peor que un +0,03%.
>
> Efecto secundario conocido: `max_net_delta` 0.30 pasa a ser el gate que manda por delante de
> `max_positions`, porque el presupuesto de delta es absoluto y no escala con el tamaño. Si
> aparecen rechazos `portfolio delta band`, la respuesta pre-acordada es `max_net_delta → 0.60`
> (decidida en frío, no en sesión).

### 17. ~~Riesgo de asignación temprana en patas cortas ITM~~ ✅ MITIGADO (29 ago)
`execution.py:180-182` · issue #25

Las opciones sobre SPY/QQQ/IWM son de **estilo americano**: una pata corta ITM puede asignarse en cualquier momento. `strategy-spec.md` promete cerrar toda pata corta ITM a las 15:45 ET, pero el código solo cierra la estructura completa **el día de expiración**. Si nos asignan, aparecen ~$77.000 de nocional en acciones y el agente no lo contempla en absoluto.

Riesgo bajo en esta ventana (el ex-dividendo de SPY cae fuera), pero hay que decidir explícitamente si se mitiga o se acepta.

### 24. El corte de expiración ≤ 3 sep estaba documentado pero no implementado 🔴 P0 ✅ RESUELTO (31 ago)
`signal.py:272-289`

`CLAUDE.md` y `STATUS.md` daban por cerrada la regla "las operaciones de competición usan
expiración ≤ 3 sep". **No existía en el código.** `pick_expiration` elegía la primera expiración
con `1 <= dte <= 3` y, si no encontraba ninguna, caía a `exps[0]`. Simulado por sesión:

```
  sesion 2026-09-01 -> 2026-09-02 (dte 1)   OK
  sesion 2026-09-02 -> 2026-09-03 (dte 1)   OK
  sesion 2026-09-03 -> 2026-09-04 (dte 1)   >>> FUERA DE LA VENTANA <<<
```

El jueves 3 es la última sesión puntuable y el snapshot es a su cierre: cada trade abierto ese día
habría expirado el viernes, excluido de la medición, y además restando en el snapshot como prima
vendida sin decaer. La sesión 3 de 3 se habría desperdiciado entera.

Arreglado con un tope duro (`LAST_EXPIRATION`, override por `DESK_LAST_EXPIRATION`): se descartan
las expiraciones posteriores al corte, el jueves se acepta el mismo día (0DTE, ya gobernado por
`no_new_0dte_after_et`), y si no queda ninguna válida se devuelve `None` → `stand_down:
"expiration"` en vez de una expiración fuera de ventana. 6 tests nuevos en `test_signal.py`.

### 25. `pf.net_delta` no se acumulaba entre subyacentes del mismo run ✅ RESUELTO (31 ago)
`desk.py:260-262`

`_consider` incrementaba `pf.n_positions` y `pf.open_risk` tras abrir, pero **no** `pf.net_delta`.
Cada subyacente posterior al primero se evaluaba contra la delta del libro *previa al run*. Con
`risk_per_trade` 0.005 el error era ruido (~0,01 de una banda de 0,30); al pasar a 0.02 un solo
condor mueve 0,10–0,20 y tres aperturas en el mismo run podían pasar a 0,28 cada una y dejar el
libro en 0,84. Una línea: `pf.net_delta += proposed.net_delta`.

### 18. ~~Fechas del calendario macro sin verificar~~ ✅ VERIFICADO (2 sep)
`calendar.py:16-22` · issue #17

**El lun 31 ago es sesión hábil** (Labor Day 2026 es el 7 sep). Las 5 fechas de `EVENTS`
verificadas el 2 sep contra el patrón real de publicación de cada informe (día de la semana
calculado, no supuesto):

| Fecha | Día | Evento | Regla real |
|---|---|---|---|
| 2026-09-01 | martes | ISM Manufacturing PMI | 1er día hábil del mes, 10:00 ET |
| 2026-09-02 | miércoles | ADP employment | miércoles anterior al NFP, 08:15 ET |
| 2026-09-03 | jueves | Initial jobless claims | siempre jueves, 08:30 ET |
| 2026-09-03 | jueves | ISM Services PMI | 3er día hábil del mes, 10:00 ET |
| 2026-09-04 | viernes | NFP / Employment Situation | 1er viernes del mes, 08:30 ET |

Las 5 encajan exactamente con su regla de calendario real. Sin discrepancias.

---

## Deliverables con problemas

### 19. ~~`write-up.md` afirma cosas que no existen~~ ✅ RESUELTO (29 ago)
`docs/write-up.md` · issue #18 · **reescrito desde el código, con placeholders `[[EN CONSTRUCCIÓN]]` para lo que aún no existe**

Redactado en presente, promete *"scheduled Alpaca CLI loop"* (es REST), *"MCP server"* (no existe) y el ensemble Featherless (no existe). Los jueces son **de Alpaca** y van a buscar exactamente esas integraciones. No es exageración de marketing: hunde el eje de Technology Implementation.

**Regla:** el write-up se escribe **desde el código**, no desde el plan.

### 20. ~~Datos del hackathon incorrectos en los docs~~ ✅ RESUELTO (29 ago)
issue #19 · ver [`REGLAS-HACKATHON.md`](REGLAS-HACKATHON.md) · **premio, criterios y ventana de P&L confirmados (Discord 29 ago)**

Premio ($6.300 → $5.000), criterios de jurado (son 4, no 5), y ventana de P&L — todo confirmado (Discord 29 ago): snapshot jueves 3 EOD, expiraciones ≤ 3 sep.

---

## Lo que está bien

No todo son fallos, y estos puntos son defendibles ante el jurado:

- **La arquitectura coincide con lo que la propia Alpaca publica como buena práctica**: agentes especializados, risk guard determinista sin LLM, monitorización cada 15 min. Merece una frase explícita en el write-up.
- **La separación LLM/determinista es correcta.** Todo lo que puede quemar dinero — salidas, gates, sizing — es Python puro. Casi nadie lo hace así.
- **Los probes del Día 0 ahorraron días**: griegas e IV vienen de Alpaca (sin Black-Scholes), OPRA bloqueado pero `indicative` a ~2s, OI solo en `/v2/options/contracts` con T-2. Verificado contra mercado real.
- **La disclosure pre-evento y la separación testing/competición están impecables.**
- **La señal es genuinamente original** frente a los ~2.000 "multiagente + RSI sobre SPY" que va a recibir el jurado.

---

## Reparto

El trabajo está repartido en [los issues](https://github.com/alvaarocl/iv-desk/issues) por lanes que **desacoplan ficheros**, para minimizar conflictos:

- **`lane/ejecucion`** (Álvaro) — `broker.py`, `execution.py`, workflow. Issues #1-#4, #8, #9, #15, #16, #17, #20, #21, #22, #23.
- **`lane/senal`** (Ángel) — `signal.py`, `config.py`, backtest. Issues #5-#7, #10-#12, #14, #25.
- **`lane/entrega`** — capa LLM (#13), write-up (#18), reglas (#19), MCP (#20), submission (#21), runbook (#24).

**#12 y #16 son decisiones humanas**, no tareas: hablarlas los dos antes de tocar código.
