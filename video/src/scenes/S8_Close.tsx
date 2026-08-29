import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {Grid} from '../components/Grid';
import {C, MONO, SANS, snap} from '../theme';
import {CLOSE, TITLE} from '../data';

export const S8_Close: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const lineS = snap(frame, fps, 4);
  const nameS = snap(frame, fps, 22);
  const metaS = snap(frame, fps, 38);
  return (
    <AbsoluteFill style={{fontFamily: SANS}}>
      <Grid />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div
          style={{
            fontFamily: SANS,
            fontSize: 32,
            color: C.ink,
            marginBottom: 36,
            maxWidth: 1100,
            textAlign: 'center',
            opacity: Math.min(1, lineS),
            transform: `translateY(${(1 - lineS) * 14}px)`,
          }}
        >
          {CLOSE.line} Go check us against it.
        </div>
        <div
          style={{
            fontFamily: MONO,
            fontWeight: 600,
            fontSize: 98,
            letterSpacing: 6,
            color: C.ink,
            opacity: Math.min(1, nameS),
            transform: `scale(${interpolate(Math.min(1, nameS), [0, 1], [0.95, 1])})`,
          }}
        >
          {TITLE.name}
        </div>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 26,
            color: C.muted,
            marginTop: 24,
            display: 'flex',
            gap: 28,
            opacity: Math.min(1, metaS),
          }}
        >
          <span style={{color: C.accent}}>{CLOSE.repo}</span>
          <span>·</span>
          <span>{CLOSE.account}</span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
