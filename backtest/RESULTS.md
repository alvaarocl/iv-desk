# Backtest — resultados (datos REALES)

Generado el **30 ago 2026** con:
```
uv run python -m backtest.replay --days 60 --symbols SPY,QQQ,IWM
```
sobre barras históricas reales de Alpaca (cuenta de testing `PA3TQHQKM5AD`), 60 sesiones,
`config.py` calibrado. Issues **#5 #6 #7 #10 #29 #30**.

> **Qué es y qué NO es.** Contesta la pregunta binaria del #5 (*¿la estrategia dispara?*), fija
> los umbrales de la señal con evidencia (#6, #7, #10), y da un P&L aproximado *held-to-expiry*
> (sin gestión de salidas — el exit manager no está en el replay). **No** es una previsión del
> resultado del hackathon: 4 sesiones son una lotería de varianza y esto son 60.
>
> Bug arreglado para poder correrlo (`backtest/replay.py:stock_bars`): pedía `feed=sip` con
> `end=hoy`, y el plan gratuito prohíbe SIP dentro de los últimos 15 min → 403. Cambiado a
> `feed=iex` (real-time en el plan gratis, suficiente para una estimación de RV).

---

## La respuesta al #5: la estrategia dispara, pero poco

| Config | Trades / 174 sesiones-subyacente | P&L aprox. held-to-expiry |
|---|---|---|
| **Pre-auditoría** (vrp abs 0.03, credit 0.33, width 4/2, fade on) | **0** | $0 — *nunca opera* |
| vrp 1.15 + gex 0.10 (primer intento post-auditoría) | 3 | −$35 |
| **Calibrada (actual)** — vrp **1.05**, gex **0.03**, credit 0.20, delta 0.18, width 2/1 | **11** | **+$484** |

Los pre-auditoría confirman lo que sospechábamos: el gate de crédito (`0.33 × width`) era
**geométricamente inalcanzable** (#7). Con IV al 6–10% a 1–3 DTE el `credit/width` real tiene
mediana **0.27** y máximo **0.36** — el suelo de 0.33 estaba por encima del techo de la estructura.
Apagar el VRP por completo no cambiaba nada: seguían saliendo **cero** trades por el crédito.

---

## Embudo — config calibrada

```
  IV/RV >= 1.05 | gex_norm >= 0.03 | credit/width >= 0.20 | delta 0.18 | width 2/1 | fade_trend False

 #  STAGE                                                  PASS  KILLED  OF ALL
 1  underlying-sessions evaluated                           174       0  100.0%
 2  chain + history usable                                  169       5   97.1%
 3  IV and RV_hat both measurable                           169       0   97.1%
 4  VRP rich      IV/RV_hat >= 1.05    [gate: vrp]           48     121   27.6%   <<< DIES HERE
 5  dealer gamma  gex_norm >= 0.03     [gate: gex]           16      32    9.2%
 6  tape not trending                  [gate: trend]         13       3    7.5%
 7  signal.sell_premium is True                              13       0    7.5%
 8  structure built (strikes found)                          11       2    6.3%
 9  credit gate   credit/width >= 0.20                        11       0    6.3%
10  sizing / delta / risk.evaluate()                          11       0    6.3%
13  TRADES OPENED                                             11       0    6.3%

    ATM IV       median 16.6%  p90 26.5%
    RV_hat       median 16.6%  p90 26.8%
    IV/RV_hat    median  0.90  p90  1.27  max 1.83     (threshold 1.05)
    gex_norm     median -0.02  p90 +0.20               (threshold 0.03)
    credit/width median  0.27  p90  0.34  max 0.36     (threshold 0.20)
    approx P&L held-to-expiry: +$484 over 11 trades / 174 underlying-sessions
```

**El VRP es el gate letal, y es delgado de verdad.** La mediana de IV/RV_hat es **0.90** — la
implícita corta está, la mitad de los días, *por debajo* de la realizada. Solo un cuarto de las
sesiones tienen la prima que buscamos. Esto **no** es un artefacto de medición (los bugs de #26 y
del gap overnight en `yang_zhang` ya están arreglados): es el mercado de 2026, vol baja.

---

## Los 11 trades

```
DAY         SYM  STRUCTURE      CREDIT  W  N   CR/W  IV/RV   PNL $
2026-06-05  QQQ  iron_condor      0.46  2  3  0.230  1.76     123
2026-06-05  SPY  iron_condor      0.54  2  3  0.270  1.83     162
2026-06-09  IWM  iron_condor      0.31  1  7  0.310  1.26     217
2026-06-09  QQQ  iron_condor      0.51  2  3  0.255  1.27     153
2026-06-09  SPY  iron_condor      0.51  2  3  0.255  1.31    -447
2026-06-11  IWM  iron_condor      0.34  1  7  0.340  1.19     238
2026-06-11  SPY  iron_condor      0.58  2  3  0.290  1.27     174
2026-06-12  IWM  iron_condor      0.27  1  6  0.270  1.05     162
2026-07-28  IWM  iron_condor      0.36  1  7  0.360  1.71      -7
2026-07-28  SPY  iron_condor      0.61  2  3  0.305  1.36    -417
2026-08-27  SPY  iron_condor      0.42  2  3  0.210  1.11     126
```

**8 ganadores, 3 perdedores. Los 3 perdedores son grandes** (−$447, −$417, −$7): un movimiento
grande atraviesa un ala. Es el perfil de pago clásico de vender primas — *"gano poco a menudo,
pierdo mucho de vez en cuando"*. El exit manager (stop a 2× crédito, no en el replay) recortaría
esas colas, así que el P&L real debería ser algo mejor que el held-to-expiry de +$484.

Nota: los trades se agrupan en junio y luego se secan. Julio–agosto solo dio 3 señales en 40
sesiones. **En la ventana real (lun 31 – jue 3) esperamos ~2–4 trades**, y podrían ser 0.

---

## Calibración — de dónde salen los números

De la rejilla de sensibilidad (17 variantes sobre las mismas 60 sesiones — **cuidado con
sobreajustar**, por eso solo se movieron 2 parámetros hacia inflexiones reales, no hacia el P&L
máximo):

| Cambio vs actual | Trades | P&L $ | Lectura |
|---|---|---|---|
| `vrp_ratio_min` 1.05 → 1.30 | 5 | **−586** | demasiado restrictivo mata los buenos |
| `vrp_ratio_min` 1.05 → 1.00 (off) | 13 | +117 | los trades entre 1.00 y 1.05 son **perdedores netos** → 1.05 es una inflexión real |
| `gex_min` 0.03 → 0.30 | 0 | 0 | el gate de magnitud fuerte mata todo |
| `gex_min` 0.03 → 0.00 (solo signo) | 11 | +484 | idéntico a 0.03 en estas 60 sesiones → 0.03 es un filtro de zona muerta que aquí no llegó a morder |
| `short_delta` 0.18 → 0.25 | 11 | **−368** | cortos más cerca del dinero = más riesgo por trade, peor |
| `width` 2/1 → 4/2 | 7 | +484 | alas anchas también funcionan, menos trades |
| `min_credit_frac` 0.20 → 0.10 | 11 | +484 | no muerde (mediana real 0.27) |
| **ALL GATES OFF** | 78 | +401 | el edge bruto es positivo pero **delgado** |

**Decisión (#30):**
- `vrp_ratio_min` 1.15 → **1.05** — inflexión clara en la rejilla; sigue muy por encima de la
  mediana 0.90.
- `gex_min` 0.10 → **0.03** — el 0.10 costaba 6 de 11 supervivientes del VRP sin ganancia de P&L.
  0.03 mantiene el filtro de flip-flop cerca de cero (la queja real de #10) sin el umbral caro.
- `min_credit_frac`, `short_delta`, `width` — **sin tocar**. La rejilla no da motivo y moverlos
  añade riesgo o resta trades.

---

## Qué significa para la entrega

**Esto es un proyecto de rama B: "una mesa que sabe cuándo NO operar".** El 94% de las sesiones
son stand-down documentado. El eje de P&L no se gana en 4 días con este edge — y forzarlo (bajar
el VRP a 1.00) *empeora* el P&L. La submission se sostiene en los otros 3 ejes (75%):

- **la disciplina es demostrable** — el log de `rejected` / `stand_down` con motivo es el exhibit;
- **el debate de la mesa** sobre los 2–4 trades reales, con tesis falsable calificada;
- **la robustez del workflow** — guardarraíl de cuenta, reconcile, kill switch, blackout asimétrico.

`docs/write-up.md` ya está escrito en esa línea. Confirmar con el equipo antes del lunes.
