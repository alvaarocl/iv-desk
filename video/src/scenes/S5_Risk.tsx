import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {SceneFrame} from '../components/SceneFrame';
import {C, MONO, snap} from '../theme';
import {RISK_LINES} from '../data';

export const S5_Risk: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const headS = snap(frame, fps, 4);
  return (
    <SceneFrame kicker="The Risk Officer · no discretion" center>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 36,
          color: C.ink,
          opacity: Math.min(1, headS),
          transform: `translateX(${(1 - headS) * -30}px)`,
        }}
      >
        The final size is one line.
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 30,
          color: C.accent,
          background: C.surface2,
          borderRadius: 10,
          padding: '18px 24px',
          opacity: interpolate(frame, [24, 40], [0, 1], {extrapolateRight: 'clamp'}),
          transform: `scale(${interpolate(frame, [24, 40, 50], [0.96, 1.02, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          })})`,
        }}
      >
        min( Desk Head&rsquo;s number , risk officer&rsquo;s cap )
      </div>
      <div
        style={{
          background: C.surface,
          border: `1px solid ${C.line}`,
          borderRadius: 14,
          padding: '28px 34px',
          display: 'flex',
          flexDirection: 'column',
          gap: 15,
        }}
      >
        {RISK_LINES.map((l, i) => {
          const isLLM = l.includes('no LLM');
          const p = interpolate(frame - (70 + i * 9), [0, 12], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          });
          return (
            <div
              key={i}
              style={{
                fontFamily: MONO,
                fontSize: 26,
                color: isLLM ? C.accent : C.ink,
                opacity: p,
                transform: `translateX(${(1 - p) * 20}px)`,
              }}
            >
              {l}
            </div>
          );
        })}
      </div>
    </SceneFrame>
  );
};
