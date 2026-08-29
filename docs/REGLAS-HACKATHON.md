# Reglas del hackathon

Verificado el **29 ago 2026** contra las fuentes públicas del evento. Lo que viene de las guidelines privadas de Alpaca está marcado como tal.

---

## Requisitos obligatorios

| Requisito | Nuestro estado |
|---|---|
| Usar la **Trading API** de Alpaca **y además el MCP server o el CLI** | ❌ **INCUMPLE.** `broker.py` es `httpx` + REST puro. El CLI se instala en `.github/workflows/desk.yml` y **no se usa jamás**. El MCP no existe. → issue #4 |
| La estrategia debe incorporar **opciones** | ✅ Es lo único que hace |
| **Cuenta paper nueva y dedicada** para la submission | ✅ `PA39HSCQE8S3`, intacta. Testing separado en `PA3TQHQKM5AD` |
| Python + GitHub | ✅ |
| Todo en **paper trading**, nada de dinero real | ✅ |
| Edad 18+, cualquier país | ✅ |

**Este es el riesgo número uno del proyecto** y no es una mejora opcional: sin CLI ni MCP, la entrega podría no ser elegible por muy bueno que sea el resto.

---

## Criterios de jurado: son CUATRO

1. **P&L Performance**
2. **Technology Implementation**
3. **Creativity & Originality**
4. **Presentation & Execution**

### Corrección importante a `docs/CONCEPT.md`

Nuestro `CONCEPT.md` monta una tabla de **cinco** criterios al ~20% metiendo **Social Engagement**. Eso es incorrecto: el social es un **premio aparte**, no un eje del rubro.

**Consecuencia práctica:** el P&L pesa **~25%, no ~20%**. Este documento **decía** *"Cedemos este"*; corregido el 29 ago. Ceder un cuarto del rubro sería defendible si a cambio el motor no pudiera perder dinero — pero con la configuración actual cedemos el upside y conservamos todo el downside. Ver [`VIABILIDAD.md`](VIABILIDAD.md) y el issue #16.

---

## Premio

La ficha del evento da **$5.000**: 1º $2.500 · 2º $1.500 · 3º $1.000. Otras fuentes mencionan $6.000 (probablemente $5.000 + 2 premios sociales de $500).

`CLAUDE.md` dice **$6.300**, que no coincide con ninguna fuente. **Corregir antes de que el número aparezca en el write-up o en un post.** → issue #19

---

## Fechas

| Qué | Cuándo | Fuente |
|---|---|---|
| Evento | 28 ago – 4 sep 2026 | Pública |
| **Deadline de submission** | **vie 4 sep, 15:00 UTC** (17:00 CEST) | Pública |
| **Ventana de P&L** | lun 31 ago 09:30 ET → **vie 4 sep 09:30 ET** | ✅ Confirmado en Discord |
| **Snapshot de equity** | **cierre del jueves 3 sep** (close of business) | ✅ Confirmado en Discord |
| Sesiones que cuentan | lun 31 · mar 1 · mié 2 · jue 3 = **4 sesiones** | ✅ |

### Confirmado en Discord (29 ago)

Cita literal de la respuesta:

> *"The official P&L scoring window is from Monday, August 31 at 9:30 a.m. ET to Friday,
> September 4 at 9:30 a.m. ET. The total equity snapshot will be taken at the close of business
> on Thursday, September 3. Positions expiring on Friday, September 4 are indeed excluded from
> this measurement."*

**Consecuencia (sin cambios respecto a lo que asumíamos):** el número que cuenta es la equity a
cierre del **jueves 3**. Las **operaciones de competición usan expiraciones ≤ 3 sep** — nada que
expire el viernes 4, porque ya no entra en la medición. El viernes por la mañana no hay snapshot;
es día de entrega, no de trading.

### Verificado por nuestra parte

- **Lun 31 ago es sesión hábil.** El Labor Day 2026 cae el **lun 7 sep**, después del hackathon. No hay festivo dentro de la ventana.
- Días de la semana: 31 ago lunes · 1 sep martes · 3 sep jueves · 4 sep viernes.

---

## Otras reglas relevantes

- **Trabajo pre-evento permitido, pero hay que declararlo en el README.** ✅ Ya está hecho y es correcto.
- El repo puede seguir **privado durante el hackathon**; público en la submission. Flipar el **4 sep, no antes**. → issue #21
- Se juzga por **equity total de la cuenta**, no por caja. No hay Sharpe, Sortino ni drawdown como métrica.
- No hay scoreboard en vivo.
- El feed gratuito da **quotes de opciones en tiempo real**; el retraso de 15 min aplica solo a datos históricos.

---

## Qué recomienda la propia Alpaca

En su artículo [Building a Multi-Agent AI Trading System on Alpaca](https://alpaca.markets/learn/building-a-multi-agent-ai-trading-system-on-alpaca), Alpaca describe la arquitectura que considera buena práctica:

- Agentes **especializados** en vez de un LLM generalista — *"One LLM with a broad prompt mixes momentum logic with macro logic. Signals dilute."*
- Un agente **crítico** que valida contra reglas predefinidas.
- Un **risk guard determinista en Python, sin LLM**.
- Monitorización de posiciones **cada 15 minutos**.

**Nuestra arquitectura coincide casi punto por punto.** Eso es un argumento fuerte para el eje de Technology Implementation y merece una frase explícita en el write-up.

---

## Fuentes

- [Alpaca AI Trading Agents Hackathon — lablab.ai](https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon)
- [Ficha del evento con premios y criterios](https://hiretoday.in/competitiondetails/40000151)
- [Building a Multi-Agent AI Trading System on Alpaca](https://alpaca.markets/learn/building-a-multi-agent-ai-trading-system-on-alpaca)
