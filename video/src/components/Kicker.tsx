import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {C, MONO, snap} from '../theme';

export const Kicker: React.FC<{children: React.ReactNode; delay?: number}> = ({
  children,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = snap(frame, fps, delay);
  return (
    <div
      style={{
        fontFamily: MONO,
        fontSize: 22,
        letterSpacing: 4,
        textTransform: 'uppercase',
        color: C.muted,
        opacity: Math.min(1, s),
        transform: `translateX(${(1 - s) * -18}px)`,
      }}
    >
      {children}
    </div>
  );
};
