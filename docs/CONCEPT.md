# El concepto — IV Desk, en cristiano

Para leer con [`GLOSSARY.md`](GLOSSARY.md) al lado. Cualquier palabra en **negrita** que no entiendas
está definida ahí.

---

## Qué estamos construyendo

**IV Desk es una aseguradora automática para la bolsa.**

Piensa en una aseguradora de coches. Cobra primas a mucha gente. La mayoría no tiene un accidente
→ se queda su dinero. Algunos sí → paga la indemnización. Si pone bien los precios y no asegura a
gente temeraria, a largo plazo gana dinero.

Nuestro bot hace exactamente eso, pero con la bolsa:

1. **Cada 15 minutos** mira tres ETFs de índice: **SPY**, **QQQ** e **IWM**.
2. **Calcula si los "seguros de bolsa" (las opciones) están caros** respecto a lo que probablemente
   va a pasar. Ese exceso de precio se llama **VRP** (prima de riesgo de volatilidad).
3. **Mira si los grandes bancos van a calmar el mercado o a agitarlo**, calculando el **GEX**
   (exposición de gamma de los dealers).
4. **Si los seguros están caros de más Y el mercado va a estar tranquilo** → **vende un iron
   condor**: cobra ~$50–150 apostando a que SPY (o QQQ, o IWM) **se queda dentro de un rango**
   durante los próximos 1–3 días.
5. **Aplica reglas de seguridad automáticas**: no arriesgar más de un 0.5–2% del capital por
   operación, cerrar cuando lleve el 50% del beneficio, cortar pérdidas al doble, y **no operar
   antes de datos macro importantes** como el informe de empleo (NFP).
6. **Encima de todo esto**, un equipo de personajes de IA — el **Quant**, el **Alcista**, el
   **Bajista** y el **Jefe de Mesa** — **discute cada operación** antes de hacerla y **escribe por
   qué la hace**, con una predicción concreta y comprobable. Todo eso se ve en una **web en directo**
   que cualquiera puede mirar mientras la mesa opera.

---

## Por qué esto y no otra cosa — la estrategia para ganar

El hackathon tiene ~2.000 inscritos. **Casi todos van a entregar la misma idea**: un sistema
multi-agente que vende credit spreads en SPY cuando el RSI (un indicador de precio básico) está
sobrevendido. Todos los asistentes de IA convergen a esa respuesta.

Nos diferenciamos en tres capas:

### 1. La señal — miramos las opciones, no el precio
Los demás miran el gráfico del precio de SPY y calculan indicadores sobre él. Nosotros miramos
**la superficie de opciones misma**: comparamos la volatilidad que el mercado espera (**IV**) con
la que probablemente habrá (**RV**), y leemos cómo está posicionado el dinero institucional
(**GEX**). Casi nadie de los 2.000 sabe qué es el gamma de los dealers. **Ahí está nuestra ventaja
real.**

### 2. La fiabilidad — de verdad opera las 4 sesiones
El hackathon exige una **cuenta nueva**, con **$100.000**, y que se pueda **verificar el P&L** de la
ventana entera (lun 31 ago → cierre del jue 3 sep, **4 sesiones**; ver
[`CALENDARIO.md`](CALENDARIO.md)). Eso descalifica a la mayoría: mucha gente monta algo el fin de
semana y no tiene cuatro días de trading automático limpio. Solo por llegar al final con un bot que
ha operado de verdad todas las sesiones, ya estás en el ~20% de arriba.

### 3. Se puede ver operar
> ⚠️ **El dashboard es opcional.** Las guidelines oficiales dicen que la UI **no es obligatoria**
> (*"we are primarily evaluating the autonomous agent workflow and its trading performance"*), así que
> está en la lista de recortes: se construye solo si el agente y la entrega están cerrados. Lo que
> **sí** entregamos siempre es el journal falsable (`data/journal.jsonl`). No prometáis la web en el
> write-up si no existe → issue #18.

Los demás entregan un repositorio de código y un vídeo grabado de la pantalla. Nosotros entregamos
además una **web en directo** donde se ve la mesa debatir, la superficie de volatilidad que está
leyendo, el libro de posiciones abiertas, y un **registro de predicciones** donde cada tesis queda
calificada como acertada o fallada. Eso gana el eje de Presentación y da material para las redes.

---

## Cómo puntúa en el jurado

**Son CUATRO criterios, de peso parecido (~25% cada uno).** Verificado el 29 ago contra las fuentes
públicas → [`REGLAS-HACKATHON.md`](REGLAS-HACKATHON.md).

*(Antes esta tabla listaba cinco al ~20% metiendo "Social Engagement". Era incorrecto: el social es un
**premio aparte** — dos de $500 —, no un eje del rubro. La corrección no es cosmética: mueve el peso
del P&L de ~20% a ~25%.)*

