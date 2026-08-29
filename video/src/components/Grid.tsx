import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate} from 'remotion';
import {C} from '../theme';

/** Ambient background: a drifting grid and a quick scan line. Keeps the frame alive without
 *  competing with the content. */
export const Grid: React.FC = () => {
  const frame = useCurrentFrame();
  const drift = interpolate(frame % 720, [0, 720], [0, 72]); // one grid cell per 12s
  const scanY = interpolate(frame % 210, [0, 210], [-40, 1120]);
  const scanFade = interpolate(frame % 210, [0, 20, 190, 210], [0, 1, 1, 0]);
  return (
    <AbsoluteFill style={{backgroundColor: C.bg}}>
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${C.line} 1px, transparent 1px), linear-gradient(90deg, ${C.line} 1px, transparent 1px)`,
          backgroundSize: '72px 72px',
          backgroundPosition: `${drift}px ${drift * 0.6}px`,
          opacity: 0.16,
        }}
      />
      <AbsoluteFill
        style={{background: `radial-gradient(1300px 760px at 50% 44%, transparent, ${C.bg} 76%)`}}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: scanY,
          height: 2,
          opacity: scanFade * 0.9,
          background: `linear-gradient(90deg, transparent, ${C.accent}33, transparent)`,
        }}
      />
    </AbsoluteFill>
  );
};
