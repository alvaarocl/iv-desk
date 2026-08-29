# backtest-lite — ¿dispara la estrategia alguna vez? (issue #5)

```bash
uv run python -m backtest.replay --synthetic   # sin claves ni red: tape sintético
uv run python -m backtest.replay               # ~60 sesiones reales (necesita las claves)
uv run python -m backtest.replay --selftest    # asserts del pipeline, sin red
```

**Cómo leer la tabla de embudo.** Cada fila es un gate; `PASS` son los candidatos que siguen vivos
*después* de ese gate (acumulado), `KILLED` los que mueren ahí y `<<< DIES HERE` marca el gate que
mata a más. La unidad es la **sesión-subyacente** (60 sesiones × 3 nombres = 180). El bloque de
estadísticas de debajo da la mediana/p90 de la magnitud que lee cada gate junto a su umbral: si la
p90 de `credit/width` está por debajo del umbral, ese gate es inalcanzable, no estricto. Se imprimen
dos embudos — los parámetros actuales de `config.py` y los **pre-auditoría** (`IV-RV >= 0.03`,
`credit/width >= 0.33`, alas 4/2), que son la pregunta original del issue #5 — y una tabla de
sensibilidad que dice cuántos trades salen con cada umbral alternativo. Esa tabla es la que se usa
para calibrar: **no calibrar a ojo**.

**Qué es sólido y qué no.** El embudo llama al motor real (`signal.build_signal`, `desk._pick`,
`execution.select_condor/size`, `risk.evaluate`), no a una copia. Sin quotes históricas, la cadena se
reconstruye desde barras diarias invirtiendo Black-Scholes; usar el cierre como mid es *optimista*
frente a un bid/ask real, así que el gate de crédito sale favorecido: si aun así muere ahí, muere de
verdad. El OI histórico no existe, se usa el volumen como proxy → **la fila de GEX es la más
débil**, y en modo `--synthetic` es circular (`gex_norm ≈ --gex-bias`). El P&L es a vencimiento, sin
take-profit ni stop: es secundario, no una estimación de rentabilidad.

**Detalles.** `backtest/cache/` se crea en runtime y guarda las respuestas de la API por
sesión-subyacente (borrarlo = refetch; `--no-cache` lo ignora). **No está en `.gitignore`** — añadidlo
quien tenga ese fichero. El tiempo se mide en sesiones (1/252), no en días naturales, para que la
prima y la RV anualizada de `signal.py` usen el mismo reloj. `sensitivity()` es una función pura sobre
los días ya cacheados: barrer umbrales no cuesta ni una llamada más a la API.
