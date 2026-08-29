import React from 'react';
import {useCurrentFrame, spring, useVideoConfig, interpolate} from 'remotion';
import {C, MONO, SANS} from '../theme';

export const GateRow: React.FC<{
  name: string;
  rule: string;
  value: string;
  detail: string;
  pass: boolean;
  delay: number;
}> = ({name, rule, value, detail, pass, delay}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame: frame - delay, fps, config: {damping: 200}});
  const resolve = spring({frame: frame - delay - 14, fps, config: {damping: 200}});
  const col = pass ? C.up : C.down;

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '400px 1fr 280px',
        alignItems: 'center',
        gap: 24,
        padding: '24px 34px',
        borderRadius: 14,
        background: C.surface,
        border: `1px solid ${C.line}`,
        opacity: enter,
        transform: `translateX(${(1 - enter) * -40}px)`,
      }}
    >
      <div>
        <div style={{fontFamily: MONO, fontSize: 30, color: C.ink}}>{name}</div>
        <div
          style={{fontFamily: SANS, fontSize: 18, color: C.muted, marginTop: 4, lineHeight: 1.3}}
        >
          {detail}
        </div>
      </div>
      <div style={{fontFamily: MONO, fontSize: 22, color: C.muted}}>{rule}</div>
      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 14}}>
        <span
          style={{
            fontFamily: MONO,
            fontSize: 26,
            color: col,
            opacity: resolve,
            whiteSpace: 'nowrap',
          }}
        >
          {value}
        </span>
        <span
          style={{
            fontFamily: MONO,
            fontSize: 15,
            letterSpacing: 2,
            textTransform: 'uppercase',
            color: col,
            border: `1px solid ${col}`,
            borderRadius: 999,
            padding: '4px 12px',
            opacity: resolve,
            transform: `scale(${interpolate(resolve, [0, 1], [0.8, 1])})`,
          }}
        >
          {pass ? 'pass' : 'stand down'}
        </span>
      </div>
    </div>
  );
};
