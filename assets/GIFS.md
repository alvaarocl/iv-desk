# Los tres GIFs del README

Recortados del vídeo que ya existe (`video/out/IVDESK-UC3M.mp4`) o grabados en pantalla. Van
donde el README tiene el comentario `TODO antes de la entrega`.

**Regla:** ninguno enseña P&L. Los tres enseñan al agente **decidiendo**. Es el eje que estamos
jugando y es el que nadie más va a enseñar.

| # | Qué se ve | Dónde sacarlo | Duración |
|---|---|---|---|
| 1 | **El desk negándose a operar.** El log escupe `stand_down: vrp` con el ratio IV/RV al lado, y no pasa nada más. | `uv run python -m agent.desk` en `dry_run` con el mercado abierto, o `grep stand_down data/journal.jsonl \| tail -3 \| python -m json.tool` | 4-6 s |
| 2 | **La mesa debatiendo.** Bull y Bear con argumentos **distintos**, y la tesis falsable del Desk Head. | `grep '"event": "debate"' data/journal.jsonl \| tail -1 \| python -m json.tool` | 6-8 s |
| 3 | **El dashboard en vivo.** Scroll corto por la curva de equity y el libro de posiciones. | `dashboard/index.html` en el navegador | 4-6 s |

## Cómo generarlos

```bash
# de vídeo a GIF, ancho 900, 12 fps — pesa poco y se ve nítido en GitHub
ffmpeg -ss 00:01:12 -t 6 -i video/out/IVDESK-UC3M.mp4 \
  -vf "fps=12,scale=900:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" \
  -loop 0 assets/gif-standdown.gif
```

Nombres esperados por el README: `assets/gif-standdown.gif`, `assets/gif-debate.gif`,
`assets/gif-dashboard.gif`.

**Peso:** por debajo de 5 MB cada uno. GitHub no los carga bien por encima, y un README que tarda
en pintar en la primera visita del jurado es peor que un README sin GIFs.

## Cuando existan

Sustituir el comentario `<!-- TODO ... -->` del README por:

```markdown
| El desk negándose a operar | La mesa debatiendo |
|---|---|
| ![](assets/gif-standdown.gif) | ![](assets/gif-debate.gif) |
```
