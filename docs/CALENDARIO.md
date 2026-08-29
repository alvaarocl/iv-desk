# Calendario — todas las fechas en un sitio

**Estamos en España (CEST = UTC+2). El mercado americano va 6 horas por detrás (ET = UTC−4).**
`CEST = ET + 6`. Esta conversión es la fuente de errores más tonta que tenemos: aquí va hecha.

Reglas y fuentes en [`REGLAS-HACKATHON.md`](REGLAS-HACKATHON.md). Qué hacer cada día en
[`RUNBOOK.md`](RUNBOOK.md).

---

## Los cuatro números que importan

| Qué | Hora local (CEST) | Hora del mercado (ET) |
|---|---|---|
| **Arranque de la ventana de P&L** | lun 31 ago, **15:30** | lun 31 ago, **09:30** |
| **Cierre por expiración** (última ventana para descargar riesgo) | **21:45** cada sesión | **15:45** |
| **Cierre de mercado / snapshot de equity** | jue 3 sep, **22:00** | jue 3 sep, **16:00** |
| **Deadline de submission (lablab)** | vie 4 sep, **17:00** | vie 4 sep, **11:00** (15:00 UTC) |

---

## Sesiones que cuentan para el P&L

Cuatro. Todas de **15:30 a 22:00 CEST** (09:30–16:00 ET).

| Sesión | Fecha | Nota |
|---|---|---|
| 1 | **lun 31 ago** | Primera orden de la cuenta de competición. Nada anterior cuenta. Sizing conservador |
| 2 | **mar 1 sep** | Escalar sizing solo si el lunes fue limpio |
| 3 | **mié 2 sep** | Preferir expiraciones del 3 sep |
| 4 | **jue 3 sep** | **FINAL.** Snapshot de equity al cierre (22:00 CEST). Libro limpio |

- **Vie 4 sep no cuenta para P&L.** Es día de entrega, no de trading. El NFP de esa mañana es irrelevante para el scoring.
- **Lun 31 ago es sesión hábil** — verificado: el Labor Day 2026 cae el **lun 7 sep**, fuera de la ventana. No hay festivo ni cierre anticipado dentro de la ventana.
- **Expiraciones de competición: ≤ 3 sep.** Nada que expire el viernes 4, porque el snapshot ya habrá pasado.

> ⚠️ **Pendiente de confirmar en Discord.** La ventana "snapshot EOD jueves 3 sep" viene de las
> guidelines privadas de Alpaca del 29 ago y **no es verificable públicamente**. Toda la política de
> expiraciones depende de ella. No la cambiéis sin confirmar: si el snapshot fuera el viernes y
> cerramos el jueves perdemos una sesión, pero si es el jueves y tenemos expiraciones del viernes
> abiertas perdemos el proyecto. La asimetría actual es la correcta. → issue #19

---

## Momentos críticos de cada sesión

| CEST | ET | Qué pasa |
|---|---|---|
| 15:30 | 09:30 | Apertura. Primer loop de la sesión. Spreads anchos: los primeros minutos son los peores para entrar |
| 20:00 | 14:00 | Corte de nuevos 0DTE (`no_new_0dte_after_et` en `agent/config.py`) |
| **21:45** | **15:45** | **Cierre por expiración.** `manage_exits()` cierra las estructuras que expiran hoy. Si este loop se salta, la posición se va a expiración con riesgo de pin y asignación |
| 22:00 | 16:00 | Cierre. El loop siguiente ya registra `market_closed` |

El cron de `.github/workflows/desk.yml` corre `*/15 13-20 * * 1-5` **UTC** = cada 15 min de 15:00 a
22:45 CEST. Los `schedule:` de GitHub son **best-effort** (issue #23): pueden retrasarse o saltarse.

---

## Calendario macro (blackout de eventos)

Fuente: `agent/calendar.py`. El gate bloquea **abrir** posiciones **±2 h** alrededor de cada evento.

| Evento | Fecha | ET | CEST | Blackout (CEST) |
|---|---|---|---|---|
| PCE price index | vie 28 ago | 08:30 | 14:30 | 12:30–16:30 — antes de la ventana |
| ISM Manufacturing PMI | **mar 1 sep** | 10:00 | 16:00 | **14:00–18:00** |
| ADP employment | **jue 3 sep** | 08:15 | 14:15 | 12:15–16:15 |
| ISM Services PMI | **jue 3 sep** | 10:00 | 16:00 | **14:00–18:00** |
| NFP / jobs report | vie 4 sep | 08:30 | 14:30 | 12:30–16:30 — fuera de la ventana de P&L |

> ⚠️ **Fechas y horas sin verificar contra un calendario económico real** (el propio docstring de
> `agent/calendar.py` lo pide). → issue #17

**Consecuencia operativa que hay que tener presente:** el martes 1 y el jueves 3 el blackout se come
**desde la apertura hasta las 18:00 CEST**. En esas dos sesiones la mesa no abre nada durante las
primeras 2,5 horas — eso es *correcto y deseado*, y va al journal como `rejected: macro event
blackout`, que es exactamente el material del argumento "una mesa que sabe cuándo no operar"
([`VIABILIDAD.md`](VIABILIDAD.md)). No lo confundáis con que el desk esté roto.

---

## Fuera de la ventana

| Qué | Cuándo (CEST) |
|---|---|
| Preparación: crear cuenta de competición, secrets, calibración, dry runs | sáb 29 – dom 30 ago (mercado cerrado) |
| Checklist de arranque ([`RUNBOOK.md`](RUNBOOK.md)) | lun 31 ago, **15:00** — media hora antes de abrir |
| Snapshot final: equity, posiciones, activity log | jue 3 sep, **después de 22:00** |
| Repo a público + submission | vie 4 sep, antes de las **17:00** |
