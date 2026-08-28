# Estado del proyecto

Última actualización: **29 ago 2026**. Este archivo se actualiza a mano según avanza el trabajo.

---

## Resumen en una línea

Motor determinista construido y probado contra el mercado real (~40% del proyecto).
Falta: capa de IA (la mesa de agentes), dashboard, calibración con mercado abierto, y material de
entrega.

---

## Qué funciona — probado en vivo contra la cadena real de Alpaca

| Componente | Detalle |
|---|---|
| `agent/broker.py` | Cliente REST de la Trading API: cuenta, órdenes, `mleg`, posiciones, cancelar. Probado. |
| `agent/marketdata.py` | Snapshots de la cadena (griegas + IV), contratos (open interest), barras diarias. Probado. |
| `agent/signal.py` | Señal completa: previsión de RV (Yang-Zhang + EWMA), VRP, GEX desde OI, régimen (ADX/EMA), skew → objeto `Signal`. Corre; **falta calibrar los umbrales**. |
| `agent/execution.py` | Selección de strikes (condor y vertical) al delta objetivo, sizing por riesgo, exit manager determinista (50% TP / 2× stop / cierre en expiración), log de trades. Corre; **el exit manager no se ha probado sobre una posición real**. |
| `agent/risk.py` | Risk Officer: todos los gates, sin discrecionalidad. `evaluate()` es la entrada única. Hecho. |
| `agent/calendar.py` | Calendario estático de eventos macro para el blackout (NFP, ISM...). Hecho; **verificar fechas/horas**. |
| `agent/desk.py` | Loop principal en `dry_run`: exits → gates → señal por subyacente → decisión de abrir → journal. Corre end-to-end. |
| `agent/journal.py` | Log de decisiones (`data/journal.jsonl`) + curva de equity + registro de predicciones. Hecho. |
| Probes Día 0 | Los 3 pasaron. Ver `../probes/RESULTS.md`. |
| Repo + CI skeleton | `.github/workflows/desk.yml` existe (cada 15 min, horario de mercado). **Secrets sin poner.** |

## Qué falta

| Tarea | Lane | Prioridad |
|---|---|---|
| Capa de IA: Quant ensemble (Featherless) + Bull / Bear / Desk Head + debate | A | Alta — es el diferenciador |
| Calibrar la señal con quotes de mercado abierto (lunes 31 ago) | A | Alta — bloquea el "en vivo" |
| Decidir modo adaptativo vs disciplina estricta | humano | Alta — bloquea calibración |
| Agregación de delta de cartera (ahora el gate usa 0) | A | Media |
| Probar el exit manager sobre una posición real (abrir condor mínimo, ver que cierra) | A | Alta antes de ir en vivo |
| Poner secrets en GitHub, activar el cron | A | Media |
| Dashboard "trading floor" (Next.js / Vercel) | B | Alta — segundo diferenciador |
| Registro de predicciones en el dashboard | B | Media |
| Reflexión nocturna (post-mortem + ajuste de parámetros) | A | Baja — primera en la lista de recortes |
| One-page write-up (`write-up.md`) | C | Alta — entregable obligatorio |
| Vídeo demo + slide deck + cover image | C | Alta — entregables obligatorios |
| Posts de redes (build in public), hasta 5 | C | Media — premio aparte |

---

## Decisiones cerradas

Fijadas por los probes de Día 0 (`../probes/RESULTS.md`). No revisar sin motivo.

- **Estructura:** iron condor como una sola orden `mleg` de 4 patas. Confirmado en paper.
- **Feed de datos de opciones:** `feed=indicative` (OPRA es de pago y no lo tenemos; indicative va ~2s fresco).
- **Griegas + IV:** de los snapshots de Alpaca. Sin motor de Black-Scholes propio.
- **Open interest:** solo en `/v2/options/contracts`, con retraso T-2. Vale para el GEX (régimen, aproximado).
- **DTE:** preferir 1–3 días. 0DTE solo con stops más anchos.
- **Transporte:** `httpx` + REST. El CLI de Alpaca se cablea como vía secundaria para cumplir el requisito "MCP o CLI".
- **Universo:** SPY, QQQ, IWM. Los tres tienen expiración diaria toda la semana.
- **Postura de riesgo:** núcleo consistente + sleeve satélite direccional (≤15% del presupuesto de riesgo).
- **Concepto:** IV Desk completo (VRP + GEX + mesa de agentes). Plan B documentado en `CONCEPT.md`.

## Decisiones abiertas

- **Modo adaptativo al régimen vs disciplina estricta.** A 28 ago la volatilidad está baja
  (IV ATM 6–10%) → la señal VRP pura no genera ningún trade. Recomendación: adaptativo — vender
  condors cuando el VRP es rico, comprar debit spreads direccionales baratos cuando el gamma es
  negativo y hay tendencia. Mantiene la disciplina y garantiza un historial de P&L (que es un eje
  del jurado). Decisión final + calibración de parámetros el lunes 31 con quotes reales.
- Parámetros a calibrar: `vrp_min`, `short_delta`, `min_credit_frac`, umbral de GEX.

---

## Datos clave

| | |
|---|---|
| Cuenta paper (submission) | `PA3TQHQKM5AD` — $100.000, opciones nivel 3, creada 28 ago 2026 |
| Repo | github.com/alvaarocl/iv-desk — **privado hasta el 4 sep**, luego público (obligatorio) |
| Cupón Featherless | `ALPACA26` — $25, redimir en featherless.ai |
| Fin de submissions | **4 sep 2026, 17:00 CEST** |
| Sesiones de mercado | 28, 31 ago · 1, 2, 3, 4 sep (6 días) |
| NFP | 4 sep, 8:30 ET / 14:30 España — último día, el blackout debe funcionar |
