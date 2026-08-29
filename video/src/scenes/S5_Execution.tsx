import React from 'react';
import {useCurrentFrame, spring, useVideoConfig, interpolate} from 'remotion';
import {SceneFrame} from '../components/SceneFrame';
import {TypeOn} from '../components/TypeOn';
import {C, MONO} from '../theme';
import {EXECUTION} from '../data';

export const S5_Execution: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <SceneFrame kicker="Execution · one 4-leg order · the official Alpaca CLI">
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 50}}>
        <div style={{display: 'flex', flexDirection: 'column', gap: 14}}>
          {EXECUTION.legs.map((leg, i) => {
            const s = spring({frame: frame - (16 + i * 10), fps, config: {damping: 200}});
            return (
              <div
                key={leg.k}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontFamily: MONO,
                  fontSize: 30,
                  background: C.surface,
                  border: `1px solid ${C.line}`,
                  borderRadius: 10,
                  padding: '16px 24px',
                  opacity: s,
                  transform: `translateX(${(1 - s) * -24}px)`,
                }}
              >
                <span style={{color: leg.k.startsWith('sell') ? C.up : C.muted}}>{leg.k}</span>
                <span style={{color: C.ink}}>{leg.v}</span>
              </div>
            );
          })}
        </div>

        <div style={{display: 'flex', flexDirection: 'column', gap: 18, justifyContent: 'center'}}>
          {EXECUTION.exits.map((e, i) => (
            <div
              key={e}
              style={{
                fontFamily: MONO,
                fontSize: 26,
                color: C.ink,
                opacity: interpolate(frame, [90 + i * 12, 104 + i * 12], [0, 1], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                }),
              }}
            >
              → {e}
            </div>
          ))}
        </div>
      </div>

      <div
        style={{
          fontFamily: MONO,
          fontSize: 22,
          color: C.accent,
          background: C.surface2,
          borderRadius: 10,
          padding: '18px 24px',
          marginTop: 10,
        }}
      >
        <TypeOn text={EXECUTION.order} start={40} durationInFrames={70} />
      </div>

      <div
        style={{
          fontFamily: MONO,
          fontSize: 23,
          color: C.muted,
          opacity: interpolate(frame, [150, 168], [0, 1], {extrapolateRight: 'clamp'}),
        }}
      >
        {EXECUTION.cron}
      </div>
    </SceneFrame>
  );
};
