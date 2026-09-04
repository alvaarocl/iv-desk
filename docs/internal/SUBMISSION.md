# Submission checklist (issue #21)

**Deadline: viernes 4 sep, 15:00 UTC (17:00 CEST).** No a las 16:55.
Plataforma: lablab.ai. Reglas verificadas en [`REGLAS-HACKATHON.md`](../REGLAS-HACKATHON.md).

---

## Entregables obligatorios

| # | Entregable | Estado | Notas |
|---|---|---|---|
| 1 | **Repo público** | ✅ | Ya público desde el 1 sep (antes de lo planeado). Verificado: `gh repo view` → `PUBLIC` |
| 2 | Licencia MIT presente | ✅ | `LICENSE` en la raíz |
| 3 | **Disclosure de trabajo pre-evento** en el README | ✅ | Sección "Pre-event work disclosure". Sigue exacta |
| 4 | **ID de la cuenta de competición** | ✅ dato | `PA39HSCQE8S3` ("PAPER UC3M"). Va en el formulario de submission |
| 5 | **Vídeo demo** (~3:12) | ✅ | Final con audio: `video/out/IVDESK-UC3M.mp4` (1920x1080, 30fps, 191.9s, con narración + subtítulos, S7 con el resultado real). Master mudo: `video/out/iv-desk-presentation.mp4`. Verificado por fotograma 4 sep: cifras y verdict correctos |
| 6 | **One-page write-up** | ✅ | `docs/write-up.md` reescrito 3 sep con los números reales (1 trade, +$318.85, 295 stand-downs) |
| 7 | **Deck / slides** | ✅ listo | `assets/IV-Desk-Slides.pdf` (11 páginas, 16:9, diseñado en Pencil) — hecho por si el formulario de lablab lo pide. Sigue sin aparecer como requisito explícito en `REGLAS-HACKATHON.md`, pero ya no bloquea nada si lo piden |
| 8 | **Descripción + tags + título** para lablab | ⬜ | Contenido preparado para copiar/pegar, ver abajo. Envío del formulario requiere confirmación explícita del usuario en el momento |
| 9 | Hasta **5 links sociales** | ⬜ | Premio aparte ($500 ×2), no bloquea la entrega principal |
| 10 | **Capturas post-cierre del jueves 3** | ✅ equivalente | Equity y P&L confirmados dos veces vía `gh workflow run desk.yml -f mode=exits_only` contra la cuenta real: $100.318,85 (+$318,85). Capturas de pantalla serían redundantes con esto — opcional |

Leyenda: ✅ hecho · 🔶 en curso · ⬜ pendiente

---

## Vídeo — Remotion, no screen-recordings

El vídeo de la entrega es un **proyecto Remotion** (`video/`): motion graphics programáticas,
renderizado **sin audio**. La narración va aparte: `video/NARRATION.md` (inglés) → text-to-speech →
se compone bajo el vídeo. Siete escenas · ~2:52 · toda cifra sale de `backtest/RESULTS.md` o del
transcript real del debate.

El `docs/internal/video-script.md` de Ángel (screen-recordings) queda como **B-roll opcional** — no es la
entrega principal.

El vídeo **no** vende el P&L (4 sesiones = lotería de varianza). Vende **el agente decidiendo solo**
y el momento en que se niega a operar.

<details><summary>Guion narrado por escena (ver <code>video/NARRATION.md</code> para timings)</summary>

1. **0:00–0:20 — El problema.** "No predecimos la dirección del mercado. Vendemos seguro
   sobrevalorado, y solo cuando lo está." Una frase, sin jerga.
2. **0:20–0:50 — La arquitectura.** Señal determinista (VRP ratio + GEX normalizado) → gates de
   riesgo sin discreción → **la mesa LLM debate** → CLI de Alpaca ejecuta. Coincide casi punto por
   punto con la arquitectura que la propia Alpaca publica como buena práctica ([`REGLAS-HACKATHON.md`](../REGLAS-HACKATHON.md)).
3. **0:50–1:50 — Metraje real** (el corazón del vídeo):
   - Un evento `debate` del journal: Quant, Bull, Bear, Desk Head, y la tesis falsable.
   - Una orden `mleg` de 4 patas colocada vía CLI.
   - **El momento en que la mesa se niega a operar** por un gate de riesgo o un stand-down de VRP —
     ese plano es el que gana el eje de robustez.
   - Una salida gestionada (take-profit / stop / expiry).
4. **1:50–2:30 — Resultado.** La curva de equity de `PA39HSCQE8S3`, el ledger de predicciones
   (cuántas tesis resueltas correctas), el log de incidencias resueltas.

</details>

---

## Antes de hacer el repo público — ya hecho el 1 sep, verificado de nuevo 3 sep

- [x] `data/journal.jsonl` y `data/equity.csv` revisados — sin claves, sin nada sensible (son el
      audit trail, es intencionado que sean públicos). Re-verificado con grep 3 sep: 0 coincidencias.
- [x] `.env` **no** está trackeado (`git ls-files | grep -c '\.env$'` → 0, verificado 3 sep).
- [x] La disclosure pre-evento del README describe exactamente lo que hay.
- [x] El write-up no afirma nada que no esté en el código (issue #18); reescrito 3 sep con números
      reales, ninguno inventado.
- [x] `Refs/` (vídeos de referencia, ~450 MB) sigue en `.gitignore`.
- [x] Wiki: no hay wiki (descartada).

---

## Checklist del día de entrega (viernes 4)

1. [x] Confirmar el número de P&L final — $100.318,85 (+$318,85), verificado dos veces contra la
       cuenta real vía `gh workflow run desk.yml -f mode=exits_only`, 3 sep.
2. [x] Write-up final con ese número — `docs/write-up.md`, 3 sep.
3. [ ] Subir vídeo (YouTube/Vimeo no listado) — `video/out/IVDESK-UC3M.mp4` ya está terminado y en
       el repo (4 sep), solo falta subirlo. Deck sin confirmar si lablab lo pide de verdad (ver ítem
       7 arriba).
4. [x] `gh repo edit --visibility public` — hecho el 1 sep, verificado de nuevo 3 sep.
5. [ ] Rellenar el formulario de lablab: título, descripción, tags, cover, links (repo, vídeo,
       hasta 5 sociales), **account ID `PA39HSCQE8S3`**. Contenido preparado para copiar/pegar —
       envío requiere confirmación explícita del usuario en el momento, no se hace en su nombre.
6. [ ] Enviar **antes de las 17:00 CEST**.
7. [ ] Post social final: resultados + repo.
