import React from 'react';
import {useCurrentFrame} from 'remotion';

/** Reveals `text` character by character between `start` and `start + durationInFrames`. */
export const TypeOn: React.FC<{
  text: string;
  start?: number;
  durationInFrames?: number;
  style?: React.CSSProperties;
  cursor?: boolean;
}> = ({text, start = 0, durationInFrames = 45, style, cursor = true}) => {
  const frame = useCurrentFrame();
  const p = Math.max(0, Math.min(1, (frame - start) / durationInFrames));
  const shown = text.slice(0, Math.round(p * text.length));
  const blink = cursor && p < 1 && Math.floor(frame / 8) % 2 === 0;
  return (
    <span style={style}>
      {shown}
      {blink ? '▋' : ''}
    </span>
  );
};
