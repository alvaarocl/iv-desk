# Los tres GIFs del README

Generados con Remotion, no capturados de pantalla — mismo lenguaje visual que
`video/out/IVDESK-UC3M.mp4` (tema, tipografías, componentes de `video/src/components/`), pero
con **datos reales del 2 sep** (sesión 3 de 4), no del guion fijo del vídeo principal.

**Regla:** ninguno enseña P&L. Los tres enseñan al agente **decidiendo**. Es el eje que estamos
jugando y es el que nadie más va a enseñar.

| # | Fichero | Qué se ve | Fuente real |
|---|---|---|---|
| 1 | `gif-standdown.gif` | El desk negándose a operar: VRP rico (1.33) pero vetado por GEX. | `signal` event de IWM, 2 sep, `data/journal.jsonl` |
| 2 | `gif-debate.gif` | La mesa en sombra debatiendo SPY — 2/3 quant confirman, Bull y Bear genuinamente en desacuerdo (similarity 0.082), el Desk Head veta. | primer `debate` con `shadow: true` de la semana, `data/journal.jsonl` |
| 3 | `gif-dashboard.gif` | El resumen de una sesión completa: 84 señales, 3 subyacentes, 2 debates en sombra, 0 trades, equity intacta. | contadores del 2 sep, `data/journal.jsonl` |

## Cómo se generaron

Composiciones nuevas en `video/src/gifs/` (`G1_StandDown.tsx`, `G2_Debate.tsx`,
`G3_Dashboard.tsx`), datos reales congelados en `video/src/gifData.ts`, registradas en
`video/src/Root.tsx` como composiciones aparte — **no** tocan la película narrada principal
(`IVDesk`), que sigue esperando al cierre del jueves para sus propios números.

```bash
cd video
npm run gifs   # renderiza los 3 a video/out/*.mp4 (1600x900, 60fps)
```

Luego a GIF con la misma receta de siempre — ancho 900, 12 fps, paleta propia:

```bash
ffmpeg -i video/out/gif1-standdown.mp4 \
  -vf "fps=12,scale=900:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" \
  -loop 0 assets/gif-standdown.gif
```

(mismo comando para `gif2-debate.mp4` → `gif-debate.gif` y `gif3-dashboard.mp4` →
`gif-dashboard.gif`).

**Peso real:** 704 KB / 1.1 MB / 708 KB — todos por debajo del límite de 5 MB.

## Para refrescarlos con datos más recientes

`video/src/gifData.ts` documenta de dónde sale cada número. Basta con actualizar ese fichero
contra un `data/journal.jsonl` más reciente y volver a correr `npm run gifs` + la conversión de
arriba — no hace falta tocar las composiciones.
