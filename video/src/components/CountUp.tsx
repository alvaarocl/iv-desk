import React from 'react';
import {useCurrentFrame, spring, useVideoConfig} from 'remotion';

export const CountUp: React.FC<{
  to: number;
  from?: number;
  delay?: number;
  durationInFrames?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  style?: React.CSSProperties;
}> = ({to, from = 0, delay = 0, durationInFrames = 40, prefix = '', suffix = '', decimals = 0, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({
    frame: frame - delay,
    fps,
    durationInFrames,
    config: {damping: 200},
  });
  const v = from + (to - from) * s;
  return (
    <span style={{fontVariantNumeric: 'tabular-nums', ...style}}>
      {prefix}
      {v.toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals})}
      {suffix}
    </span>
  );
};
