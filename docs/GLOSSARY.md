# Glosario — todos los términos, sin dar nada por sabido

Para leer junto con [`CONCEPT.md`](CONCEPT.md). Si un término del código o de las conversaciones no
aparece aquí, pídelo y se añade.

---

## Lo básico

**Acción (stock)**
Un trozo de una empresa. Compras a $100, si sube a $110 ganas $10.

**ETF**
Un fondo que agrupa muchas acciones. En vez de comprar 500 empresas, compras una sola cosa que las
contiene todas.
- **SPY** = las 500 grandes empresas de EEUU (índice S&P 500)
- **QQQ** = las 100 tecnológicas (índice Nasdaq-100)
- **IWM** = 2000 empresas pequeñas (índice Russell 2000)

Estos 3 son los que más se negocian en opciones → los spreads son estrechos y baratos de operar.
Por eso son nuestro universo.

**Subyacente (underlying)**
El activo sobre el que va una apuesta. El subyacente de "una opción de SPY" es SPY.

**Índice (index)**
Una media de un grupo de acciones. El S&P 500 es un número que resume cómo van las 500 grandes.
No se compra directamente; se compra el ETF que lo replica (SPY).

**Paper trading**
Trading con dinero de mentira pero con precios reales de mercado. No arriesgas nada real.
Todo el hackathon se hace así. Nuestra cuenta: `PA3TQHQKM5AD`, con $100.000 simulados.

**P&L (profit and loss)**
Cuánto ganas o pierdes. "P&L de +$1.200" = has ganado 1.200.

**Líquido / liquidez (liquid / liquidity)**
Un activo es líquido si hay mucha gente comprando y vendiendo → puedes entrar y salir sin mover el
precio y sin pagar de más. SPY es muy líquido. Una opción rara de una empresa pequeña, no.

**Spread bid-ask (horquilla)**
La diferencia entre el precio al que puedes comprar (ask) y al que puedes vender (bid) ahora mismo.
Horquilla estrecha = barato operar. Ancha = caro.

---

## Opciones

**Opción (option)**
Un contrato que te da el **derecho** (no la obligación) de comprar o vender una acción a un precio
fijo antes de una fecha. Es como una "reserva" o un "seguro".

**Call**
Derecho a **comprar** a un precio fijo. Lo compras si crees que la acción va a **subir**.

**Put**
Derecho a **vender** a un precio fijo. Lo compras si crees que la acción va a **bajar**.

**Strike (precio de ejercicio)**
El precio fijo del contrato. "Call de SPY strike 780" = derecho a comprar SPY a 780,
da igual a cuánto esté SPY de verdad.

**Expiración (expiration)**
La fecha en que el contrato caduca. Después ya no vale nada, o se ejecuta automáticamente si tiene
valor. Las opciones de SPY/QQQ/IWM tienen expiración **cada día de mercado**.

**DTE (days to expiration, días hasta expiración)**
Cuántos días faltan para que caduque.
- **0DTE** = caduca hoy mismo. Muy sensible, se mueve mucho en horas.
- **1-3DTE** = caduca en 1 a 3 días. Lo que usamos nosotros: suficiente theta, menos locura.

**Prima (premium)**
El precio de la opción.
- Si **compras** una opción → **pagas** la prima.
- Si **vendes** una opción → **cobras** la prima por adelantado.

**"En dinero" / ITM (in the money)**
Cuando la opción tiene valor real si se ejerciera ahora. Un call strike 100 con la acción a 110
está "en dinero" por 10.

**"Fuera de dinero" / OTM (out of the money)**
Cuando la opción no tiene valor de ejercicio. Un call strike 120 con la acción a 110 está "fuera".
Nosotros **vendemos opciones OTM** — apostamos a que se quedan fuera y caducan sin valor.

**Asignación (assignment)**
Cuando eres el que vendió una opción y el comprador la ejerce → estás obligado a comprar o vender
las acciones. Se evita cerrando la posición antes de la expiración si está "en dinero".

**Multi-leg / mleg (varias patas)**
Una orden que combina varias opciones a la vez como una sola operación. Un iron condor son 4 patas
en una orden. Alpaca lo soporta con `order_class: "mleg"`.

