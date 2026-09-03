# Dossier de defensa — IV Desk

Documento para **leer antes de presentar** y para responder cualquier pregunta del jurado o de un
mentor sin quedarse en blanco. Dos registros:

- **[Parte A — para cualquier persona](#parte-a--para-cualquier-persona)**: sin saber nada de
  opciones ni de trading. Es lo que dices en voz alta.
- **[Parte B — técnica](#parte-b--técnica)**: la maquinaria real, fichero a fichero, para las
  preguntas de ingeniería.

Complementa —no sustituye— a [`CONCEPT.md`](CONCEPT.md) (posicionamiento), [`write-up.md`](write-up.md)
(el one-pager de la submission) y [`strategy-spec.md`](strategy-spec.md) (la estrategia exacta).
Glosario completo en [`GLOSSARY.md`](GLOSSARY.md).

Estado a 3 sep, cierre de la ventana puntuable: motor + capa LLM construidos, cableados y en
`main`; 181 tests; calibrado con 60 sesiones reales; **1 trade real abierto y cerrado en la
semana** (QQQ iron condor, ganador, +$318,85), 295 stand-downs documentados en 4 sesiones.

---

## En una frase

**IV Desk es una aseguradora automática para la bolsa: vende "seguros" sobre índices (SPY, QQQ, IWM)
solo cuando están estadísticamente caros y el mercado va a estar tranquilo, con reglas de riesgo
mecánicas y una mesa de agentes de IA que debate y deja por escrito una predicción comprobable de
cada operación.** Todo en cuenta de prácticas (*paper*), sin dinero real.

---

# Parte A — para cualquier persona

## 1. La analogía: la aseguradora de coches

Una aseguradora cobra primas a mucha gente. La mayoría no choca → se queda el dinero. Algunos sí →
paga. Si **pone bien los precios** y **no asegura a temerarios**, a largo plazo gana.

Nuestro bot hace exactamente eso, pero el "accidente" es que la bolsa se mueva mucho:

1. Vende un "seguro" a alguien que quiere protegerse de que SPY suba o baje demasiado en los
   próximos 1–3 días.
2. Cobra una prima (~$50–150 por operación).
3. Si SPY se queda tranquilo → el seguro caduca sin valer nada → nos quedamos la prima.
4. Si SPY se mueve mucho → pagamos. **Pero la pérdida está topada de antemano** (por eso se llama
   "riesgo definido"): sabemos el peor caso antes de entrar.

El negocio de las aseguradoras funciona porque **la gente paga de más por tranquilidad**. En bolsa
pasa lo mismo: el "seguro" (una opción) casi siempre se vende más caro de lo que la estadística
dice que vale. Ese exceso tiene nombre: **prima de riesgo de volatilidad (VRP)**. Es de las
anomalías mejor documentadas de las finanzas — no es una teoría nuestra.

## 2. Qué hace el bot, cada 15 minutos

Un robot (un *cron* de GitHub Actions) despierta cada 15 minutos mientras la bolsa de EEUU está
abierta y ejecuta siempre la misma secuencia:

1. **¿Tengo posiciones abiertas?** Si sí, comprueba si toca cerrarlas (ver punto 5).
2. **¿Puedo operar hoy?** Comprueba las reglas de seguridad de cartera (¿he perdido mucho hoy? ¿hay
   un dato macro importante en las próximas 2 horas?). Si alguna salta → hoy solo gestiona, no abre
   nada.
3. **Para cada índice (SPY, QQQ, IWM), calcula dos cosas:**
   - **¿Está caro el seguro?** Compara lo que el mercado *espera* que se mueva SPY (volatilidad
     implícita) con lo que *probablemente* se moverá según su historia reciente (volatilidad
     realizada prevista). Si lo implícito es bastante más alto → el seguro está caro → interesa
     venderlo.
   - **¿Va a estar tranquilo el mercado?** Mira cómo están posicionados los grandes bancos que hacen
     de intermediarios (los *dealers*). Cuando tienen cierta posición ("gamma positivo"), su forma
     de cubrirse *amortigua* los movimientos — el mercado tiende a quedarse en un rango. Cuando es
     la contraria, tiende a irse con fuerza. Si la señal dice "va a estar tranquilo" → adelante.
4. **Si las dos condiciones se cumplen** → construye un **iron condor** (ver abajo), decide cuántos
   contratos según cuánto está dispuesto a arriesgar, y **antes de mandarlo la mesa de IA lo debate**
   (punto 6). Si aprueba, manda la orden.
5. **Gestión mecánica de lo abierto**, sin ninguna IA:
   - Si la operación ya lleva el **50% del beneficio máximo** → cerrar y cobrar.
   - Si la pérdida llega al **doble de la prima cobrada** → cortar.
   - El **día que vence** → cerrar todo antes del cierre, para no arriesgarse a que te "asignen"
     acciones.
6. **Lo escribe todo** en un registro público append-only (`data/journal.jsonl`): cada señal, cada
   "hoy no opero y este es el motivo", cada debate completo, cada apertura y cada cierre con su
   resultado.

## 3. Qué es una "opción" y un "iron condor", en cristiano

**Opción** = un contrato que te da el *derecho* (no la obligación) a comprar o vender algo a un
precio fijo antes de una fecha. Se compra y se vende como cualquier cosa. El que la vende cobra una
prima por asumir la obligación del otro lado.

**Iron condor** = vender a la vez dos "seguros": uno contra que SPY suba mucho y otro contra que
baje mucho, y **comprar dos seguros más baratos aún más lejos** que limitan la pérdida. El resultado
es una apuesta a que **SPY se queda dentro de un rango**. Dibujado, el beneficio/pérdida tiene forma
de meseta: ganas una cantidad fija si SPY acaba dentro del rango, pierdes una cantidad fija (topada)
si se sale mucho.

- **Se manda como una sola orden de 4 patas** (`order_class: mleg` de Alpaca), no como 4 órdenes
  sueltas. Eso evita quedarte con media posición si una pata no se ejecuta.
- **1–3 días hasta el vencimiento.** Corto plazo: la prima se "derrite" rápido a nuestro favor y no
  tenemos que adivinar nada a largo plazo.

## 4. Las reglas de seguridad (el "Risk Officer")

Es código puro, **sin IA, sin excepciones**. Antes de cada operación comprueba, y si algo falla la
operación no se hace:

| Regla | Qué impide |
|---|---|
| Máx **0.5%** del capital en riesgo por operación | que una sola operación haga daño serio |
| Máx **10%** del capital en riesgo entre todas las abiertas | acumular demasiado a la vez |
| Máx **8** posiciones simultáneas | sobreexposición |
| La cartera no puede quedar demasiado "direccional" (±30% del capital en delta) | apostar sin querer a que la bolsa sube o baja |
| **Cortacircuitos diario**: si hoy pierde el 3% del capital → deja de abrir | un día malo en espiral |
| **Freno por drawdown**: si la cuenta cae 8% desde su máximo → media posición; 12% → parada total | hundirse poco a poco |
| **Apagón macro**: no abre nada 2h antes de un dato importante (empleo, ISM…) y 45 min después | operar a ciegas justo cuando el mercado va a dar un salto |
| Nada de opciones que vencen hoy después de las 14:00 (hora de NY) | el tramo del día donde más se descontrola |

Dos guardas más, fuera de esa lista, que funcionan aunque todo lo demás falle:
- **Guardarraíl de cuenta**: se niega a operar en real si las credenciales no apuntan a la cuenta de
  competición, y se niega a tocar esa cuenta antes de que abra la ventana el lunes.
- **Detección de asignación temprana**: si aparecen acciones en la cuenta (alguien ejerció una
  opción contra nosotros), el bot se planta solo y solo gestiona salidas hasta que un humano mire.

## 5. La mesa de IA

Encima del motor determinista hay **cuatro "asientos"**, cada uno un modelo de lenguaje abierto
servido por **Featherless** (un único proveedor, sin gasto de bolsillo, cupón del hackathon):

- **Quant** — en realidad son **3 modelos votando por separado** sobre la misma papeleta. Hace falta
  **mayoría estricta** y que estén de acuerdo con la estructura que eligió el motor. Si no hay
  consenso → no se abre.
- **Alcista / Bajista** — discuten el sesgo direccional del índice. **Obligados a citar números
  concretos** de la señal; si no citan al menos dos campos reales, su argumento se descarta. El
  Bajista rebate explícitamente al Alcista (son adversarios de verdad, no dos textos parecidos).
- **Jefe de Mesa** — decide el tamaño final (**nunca mayor** que el que ya aprobó el Risk Officer) y
  escribe una **predicción falsable**: un rango de cierre para la fecha de vencimiento. Si el rango
  es absurdo o está invertido, la operación no se hace.

**La propiedad clave, y es una línea de código:** `contracts = max(0, min(head.contracts, cap))`.
La IA **solo puede recortar o vetar, nunca ampliar** el riesgo. Cualquier fallo (un modelo caído,
un *timeout*, un JSON roto, un empate) se resuelve como "no operar", nunca como "sí". Si Featherless
se cae, un interruptor (`DESK_DEBATE=off`) hace que el desk siga operando solo con la decisión
determinista.

## 6. Qué entregamos el viernes

- **El repositorio público** con todo el código y los 181 tests.
- **El registro `data/journal.jsonl`**: la prueba falsable de todo lo que hizo la mesa — incluidas
  las veces que **decidió no operar**, con el motivo y los números.
- **El one-pager** (`write-up.md`) y un **vídeo** de ~3 minutos con narración.
- **Un dashboard en vivo** (opcional según las reglas): https://alvaarocl.github.io/iv-desk/
- La cuenta de competición `PA39HSCQE8S3` con su histórico 100% generado por el agente.

## 7. Preguntas difíciles y cómo responderlas

**"¿Y si pierde dinero esta semana?"**
Son 4 sesiones. El VRP paga poco el 85% de las veces y pierde bastante el 15% — en 4 muestras, la
suerte domina al edge. Por eso **no apostamos el proyecto al eje de P&L**. El jurado tiene 4
criterios y el P&L es uno (~25%). Lo que demostramos es un agente **autónomo, robusto y disciplinado**,
y eso se ve igual de bien tanto si gana como si se planta.

**"Esto lo hace todo el mundo: multiagente + un indicador sobre SPY."**
Exacto, y por eso no vamos por ahí. Los ~2.000 inscritos van a mirar el **gráfico de precios**.
Nosotros miramos la **superficie de opciones** — comparamos volatilidad implícita con realizada y
leemos el posicionamiento de gamma de los dealers. Casi nadie de esos 2.000 sabe qué es el gamma de
los dealers. El debate alcista/bajista no es original por sí solo; **el anclaje en la señal de
volatilidad sí**.

**"¿La IA decide las operaciones?"**
No. La IA **nunca toca el dinero**. Todo lo que puede quemar capital — señal, selección de strikes,
tamaño, salidas, reglas de riesgo — es Python determinista y está testeado. La IA solo debate una
operación **que el motor ya aprobó**, y solo puede recortarla o vetarla. Es la arquitectura que la
**propia Alpaca publica como buena práctica**.

**"¿Por qué tan pocas operaciones?"**
Es deliberado. El backtest con 60 sesiones reales muestra que la señal solo dispara en ~6% de las
sesiones — el mercado de 2026 tiene la volatilidad baja y el "seguro" no está caro casi nunca.
Forzar más operaciones (bajar el umbral) **empeora** el resultado en el backtest. Un agente que sabe
cuándo **no** operar, y lo deja por escrito, es una demostración de autonomía mejor que uno que
acertó tres condors por suerte.

**"¿Es esto rentable de verdad a largo plazo?"**
La estrategia (vender VRP de índice con gating de gamma) tiene retorno esperado positivo bien
documentado a horizontes largos. En 4 días no se puede *medir* — pero eso es una limitación del
formato del concurso, no de la idea. El backtest de 60 sesiones da 8 aciertos de 11 operaciones; con
la gestión de salidas real eso es aproximadamente plano-positivo (~+$334 sobre $100k), porque la
gestión **corta la cola mala a cambio de parte del beneficio**.

---

# Parte B — técnica

## 1. Arquitectura: capas, y la IA fuera del *money path*

```
cron (GitHub Actions, cada 15 min RTH)
        │
        ▼
agent/desk.py :: run_once()
  0. guardarraíl de cuenta (_guard_account)            ── determinista
  1. reconcile contra Alpaca (execution.reconcile)     ── determinista
  2. exits del libro abierto (execution.manage_exits)  ── determinista
  3. gates de cartera (risk.size_multiplier, breaker)  ── determinista
  4. señal por subyacente (signal.build_signal)        ── determinista
  5. selección + sizing (execution.select_condor/size) ── determinista
     risk.evaluate(proposed) -> (ok, reason)           ── determinista, entrada única
  6. debate LLM (debate.review_open)  ← SOLO recorta o veta ── LLM, acotado
  7. execution.open_trade(...)                         ── determinista
  8. journal.append(...) + record_equity(...)          ── determinista
```

| Capa | Fichero | Determinista | Nota |
|---|---|---|---|
| Señal | `agent/signal.py` | Sí | lee la superficie de opciones, no el gráfico de precio |
| Estructura + sizing | `agent/execution.py` (`select_condor`, `size`) | Sí | strikes a delta objetivo tras gates de liquidez |
| Risk Officer | `agent/risk.py` (`evaluate`) | Sí | **ningún path de LLM entra aquí** |
| Gestión de trade | `agent/execution.py` (`manage_exits`) | Sí | 50% TP / 2× stop / cierre en expiración |
| La mesa | `agent/debate.py`, `agent/seats.py` | No, y acotada | debate solo en una apertura |
| Journal | `agent/journal.py` | Sí | JSONL append-only + `equity.csv` |
| Transporte | `agent/broker.py` (`_cli`) | Sí | shell-out al CLI de Alpaca |
| Datos de mercado | `agent/marketdata.py` | Sí | REST (lecturas permitidas) |
| Config | `agent/config.py` (`Params`) | Sí | un dataclass, cada número con su razón al lado |

`main` corre siempre limpio en `dry_run`; el cron opera desde ahí.

## 2. Señal (`agent/signal.py`)

Devuelve un `Signal` con **tres gates**, cada uno capaz de decir "stand down" por su cuenta, y cada
uno escribe su motivo en `stand_down` (`vrp` / `gex` / `trend` / `data`) para que el journal muestre
al desk *decidiendo* no operar.

### VRP — ¿está caro el seguro?

- **IV** (`atm_iv`): mediana de la volatilidad implícita de los ~6 strikes más cercanos a spot
  (call+put), robusta a una quote mala. Viene de los snapshots de Alpaca — **no hay motor de
  Black-Scholes propio** (decisión de los probes del Día 0).
- **RV_hat** (`rv_forecast`): mezcla 50/50 de Yang-Zhang (eficiente en rango, corregido para que
  todos los componentes usen las mismas n periods y el término medio sea open-to-close, no
  close-to-close) y EWMA (λ=0.94), anualizada sobre 20 sesiones.
- **El gate es un ratio, no una diferencia absoluta** (issue #6): `sell_premium` requiere
  `IV / RV_hat ≥ vrp_ratio_min`. Un umbral absoluto (`IV − RV ≥ 0.03`) estaba calibrado mentalmente
  para un mundo de VIX 20 y con IV al 8% exige que la implícita esté ~40% por encima de la
  realizada. El ratio absorbe el sesgo de horizonte (20 sesiones anualizadas vs 1–3 DTE), que es
  aproximadamente multiplicativo y estable, sin un modelo de estructura temporal que no podemos
  validar en 4 sesiones.
- **Valor calibrado: `vrp_ratio_min = 1.05`** (backtest, ver §7).

### GEX — ¿va a estar tranquilo el mercado?

- `compute_gex`: agrega gamma de dealers dentro de ±`gex_band` de spot. Calls +, puts −.
  `contrib = gamma · OI · 100 · spot² · 0.01`.
- **Se normaliza** dividiendo por el gamma notional *bruto* de los mismos strikes → `gex_norm ∈
  [−1, 1]` (issue #10). El dólar bruto escala con `spot²`, con el nivel de open interest y con el
  régimen de vol, así que un umbral fijo en dólares significa tres cosas distintas para SPY vs IWM,
  para septiembre vs marzo, y para un día tranquilo vs uno movido. La normalización cancela las
  tres a la vez y deja un **ratio de desequilibrio** puro.
- `gex_state`: `+1` si `gex_norm ≥ gex_min`, `−1` si `≤ −gex_min`, `0` en la **zona muerta**. La
  zona muerta es el punto: el open interest es **T-2** (Alpaca solo lo publica con 2 días de
  retraso), así que `+0.01` y `−0.01` son la misma lectura con ruido distinto; un test de signo
  puro hacía al desk cambiar de opinión cada 15 minutos.
- **Valor calibrado: `gex_min = 0.03`** — filtro de flip-flop cerca de cero sin el umbral caro que
  costaba trades sin ganar P&L.
- El gate rechaza si `state ≤ 0` (dealers cortos de gamma, o dentro de la zona muerta).

### Régimen — ¿hay tendencia?

- `classify_regime`: EMA20/EMA50 + ADX de Wilder de 14 (DX suavizado con RMA de n periods —
  la versión anterior colapsaba +DI/−DI a escalares y devolvía un DX puntual, mucho más ruidoso y
  alto, así que el umbral `> 22` no significaba lo que decía la spec).
- **`fade_trend = False`** (issue #12): en un tape con tendencia, `stand_down = "trend"` — **no se
  vende prima corta en absoluto**. Vender primas contra la dirección del movimiento es la forma
  clásica de reventar un libro de vol corta, y estaba gateado solo por un signo de GEX ruidoso.
  `fade_trend = True` restaura el comportamiento antiguo con un flag.

### Consecuencia de la geometría del código

`build_signal` solo alcanza las ramas `put_credit_spread` / `call_credit_spread` cuando hay
tendencia **y** `fade_trend = True`. Con la config de producción (`fade_trend = False`) **la única
estructura que el desk puede producir es el iron condor**; `select_vertical` y las dos ramas de
`_pick` para verticales están, pero no se ejercen en producción. Es una decisión, no un bug — pero
si alguien pregunta "¿y los credit spreads direccionales?", la respuesta honesta es: existen en el
código, no se disparan con la config actual.

## 3. Ejecución (`agent/execution.py`)

### Unidades (era un bug en vivo, issue #2)

Dos monedas conviven y mezclarlas rompía el exit manager:
- **por acción** (`_ps`): lo que Alpaca cotiza y lo que espera `limit_price`.
- **dólares por 1 lote** = por acción × 100: todo lo que se guarda en `Trade` y toda comparación de
  umbral.

### Selección de strikes

`select_condor(chain, short_delta, width, oi, params)`: busca strikes cortos al delta objetivo
(`short_delta = 0.18`), alas a `width` de distancia (SPY/QQQ `width_spy = 2.0`, IWM `width_iwm =
1.0` — ambos cotizan strikes de $1 cerca del dinero), tras **gates de liquidez**: `MIN_OI = 500` y
spread `≤ MAX_SPREAD_FRAC = 0.10` del mid, **en las dos patas**. `_mid()` ya no cae a 0.0 en
silencio cuando falta quote (issue #22).

Sobre la geometría del crédito: en un condor `credit/width ≈ 2 × |Δ| medio entre el strike corto y
el largo`, porque se cobran las dos alas y solo una puede perder. Por eso `min_credit_frac × width`
con `0.33 × 4.0` era **geométricamente inalcanzable** (issue #7): la solución fue estrechar el ala
(4→2, 2→1), no esperar a que subiera la IV. Suelo actual: `min_credit_frac = 0.20` (el máximo real
observado en el tape fue ~0.28).

### Sizing

`size(width, credit, nav, risk_per_trade, mult)`: número de contratos tal que
`max_loss = (width − credit) · 100 · n ≤ risk_per_trade · nav · mult`. Con NAV $100k y `mult = 1.0`:
presupuesto $500 → condor SPY width 2.0 al suelo de crédito → ~$160/lote → **3 contratos**; IWM
width 1.0 → ~$80/lote → **6 contratos**.

### Exit manager (`manage_exits`)

Todo en $/lote. Prioridad: `take_profit` → `stop` → `expiry_close`.
- `take = entry_credit · (1 − take_profit_frac)` con `take_profit_frac = 0.50` → recompra al 50% del
  crédito.
- `stop = entry_credit · stop_multiple` con `stop_multiple = 2.0` → cuando el coste de cierre llega
  a 2× el crédito recibido, se cierra: pérdida ≈ **−1.0 × crédito** por lote.
- `expiry_close`: si `expiration == hoy` y la hora es `≥ 15:30` ET, se cierra. **Dispara en
  cualquier run desde las 15:30**, no en un único run de las 15:45 — el cron de GitHub es
  best-effort y un run saltado ya no manda una posición a expiración sin gestionar (issue #23).
- Guarda: si una pata pierde la quote a dos caras, `_combo_cost_to_close` devuelve `None` y la
  salida **se salta ese loop** (incluido un cierre por expiración). Mitigación operativa: vigilar el
  journal en la ventana 21:30–22:00 CEST del primer día con posición.

### Ciclo de vida de la orden e idempotencia (issue #3)

- Las órdenes de Alpaca son **asíncronas**: un 200 confirma recepción, no ejecución. Un trade es
  `open` solo cuando su orden de entrada reporta `filled`; hasta entonces es `pending_open` y
  retiene su presupuesto de riesgo pero no cuenta como posición.
- `_client_order_id(underlying, expiration, structure, now)` es **determinista por intención de
  trade** → un re-run o un dispatch manual no puede duplicar una orden.
- `reconcile(mode)` en cada arranque: **Alpaca es la fuente de verdad**. Resuelve entradas
  pendientes contra el estado real de la orden, revisa cierres pendientes, cancela entradas resting
  demasiado viejas (`PENDING_ENTRY_MAX_MIN = 20`), y detecta posiciones de acciones inesperadas
  (asignación temprana). `data/trades.jsonl` es un journal, no la fuente de verdad.
- `limit_price` de `mleg` va **firmado**: `limit_ps = -abs(credit_ps · 0.92)` (negativo = crédito,
  ~8% dentro del mid). `broker.submit_mleg` rechaza un precio de cero con `ValueError` en vez de
  adivinar.

## 4. Risk Officer (`agent/risk.py`)

Entrada única `evaluate(trade, pf, params, now_et) -> (ok, reason)`, fail-fast en orden. Todos los
umbrales salen de `config.Params`:

| # | Gate | Constante | Valor |
|---|---|---|---|
| 1 | `max_loss ≤ risk_per_trade · nav` | `risk_per_trade` | `0.005` |
| 2 | `open_risk + max_loss ≤ max_portfolio_risk · nav` | `max_portfolio_risk` | `0.10` |
| 3 | `n_positions < max_positions` | `max_positions` | `8` |
| 4 | `|net_delta + trade.net_delta| ≤ max_net_delta` | `max_net_delta` | `0.30` (fracción de NAV) |
| 5 | `day_pnl > -daily_loss_breaker · nav` | `daily_loss_breaker` | `0.03` |
| 6 | `dd < dd_halt`, `dd = 1 − nav/peak_nav` | `dd_halt` | `0.12` |
| 7 | `not in_event_blackout(now_et)` | blackout | `2h` antes / `45min` después (asimétrico) |
| 8 | `not (is_0dte and now ≥ no_new_0dte_after_et)` | `no_new_0dte_after_et` | `"14:00"` ET |

`size_multiplier(pf, params)`: `dd ≥ 0.12` → `0.0`; `dd ≥ dd_throttle (0.08)` → `0.5`; si no `1.0`.
Duplicado a nivel cartera en `desk.py`: `breaker`, `mult == 0.0`, `exits_only` o `assigned`
cortocircuitan el loop a exits-only.

**El blackout asimétrico** (2h antes / 45min después) es un ejemplo de cómo razona el desk sobre sus
propios gates: el riesgo es abrir prima en un dato **sin resolver**, y vive entero antes del
release; después la IV se aplasta, que es la mejor entrada del día para un vendedor de prima. El
argumento está escrito al lado de la constante en `agent/calendar.py`.

Calendario macro de la ventana (`agent/calendar.py`, verificado a mano, issue #17): ISM Mfg mar 1
10:00 ET, ADP mié 2 08:15 ET, jobless claims jue 3 08:30 ET, ISM Services jue 3 10:00 ET, NFP vie 4
08:30 ET. Con la pre-ventana de 2h, **el martes 1 y el jueves 3 no se abre nada hasta ~12:00 ET** —
correcto y deseado, va al journal como `rejected: macro event blackout`.

## 5. La mesa LLM (`agent/debate.py`, `agent/seats.py`)

**Un proveedor, una clase de transporte, ningún modelo propietario en el loop**
(`FeatherlessSeatClient`, endpoint compatible con OpenAI). Modelos en las variables de GitHub:
`Qwen/Qwen2.5-32B-Instruct`, `NousResearch/Hermes-3-Llama-3.1-70B`, `mistralai/Mistral-Nemo-Instruct-2407`;
arguer `Hermes-3-Llama-3.1-70B`.

`debate.review_open(signal, selection, cap_contracts, base_thesis) -> DebateOutcome` es el **único
punto de entrada** que `desk.py` necesita y es seguro llamarlo siempre: degrada a stand-down ante
cualquier fallo y a pass-through con `DESK_DEBATE=off`. **Nunca lanza.**

Secuencia con presupuesto de reloj de 90 s repartido en deadlines por asiento:

1. **Quant ensemble** — hasta 3 modelos votan en paralelo la misma papeleta. `seats.consensus`
   exige **mayoría estricta de los modelos despachados** (no de los que contestaron) **y** acuerdo
   con la estructura que eligió el motor. `verdict != "confirm"` → stand-down.
2. **Bull / Bear** en paralelo — `seats.argue` descarta un argumento con menos de **dos nombres de
   campo `Signal` reales**. `_run_arguers` corre Bull y luego Bear rebatiendo a Bull;
   `adversarial_ratio` mide el solape textual y lo registra (`DEGENERATE_SIMILARITY = 0.80`).
3. **Desk Head** — `seats.desk_head` devuelve tamaño final (≤ cap) + `prediction`: un rango de
   cierre en la fecha de expiración. `_validate_prediction` rechaza rangos invertidos, no numéricos
   o inverosímiles → la operación no ocurre.

**El clamp, y es literalmente una línea** (`debate.py:273`):

```python
contracts = max(0, min(int(head.contracts), cap))
```

`cap` es la `n` que ya aprobó `risk.evaluate()`. **El debate es una función monótona no creciente
del riesgo**: recorta o veta, nunca amplía. `test_debate.py` incluye un test de que una inyección de
prompt no puede subir el cap, y de que el `chain` de opciones nunca llega a un prompt.

Todo fallo — outage, timeout, JSON truncado, ensemble partido — resuelve a `approved=False` con el
motivo registrado. No hay path donde basura signifique "sí" (`seats.py`, regla de diseño 2).

Kill switch de la mesa, independiente de `DESK_MODE`: `DESK_DEBATE=off` → el desk sigue operando con
la decisión determinista; **no** desactiva salidas ni gates de riesgo. Es el modo degradado seguro.

## 6. Infraestructura

- **Transporte**: `agent/broker.py::_cli()` hace `subprocess.run(["alpaca","api",METHOD,path,...])`
  para **toda** la Trading API (cuenta, clock, posiciones, órdenes, `mleg`, cancelaciones,
  `/v2/options/contracts`). `marketdata.py` sigue en REST `httpx` — la excepción permitida (solo
  lecturas de datos de mercado). El requisito de las reglas es "Trading API + MCP o CLI"; usamos el
  CLI. Binario pineado a `v0.0.14` y **verificado** con un assert duro en CI.
- **Cron** (`.github/workflows/desk.yml`): `*/15 13-20 * * 1-5` UTC (cubre 09:30–16:00 ET con
  margen). `concurrency: {group: desk-loop, cancel-in-progress: false}`, `timeout-minutes: 10`.
  `DESK_MODE` sale de: input del `workflow_dispatch` → variable de repo → `dry_run` por defecto.
- **Persistencia**: el workflow commitea `data/` con `if: always()` (el journal persiste incluso en
  un loop fallido), `pull --rebase` + reintento ×3, `exit 1` si no lo consigue. `data/trades.jsonl`
  **es** el libro de posiciones — un push perdido haría que el agente olvide posiciones abiertas.
- **Journal** (`agent/journal.py`): `data/journal.jsonl` append-only + `data/equity.csv`. Eventos:
  `account`, `portfolio`, `signal` (uno por subyacente, con el `stand_down` completo), `rejected`,
  `debate` (transcript completo), `opened`, `exit`, `reconcile`, `exits_only`, `error`, `fatal`.
- **Tests**: 181, sin red y sin claves. La mesa se prueba con dobles inyectados. `ruff` limpio.
  Cobertura fuerte en `test_debate.py` (contrato de seguridad de la capa LLM),
  `test_exit_manager_replay.py` (harness de replay), `test_blackscholes.py` (backfill de IV/griegas
  para 0DTE) y 4 regresiones sobre `_close_legs` (issue #26, ver más abajo). **Hueco conocido**:
  `desk.run_once()` no tiene test end-to-end; el orden de etapas y el aislamiento de excepciones
  van sin cobertura.
- **Cuentas**: testing `PA3TQHQKM5AD` (todo el dev), competición `PA39HSCQE8S3` ($100k, nivel 3,
  intacta; primera orden lun 31 ago 09:30 ET; sus keys solo en secrets de GitHub).

## 7. Calibración — el backtest

`uv run python -m backtest.replay --days 60 --symbols SPY,QQQ,IWM` sobre **barras históricas reales
de Alpaca**, 60 sesiones, `config.py` calibrado. Responde la pregunta binaria del issue #5 (*¿la
estrategia dispara?*).

**Embudo (config calibrada):**

```
1  underlying-sessions evaluadas                174
4  VRP rico   IV/RV_hat >= 1.05    [gate vrp]    48   <<< MUERE AQUÍ (121 de 174)
5  dealer gamma  gex_norm >= 0.03  [gate gex]    16
6  tape sin tendencia               [gate trend] 13
9  credit gate  credit/width >= 0.20             11
13 TRADES ABIERTOS                               11   (6.3%)

    IV/RV_hat     mediana 0.90  p90 1.27  max 1.83   (umbral 1.05)
    credit/width  mediana 0.27  p90 0.34  max 0.36   (umbral 0.20)
```

**El VRP es el gate letal, y es delgado de verdad**: la mediana de IV/RV_hat es **0.90** — la
implícita corta está, la mitad de los días, por debajo de la realizada. **No es un artefacto de
medición** (los bugs de #26 y del gap overnight en `yang_zhang` ya están arreglados): es el mercado
de 2026, vol baja.

**Los 11 trades: 8 ganadores, 2 perdedores grandes, 1 scratch.** P&L held-to-expiry **+$484**.
Con las reglas de salida reales (TP 50% / stop 2×): **≈ +$334** — la gestión mecánica cuesta ~31%
del P&L bruto a cambio de topar el peor caso por trade en ≈ −1× crédito. Breakeven en 66,7% de
acierto; el backtest dio 72,7% (8/11, n=11 — intervalo enorme). **La gestión no añade edge, corta la
cola.** Detalle en [`../backtest/RESULTS.md`](../backtest/RESULTS.md).

**Rejilla de sensibilidad** (17 variantes, cuidado con sobreajustar — solo se movieron 2 parámetros
hacia inflexiones reales, no hacia el P&L máximo):

| Cambio | Trades | P&L $ | Lectura |
|---|---|---|---|
| `vrp_ratio_min` 1.05 → 1.30 | 5 | −586 | demasiado restrictivo mata los buenos |
| `vrp_ratio_min` 1.05 → 1.00 | 13 | +117 | los trades entre 1.00 y 1.05 son perdedores netos → 1.05 es inflexión real |
| `gex_min` 0.03 → 0.30 | 0 | 0 | el umbral fuerte mata todo |
| `short_delta` 0.18 → 0.25 | 11 | −368 | cortos más cerca del dinero = peor |
| **TODOS LOS GATES OFF** | 78 | +401 | el edge bruto es positivo pero **delgado** |

**No existe una palanca honesta que compre más trades sin empeorar la expectativa.** Es un proyecto
de **rama B**: "una mesa que sabe cuándo NO operar". El 94% de las sesiones del backtest son
stand-down documentado — **y la ventana real lo confirmó**: 295 stand-downs documentados en 4
sesiones (lun 31 – jue 3), **1 solo trade** (QQQ iron condor, aprobado por la mesa real, no en
sombra), cerrado dentro de las strikes. Equity final **$100.318,85 (+$318,85)**. Detalle en
[`../docs/write-up.md`](write-up.md) y `data/journal.jsonl`.

## 8. Límites conocidos (asumidos con los ojos abiertos)

- **4 sesiones son una lotería de varianza** en el P&L. Un solo día de tendencia fuerte borra una
  semana de condors. Por eso no apostamos el proyecto a ese eje.
- **El GEX que calculamos** — open interest T-2, sin inferir el posicionamiento real de dealers —
  es un proxy tosco. Como narrativa diferenciadora es excelente; como edge medible en 4 días, es
  marginal.
- **`desk.run_once()` sigue sin test end-to-end.** El orden de etapas y el aislamiento de
  excepciones corrieron 4 sesiones reales sin caerse, pero no hay un test que lo fije.
- **El exit manager sí cerró una posición real — y el primer intento falló.** El trade del jueves
  (QQQ iron condor) disparó 13 intentos de cierre rechazados, 13:28–15:13 ET, todos por el mismo
  error: `_close_legs` invertía `side` pero no el prefijo de `position_intent`, así que una pata
  corta (`side=sell`, `position_intent=sell_to_open`) intentaba cerrar como `side=buy` pero
  `position_intent=sell_to_close` — Alpaca lo rechaza siempre. La posición se cerró igualmente,
  sola: expiró dentro de las strikes y OCC la liquidó a las 16:00, el código nunca llegó a
  gestionarla. Diagnosticado el mismo día desde el log de errores real, arreglado y con 4 tests
  de regresión antes de la siguiente sesión de mercado — issue #26 en
  [`AUDITORIA.md`](AUDITORIA.md). Ningún test lo había atrapado antes porque no existía ninguno
  sobre `_close_legs`.
- **El debate alcista/bajista no es original por sí solo** — `ai-hedge-fund` ya lo hace. El
  presupuesto de originalidad se gasta en la señal (VRP + gamma), no en el debate.
- **Solo el iron condor se opera en producción** (ver §2). Los verticales están en el código pero
  `fade_trend=False` los deja inalcanzables.

---

## Posicionamiento para el jurado

**Cuatro criterios, ~25% cada uno.** Social Engagement es un premio **aparte** ($500 ×2), no un eje.

| Criterio | Nuestra jugada |
|---|---|
| **P&L Performance** | No es nuestro eje — 4 sesiones = suerte. Pero el resultado real es limpio: 1 trade, ganador, +$318,85, cerrado dentro de las strikes exactamente como estaba diseñado. Sizing consistente, downside topado, y el backtest muestra que forzarlo empeora el resultado |
| **Technology Implementation** | Uso profundo y real del stack de Alpaca: Trading API por el CLI, datos de opciones con griegas/IV, OI para el GEX, condors de 4 patas como una orden `mleg`, idempotencia + reconcile, 181 tests. La arquitectura coincide casi punto por punto con la que **Alpaca publica como buena práctica** |
| **Creativity & Originality** | La señal: superficie de volatilidad + gamma de dealers, no un indicador sobre el precio. La mesa de agentes anclada a números reales de la señal, con predicción falsable calificada |
| **Presentation & Execution** | One-pager escrito desde el código (nada que no exista), vídeo con el momento en que la mesa **se niega a operar** antes de un dato macro, journal falsable, dashboard en vivo |

**El reencuadre**: *"no vendemos una mesa que gana dinero, vendemos una mesa que sabe cuándo no
operar"*. El journal lo demuestra: **295 decisiones de stand-down documentadas** en 4 sesiones,
y **1 trade real** — abierto por la mesa real (no en sombra), cerrado dentro de las strikes,
+$318,85. Las dos cosas a la vez, con números reales, no proyectados.

---

## Glosario exprés

| Término | En una línea |
|---|---|
| **Opción** | Contrato: derecho a comprar/vender algo a precio fijo antes de una fecha. El vendedor cobra prima |
| **Prima** | Lo que se paga por una opción. Nuestro ingreso cuando vendemos |
| **Iron condor** | Vender un rango: ganas fijo si el índice se queda dentro, pierdes fijo (topado) si se sale |
| **IV (volatilidad implícita)** | Cuánto espera el mercado que se mueva el índice, según el precio de las opciones |
| **RV (volatilidad realizada)** | Cuánto se movió de verdad. `RV_hat` = nuestra previsión de ella |
| **VRP** | IV − RV. El "exceso de precio" del seguro. Nuestra fuente de retorno |
| **GEX (gamma exposure)** | Cómo están posicionados los dealers. Positivo → mercado amortiguado; negativo → mercado que se va con fuerza |
| **DTE** | Días hasta el vencimiento. Operamos a 1–3 |
| **0DTE** | Opción que vence hoy. Solo la tocamos antes de las 14:00 ET |
| **Delta** | Sensibilidad de la opción al precio del subyacente. Elegimos strikes cortos a delta 0.18 |
| **Strike** | El precio fijo de una opción |
| **mleg (multi-leg)** | Una orden que agrupa varias patas de opciones en una sola |
| **NAV / equity** | El valor total de la cuenta. Es lo que puntúa el jurado |
| **Drawdown** | Caída desde el máximo de la cuenta. Dispara los frenos de tamaño |
| **Stand down** | El desk decide no operar. Se registra con el motivo |
| **Paper trading** | Dinero simulado, precios reales. Todo el hackathon es así |
