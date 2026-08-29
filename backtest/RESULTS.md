# Backtest — resultados

> ⚠️ **Esto es tape SINTÉTICO, no mercado real.** Vale para responder a la pregunta binaria del
> issue #5 (*¿la estrategia dispara alguna vez?*) y para demostrar el argumento geométrico del #7.
> **No vale para calibrar** `vrp_ratio_min`, `gex_min` ni los anchos, y el P&L que aparece abajo no
> es una previsión de nada.
>
> La corrida real la cubre el **issue #29** y necesita `.env` con claves de Alpaca:
> ```
> uv run python -m backtest.replay --days 60 --symbols SPY,QQQ,IWM
> ```
> Cuando exista, **este fichero se reemplaza** con la salida real.

Generado con `uv run python -m backtest.replay --synthetic` sobre el `config.py` de la rama
`lane/senal-finde` (mesa Featherless, blackout asimétrico).

---

## Lo que contesta

**Con los parámetros previos a la auditoría, el desk no abría ni una sola posición en 180
sesiones-subyacente.** El gate de crédito era el letal y era *independientemente* fatal: apagando
el VRP por completo los candidatos se triplicaban y seguían saliendo **cero** trades. El
`credit/width` observado tenía mediana 0.240 y máximo 0.310 contra un umbral de 0.33 — el suelo
estaba por encima del techo geométrico de la estructura.

Con la configuración actual dispara. El embudo completo:

---

