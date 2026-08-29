import React from 'react';
import {AbsoluteFill, useCurrentFrame, spring, useVideoConfig, interpolate} from 'remotion';
import {Grid} from '../components/Grid';
import {JsonBlock} from '../components/JsonBlock';
import {C, MONO, SANS} from '../theme';
import {TITLE, HOOK_SIGNAL} from '../data';

export const S1_Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const titleIn = spring({frame, fps, config: {damping: 200}});
  const titleOut = interpolate(frame, [110, 135], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const jsonIn = interpolate(frame, [120, 140], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{fontFamily: SANS}}>
      <Grid />
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          opacity: titleOut,
          transform: `scale(${interpolate(titleOut, [0, 1], [0.96, 1])})`,
        }}
      >
        <div
          style={{
            fontFamily: MONO,
            fontWeight: 600,
            fontSize: 132,
            letterSpacing: 6,
            color: C.ink,
            opacity: titleIn,
          }}
        >
          {TITLE.name}
        </div>
        <div
          style={{
            fontFamily: SANS,
            fontSize: 34,
            color: C.accent,
            marginTop: 10,
            opacity: interpolate(frame, [14, 34], [0, 1], {extrapolateRight: 'clamp'}),
          }}
        >
          {TITLE.tagline}
        </div>
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          opacity: jsonIn,
          transform: `translateY(${(1 - jsonIn) * 20}px)`,
        }}
      >
        <div style={{width: 900}}>
          <div
            style={{
              fontFamily: MONO,
              fontSize: 20,
              letterSpacing: 3,
              textTransform: 'uppercase',
              color: C.muted,
              marginBottom: 16,
            }}
          >
            data/journal.jsonl
          </div>
          <JsonBlock data={HOOK_SIGNAL} start={130} linesPerSecond={14} highlightKey="stand_down" />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
