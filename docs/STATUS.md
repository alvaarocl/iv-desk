# Estado del proyecto

Última actualización: **29 ago 2026**. Este archivo se actualiza a mano según avanza el trabajo.

---

## Reglas oficiales (guidelines de Alpaca, recibidas 29 ago)

Datos del concurso verificados en [`REGLAS-HACKATHON.md`](REGLAS-HACKATHON.md). Todas las fechas con
hora CEST y ET en [`CALENDARIO.md`](CALENDARIO.md).

- **Criterios de jurado: CUATRO** — P&L Performance · Technology Implementation · Creativity &
  Originality · Presentation & Execution (~25% cada uno). **Social Engagement es un premio aparte**,
  no un eje del rubro → el P&L pesa **~25%, no ~20%**.
- **Premio: $5.000** (1º $2.500 · 2º $1.500 · 3º $1.000). Algunas fuentes dicen $6.000 contando dos
  premios sociales de $500. **No usar la cifra de $6.300 que arrastraba `CLAUDE.md`.**
- **Ventana de scoring de P&L:** lunes **31 ago 9:30 ET (15:30 CEST) → snapshot de equity a cierre del
  jueves 3 sep (22:00 CEST)**. Cuentan 4 sesiones: lun 31, mar 1, mié 2, jue 3.
  **El viernes 4 NO cuenta para P&L.**
  > ⚠️ **PENDIENTE: confirmar en Discord.** Esto viene de las guidelines privadas y **no es
  > verificable públicamente**. Toda la política de expiraciones (≤ 3 sep) depende de ello.
  > No cambiarlo sin confirmar. → issue #19
- Se juzga por **equity total de la cuenta** (no caja) + creatividad, autonomía y robustez del workflow.
  No hay Sharpe/Sortino/drawdown como métrica, solo equity. Sin scoreboard en vivo.
- **La UI NO es obligatoria.** *"We are primarily evaluating the autonomous agent workflow and its
  trading performance."* → el dashboard pasa a **opcional**.
- El agente debe **empezar a operar el lunes 31 a las 9:30 ET desde la cuenta de competición**.
  Nada anterior cuenta. Los trades en la cuenta de testing no puntúan.
- **Cuenta nueva obligatoria** para la submission ($100k). La de testing no se puede usar para el
  P&L oficial. Se puede crear otra con el mismo email.
- **Transporte:** vale MCP o CLI; alpaca-py vale "para gestionar el loop en tu propio código";
  si usas un SDK, prioriza los oficiales. → decisión: **rutar la ejecución por el CLI de Alpaca**.
- El MCP oficial de Alpaca soporta opciones (contratos, chains, quotes, griegas, órdenes single y
  multi-leg). Las quotes más recientes del feed gratis SON en tiempo real (el retraso de 15 min es
  solo histórico).
