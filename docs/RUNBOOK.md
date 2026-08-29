# Runbook — las 4 sesiones en vivo

Qué mirar y qué hacer cuando algo falla. **Leerlo los dos antes del lunes.** Fechas completas en
[`CALENDARIO.md`](CALENDARIO.md). Convenciones de la API en [`API-ALPACA.md`](API-ALPACA.md).

**Sesión: 15:30–22:00 CEST** (09:30–16:00 ET). Críticos: **15:30** apertura · **21:45** cierre por
expiración (=15:45 ET) · **22:00** cierre.

---

## Checklist de arranque — lunes 31, 15:00 CEST

- [ ] Cuenta **de competición** `PA39HSCQE8S3` ("PAPER UC3M"): **portfolio_value $100.000**
      (el "buying power" $200k es el 2× de margen — no es la equity), **cero** posiciones, **cero**
      órdenes, **cero** histórico.
- [ ] Secrets de GitHub = keys de `PA39HSCQE8S3`. **NO** las de testing `PA3TQHQKM5AD`.
      Comprobación: un run manual en `dry_run` debe loguear el evento `account` con
      `"account": "PA39HSCQE8S3"` y `nav 100000`.
- [ ] Repo variable `ALPACA_ACCOUNT_ID` = `PA39HSCQE8S3` y `DESK_MODE` = `live`. Nada antes de las 15:30.
- [ ] El guardarraíl de cuenta hace su trabajo solo: rechaza `live` si las credenciales no son
      `PA39HSCQE8S3`, y rechaza tocar esa cuenta antes del lunes 09:30 ET. No sustituye a la
      comprobación manual de arriba.
- [ ] Último run del cron es reciente y verde (Actions → *IV Desk loop*).
- [ ] `data/journal.jsonl` y `data/equity.csv` limpios de la sesión de testing (o asumido y anotado).
- [ ] **La mesa va 100% Featherless.** `FEATHERLESS_API_KEY` puesta y `FEATHERLESS_MODELS` con 3
      ids de modelo separados por comas (ver "La capa LLM" abajo). No hay ningún otro proveedor de
      LLM en el loop: los cuatro asientos salen de `FeatherlessSeatClient` (`agent/seats.py`).
      Opcional: `FEATHERLESS_ARGUER_MODEL` para Bull/Bear/Desk Head; si no está, usan el primero de
      `FEATHERLESS_MODELS`.
- [ ] Los dos con el repo abierto y este documento a mano.

---

## El loop tolera un run saltado — por diseño

El cron de GitHub Actions es best-effort: puede retrasarse 5–30 min o saltarse. El loop está hecho
para que un run perdido no sea fatal:

- **En cada arranque reconcilia contra Alpaca** (`ex.reconcile`): resuelve entradas pendientes
  contra el estado real de la orden, revisa cierres pendientes, y detecta posiciones de acciones
  inesperadas (asignación temprana). `data/trades.jsonl` es un journal, no la fuente de verdad.
- **El cierre por expiración dispara en cualquier run desde las 15:30 ET**, no en un único run de
  las 15:45. Un tick saltado ya no significa que una posición se vaya a expiración sin gestionar.
- `client_order_id` es determinista por intención de trade → un re-run o un dispatch manual no
  puede duplicar una orden.

### Si un run se salta

| Momento | Riesgo | Acción |
|---|---|---|
| **Cerca de la apertura (15:30–16:00)** | Una entrada planificada se retrasa. Poca urgencia. | Nada. El siguiente tick la abre si la señal sigue. |
| **Mitad de sesión** | Un take-profit o stop que debía saltar va con retraso. | Mirar el timestamp del último evento `portfolio`/`exit` en `data/journal.jsonl`. Si el último run tiene >30 min y el mercado está abierto → run manual. |
| **21:30–22:00 CEST en un día de expiración** | Una posición puede expirar sin gestionar → pin, asignación, ~$77k de nocional en acciones. | **Run manual YA.** Si Actions no responde, correr el loop local en `exits_only` (abajo) o cerrar a mano en el dashboard. |