```
synthetic tape: 60 sessions x 3 underlyings, seed 7, vol 9%, IV/RV 1.12, spike True
  CAVEAT: on a synthetic tape `gex_norm` is ~ --gex-bias by construction, so the GEX row
  is circular and says nothing about the real market. The VRP, credit and sizing rows do not
  depend on that assumption. Re-run without --synthetic before calibrating gex_min.

====================================================================================
FUNNEL — CURRENT config.py
  IV/RV >= 1.15 | gex_norm >= 0.10 | credit/width >= 0.20 | delta 0.18 | width 2/1 | fade_trend False
====================================================================================
 #  STAGE                                                  PASS  KILLED  OF ALL
------------------------------------------------------------------------------------
 1  underlying-sessions evaluated                           180       0  100.0%
 2  chain + history usable (>=8 contracts, >=25 bars)       180       0  100.0%
 3  IV and RV_hat both measurable      [gate: data]         180       0  100.0%
 4  VRP rich      IV/RV_hat >= ratio   [gate: vrp]           65     115   36.1%   <<< DIES HERE
 5  dealer gamma  gex_norm >= gex_min  [gate: gex]           65       0   36.1%
 6  tape not trending                  [gate: trend]         57       8   31.7%
 7  signal.sell_premium is True                              57       0   31.7%
 8  structure built (strikes found)                          47      10   26.1%
 9  credit gate   credit/width >= min_credit_frac            42       5   23.3%
10  sizing gate   >= 1 contract                              42       0   23.3%
11  leg deltas available                                     42       0   23.3%
12  risk.evaluate() == ok                                    42       0   23.3%
13  TRADES OPENED                                            42       0   23.3%
------------------------------------------------------------------------------------
    ATM IV        median  13.73%  p90  20.05%
    RV_hat        median  12.53%  p90  16.04%
    IV/RV_hat     median    1.08  p90    1.44  max    4.51   (threshold 1.15)
    IV-RV_hat     median +0.0081  p90 +0.0552  max +0.3842   (legacy threshold +0.0300)
    gex_norm      median  +0.176  p90  +0.215   (threshold +0.10)
    credit/width  median   0.285  p90   0.312  max   0.340   (threshold 0.200)
    structures  : iron_condor=47
    approx P&L held-to-expiry: $1,863 over 42 trades / 180 underlying-sessions

DAY         SYM  STRUCTURE             CREDIT    W   N   CR/W  IV/RV    PNL $
------------------------------------------------------------------------------
2026-06-04  QQQ  iron_condor             0.57    2   3  0.285   1.44      171
2026-06-05  QQQ  iron_condor             0.59    2   3  0.295   1.21      177
2026-06-08  QQQ  iron_condor             0.59    2   3  0.295   1.58     -423
2026-06-09  QQQ  iron_condor             0.57    2   3  0.285   1.24     -429
2026-06-24  IWM  iron_condor             0.34    1   7  0.340   4.50      238
2026-06-24  SPY  iron_condor             0.62    2   3  0.310   3.79      186
2026-06-25  IWM  iron_condor             0.31    1   7  0.310   3.26      217
2026-06-25  QQQ  iron_condor             0.63    2   3  0.315   2.55     -411
2026-06-25  SPY  iron_condor             0.58    2   3  0.290   3.08     -426
2026-06-26  IWM  iron_condor             0.30    1   7  0.300   2.89      210
2026-06-26  QQQ  iron_condor             0.56    2   3  0.280   1.55      168
2026-06-26  SPY  iron_condor             0.61    2   3  0.305   1.58      183
... and 30 more


====================================================================================
FUNNEL — LEGACY pre-audit params (issue #5)
  IV-RV >= 0.030 (legacy absolute) | gex_norm >= 0.00 | credit/width >= 0.33 | delta 0.18 | width 4/2 | fade_trend True
====================================================================================
 #  STAGE                                                  PASS  KILLED  OF ALL
------------------------------------------------------------------------------------
 1  underlying-sessions evaluated                           180       0  100.0%
 2  chain + history usable (>=8 contracts, >=25 bars)       180       0  100.0%
 3  IV and RV_hat both measurable      [gate: data]         180       0  100.0%
 4  VRP rich      IV/RV_hat >= ratio   [gate: vrp]           41     139   22.8%   <<< DIES HERE
 5  dealer gamma  gex_norm >= gex_min  [gate: gex]           41       0   22.8%
 6  tape not trending                  [gate: trend]         41       0   22.8%
 7  signal.sell_premium is True                              41       0   22.8%
 8  structure built (strikes found)                          34       7   18.9%
 9  credit gate   credit/width >= min_credit_frac             1      33    0.6%
10  sizing gate   >= 1 contract                               1       0    0.6%
11  leg deltas available                                      1       0    0.6%
12  risk.evaluate() == ok                                     1       0    0.6%
13  TRADES OPENED                                             1       0    0.6%
------------------------------------------------------------------------------------
    ATM IV        median  13.73%  p90  20.05%
    RV_hat        median  12.53%  p90  16.04%
    IV/RV_hat     median    1.08  p90    1.44  max    4.51   (threshold 1.15)
    IV-RV_hat     median +0.0081  p90 +0.0552  max +0.3842   (legacy threshold +0.0300)
    gex_norm      median  +0.176  p90  +0.215   (threshold +0.00)
    credit/width  median   0.244  p90   0.285  max   0.330   (threshold 0.330)
    structures  : iron_condor=33, call_credit_spread=1
    approx P&L held-to-expiry: $231 over 1 trades / 180 underlying-sessions

====================================================================================================
PARAMETER SENSITIVITY — survivors at each gate under other thresholds
====================================================================================================
VARIANT                                    VRP   GEX  TREND  STRUCT  CREDIT  SIZE  RISK  TRADES    P&L $
----------------------------------------------------------------------------------------------------
CURRENT config.py                           65    65     57      47      42    42    42      42    1,863
LEGACY pre-audit (issue #5 question)        41    41     41      34       1     1     1       1      231
LEGACY but credit 0.33 -> 0.20              41    41     41      34      30    30    30      30      978
LEGACY but width 4/2 -> 2/1                 41    41     41      34       2     2     2       2      469
LEGACY but vrp 0.03 -> 0.00                120   120    120      84       1     1     1       1      231
LEGACY, credit 0.20 AND width 2/1           41    41     41      34      32    32    32      32    1,609
vrp_ratio_min 1.15 -> 1.30                  32    32     31      28      27    27    27      27    1,516
vrp_ratio_min 1.15 -> 1.05                 100    99     86      63      55    55    55      55    2,522
vrp_ratio_min 1.15 -> 1.00 (off)           120   119     98      71      62    62    62      62    3,226
gex_min 0.10 -> 0.30                        65     0      0       0       0     0     0       0        0
gex_min 0.10 -> 0.00 (bare sign)            65    65     57      47      42    42    42      42    1,863
min_credit_frac 0.20 -> 0.30                65    65     57      47      13    13    13      13    1,533
min_credit_frac 0.20 -> 0.10                65    65     57      47      47    47    47      47    1,559
short_delta 0.18 -> 0.25                    65    65     57      55      55    55    55      55    2,934
width 2/1 -> 4/2 (wider wings)              65    65     57      47      38    38    38      38    1,172
fade_trend True (legacy #12)                65    65     65      50      42    42    42      42    1,863
ALL GATES OFF (upper bound)                180   180    142     101     101   101   101     101    4,301
----------------------------------------------------------------------------------------------------
Columns are survivors AT that gate (cumulative), not deaths. TRADES answers issue #5.

====================================================================================
VERDICT
  pre-audit params : 1 trades over 180 underlying-sessions
  current params   : 42 trades, approx P&L $1,863
====================================================================================
```

---

## Cómo leer esto

Las columnas son **supervivientes acumulados en ese gate**, no muertes. La fila `TRADES OPENED` es
la respuesta al #5.

## Avisos para la calibración (#30)

- **La fila del GEX es circular en sintético.** `gex_norm ≈ --gex-bias` por construcción. No
  toques `gex_min` con este número: necesita la corrida real.
- **`gex_min = 0.10` tiene muy poco margen.** Subirlo a 0.30 devuelve el desk a cero trades.
- **`min_credit_frac = 0.20` no está mordiendo** ahora mismo (0.20 y 0.10 dan lo mismo), pero 0.30
  baja los trades drásticamente. Está bien colocado justo por debajo de la distribución.
- El rebuild de la cadena usa el cierre como mid, que es optimista frente a un bid/ask real: el
  gate de crédito sale **favorecido**. Aun así mataba todo con los parámetros viejos.
- **La medición de VRP del smoke run de `lane/ejecucion`** (`rv_hat` 15-27% contra IV 8-12%) se
  hizo con dos bugs activos que ya están arreglados (#26 y el `yang_zhang` que duplicaba el gap
  overnight). **No sirve para calibrar.** Hay que volver a medir.
