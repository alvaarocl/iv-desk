# Runbook — las 4 sesiones en vivo

Qué mirar y qué hacer cuando algo falla. **Leerlo los dos antes del lunes.** Fechas completas en
[`CALENDARIO.md`](CALENDARIO.md).

**Sesión: 15:30–22:00 CEST** (09:30–16:00 ET). Críticos: **15:30** apertura · **21:45** cierre por
expiración (=15:45 ET) · **22:00** cierre.

---

## Checklist de arranque — lunes 31, 15:00 CEST

- [ ] Cuenta **de competición** `PA39HSCQE8S3` ("PAPER UC3M"): equity **$100.000**, **cero** posiciones, **cero** órdenes, **cero** histórico.
- [ ] Secrets de GitHub = keys de `PA39HSCQE8S3`. **NO** las de testing `PA3TQHQKM5AD`. Comprobación: un run manual en `dry_run` debe loguear `nav: 100000.00` y `n_pos: 0`.
- [ ] Repo variable `DESK_MODE=live`. Nada antes de las 15:30.
- [ ] Último run del cron es reciente y verde (Actions → *IV Desk loop*).
- [ ] `data/journal.jsonl` y `data/equity.csv` limpios de la sesión de testing (o asumido y anotado).
- [ ] Los dos con el repo abierto y este documento a mano.

---

## En cada invocación (cada 15 min)

Mirar el **último bloque del journal** (`data/journal.jsonl`) y el último run de Actions:

| Campo | Qué esperar | Alarma si |
|---|---|---|
| último `event` | `portfolio` + un `signal` por cada SPY/QQQ/IWM | no hay evento nuevo en >20 min → **cron saltado** |
| `nav` | ~$100k, movimiento suave | salto brusco sin `opened`/`exit` que lo explique |
| `day_pnl` | dentro de ±$1.500 | ≤ −$3.000 → el breaker debería haber saltado (`daily_loss_breaker` 3%) |
| `n_pos` | ≤ `max_positions` y coincide con Alpaca | no coincide con el dashboard → **posición fantasma** |
| `size_mult` | `1.0` | `0.5` = throttle por drawdown 8% · `0.0` = halt 12% |
| `rejected` | motivos esperados: `macro event blackout`, `credit_frac`, `per-trade risk` | motivos raros: `missing greeks`, `portfolio delta band` repetido, o **cero eventos `signal`** |
| `exits_only` | — | `early_assignment` → asignación temprana, ver abajo |

`market_closed` fuera de horario es normal. Un `rejected` documentado **no es un fallo**: es el
producto que estamos vendiendo ([`VIABILIDAD.md`](VIABILIDAD.md)). Un journal **vacío** sí lo es.

---

## Kill switch (< 1 minuto)

1. **Parar de abrir** → repo variable `DESK_MODE=live` → `dry_run`.
   `gh variable set DESK_MODE --body dry_run`. Surte efecto **en el siguiente loop** (≤15 min).
2. **Parar todo el loop** → `gh workflow disable "IV Desk loop"` (o Actions → ⋯ → *Disable workflow*).
3. **Aplanar el libro** → a mano en el dashboard de Alpaca, cuenta `PA39HSCQE8S3`.

> ⚠️ `dry_run` **también desactiva las salidas** (`manage_exits` solo manda órdenes en `live`). El
> libro se queda congelado tal cual. Si hay riesgo abierto, tras pisar el kill switch hay que
> **cerrar a mano**. Un modo "solo salidas" está pendiente → issue #23.

---

## Árbol de incidentes

| Síntoma | Primero | Después |
|---|---|---|
| **Orden rechazada** (error de Alpaca) | Leer el motivo en el run de Actions. `insufficient qty` → esperar al siguiente loop | Si es `limit_price`/signo → kill switch y arreglar antes de reactivar ([`API-ALPACA.md`](API-ALPACA.md)) |
| **Orden no se llena** (queda `new`) | Normal si es no marketable. Comprobar en el dashboard que sigue viva | Si sigue abierta >2 loops: cancelar a mano. El repricing automático no está implementado (issue #3) |
| **Posición fantasma** (Alpaca ≠ `data/trades.jsonl`) | **Alpaca manda.** Contar posiciones en el dashboard | Si el desk cree tener menos → riesgo de reabrir: kill switch. Si cree tener más → corregir `data/trades.jsonl` a mano y commitear |
| **Breaker disparado** (`exits_only: breaker`) | Correcto, dejarlo. Solo salidas hasta el día siguiente | Confirmar la pérdida en el dashboard. Si es un `nav` erróneo, no reactivar sin entender por qué |
| **Asignación temprana** (`exits_only: early_assignment`) | Hay **acciones** en la cuenta, no un condor. El desk se planta solo | Cerrar la posición de acciones a mano y luego las patas huérfanas. Anotar el nocional |
| **Cron saltado** | Actions → *Run workflow* manualmente | Si es cerca de las **21:45 CEST**: lanzarlo YA. Una posición en expiración sin cerrar = riesgo de pin y asignación |
| **Todo verde pero 0 trades en toda la sesión** | Buscar `rejected`/`no_structure` y su motivo | Si el motivo es siempre `credit_frac`, los umbrales bloquean todo (issues #6/#7). Decisión humana, no tocar en caliente |

**Cambios en caliente:** solo parámetros vía `data/params.json` o el kill switch. **Nada de deploys
de código durante la sesión** salvo que el desk esté perdiendo dinero por un bug.

---

## Log de incidentes

Cada incidente resuelto es material para el write-up en el eje de robustez — que es un eje explícito
del jurado. Rellenar en el momento, no de memoria el viernes.

| # | Fecha/hora CEST | Síntoma | Causa | Qué hicimos | Impacto en P&L |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

## La capa LLM (la mesa)

**Antes del lunes:** `FEATHERLESS_MODELS` tiene que llevar **3 ids de modelo separados por comas**.
Si está vacío, el Quant no alcanza consenso y **cada apertura se planta** con `debate_unavailable`
en el journal. No es un fallo silencioso, pero sí se parece a "el desk no opera nunca".

**Kill switch de la mesa** (independiente del `DESK_MODE`):

| Situación | Acción |
|---|---|
| Featherless o Anthropic caídos, o el cupón agotado | `DESK_DEBATE=off` → el desk sigue operando con la decisión determinista |
| Sospecha de que la mesa aprueba cosas raras | `DESK_DEBATE=required` y revisar los eventos `debate` del journal |
| Parar el desk entero | Ver el kill switch de arriba (`DESK_MODE`) |

`DESK_DEBATE=off` **no** desactiva las salidas ni los gates de riesgo: solo salta el debate. Es el
modo degradado seguro, no un apagado.

**Qué mirar en el journal:** cada apertura escribe un evento `debate` con el transcript completo y la
predicción. Si `approved: false`, el motivo está en el registro — eso es material para el write-up.
