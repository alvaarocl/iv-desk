import React from 'react';
import {AbsoluteFill, useCurrentFrame, spring, useVideoConfig} from 'remotion';
import {Grid} from '../components/Grid';
import {C, MONO, SANS} from '../theme';
import {CLOSE, TITLE} from '../data';

export const S7_Close: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame, fps, config: {damping: 200}});
  return (
    <AbsoluteFill style={{fontFamily: SANS}}>
      <Grid />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: s}}>
        <div style={{fontFamily: SANS, fontSize: 34, color: C.ink, marginBottom: 40}}>
          {CLOSE.line} Go check us against it.
        </div>
        <div style={{fontFamily: MONO, fontWeight: 600, fontSize: 96, letterSpacing: 6, color: C.ink}}>
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
