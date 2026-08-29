import React from 'react';
import {useCurrentFrame, spring, useVideoConfig} from 'remotion';
import {C, MONO} from '../theme';

export const Kicker: React.FC<{children: React.ReactNode; delay?: number}> = ({
  children,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - delay, fps, config: {damping: 200}});
  return (
    <div
      style={{
        fontFamily: MONO,
        fontSize: 22,
        letterSpacing: 4,
        textTransform: 'uppercase',
        color: C.muted,
        opacity: s,
        transform: `translateY(${(1 - s) * 12}px)`,
      }}
    >
      {children}
    </div>
  );
};
