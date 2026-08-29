import React from 'react';
import {useCurrentFrame, spring, useVideoConfig} from 'remotion';
import {C, MONO, SANS} from '../theme';

export const Callout: React.FC<{
  big: React.ReactNode;
  label: string;
  delay?: number;
  color?: string;
}> = ({big, label, delay = 0, color = C.accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - delay, fps, config: {damping: 200}});
  return (
    <div style={{opacity: s, transform: `translateY(${(1 - s) * 16}px)`, textAlign: 'center'}}>
      <div style={{fontFamily: MONO, fontWeight: 600, fontSize: 140, lineHeight: 1, color}}>
        {big}
      </div>
      <div
        style={{
          fontFamily: SANS,
          fontSize: 26,
          color: C.muted,
          marginTop: 18,
          maxWidth: 780,
          marginLeft: 'auto',
          marginRight: 'auto',
        }}
      >
        {label}
      </div>
    </div>
  );
};
