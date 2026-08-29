import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {glide} from '../theme';

export const CountUp: React.FC<{
  to: number;
  from?: number;
  delay?: number;
  durationInFrames?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  style?: React.CSSProperties;
}> = ({to, from = 0, delay = 0, durationInFrames = 28, prefix = '', suffix = '', decimals = 0, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = glide(frame, fps, delay, durationInFrames);
  const v = from + (to - from) * Math.min(1, s);
  return (
    <span style={{fontVariantNumeric: 'tabular-nums', ...style}}>
      {prefix}
      {v.toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals})}
      {suffix}
    </span>
  );
};
