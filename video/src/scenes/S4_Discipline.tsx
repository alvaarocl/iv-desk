import React from 'react';
import {useCurrentFrame, interpolate} from 'remotion';
import {SceneFrame} from '../components/SceneFrame';
import {FunnelBar} from '../components/FunnelBar';
import {Callout} from '../components/Callout';
import {C, MONO} from '../theme';
import {FUNNEL, STAND_DOWN_PCT, RISK_LINES} from '../data';

export const S4_Discipline: React.FC = () => {
  const frame = useCurrentFrame();
  const max = FUNNEL[0].n;

  // first ~18s: funnel + the 94% callout.  then: the risk gates.
  const phase2 = interpolate(frame, [520, 545], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <SceneFrame kicker="Discipline · 60 real sessions · 3 underlyings" center>
      {phase2 < 1 ? (
        <div style={{opacity: 1 - phase2}}>
          <div style={{display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 60, alignItems: 'center'}}>
            <div style={{display: 'flex', flexDirection: 'column', gap: 26}}>
              {FUNNEL.map((f, i) => (
                <FunnelBar
                  key={f.label}
                  label={f.label}
                  n={f.n}
                  max={max}
                  delay={24 + i * 26}
                  highlight={i === FUNNEL.length - 1}
                />
              ))}
            </div>
            <Callout
              big={<><span>{STAND_DOWN_PCT}</span>%</>}
              label="of sessions the desk stands down — every one with the exact gate and numbers in the journal"
              delay={200}
            />
          </div>
        </div>
      ) : (
        <div style={{opacity: phase2}}>
          <div style={{fontFamily: MONO, fontSize: 34, color: C.ink, marginBottom: 26}}>
            The Risk Officer — no discretion, no LLM path into it
          </div>
          <div
            style={{
              background: C.surface,
              border: `1px solid ${C.line}`,
              borderRadius: 14,
              padding: '30px 36px',
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
            }}
          >
            {RISK_LINES.map((l, i) => (
              <div
                key={i}
                style={{
                  fontFamily: MONO,
                  fontSize: 27,
                  color: l.includes('no LLM') ? C.accent : C.ink,
                  opacity: interpolate(frame, [560 + i * 10, 574 + i * 10], [0, 1], {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                  }),
                }}
              >
                {l}
              </div>
            ))}
          </div>
        </div>
      )}
    </SceneFrame>
  );
};
