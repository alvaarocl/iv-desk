# Referencia: API, CLI y feeds de Alpaca

Hallazgos duros verificados contra la API real. Es la página más reutilizable del repo: aquí van las convenciones que nos han costado tiempo descubrir, para no volver a descubrirlas.

Fuente original: `probes/RESULTS.md` (Día 0, 28 ago, cuenta `PA3TQHQKM5AD`), ampliado con la documentación oficial el 29 ago.

---

## Órdenes multi-pata (`order_class: mleg`)

### El `limit_price` va FIRMADO

**Esta es la convención que más caro sale equivocarse.**

| Signo | Significado |
|---|---|
| **Positivo** | **Débito** — es lo que estás dispuesto a **pagar** |
| **Negativo** | **Crédito** — es lo que quieres **cobrar** |

En el dashboard de Alpaca los créditos se muestran también como negativos ("Limit Price (Credit)").

Para un iron condor de crédito con crédito de mercado ~$1.20, la orden correcta es `limit_price: "-1.10"` (acepta cobrar al menos 1.10). Mandar `"1.10"` significa *"acepto pagar hasta 1.10"* — la orden se vuelve marketable al instante y pierdes todo el control de precio.

**Ojo con el probe del Día 0:** validó un condor *largo* (débito) a `limit_price: "0.01"`. No fue marketable, se quedó en `new`, se canceló limpio. Eso confirma la dirección de débito y **no dice nada de la de crédito**.

### Estructura de la petición

```json
POST /v2/orders
{
  "order_class": "mleg",
  "qty": "1",
  "type": "limit",
  "time_in_force": "day",
  "limit_price": "-1.10",
  "legs": [
    {"symbol": "SPY260903P00770000", "side": "sell", "ratio_qty": "1", "position_intent": "sell_to_open"},
    {"symbol": "SPY260903P00766000", "side": "buy",  "ratio_qty": "1", "position_intent": "buy_to_open"},
    {"symbol": "SPY260903C00780000", "side": "sell", "ratio_qty": "1", "position_intent": "sell_to_open"},
    {"symbol": "SPY260903C00784000", "side": "buy",  "ratio_qty": "1", "position_intent": "buy_to_open"}
  ]
}
```

- `position_intent`: `buy_to_open` · `buy_to_close` · `sell_to_open` · `sell_to_close`.
- **4 patas en una sola orden funcionan** en paper con nivel 3. Confirmado.
- Las 4 patas se llenan juntas o ninguna — evita fills parciales.
- Cerrar = las mismas patas con el lado invertido y `_open` → `_close`.

### Las órdenes son asíncronas

Palabras de Alpaca en su foro: *"All orders are simply 'requests'... Orders are executed asynchronously both in paper and certainly live trading."*

**El 200 confirma recepción, no ejecución.** Hay que consultar el estado (`GET /v2/orders`) antes de dar una posición por abierta. Ver el issue #3.

Enviar varias órdenes muy seguidas puede dar `insufficient qty available`; el workaround recomendado es esperar ~500ms entre envíos.

---

## Datos de opciones

### Snapshots de la cadena — griegas e IV gratis

```
GET /v1beta1/options/snapshots/{underlying}?feed=indicative&limit=1000
```

Devuelve por contrato: `greeks{delta,gamma,theta,vega,rho}`, `impliedVolatility`, `latestQuote`, `latestTrade`, `minuteBar`, `dailyBar`, `prevDailyBar`.

**Las griegas y la IV vienen de Alpaca. No hace falta un motor de Black-Scholes propio.**

- Una cadena completa de SPY para una expiración = **490 contratos en ~0.83 s**, una sola llamada.
- Paginación por `next_page_token`.

### Feeds

| Feed | Estado |
|---|---|
| `opra` | ❌ **Bloqueado** — *"OPRA agreement is not signed"*. Es el add-on de pago |
| `indicative` | ✅ El tier gratuito. **Frescura medida ~2 s** contra reloj de pared |

