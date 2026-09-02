# Viabilidad y posicionamiento

Juicio honesto sobre si la idea funciona, y cómo presentarla. Escrito el 29 ago, con la ventana de P&L a dos días.

---

## ¿Es viable la idea?

Son dos preguntas distintas con respuestas distintas.

### Como estrategia de trading: buena, pero no validable en 4 sesiones

El VRP es de las anomalías mejor documentadas en finanzas. Vender volatilidad de índice tiene retorno esperado positivo a largo plazo. No es humo. Y el gating por gamma de dealers es un efecto real: cuando los dealers están largos de gamma, su cobertura suprime la volatilidad realizada.

**El problema es de horizonte.** El VRP paga ~2-4 puntos de vol anualizados, y su perfil de pago es *"gano poco el 85% de las veces, pierdo mucho el 15%"*. En **cuatro sesiones** sacamos cuatro muestras de esa distribución: la varianza domina por completo al edge. Un condor que revienta el miércoles borra la semana y **no dice nada** sobre si la estrategia es buena.

Y el GEX que podemos calcular — open interest con retraso T-2, sin inferir el posicionamiento real de dealers — es un proxy tosco. Como **narrativa diferenciadora** es excelente; como **edge medible en 4 días**, es marginal.

Conclusión: es una estrategia correcta metida en un formato de concurso que no puede medirla. Eso no es un fallo del proyecto, pero sí determina cómo hay que presentarlo.

### Como propuesta de hackathon: sí, y está bien posicionada

El jurado son **4 criterios** y el P&L es **uno**. Los otros tres — Technology, Creativity, Presentation — son el **75%**, y en esos tres la idea es de las mejores que va a ver el jurado:

- La arquitectura coincide casi punto por punto con lo que la **propia Alpaca publica como buena práctica**: agentes especializados, risk guard determinista sin LLM, monitorización cada 15 min.
- Frente a los ~2.000 *"multiagente + RSI sobre SPY"* que van a llegar, mirar la superficie de volatilidad y el gamma de dealers es genuinamente distinto.

**Veredicto: viable, con margen ajustado pero real.** Los bugs bloqueantes son todos de minutos (signos, unidades, umbrales). Lo único grande que falta construir es la capa LLM, y es un día de trabajo.

**Lo que puede matar el proyecto no es la falta de tiempo: es no descubrir hasta el lunes que la estrategia no dispara nunca.** De ahí que el backtest (issue #5) vaya antes que cualquier arreglo.

---

## El reencuadre: una mesa que sabe cuándo NO operar

**Dejad de vender "una mesa que gana dinero" y vended "una mesa que sabe cuándo no operar".**

Por qué funciona:

1. **Convierte la mayor debilidad en la tesis.** Una semana de volatilidad baja donde la señal casi no dispara deja de ser un fracaso y pasa a ser la demostración de que la disciplina es real.
2. **Es el discurso al que responden estos jueces.** Son gente de Alpaca, gente de riesgo. Un agente que se niega a operar antes del NFP es más impresionante que uno que acertó tres condors.
3. **Ya tenemos el artefacto.** `data/journal.jsonl` con eventos `rejected` es exactamente la prueba, y es falsable.

### La condición que lo hace funcionar

Esto **solo** vale si el journal muestra a la mesa **decidiendo** no operar con motivo documentado, no quedándose callada. Un log vacío no demuestra disciplina: demuestra que no funciona.

Y hacen falta **algunos** trades igualmente. Presentarse el viernes con 0 operaciones y un journal precioso nos deja en el fondo del 25% del P&L. **Las dos cosas a la vez:** recalibrar para que dispare (issues #6 y #7) y loguear los stand-downs como feature.

---

## La incoherencia de riesgo que hay que resolver

`CONCEPT.md` **decía** del eje de P&L *"Cedemos este"* (corregido el 29 ago). Pero la configuración actual **cede el upside y conserva todo el downside**:

- 0.5% de $100k = $500/trade → **1 contrato** → ~$120 de crédito.
- Con 3 posiciones en 4 sesiones, el mejor escenario posible es **~0.3% de retorno**. Indistinguible de cero.
- Pero el max loss de ese condor son **$280**, y una sola rotura se come dos ganadores.

Estamos corriendo riesgo real por un premio que no mueve la aguja en el eje que decimos ceder. Es la peor combinación posible.

**Hay que elegir una de las dos, y codificarla:**

| Opción | Qué implica |
|---|---|
| **(a) Asumir la cesión** | Optimizar el 75% restante, pero **reducir también el riesgo**: menos posiciones, más selectivo. Que el downside sea coherente con el upside |
| **(b) Rampa agresiva** | 0.5% el lunes; 1.5-2% desde el martes si el lunes fue limpio. Es lo que ya dice `PLAN.md` pero **no está codificado en ningún sitio** |

Cualquiera vale. Lo que no vale es la posición actual, que es (a) en el upside y (b) en el downside. Issue #16.

---

## Prioridades

Orden recomendado para el fin de semana. Detalle en [`AUDITORIA.md`](../AUDITORIA.md) y en los issues.

### Sábado 29
1. **Backtest-lite** (#5) — antes de tocar nada. Es el diagnóstico que valida o tumba todo lo demás.
2. Signo del `limit_price` (#1) — una línea.
3. Unidades del exit manager (#2) — una línea y un test.
4. Migrar la ejecución al CLI (#4) — requisito de elegibilidad.

### Domingo 30
5. Recalibrar VRP a ratio relativo (#6) y bajar `width_spy` (#7). Sin esto lo demás no sirve.
6. Reconciliar contra `broker.positions()` + `client_order_id` (#3).
7. Probar el exit manager sobre un condor real de 1 lote en **testing**.
8. Los 4 tests mínimos (#9).
9. Capa LLM (#13) — el chunk grande.

### Qué cortar sin pensarlo
- **El dashboard.** Las reglas dicen explícitamente que la UI no es obligatoria.
- La reflexión nocturna / auto-tuning.

### Qué NO cortar
La capa LLM. Es la mitad del eje de Creativity y es lo que justifica llamar a esto "una mesa" en vez de "un script".

---

## Riesgos asumidos con los ojos abiertos

- **Semana de volatilidad baja.** Mitigado parcialmente por la recalibración, no eliminado.
- **4 sesiones son una lotería de varianza.** Por eso no apostamos el proyecto a ese eje.
- **El debate alcista/bajista no es original por sí solo** — `ai-hedge-fund` ya lo hace y mucha gente lo copiará. Nuestro presupuesto de originalidad se gasta en la señal, no en el debate.
- **Scope ajustado:** capa LLM + calibración + contenido en 2 días con 2 personas. La lista de recortes de `PLAN.md` existe por algo.
