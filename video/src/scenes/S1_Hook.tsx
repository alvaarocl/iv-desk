import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {Grid} from '../components/Grid';
import {JsonBlock} from '../components/JsonBlock';
import {C, MONO, SANS, snap} from '../theme';
import {TITLE, HOOK_SIGNAL} from '../data';

export const S1_Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const t = snap(frame, fps, 4);
  const tagS = snap(frame, fps, 20);
  // title lifts up and fades as the JSON rises
  const handoff = interpolate(frame, [230, 270], [0, 1], {
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
          opacity: 1 - handoff,
          transform: `translateY(${handoff * -70}px)`,
        }}
      >
        <div
          style={{
            fontFamily: MONO,
            fontWeight: 600,
            fontSize: 134,
            letterSpacing: 6,
            color: C.ink,
            opacity: Math.min(1, t),
            transform: `translateY(${(1 - t) * 26}px)`,
          }}
        >
          {TITLE.name}
        </div>
        <div
          style={{
            fontFamily: SANS,
            fontSize: 34,
            color: C.accent,
            marginTop: 12,
            opacity: Math.min(1, tagS),
            transform: `translateY(${(1 - tagS) * 14}px)`,
          }}
        >
          {TITLE.tagline}
        </div>
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          opacity: handoff,
          transform: `translateY(${(1 - handoff) * 50}px)`,
        }}
      >
        <div style={{width: 940}}>
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
          <JsonBlock data={HOOK_SIGNAL} start={250} linesPerSecond={22} highlightKey="stand_down" />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
