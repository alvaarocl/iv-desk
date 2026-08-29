import React from 'react';
import {useCurrentFrame, interpolate} from 'remotion';
import {SceneFrame} from '../components/SceneFrame';
import {GateRow} from '../components/GateRow';
import {C, MONO} from '../theme';
import {GATES} from '../data';

export const S2_Signal: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <SceneFrame kicker="The signal · deterministic Python" center>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 38,
          color: C.ink,
          maxWidth: 1200,
          opacity: interpolate(frame, [8, 26], [0, 1], {extrapolateRight: 'clamp'}),
          transform: `translateY(${interpolate(frame, [8, 26], [12, 0], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          })}px)`,
        }}
      >
        It reads the option surface, not the price chart.
      </div>
      <div style={{display: 'flex', flexDirection: 'column', gap: 18}}>
        {GATES.map((g, i) => (
          <GateRow key={g.name} {...g} delay={40 + i * 40} />
        ))}
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 24,
          color: C.muted,
          opacity: interpolate(frame, [200, 220], [0, 1], {extrapolateRight: 'clamp'}),
        }}
      >
        three gates · any one stands the desk down · each writes the number that said no
      </div>
    </SceneFrame>
  );
};