---

## Vender prima — nuestra estrategia base

**Vender prima (selling premium / short options)**
En vez de comprar opciones, las vendes. Cobras dinero por adelantado y te lo quedas si la opción
caduca sin valor (o sea, si el que te la compró se equivocó de dirección o de magnitud).

**Eres la casa de apuestas, no el apostante.** Ganas muchas veces poco, pierdes pocas veces más.
El truco está en poner bien los precios y controlar el riesgo para que el balance sea positivo.

**Theta / decaimiento temporal (time decay)**
Cuánto valor pierde una opción **cada día que pasa**, solo porque queda menos tiempo.
El que **vende** prima **gana theta** todos los días. Es nuestro motor de ingresos:
literalmente cobramos por el paso del tiempo.

**Riesgo definido (defined risk)**
Cuando sabes de antemano exactamente cuánto puedes perder como máximo. Todas nuestras operaciones
son de riesgo definido — nunca una pérdida "infinita".

---

## Estructuras (combinaciones de opciones)

**Spread (diferencial)**
Combinar dos o más opciones para limitar el riesgo.

**Credit spread (diferencial de crédito)**
Vendes una opción y **compras otra más lejana como seguro**. Cobras la diferencia (el "crédito").
Tu pérdida máxima = (distancia entre strikes − crédito cobrado). Limitada y conocida.
- **Put credit spread**: cobras apostando a que la acción **no baja** por debajo de cierto nivel.
- **Call credit spread**: cobras apostando a que **no sube** por encima de cierto nivel.

**Iron condor**
Un put credit spread + un call credit spread a la vez. Cobras prima por **los dos lados**,
apostando a que la acción **se queda en un rango** hasta la expiración. Son 4 opciones.
Es nuestra estructura principal. Ejemplo: SPY a 774 → vendemos el condor 760/765 – 785/790,
cobramos ~$120, ganamos si SPY cierra entre 765 y 785.

**Debit spread (diferencial de débito)**
Lo contrario del credit spread: **pagas** para apostar una dirección concreta, con pérdida limitada.
Se usa cuando esperas un movimiento fuerte. Nosotros lo usamos como "satélite" cuando el mercado
tiene tendencia clara y vender prima sería mala idea.

**Width / anchura (del spread)**
La distancia entre los dos strikes de un spread. Un condor "de $5 de ancho" tiene los strikes
separados $5. Más ancho = más crédito pero más riesgo.

---

## Volatilidad — el corazón de la señal

**Volatilidad (volatility)**
Cuánto se mueve el precio de un activo. Movimientos grandes = volatilidad alta.
Mercado plano y aburrido = volatilidad baja.

**IV — volatilidad implícita (implied volatility)**
Cuánto movimiento **espera el mercado** de aquí a la expiración, deducido de lo caras que están las
opciones. Opciones caras → IV alta → el mercado tiene miedo o incertidumbre.
Se mide en % anualizado (ej. "IV del 12%").

**RV — volatilidad realizada (realized volatility)**
Cuánto se movió el precio **de verdad**, calculado mirando el historial reciente.
También en % anualizado.

**RV forecast / previsión de RV**
Nuestra estimación de cuánta RV va a haber en los próximos días, calculada con dos métodos
estadísticos (Yang-Zhang y EWMA) mezclados. Es la "verdad esperada" contra la que comparamos la IV.

**VRP — prima de riesgo de volatilidad (volatility risk premium)**
La diferencia: `VRP = IV − RV_prevista`.

Dato histórico bien documentado: **el mercado casi siempre sobreestima el movimiento futuro**.
Las opciones están, de media, un pelín caras de más. Ese "de más" es el VRP.

**Vender opciones cuando el VRP es claramente positivo tiene ventaja estadística** — es como una
aseguradora que cobra primas un poco infladas respecto al riesgo real. Nuestro bot **solo vende
cuando el VRP supera un umbral** (`vrp_min`). Si las opciones están baratas, no vende.