- **Trabajo pre-evento permitido pero hay que declararlo** en el README.
- Repo puede seguir privado durante el hackathon.
- **Consecuencia clave:** las operaciones de competición usan **expiraciones ≤ 3 sep**. El libro
  debe estar resuelto o bien marcado a cierre del jueves 3.

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
| **Cambiar `execution.py` para colocar órdenes vía CLI de Alpaca** (no REST) | A | Alta — requisito de las reglas |
| Crear cuenta paper NUEVA para competición, no tocarla hasta el lunes 9:30 ET | humano | Alta — bloquea el "en vivo" |
| Capa de IA: Quant ensemble (Featherless) + Bull / Bear / Desk Head + debate | A | Alta — es el diferenciador |
| Calibrar la señal con la cadena del cierre del viernes | A | Alta — bloquea el "en vivo" |
| Decidir modo adaptativo vs disciplina estricta | humano | Alta — bloquea calibración |
| Agregación de delta de cartera (ahora el gate usa 0) | A | Media |
| Probar el exit manager sobre una posición real en la cuenta de TESTING | A | Alta antes de ir en vivo |
| Poner secrets en GitHub (keys de la cuenta de COMPETICIÓN), activar el cron | A | Media |
| Disclosure de trabajo pre-evento en el README | C | Alta — requisito |
| Reflexión nocturna (post-mortem + ajuste de parámetros) | A | Baja — lista de recortes |
| Dashboard "trading floor" (Next.js / Vercel) | B | **Opcional** — UI no obligatoria; solo si sobra tiempo |
| One-page write-up (`write-up.md`) — **se escribe desde el código, no desde el plan** (#18) | C | Alta — entregable obligatorio |
| Runbook y calendario operativos (`RUNBOOK.md`, `CALENDARIO.md`) | C | ✅ hechos — leerlos los dos antes del lunes |
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
- **Transporte:** ~~`httpx` + REST~~ → **CLI de Alpaca para la ejecución de órdenes** (las reglas piden
  MCP o CLI). REST/`httpx` se mantiene solo para lecturas de market data. *(cambiado 29 ago tras las guidelines)*
- **Universo:** SPY, QQQ, IWM. Los tres tienen expiración diaria toda la semana.
- **Postura de riesgo:** núcleo consistente + sleeve satélite direccional (≤15% del presupuesto de riesgo).
- **Concepto:** IV Desk completo (VRP + GEX + mesa de agentes). Plan B documentado en `CONCEPT.md`.
- **Expiraciones de competición:** ≤ 3 sep (snapshot de equity a cierre del jueves 3).
- **Cuenta:** `PA3TQHQKM5AD` = testing. Cuenta de competición = nueva, creada el finde, intacta hasta el lunes.

## Decisiones abiertas

- **Modo adaptativo al régimen vs disciplina estricta.** A 28 ago la volatilidad está baja
  (IV ATM 6–10%) → la señal VRP pura no genera ningún trade. Recomendación: adaptativo — vender
  condors cuando el VRP es rico, comprar debit spreads direccionales baratos cuando el gamma es
  negativo y hay tendencia. Mantiene la disciplina y garantiza un historial de P&L (que es un eje
  del jurado). Decisión final + calibración de parámetros el lunes 31 con quotes reales.
- Parámetros a calibrar con el backtest (#5): `vrp_ratio_min`, `gex_min`, `short_delta`,
  `min_credit_frac` y el ancho de las alas. `vrp_min` (umbral absoluto) ya no existe: sustituido
  por un ratio IV/RV el 29 ago (#6).

---

## Datos clave

| | |
|---|---|
| Cuenta de **testing** | "Paper Trading" `PA3TQHQKM5AD` — $100.000, nivel 3. Tiene órdenes de prueba (canceladas). **Todo el desarrollo va aquí.** |
| Cuenta de **competición** | "PAPER UC3M" `PA39HSCQE8S3` — $100.000, nivel 3, intacta. **Primera orden: lun 31 ago 9:30 ET. No tocar antes.** Sus API keys van solo en los secrets de GitHub. |
| Repo | github.com/alvaarocl/iv-desk — **privado hasta el 4 sep**, luego público (obligatorio) |
| Cupón Featherless | `ALPACA26` — $25, redimir en featherless.ai |
| Ventana de P&L | **lun 31 ago 9:30 ET / 15:30 CEST → snapshot equity cierre jue 3 sep 16:00 ET / 22:00 CEST** (4 sesiones: 31, 1, 2, 3) — ⚠️ pendiente de confirmar en Discord (#19) |
| Fin de submissions (lablab) | **4 sep 2026, 15:00 UTC = 17:00 CEST = 11:00 ET** |
| Expiraciones de competición | ≤ 3 sep |
| Premio | **$5.000** (1º $2.500 · 2º $1.500 · 3º $1.000) |
| Criterios de jurado | **4**, ~25% cada uno. Social Engagement es premio aparte |
