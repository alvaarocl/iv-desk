import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {SceneFrame} from '../components/SceneFrame';
import {C, MONO, SANS, snap} from '../theme';
import {DEBATE_GIF} from '../gifData';

const Seat: React.FC<{title: string; tone: 'up' | 'down' | 'ink'; body: string; delay: number}> = ({
  title,
  tone,
  body,
  delay,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = snap(frame, fps, delay);
  return (
    <div
      style={{
        background: C.surface,
        border: `1px solid ${C.line}`,
        borderRadius: 14,
        padding: '20px 24px',
        opacity: Math.min(1, s),
        transform: `translateY(${(1 - s) * 20}px)`,
      }}
    >
      <div style={{fontFamily: MONO, fontSize: 18, letterSpacing: 2, textTransform: 'uppercase', color: C[tone]}}>
        {title}
      </div>
      <div style={{fontFamily: SANS, fontSize: 22, color: C.ink, marginTop: 8, lineHeight: 1.35}}>{body}</div>
    </div>
  );
};

/** README GIF 2 — the mesa arguing over a candidate GEX already vetoed. Real shadow debate,
 * SPY, 2 Sep: 2/3 quant confirm, Bull and Bear genuinely disagree (similarity 0.082), Desk
 * Head overrules the quant majority and vetoes. Shows the desk isn't a rubber stamp even in
 * observation-only mode. */
export const G2_Debate: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const headS = snap(frame, fps, 130);
  return (
    <SceneFrame kicker={`shadow debate · ${DEBATE_GIF.underlying} · GEX vetoed, mesa still runs`}>
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18}}>
        <Seat title="Quant ensemble" tone="up" delay={12} body={`${DEBATE_GIF.quant.verdict} — ${DEBATE_GIF.quant.reason}`} />
        <Seat title="Bull" tone="up" delay={28} body={DEBATE_GIF.bull.argument} />
      </div>
      <Seat title="Bear" tone="down" delay={50} body={DEBATE_GIF.bear.argument} />
      <div
        style={{
          background: C.surface,
          border: `1px solid ${C.accent}55`,
          borderRadius: 14,
          padding: '20px 24px',
          opacity: Math.min(1, headS),
          transform: `translateY(${(1 - headS) * 20}px)`,
        }}
      >
        <div style={{fontFamily: MONO, fontSize: 18, letterSpacing: 2, textTransform: 'uppercase', color: C.muted}}>
          Desk Head — {DEBATE_GIF.head.decision}
        </div>
        <div style={{fontFamily: SANS, fontSize: 24, color: C.ink, marginTop: 8}}>
          &ldquo;{DEBATE_GIF.head.thesis}&rdquo;
        </div>
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 20,
          color: C.muted,
          opacity: interpolate(frame, [190, 210], [0, 1], {extrapolateRight: 'clamp'}),
        }}
      >
        bull/bear similarity {DEBATE_GIF.similarity} — genuinely adversarial, not two copies of one answer
      </div>
    </SceneFrame>
  );
};
