# Portada — prompts para generar la imagen

Para pegar en Gemini / Nano Banana / Midjourney.

---

## Dirección D — "El payoff" *(la recomendada — probada, funciona)*

Las direcciones A/B/C de abajo son composiciones de diagrama/escena: necesitan tamaño grande para
leerse. La portada real va a verse casi siempre como una miniatura pequeña (tarjeta de submission
de lablab, thumbnail social) — ahí un mark grande y simple gana siempre a una composición detallada.

El gráfico es la forma real del payoff de un iron condor — la meseta plana de beneficio máximo y
las dos alas de pérdida acotada — así que es honesto (es literalmente lo que opera el bot), no es
un cliché de IA-trading, y se lee de un vistazo en miniatura. Probado con Nano Banana Pro (16:9,
2K) — el resultado es un wordmark "IV DESK" grande a la izquierda + el trapecio del payoff en
ámbar brillante a la derecha, sobre negro sólido. Funciona a la primera, sin retoque de texto.

> Minimalist editorial poster cover, 16:9 widescreen. Solid deep charcoal-black background
> (#13161b), no gradient, no texture. The single hero graphic fills the right two-thirds of the
> frame: one bold continuous line drawing an options iron-condor payoff diagram — a flat-topped
> trapezoid profile, like a wide plateau with two angled wings sloping down to the corners —
> rendered thick and confident in warm amber-gold (#e0a83d), with a very subtle soft glow,
> floating on the dark background with generous empty space around it, no axes, no grid, no
> numbers, no chart clutter. On the left third, large confident geometric sans-serif wordmark "IV
> DESK" in warm off-white (#e9e7e1), left-aligned, big and bold, filling maybe a third of the
> frame height. Directly beneath it, one small line of muted grey subtitle text in a smaller
> weight: "an options desk that knows when not to trade". Nothing else in the frame — no icons,
> no charts, no photographs, no illustrated people, no bulls, no bears, no brains, no neural
> network nodes, no circuit boards, no hexagon grids, no sci-fi HUD, no holographic UI, no
> candlestick charts, no green arrows, no rockets, no coins or dollar signs, no lens flare, no
> neon cyan/orange gradients, no fake statistics or percentage badges. Swiss editorial restraint,
> like a modern Bloomberg Businessweek or The Economist cover — calm, precise, high contrast, a
> lot of negative space, crisp clean typography rendered correctly and legibly.

**Nota de ratio:** este prompt pide 16:9 (lo que pide el formulario de submission). Si necesitas
también la versión Open Graph 1200×630 para redes, pide el mismo prompt con `aspect_ratio` 21:9 o
recorta el 16:9 resultante — el mark está centrado a propósito para aguantar el recorte.

---

## Direcciones A/B/C (anteriores, más "escena" que "mark") — de respaldo si D no convence

---

## Antes de nada: qué NO hacer

Las portadas de la competencia que hemos visto (AlphaPilot, VibeHedge) comparten los mismos
tics, y **dos de ellas inventan datos**: "98.7% signal accuracy", "85% win rate", "1.2M+ data
points". Eso es exactamente lo que nuestro proyecto argumenta que está mal.

**Regla dura: cero cifras inventadas en la portada.** Si aparece un número, tiene que ser uno
real de `backtest/RESULTS.md` o del journal. Un jurado de Alpaca sabe leer un win rate falso, y
nuestra tesis entera es que el registro es auditable.

Clichés a evitar, todos presentes en las referencias:

- Toros, osos, flechas verdes subiendo.
- Cerebros brillantes, redes neuronales de nodos azules, "AI" en degradado.
- Placas de circuito, hexágonos, HUDs de ciencia ficción.
- Velas japonesas genéricas de stock.
- Paletas cian/naranja neón sobre negro absoluto.

---

## Dirección A — "El registro" *(la que yo elegiría)*

Nuestro diferenciador es que **cada decisión, incluidas las de no operar, queda escrita**. La
portada es ese registro.

> Editorial tech cover, 1200×630. A dark charcoal background (#0d1117), not pure black. The
> composition is a clean monospaced log rendered as fine typography, filling the left two thirds:
> repeated timestamped lines reading `stand_down: vrp` and `stand_down: gex` in muted grey,
> and among them two or three lines in warm amber reading `opened: iron_condor`. The rejected
> lines are the majority and they are deliberately quiet; the amber lines draw the eye. To the
> right, generous negative space and the title "IV DESK" set in a confident geometric sans,
> white, with the subtitle "an options desk that knows when not to trade" beneath it in grey.
> Subtle paper-grain texture. No icons, no charts, no illustration, no glow. Swiss editorial
> restraint, like a Bloomberg Businessweek cover. High contrast, calm, precise.

**Por qué funciona:** es la única portada del hackathon que va a enseñar *no-operaciones*. Y es
literalmente cierta: ese log existe en `data/journal.jsonl`.

---

## Dirección B — "La superficie"

Miramos la superficie de volatilidad, no el gráfico de precio. Que se vea.

> Abstract data-art cover, 1200×630. A single implied-volatility surface rendered as a fine
> wireframe mesh in thin luminous lines, seen at a low three-quarter angle, floating in dark
> space (#0d1117). The mesh has a real volatility smile shape — curved up at both edges, dipping
> in the middle — not a generic terrain. One narrow band of the surface is highlighted in amber
> where the premium is rich; the rest is cool grey-blue and understated. Thin axis labels in
> small monospaced type: "strike", "days to expiry", "implied vol". Title "IV DESK" bottom left
> in a geometric sans. Precise, scientific, restrained. No bulls, no brains, no circuit boards,
> no candlesticks, no glow bloom.

**Riesgo:** puede quedar bonito pero mudo. Necesita el título haciendo el trabajo pesado.

---

## Dirección C — "La mesa vacía"

La idea más conceptual: una mesa de trading donde casi todo está apagado a propósito.

> Cinematic editorial photograph, 1200×630. A dim trading desk seen from behind, six monitors in
> a curved array. Five screens are dark and dormant; one screen glows softly, showing a sparse
> terminal with a handful of text lines. No trader in the chair — the desk is running itself. Cool
> ambient darkness, one warm amber light source from the single live screen. Shallow depth of
> field, 35mm, film grain. Quiet and deliberate, not dramatic. Title "IV DESK" overlaid bottom
> left in a clean geometric sans. No neon, no holograms, no floating UI, no bull statue.

**Por qué funciona:** comunica "disciplina" y "autónomo" sin decirlo. **Riesgo:** los generadores
tienden a meter gráficos de velas en los monitores — habrá que insistir en el negativo.

---

## Negative prompt (añádelo a cualquiera de las tres)

```
bull, bear, charging bull statue, glowing brain, neural network nodes, circuit board,
hexagon grid, sci-fi HUD, holographic interface, candlestick chart, green upward arrow,
rocket, coins, dollar signs, lens flare, neon cyan and orange gradient, stock photo trader
in a suit, fake statistics, percentage badges, watermark, distorted text, gibberish text
```

## Notas de producción

- **Formato:** 1200×630 (Open Graph). lablab pide portada; ese ratio también sirve para el post.
- **El texto lo pones tú después.** Los generadores escriben mal: genera la imagen **sin
  tipografía** y superpón "IV DESK" en Figma o Canva. Ahorra tres rondas de prompt.
- **Paleta coherente con el dashboard** (`dashboard/index.html`): fondo `#0d1117`, texto
  `#adbac7`, acento verde `#3fb950`, acento morado `#a371f7`. Si la portada usa la misma paleta,
  portada + dashboard + diagrama parecen un sistema y no tres cosas sueltas.
- **Si ninguna convence:** el diagrama `assets/architecture.svg` recortado también funciona como
  portada. Es feo decirlo, pero una portada honesta y sobria pierde menos puntos que una bonita
  que promete un 98.7% que no existe.
