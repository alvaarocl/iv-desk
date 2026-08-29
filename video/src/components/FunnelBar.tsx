import React from 'react';
import {useCurrentFrame, spring, useVideoConfig} from 'remotion';
import {C, MONO} from '../theme';

export const FunnelBar: React.FC<{
  label: string;
  n: number;
  max: number;
  delay: number;
  highlight?: boolean;
}> = ({label, n, max, delay, highlight}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const grow = spring({frame: frame - delay, fps, durationInFrames: 26, config: {damping: 200}});
  const w = (n / max) * grow;
  const col = highlight ? C.accent : C.muted;

  return (
    <div style={{opacity: spring({frame: frame - delay, fps, config: {damping: 200}})}}>
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
        <span style={{color: C.ink}}>{Math.round(n * grow)}</span>
      </div>
      <div style={{height: 26, background: C.surface2, borderRadius: 6, overflow: 'hidden'}}>
        <div
          style={{
            height: '100%',
            width: `${w * 100}%`,
            background: col,
            borderRadius: 6,
          }}
        />
      </div>
    </div>
  );
};
