# `docs/internal/` — documentos de trabajo

> **Esto no son entregables.** Son los documentos con los que el equipo se organizó durante el
> hackathon: planes por día, checklists, notas de posicionamiento y tableros de estado. Están en el
> repo público porque preferimos enseñar cómo se tomaron las decisiones a fingir que el proyecto
> salió limpio a la primera — pero **no son la documentación del producto**.
>
> Se escribieron en un momento concreto y **no se mantienen al día**. Si algo aquí contradice a
> `docs/` o al código, manda el código.

**Si has llegado buscando qué es IV Desk**, la documentación de verdad está un nivel más arriba:

| Empieza por | Qué es |
|---|---|
| [`../write-up.md`](../write-up.md) | El one-pager de la entrega. En inglés. |
| [`../CONCEPT.md`](../CONCEPT.md) | Qué hace la mesa y por qué, sin jerga. |
| [`../strategy-spec.md`](../strategy-spec.md) | La estrategia exacta: gates, strikes, sizing, salidas. |
| [`../DOSSIER.md`](../DOSSIER.md) | Defensa completa, de lo divulgativo a lo técnico fichero a fichero. |
| [`../AUDITORIA.md`](../AUDITORIA.md) | Auditoría técnica del propio código, defecto a defecto con `fichero:línea`. |
| [`../RUNBOOK.md`](../RUNBOOK.md) | Operativa en vivo: qué mirar y qué hacer si algo se rompe. |
| [`../GLOSSARY.md`](../GLOSSARY.md) · [`../API-ALPACA.md`](../API-ALPACA.md) | Glosario de opciones · notas de la API de Alpaca. |

---

## Qué hay en esta carpeta

| Documento | Qué es | Escrito para |
|---|---|---|
| [`STATUS.md`](STATUS.md) | Tablero de estado a mano: qué funciona, qué falta, quién lleva cada cosa y qué decisiones están cerradas. El tracker real del proyecto durante la semana. | Los dos, a diario |
| [`VIABILIDAD.md`](VIABILIDAD.md) | Juicio honesto de si la idea funciona en 4 sesiones (spoiler: la varianza domina al edge) y cómo la posicionamos frente al rubro del jurado. | Decidir el enfoque, 29 ago |
| [`PLAN-FINDE.md`](PLAN-FINDE.md) | Reparto de tareas del fin de semana previo al go-live (A1–A8 / B1–B8), con las decisiones que no se re-litigan. | Sáb 29 → lun 31 |
| [`SUBMISSION.md`](SUBMISSION.md) | Checklist de entrega en lablab: los diez entregables obligatorios, con estado y deadline. | Vie 4 sep |
| [`mentor-brief.md`](mentor-brief.md) | Resumen corto (inglés + español) para pedirle lectura crítica a un mentor del hackathon. | Enviar a un mentor |
| [`video-script.md`](video-script.md) | Guion de rodaje del vídeo demo por screen-recordings. Quedó como **B-roll opcional**: la entrega final es el proyecto Remotion de [`../../video/`](../../video/). | Grabación |
| [`estado.html`](estado.html) | El tablero de estado como página de una pantalla. Ábrelo en el navegador. **Congelado a 30 ago** — algunas secciones (MCP, "Anthropic" en la mesa) ya no reflejan el código. | Mirar de un vistazo |
| [`game-plan.html`](game-plan.html) | La estrategia y el plan de los 7 días como one-pager diseñado. **Congelado**: su tabla de criterios del jurado es la vieja de cinco ejes; los reales son cuatro (ver [`../REGLAS-HACKATHON.md`](../REGLAS-HACKATHON.md)). | Alinearnos al arrancar |

## Por qué siguen aquí

Tres de ellos son evidencia, no ruido:

- **`VIABILIDAD.md`** dice por escrito, dos días antes de operar, que esperábamos que la señal
  disparase poco. El backtest lo confirmó después. Es la predicción, con fecha, antes del resultado.
- **`STATUS.md`** y **`PLAN-FINDE.md`** dejan ver el orden real de trabajo: primero el backtest que
  podía matar el proyecto, después los arreglos.

Lo demás es logística, y se queda por completitud.
