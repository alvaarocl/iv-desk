import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {C, MONO, snap} from '../theme';

export const FunnelBar: React.FC<{
  label: string;
  n: number;
  max: number;
  delay: number;
  highlight?: boolean;
}> = ({label, n, max, delay, highlight}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = snap(frame, fps, delay);
  const grow = snap(frame, fps, delay + 4); // springy overshoot on the bar width
  const w = (n / max) * Math.min(1.02, Math.max(0, grow));
  const col = highlight ? C.accent : C.muted;
  const shownN = Math.round(n * Math.min(1, snap(frame, fps, delay + 4)));

  return (
    <div style={{opacity: Math.min(1, enter), transform: `translateY(${(1 - enter) * 14}px)`}}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontFamily: MONO,
          fontSize: 22,
          color: C.muted,
          marginBottom: 8,
        }}
      >
        <span style={{color: highlight ? C.ink : C.muted}}>{label}</span>
        <span style={{color: C.ink, fontVariantNumeric: 'tabular-nums'}}>{shownN}</span>
      </div>
      <div style={{height: 26, background: C.surface2, borderRadius: 6, overflow: 'hidden'}}>
        <div
          style={{
            height: '100%',
            width: `${Math.min(100, w * 100)}%`,
            background: col,
            borderRadius: 6,
            boxShadow: highlight ? `0 0 24px ${col}66` : 'none',
          }}
        />
      </div>
    </div>
  );
};
