# Submission checklist (issue #21)

**Deadline: viernes 4 sep, 15:00 UTC (17:00 CEST).** No a las 16:55.
Plataforma: lablab.ai. Reglas verificadas en [`REGLAS-HACKATHON.md`](REGLAS-HACKATHON.md).

---

## Entregables obligatorios

| # | Entregable | Estado | Notas |
|---|---|---|---|
| 1 | **Repo público** | ⬜ | `gh repo edit alvaarocl/iv-desk --visibility public` — **el 4 sep, no antes** |
| 2 | Licencia MIT presente | ✅ | `LICENSE` en la raíz |
| 3 | **Disclosure de trabajo pre-evento** en el README | ✅ | Sección "Pre-event work disclosure". Verificar que sigue siendo exacta el día 4 |
| 4 | **ID de la cuenta de competición** | ✅ dato | `PA39HSCQE8S3` ("PAPER UC3M"). Va en el formulario de submission |
| 5 | **Vídeo demo** (~2:52) | 🔶 | Proyecto Remotion en `video/`. v1 renderizada con datos del backtest. **Jueves:** editar `video/src/data.ts` (`RESULTS.mode = "live"`) + guion S6, `npm run render`, subir a YouTube no listado. Narración TTS: `video/NARRATION.md` |
| 6 | **One-page write-up** | 🔶 | `docs/write-up.md` — reescribir desde el código el día 6 (issue #18). Números reales de la ventana |
| 7 | **Deck / slides** | ⬜ | Miércoles 2. Cover image incluida |
| 8 | **Descripción + tags + título** para lablab | ⬜ | Viernes 4 |
| 9 | Hasta **5 links sociales** | ⬜ | Premio aparte ($500 ×2). Un post/día desde el lunes |
| 10 | **Capturas post-cierre del jueves 3** | ⬜ | Equity, posiciones, activity log de `PA39HSCQE8S3` tras las 22:00 CEST. **Fijar el número de P&L** |

Leyenda: ✅ hecho · 🔶 en curso · ⬜ pendiente

---

## Vídeo — Remotion, no screen-recordings

El vídeo de la entrega es un **proyecto Remotion** (`video/`): motion graphics programáticas,
renderizado **sin audio**. La narración va aparte: `video/NARRATION.md` (inglés) → text-to-speech →
se compone bajo el vídeo. Siete escenas · ~2:52 · toda cifra sale de `backtest/RESULTS.md` o del
transcript real del debate.

El `docs/video-script.md` de Ángel (screen-recordings) queda como **B-roll opcional** — no es la
entrega principal.

El vídeo **no** vende el P&L (4 sesiones = lotería de varianza). Vende **el agente decidiendo solo**
y el momento en que se niega a operar.

<details><summary>Guion narrado por escena (ver <code>video/NARRATION.md</code> para timings)</summary>

1. **0:00–0:20 — El problema.** "No predecimos la dirección del mercado. Vendemos seguro
   sobrevalorado, y solo cuando lo está." Una frase, sin jerga.
2. **0:20–0:50 — La arquitectura.** Señal determinista (VRP ratio + GEX normalizado) → gates de
   riesgo sin discreción → **la mesa LLM debate** → CLI de Alpaca ejecuta. Coincide casi punto por
   punto con la arquitectura que la propia Alpaca publica como buena práctica ([`REGLAS-HACKATHON.md`](REGLAS-HACKATHON.md)).
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

## Antes de hacer el repo público (viernes 4)

- [ ] `data/journal.jsonl` y `data/equity.csv` revisados — sin claves, sin nada sensible (son el
      audit trail, es intencionado que sean públicos, pero mirar).
- [ ] `.env` **no** está trackeado (`git ls-files | grep -c '\.env$'` → 0).
- [ ] La disclosure pre-evento del README describe exactamente lo que hay.
- [ ] El write-up no afirma nada que no esté en el código (issue #18).
- [ ] `Refs/` (vídeos de referencia, ~450 MB) sigue en `.gitignore`.
- [ ] Wiki: no hay wiki (descartada). Si se creara, su visibilidad sigue a la del repo.

---

## Checklist del día de entrega (viernes 4)

1. [ ] Confirmar el número de P&L final (de las capturas del jueves).
2. [ ] Write-up final con ese número.
3. [ ] Subir vídeo (YouTube/Vimeo no listado) y deck.
4. [ ] `gh repo edit --visibility public`.
5. [ ] Rellenar el formulario de lablab: título, descripción, tags, cover, links (repo, vídeo,
       deck, hasta 5 sociales), **account ID `PA39HSCQE8S3`**.
6. [ ] Enviar **antes de las 17:00 CEST**.
7. [ ] Post social final: resultados + repo.
