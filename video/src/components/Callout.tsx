import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {C, MONO, SANS, snap, glide} from '../theme';

export const Callout: React.FC<{
  big: React.ReactNode;
  label: string;
  delay?: number;
  color?: string;
}> = ({big, label, delay = 0, color = C.accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = glide(frame, fps, delay, 20);
  const labelS = snap(frame, fps, delay + 12);
  const punch = interpolate(frame - delay, [0, 8, 18], [0.86, 1.04, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <div style={{textAlign: 'center'}}>
      <div
        style={{
          fontFamily: MONO,
          fontWeight: 600,
          fontSize: 150,
          lineHeight: 1,
          color,
          opacity: Math.min(1, s),
          transform: `scale(${punch})`,
        }}
      >
        {big}
      </div>
      <div
        style={{
          fontFamily: SANS,
          fontSize: 26,
          color: C.muted,
          marginTop: 18,
          maxWidth: 820,
          marginLeft: 'auto',
          marginRight: 'auto',
          opacity: Math.min(1, labelS),
          transform: `translateY(${(1 - labelS) * 10}px)`,
        }}
      >
        {label}
      </div>
    </div>
  );
};