| Criterio | Nuestra jugada | Realidad |
|---|---|---|
| **P&L Performance** (~25%) | Núcleo consistente + adaptación al régimen. Positivo modesto, nunca reventar | **No es nuestro eje fuerte, pero no lo regalamos** — ver abajo |
| **Technology Implementation** (~25%) | Trading API + CLI + datos de opciones con griegas/IV + OI para el GEX + condors de 4 patas | **Aquí apretamos.** Uso profundo y real del stack de Alpaca. Solo contamos lo que esté construido |
| **Creativity & Originality** (~25%) | Mesa de agentes que discuten, anclada en la superficie de vol + gamma (no en noticias ni fundamentales) + registro público de predicciones | **Aquí apretamos.** El debate solo no es original; el anclaje en el gamma sí |
| **Presentation & Execution** (~25%) | One-pager limpio + vídeo con el debate y el momento en que la mesa se niega a operar antes de un dato macro (+ dashboard si da tiempo: la UI **no** es obligatoria) | **Aquí apretamos** |

Aparte del rubro: **Social Engagement** — un post al día contando el proceso, etiquetando a
@lablabai y @AlpacaHQ. Dos premios de $500, mucho retorno por poco esfuerzo, pero **no suma en la
puntuación del proyecto**.

### Sobre el P&L: matiz importante

Este documento decía antes *"Cedemos este"*. **Con cuatro criterios, ceder el P&L es ceder un cuarto
del rubro**, así que la frase necesita matiz: no aspiramos a ganar el eje de P&L (en cuatro sesiones
lo gana quien tenga suerte), pero **ceder el upside conservando el downside es la peor combinación
posible** — que es exactamente donde estamos hoy con el sizing actual.

El razonamiento completo, con los números, está en [`VIABILIDAD.md`](VIABILIDAD.md) → *"La
incoherencia de riesgo que hay que resolver"*. Resumen: hay que elegir explícitamente entre **(a)**
asumir la cesión y reducir también el riesgo, o **(b)** rampa de sizing agresiva si el lunes va
limpio. Cualquiera de las dos vale; la posición actual — (a) en el upside y (b) en el downside — no.
Es una decisión humana → issue #16.

---

## Riesgos que asumimos con los ojos abiertos

- **Semana de volatilidad baja.** Si el mercado está muy plano, los seguros valen poco → el P&L
  será pequeño aunque la estrategia acierte. Lo mitiga el modo adaptativo (comprar apuestas
  direccionales baratas cuando toca), no lo elimina.
- **4 sesiones son una lotería de varianza** en el P&L. Un solo día de tendencia fuerte puede borrar
  una semana de ganancias de condors. Por eso no apostamos el proyecto a ese eje.
- **Scope ajustado**: capa de IA + contenido (+ dashboard, opcional) en pocos días con 2 personas es justo. Hay una
  lista de recortes explícita en `../PLAN.md` — lo primero que se cae es la reflexión nocturna, lo
  último el motor y las reglas de riesgo (esos no se tocan).
- **El debate alcista/bajista no es original por sí solo.** El repo `ai-hedge-fund` (20k estrellas)
  ya lo hace y mucha gente lo copiará. Nuestro presupuesto de originalidad se gasta en la señal.

---

## Alternativas que consideramos y descartamos

Se valoraron estas ideas antes de decidir. Todas cumplían los requisitos del hackathon.
Se documentan por si hubiera que pivotar.

### A · Wheel Bot — la más simple
Vender puts sobre una acción buena; si te asignan las acciones, venderlas con calls. Cobrar prima en
bucle. **Descartada:** robusta y fácil de explicar, pero **nada diferenciada** (cientos la harán) y
en 4 sesiones apenas completa un ciclo.

### B · News Trader — la IA lee noticias y opera
Un agente lee noticias y resultados en tiempo real con Featherless, forma una tesis direccional y la
ejecuta con un debit spread. **Descartada:** la más fácil de presentar, pero operar noticias es
adivinar (P&L aleatorio) y "sentiment trading" es el cliché #1 del hackathon.

### C · Regime Switcher — la IA cambia de táctica según el mercado
Tres sub-estrategias y un cerebro que elige cuál usar cada día. **Parcialmente adoptada:** es
básicamente IV Desk, y su lógica de "saber cuándo NO operar y cuándo cambiar" está incorporada en
nuestro modo adaptativo. No se hizo como proyecto separado por el coste de pulir 3 estrategias.

### D · Risk Sentinel — sobrevivir es ganar
El 90% del proyecto sería gestión de riesgo autónoma extrema sobre una cartera sencilla.
**Descartada como foco principal:** los jueces (de Alpaca) valorarían la gestión de riesgo, pero el
P&L plano y la poca demostrabilidad visual pesan en contra. Su filosofía sí está en nuestras reglas
de riesgo.

### Decisión final
**IV Desk completo**, con la señal VRP + GEX y la mesa de agentes. Si durante la semana se ve que
explicar iron condors y gamma en el vídeo resulta difícil, existe un plan B de **"IV Desk
simplificado"**: quitar el GEX, quedarse solo con el VRP ("vendemos seguros de bolsa solo cuando
están caros de más") y una sola estructura (el iron condor). Mismo diferenciador, más fácil de
contar. Esa decisión se toma más adelante si hace falta.

---

## Estado actual y qué falta

Ver [`STATUS.md`](STATUS.md) para el detalle. Resumen: el **motor determinista** (pasos 1–5) está
construido y probado contra el mercado real. Falta la **capa de IA** (paso 6), el **dashboard**, la
**calibración** de los números con el mercado abierto, y todo el material de entrega
(one-pager, vídeo, deck).
