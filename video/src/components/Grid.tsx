import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate} from 'remotion';
import {C} from '../theme';

/** Ambient background: a faint grid and one slow horizontal scan line. Deliberately quiet. */
export const Grid: React.FC = () => {
  const frame = useCurrentFrame();
  const scanY = interpolate(frame % 300, [0, 300], [0, 1080]);
  return (
    <AbsoluteFill style={{backgroundColor: C.bg}}>
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${C.line} 1px, transparent 1px), linear-gradient(90deg, ${C.line} 1px, transparent 1px)`,
          backgroundSize: '72px 72px',
          opacity: 0.18,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(1200px 700px at 50% 42%, transparent, ${C.bg} 78%)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: scanY,
          height: 2,
          background: `linear-gradient(90deg, transparent, ${C.accent}22, transparent)`,
        }}
      />
    </AbsoluteFill>
  );
};