**VIX**
El "índice del miedo" — la IV a 30 días del S&P 500, en un solo número. VIX 12 = mercado tranquilo.
VIX 30+ = pánico. Alpaca no nos lo da directamente; lo aproximamos con la IV de SPY.

---

## Las griegas (sensibilidades de una opción)

Se llaman así porque se nombran con letras griegas. Miden cómo cambia el valor de una opción cuando
cambia algo del mundo.

**Delta**
Cuánto se mueve el precio de la opción si la acción se mueve $1.
También sirve como **probabilidad aproximada** de que la opción acabe "en dinero".
- Delta 0.20 ≈ 20% de probabilidad de acabar en dinero.
- **Vendemos opciones de delta bajo (~0.15–0.20)** → ~80–85% de probabilidad de que caduquen sin
  valor → nos quedamos la prima la mayoría de las veces.

**Gamma**
Cuánto cambia el *delta* cuando la acción se mueve. Cerca de la expiración el gamma se dispara y
todo se vuelve impredecible y brusco. Por eso preferimos 1–3 DTE y no 0 DTE.

**Theta**
Ya explicado arriba: valor perdido por día. El vendedor de prima lo gana.

**Vega**
Cuánto cambia el valor de la opción si la IV sube o baja un 1%.
Si vendes prima y la IV sube de golpe, pierdes por vega aunque la acción no se mueva.

**Rho**
Sensibilidad a los tipos de interés. Casi irrelevante para operaciones de pocos días.

---

## GEX — la parte más rara de la señal

**Dealers (creadores de mercado, market makers)**
Los bancos y firmas que están **siempre al otro lado** de tu operación de opciones. Si compras un
call, alguien te lo vende: un dealer. Ellos no quieren apostar dirección, así que se **cubren**
(hedge) comprando y vendiendo acciones constantemente.

**Hedging (cobertura)**
Comprar o vender el subyacente para neutralizar el riesgo direccional de una posición de opciones.

**GEX — exposición de gamma (gamma exposure)**
La suma del gamma de **todas las opciones abiertas** en un subyacente, que determina en qué
dirección tienen que operar los dealers para cubrirse:

- **GEX positivo**: los dealers **frenan** el mercado — venden cuando sube, compran cuando baja.
  El precio tiende a **quedarse en un rango**. → **bueno para vender iron condors**.
- **GEX negativo**: los dealers **amplifican** — compran cuando sube, venden cuando baja.
  El precio tiende a **hacer tendencias fuertes y movimientos bruscos**. → **malo para vender prima**;
  mejor comprar debit spreads direccionales.

Nuestro bot calcula el GEX y lo usa para decidir **qué estructura** usar y **si operar o no**.

**Open interest (OI, interés abierto)**
Cuántos contratos de una opción concreta están **vivos ahora mismo** (abiertos, sin cerrar).
Es un ingrediente del cálculo del GEX (GEX ≈ suma de gamma × OI de cada strike).
Alpaca lo publica con ~2 días de retraso, lo cual nos vale porque el GEX es para clasificar
el régimen, no para precisión.

---

## Régimen de mercado

**Régimen (regime)**
El "estado de ánimo" del mercado ahora mismo. Nuestro bot lo clasifica en:
- **trending_up / trending_down** — tendencia clara arriba o abajo
- **range** — lateral, dando vueltas en una banda
- **chop** — errático, sin dirección ni rango claro

**ADX**
Un indicador clásico (0–100) que mide **la fuerza de una tendencia**, sin decir la dirección.
ADX > 22 ≈ hay tendencia. ADX < 18 ≈ mercado lateral.

**EMA (media móvil exponencial)**
El precio medio de los últimos N días, dando más peso a los días recientes. Si el precio está por
encima de su EMA de 20 y de 50, es señal alcista.

**Skew (sesgo de volatilidad)**
Cuando los puts OTM tienen más IV que los calls OTM (casi siempre pasa: la gente paga más por
protegerse de caídas). Un skew muy alto indica miedo. Lo usamos para ajustar los strikes del condor.

---

## Gestión de riesgo