El retraso de 15 minutos del tier gratuito aplica **solo a datos históricos**. Las quotes más recientes son en tiempo real. `indicative` es suficiente para credit spreads de 0-4 DTE.

### Open interest — no está en el snapshot

Vive **solo** en `/v2/options/contracts` (y `/contracts/{symbol}`), campos `open_interest` + `open_interest_date`.

- Viene con retraso **T-2** (lag normal de la OCC). Al 28 ago los datos eran del 26 ago.
- ~60 de 62 strikes near-money tienen OI; valores reales (1k-58k cerca del dinero).
- **Consecuencia:** el GEX que calculamos es aproximado. Vale como señal de régimen, no como medida precisa. Ver el issue #10.

### Otros endpoints útiles

- Barras diarias del subyacente: `feed=sip` funciona (volumen completo). También `iex`.
- Barras históricas de opciones: `GET /v1beta1/options/bars` → sirve para el backtest-lite (issue #5).
- **VIX:** no está en `/v1beta1/indices/...`. Hay que usar la ATM IV de SPY/QQQ/IWM como proxy, o una fuente externa.

---

## El CLI (`alpacahq/cli`)

### Aviso: está en Alpha

Del README oficial:

> **Alpha Preview** — Commands, flags, and output formats may change or be removed without notice between releases. **Do not depend on current behavior in production workflows.**

**Pinead una versión concreta.** Descargar `releases/latest` en cada run del cron (26 veces al día) es pedir que un release a mitad de semana rompa el loop en silencio. Issue #8.

### No tiene flag multi-pata

`alpaca order submit` acepta `--symbol --side --qty --type --limit-price --dry-run --client-order-id`. **No documenta ningún flag para órdenes multi-pata.**

La ruta real para un condor es el escape hatch:

```bash
alpaca api POST /v2/orders --data '{"order_class":"mleg", ...}'
```

Reutiliza el body que ya está probado. Solo cambia el transporte, no la orden. Issue #4.

### Comandos que sí existen

```
Trading:      order · position · option · locate · clock · calendar
Cuenta:       account · asset · watchlist · wallet · corporate-action
Market data:  data · data option · data crypto · data screener · data news
Utilidades:   profile · api · doctor · update · version · completion
```

Opciones: `alpaca option contracts --underlying-symbol SPY`, `alpaca data option chain --underlying-symbol SPY`, `alpaca data option snapshot --symbol ...`.

Salida JSON por defecto, con `--csv`, `--jq`, `--quiet`, `--schema`.

### Autenticación en CI

```bash
export ALPACA_API_KEY=PK...
export ALPACA_SECRET_KEY=...
alpaca account get --quiet
```

Las claves por variable de entorno van a **paper por defecto**. `ALPACA_LIVE_TRADE=true` rutea a real: **no definirla nunca**, ni siquiera vacía.

Códigos de salida: `0` ok · `1` error de API · `2` error de autenticación.

### El CLI no tiene red de seguridad

> *"It is not an interactive trading terminal: there are no confirmation prompts... Every command executes immediately."*

`alpaca position close-all` liquida toda la cartera. `alpaca order cancel-all` cancela todo sin listar. Cuidado con lo que se mete en un script.

---

## Cuentas

| | |
|---|---|
| Testing | `PA3TQHQKM5AD` — $100.000, nivel 3. Órdenes de prueba canceladas. **Todo el desarrollo aquí** |
| Competición | `PA39HSCQE8S3` ("PAPER UC3M") — $100.000, nivel 3, intacta. **Primera orden: lun 31 ago 09:30 ET** |

- `options_trading_level: 3` → spreads y condors habilitados.
- `buying_power` $400.000 (4×), `options_buying_power` $100.000.
- **Cada cuenta paper tiene su propio par de claves.** Hay que generarlas tras cambiar de cuenta en el dashboard.
- Las claves de competición viven **solo** en los secrets de GitHub Actions.

---

## Universo

SPY · QQQ · IWM. Los tres tienen **expiración diaria** todas las sesiones de la ventana. Máxima liquidez, spreads estrechos, y sin riesgo de gap por resultados al ser índices.