---

## En cada invocación (cada 15 min)

Mirar el **último bloque del journal** (`data/journal.jsonl`) y el último run de Actions:

| Campo | Qué esperar | Alarma si |
|---|---|---|
| último `event` | `portfolio` + un `signal` por cada SPY/QQQ/IWM | no hay evento nuevo en >30 min → **cron saltado** |
| `event: account` | `"account": "PA39HSCQE8S3"` | cualquier otra cuenta → **PARAR**, secrets mal |
| `nav` | ~$100k, movimiento suave | salto brusco sin `opened`/`exit` que lo explique |
| `day_pnl` | dentro de ±$1.500 | ≤ −$3.000 → el breaker debería haber saltado (`daily_loss_breaker` 3%) |
| `n_pos` | ≤ `max_positions` y coincide con Alpaca | no coincide con el dashboard → **posición fantasma** (reconcile debería resolverlo) |
| `net_delta` | cerca de 0 | \|net_delta\| > 0.30 → el gate de delta debería bloquear nuevas |
| `size_mult` | `1.0` | `0.5` = throttle por drawdown 8% · `0.0` = halt 12% |
| `rejected` | motivos esperados: `macro event blackout`, `credit_frac`, `per-trade risk` | motivos raros: `missing greeks` repetido, `portfolio delta band` repetido, o **cero eventos `signal`** |
| `exits_only` | — | `early_assignment` → asignación temprana, ver abajo · `kill_switch` → alguien puso `DESK_MODE=exits_only` |

`market_closed` fuera de horario es normal. Un `rejected` documentado **no es un fallo**: es el
producto que estamos vendiendo ([`VIABILIDAD.md`](VIABILIDAD.md)). Un journal **vacío** sí lo es.

---

## Kill switch (< 1 minuto)

| Objetivo | Acción | Efecto |
|---|---|---|
| **Parar de abrir, seguir gestionando el libro** | repo variable `DESK_MODE` = `exits_only` (`gh variable set DESK_MODE --body exits_only`) + un `workflow_dispatch` con `mode: exits_only` para actuar ya | reconcilia y gestiona salidas en la cuenta live, no abre nada. **Sí cierra** posiciones. |
| **Parar el loop entero** | Actions → *IV Desk loop* → ⋯ → **Disable workflow** | no corre nada. Gestionar el libro a mano. |
| **Aplanar el libro** | a mano en el dashboard de Alpaca, cuenta `PA39HSCQE8S3` | — |

> `dry_run` en local va **siempre** contra la cuenta de testing y no coloca nada. `exits_only` y
> `live` exigen que las credenciales resuelvan a `PA39HSCQE8S3` o el guardarraíl aborta.

---

## Correr el loop en local (último recurso)

Solo si GitHub Actions está caído en una ventana crítica.

```bash
# en la raíz del repo, con las keys de COMPETICIÓN exportadas (nunca en .env):
export ALPACA_API_KEY=...  ALPACA_SECRET_KEY=...  ALPACA_ACCOUNT_ID=PA39HSCQE8S3
export ALPACA_CLI_BIN="$HOME/.local/bin/alpaca"   # o donde esté el binario
export MSYS_NO_PATHCONV=1                          # solo Git Bash
DESK_MODE=exits_only uv run python -m agent.desk
```

---

## Árbol de incidentes

