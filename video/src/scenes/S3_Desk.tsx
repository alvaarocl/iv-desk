import React from 'react';
import {useCurrentFrame, spring, useVideoConfig, interpolate} from 'remotion';
import {SceneFrame} from '../components/SceneFrame';
import {C, MONO, SANS} from '../theme';
import {DEBATE} from '../data';

const Seat: React.FC<{title: string; body: React.ReactNode; delay: number}> = ({
  title,
  body,
  delay,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - delay, fps, config: {damping: 200}});
  return (
    <div
      style={{
        background: C.surface,
        border: `1px solid ${C.line}`,
        borderRadius: 14,
        padding: '22px 26px',
        opacity: s,
        transform: `translateY(${(1 - s) * 18}px)`,
      }}
    >
      <div style={{fontFamily: MONO, fontSize: 22, letterSpacing: 2, textTransform: 'uppercase', color: C.muted}}>
        {title}
      </div>
      <div style={{fontFamily: SANS, fontSize: 26, color: C.ink, marginTop: 8}}>{body}</div>
    </div>
  );
};

export const S3_Desk: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <SceneFrame kicker="The desk · four seats · open models on Featherless">
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20}}>
        <Seat
          title="Quant ensemble"
          delay={20}
          body={
            <>
              {DEBATE.quant.map((q) => q.model).join(' · ')}
              <div style={{color: C.up, fontFamily: MONO, marginTop: 6}}>{DEBATE.verdict}</div>
            </>
          }
        />
        <Seat
          title="Bull / Bear"
          delay={40}
          body={
            <>
              must cite real <span style={{color: C.accent}}>Signal</span> fields
              <div style={{color: C.muted, fontFamily: MONO, fontSize: 20, marginTop: 6}}>
                {DEBATE.bull.cited.slice(0, 4).join(', ')}…
              </div>
            </>
          }
        />
      </div>

      <div
        style={{
          background: C.surface,
          border: `1px solid ${C.accent}55`,
          borderRadius: 14,
          padding: '24px 28px',
          marginTop: 4,
          opacity: spring({frame: frame - 64, fps: 30, config: {damping: 200}}),
        }}
      >
        <div style={{fontFamily: MONO, fontSize: 22, letterSpacing: 2, textTransform: 'uppercase', color: C.muted}}>
          Desk Head — falsifiable prediction
        </div>
        <div style={{fontFamily: SANS, fontSize: 30, color: C.ink, marginTop: 10}}>
          &ldquo;{DEBATE.head.thesis}&rdquo;
        </div>
        <div style={{fontFamily: MONO, fontSize: 24, color: C.accent, marginTop: 10}}>
          SPY closes in [{DEBATE.head.prediction.low}, {DEBATE.head.prediction.high}] on{' '}
          {DEBATE.head.prediction.date}
        </div>
      </div>

      <div
        style={{
          fontFamily: MONO,
          fontSize: 26,
          color: C.ink,
          background: C.surface2,
          borderRadius: 10,
          padding: '16px 22px',
          marginTop: 8,
          opacity: interpolate(frame, [110, 128], [0, 1], {extrapolateRight: 'clamp'}),
        }}
      >
        <span style={{color: C.muted}}># the LLM cannot widen risk — by construction</span>
        <br />
        {DEBATE.clamp}
      </div>
    </SceneFrame>
  );
};