**Sizing (dimensionamiento)**
Decidir **cuántos contratos** operar. Nuestro bot lo calcula para que la pérdida máxima de cada
operación no pase de un % fijo del capital (`risk_per_trade`, empezamos en 0.5%).

**Circuit breaker (cortacircuitos)**
Regla automática: si el bot **pierde más de un 3% en un día**, cierra todo y no abre nada más
hasta la sesión siguiente.

**Drawdown (caída desde máximos)**
Cuánto has bajado desde tu punto más alto. Si el capital cae un 8% desde el pico → el bot reduce
el tamaño a la mitad. Si cae un 12% → deja de abrir posiciones nuevas.

**Take profit (toma de beneficios)**
Cerrar la posición cuando llevas ganado el 50% del máximo posible, sin esperar a la expiración.
Reduce el riesgo de que un movimiento tardío te dé la vuelta.

**Stop loss (corte de pérdidas)**
Cerrar la posición si la pérdida llega al doble de la prima que cobraste.

**Event blackout (veto por evento)**
No abrir posiciones nuevas en las 2 horas alrededor de un dato macro importante
(NFP, ISM, datos de inflación). Esos momentos son impredecibles.

**NFP (non-farm payrolls, informe de empleo de EEUU)**
El dato macro más movido del mes. Sale el **primer viernes de cada mes a las 8:30 hora de Nueva
York** (14:30 en España). Cae el **4 de septiembre** — el último día del hackathon. El bot NO debe
operar dentro de esa ventana; que se niegue a hacerlo es un buen momento para el vídeo de demo.

---

## Infraestructura y IA

**API (interfaz de programación)**
Cómo un programa le habla a Alpaca: "dame el precio de SPY", "compra 3 contratos", "¿cuánto dinero
tengo?". Todo por peticiones HTTP.

**REST**
El estilo de API que usa Alpaca: peticiones HTTP normales (GET, POST) que devuelven JSON.
Nuestro código habla REST directamente con `httpx` (una librería de Python).

**CLI (command-line interface, interfaz de línea de comandos)**
Controlar Alpaca escribiendo comandos en una terminal (`alpaca order create ...`).
Bueno para bots que corren solos día y noche. El hackathon exige usar **CLI o MCP**; usamos ambos.

**MCP (Model Context Protocol)**
Un estándar para conectar un asistente de IA (como Claude) a herramientas externas. El "MCP server
de Alpaca" deja que Claude consulte precios y ponga órdenes **hablándole en lenguaje natural**.
Lo usamos para la demo y para que los jueces puedan "hablar con la mesa" en vivo.

**LLM (large language model, modelo grande de lenguaje)**
Un modelo de IA que entiende y genera texto (GPT, Claude, Llama, Qwen, DeepSeek...).

**Featherless AI**
Un servicio que te deja usar modelos **open-source** (Llama, Qwen...) pagando por petición.
El hackathon regala $25 en créditos (cupón `ALPACA26`) y es tech partner → usarlo bien da puntos y
opción a premio extra. Lo usamos para el "comité Quant": 3 modelos distintos valoran cada operación
y solo se opera si hay consenso.

**Agente autónomo (autonomous agent)**
Un programa que **decide y actúa solo**, sin que un humano apriete el botón cada vez.
Es el requisito central del hackathon.

**Ensemble (comité de modelos)**
Usar varios modelos de IA independientes y quedarte con lo que la mayoría diga. Reduce el riesgo de
que un solo modelo se equivoque o alucine. Nuestro puesto "Quant" es un ensemble de 3.

**Backtest**
Probar una estrategia con datos históricos para ver si habría funcionado.
Nosotros hacemos un "backtest-lite" (aproximado) para asegurarnos de que la lógica no hace locuras,
no un backtest riguroso — no hay tiempo.

**Dry run (marcha en seco)**
Ejecutar el bot en modo simulación: toma todas las decisiones y las apunta, pero **no manda
órdenes**. Es como está ahora. `DESK_MODE=dry_run`.

**Cron / scheduled workflow**
Un temporizador que ejecuta el bot automáticamente cada X minutos. El nuestro corre cada 15 minutos
en horario de mercado, mediante GitHub Actions.