| Síntoma | Primero | Después |
|---|---|---|
| **Orden rechazada** (error de Alpaca) | Leer el motivo en el run de Actions / evento `error`. `insufficient qty` → esperar al siguiente loop | Si es `limit_price`/signo → kill switch y revisar ([`API-ALPACA.md`](API-ALPACA.md): el `limit_price` de `mleg` va **firmado**, negativo = crédito) |
| **Orden no se llena** (queda `pending_open`) | Normal si es no marketable. `reconcile` la cancela sola tras ~20 min y la reintenta | Si persiste varios loops: cancelar a mano en el dashboard |
| **Posición fantasma** (Alpaca ≠ journal) | **Alpaca manda.** `reconcile` reconstruye desde `broker.positions()`/`orders()` | Si el desk cree tener menos posiciones que Alpaca → kill switch |
| **Breaker disparado** (`exits_only: breaker`) | Correcto, dejarlo. Solo salidas hasta el día siguiente | Confirmar la pérdida en el dashboard |
| **Asignación temprana** (`exits_only: early_assignment`) | Hay **acciones** en la cuenta, no un condor. El desk se planta solo y sigue gestionando salidas | Cerrar la posición de acciones a mano y luego las patas huérfanas. Anotar el nocional |
| **Cron saltado** | Actions → *Run workflow* manualmente | Si es cerca de las **21:45 CEST**: lanzarlo YA |
| **Todo verde pero 0 trades en toda la sesión** | Buscar `rejected`/`no_structure`/`debate` y su motivo | Si el motivo es siempre `credit_frac` o `vrp` → los umbrales bloquean todo. Decisión humana, no tocar en caliente |

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

## La capa LLM (la mesa Featherless)

Los cuatro asientos (Quant ×3, Bull, Bear, Desk Head) corren sobre **modelos abiertos servidos por
Featherless**, endpoint compatible con OpenAI. Es el **único** proveedor de LLM del loop.

**Antes del lunes:** `FEATHERLESS_MODELS` tiene que llevar **3 ids de modelo separados por comas**.
Si está vacío, el Quant no alcanza consenso y **cada apertura se planta** con `debate` `approved:
false` en el journal. No es un fallo silencioso, pero se parece a "el desk no opera nunca".

**Kill switch de la mesa** (independiente del `DESK_MODE`):

| Situación | Acción |
|---|---|
| Featherless caído, o el cupón agotado | `DESK_DEBATE=off` → el desk sigue operando con la decisión determinista |
| Sospecha de que la mesa aprueba cosas raras | dejar `DESK_DEBATE=required` y revisar los eventos `debate` del journal |
| Parar el desk entero | kill switch de arriba (`DESK_MODE=exits_only`) |

`DESK_DEBATE=off` **no** desactiva las salidas ni los gates de riesgo: solo salta el debate. Es el
modo degradado seguro. La mesa **nunca** puede ampliar tamaño ni saltarse `risk.evaluate` — solo
recortar o vetar (`agent/debate.py`).

---

## Reglas de cuenta (nunca romper)

| Cuenta | ID | Uso | Keys en |
|---|---|---|---|
| Paper Trading (testing) | `PA3TQHQKM5AD` | todo el dev, dry-run, pruebas de fills | `.env` local únicamente |
| PAPER UC3M (competición) | `PA39HSCQE8S3` | órdenes del agente en la ventana de P&L — equity que juzgan | secrets de GitHub Actions únicamente |

- Ninguna orden manual en `PA39HSCQE8S3`, jamás. Su historial debe ser 100% del agente.
- Las keys de competición nunca en el `.env` local.
- `ALPACA_ACCOUNT_ID` es **siempre** el id de competición (`PA39HSCQE8S3`), en todas partes — es lo
  que comprueba el guardarraíl y lo que va en la submission.

---

## Setup local (antes de poder correr nada)

El CLI de Alpaca **no es opcional**: `agent/broker.py` rutea todas las llamadas de trading por él
(issue #4), así que sin el binario ni siquiera `broker.account()` funciona.

```bash
V=0.0.14   # el mismo pin que .github/workflows/desk.yml — no uses "latest", el CLI es alpha
ARCH="darwin_arm64"   # o darwin_amd64 / linux_amd64
curl -sSL --fail "https://github.com/alpacahq/cli/releases/download/v${V}/cli_${V}_${ARCH}.tar.gz" \
  | tar -xz -C /tmp && install -m 0755 /tmp/alpaca ~/.local/bin/alpaca
alpaca version   # debe imprimir exactamente $V
```

Después, `cp .env.example .env` y rellenar. Comprobación de que todo está en pie:

```bash
uv run python -c "from agent import broker; print(broker.account()['account_number'])"
```
