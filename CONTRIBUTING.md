# Método de trabajo

Equipo de 2, una semana. Ligero, pero sin romper `main` — el cron opera desde `main`.

---

## El ciclo: lanes → auditoría cruzada → reparto

1. **Cada uno resuelve los issues de su lane.** Están etiquetados en GitHub (`lane/ejecucion`,
   `lane/senal`, `lane/entrega`).
2. **Cuando los dos han terminado su tanda**, uno de los dos hace una **auditoría cruzada** del
   trabajo del otro con Claude Code: se lee el diff, se contrasta contra
   [`docs/AUDITORIA.md`](docs/AUDITORIA.md), [`docs/strategy-spec.md`](docs/strategy-spec.md) y
   [`docs/API-ALPACA.md`](docs/API-ALPACA.md), y se comprueba que lo que el código hace es lo que los
   docs dicen que hace.
3. **Lo que salga de ahí se abre como issues nuevos**, con fichero y línea, con la misma etiqueta de
   severidad (`P0-bloqueante` / `P1` / `P2`) que usa la auditoría original.
4. **Se reparten esos issues por lane** y vuelta al paso 1.

**Por qué auditar el trabajo del otro y no el propio:** el que escribió el código ya asumió que era
correcto — es el mismo motivo por el que el probe del Día 0 validó solo la mitad de la convención de
`limit_price` que no íbamos a usar (issue #1). Ojos nuevos, o los del asistente con contexto nuevo,
encuentran lo que los tuyos ya no ven.

---

## El reparto es por **propiedad de ficheros**, no por temas

Este es el criterio, y es deliberado: **minimizar los conflictos de merge**. Con dos personas
trabajando en paralelo sobre ~1.150 líneas de Python, dos ramas tocando `execution.py` a la vez
cuestan más tiempo en resolver conflictos que el que ahorra el paralelismo. Por eso cada lane es
dueña de un conjunto de ficheros **disjunto**:

| Lane | Persona | Ficheros propios |
|---|---|---|
| **`lane/ejecucion`** | Álvaro | `agent/broker.py`, `agent/execution.py`, `.github/workflows/`, `tests/` |
| **`lane/senal`** | Ángel | `agent/signal.py`, `agent/config.py`, `backtest/` |
| **`lane/entrega`** | quien tenga hueco | `docs/`, `README.md`, capa LLM |

Reglas que se derivan de esto:

- **No toques un fichero de la otra lane.** Si necesitas un cambio ahí, abre un issue o pídelo por
  chat; no lo edites "que es una línea".
- `agent/desk.py` y `agent/risk.py` son **frontera compartida**: avisa antes de tocarlos.
- Si un issue obliga a cruzar la frontera, se habla antes de empezar. Es más barato coordinarse cinco
  minutos que resolver un conflicto en el motor a las 22:00 del domingo.

---

## `docs/AUDITORIA.md` se actualiza en el MISMO PR

Si tu PR arregla `execution.py:158`, **ese mismo PR actualiza la entrada correspondiente de
`docs/AUDITORIA.md`**. No en un PR de limpieza posterior, no "luego lo pongo".

Motivo: la auditoría es el mapa desde el que decidimos qué hacer y en qué orden, y es además material
de entrega en el eje de robustez. Una auditoría que describe defectos ya arreglados es peor que no
tenerla, porque nos hace repetir trabajo y nos hace desconfiar del resto del documento.

Lo mismo aplica a [`docs/internal/STATUS.md`](docs/internal/STATUS.md) cuando un PR cambia el estado de un componente, y
a [`docs/write-up.md`](docs/write-up.md), que **se escribe desde el código y nunca desde el plan**.

---

## Ramas

- `main` — siempre desplegable. El loop de GitHub Actions opera desde aquí.
- Trabajo en `lane/ejecucion`, `lane/senal`, `lane/entrega` (o ramas cortas `feat/*` colgando de la lane).
- PR a `main`, revisión rápida del otro, squash-merge.
- **Nunca commits directos a `main`.**

## Antes de abrir un PR

```
uv run ruff check .
uv run pytest -q
uv run python -m agent.desk    # debe correr limpio en dry_run
```

## Secretos — nunca se commitean

`.env` está en `.gitignore`. Las claves reales viven en:
- el `.env` local de cada uno (cuenta de **testing** `PA3TQHQKM5AD`);
- GitHub → **Settings → Secrets and variables → Actions** (cuenta de **competición** `PA39HSCQE8S3`):
  `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `FEATHERLESS_API_KEY`;
  y en **Variables**: `FEATHERLESS_MODELS`, `DESK_MODE`.

## Ficheros de datos

`data/journal.jsonl` y `data/equity.csv` los escribe y commitea el bot en cada loop.
**No los edites a mano.** Ante un conflicto de merge ahí, quédate con la versión de `origin/main`.

## Durante las sesiones en vivo

De lunes a jueves, 15:30–22:00 CEST, manda el [`docs/RUNBOOK.md`](docs/RUNBOOK.md): nada de deploys de
código durante la sesión salvo que el desk esté perdiendo dinero por un bug, y cada incidente se anota
en su log de incidentes.

## Visibilidad del repo

**Privado hasta la entrega.** Pasarlo a público el **4 sep** antes de enviar (las reglas exigen repo
público con licencia MIT): `gh repo edit --visibility public`.
