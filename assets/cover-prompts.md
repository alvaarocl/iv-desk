# Portada — prompts para generar la imagen

Para pegar en Gemini / Nano Banana / Midjourney. Tres direcciones distintas, elige una.

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
