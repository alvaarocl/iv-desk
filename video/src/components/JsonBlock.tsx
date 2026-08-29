import React from 'react';
import {useCurrentFrame, interpolate} from 'remotion';
import {C, MONO} from '../theme';

/** Pretty-prints an object and reveals it line by line. Keys in accent, strings in ink,
 *  numbers in up, booleans in down/up. One optional highlighted line. */
export const JsonBlock: React.FC<{
  data: unknown;
  start?: number;
  linesPerSecond?: number;
  fontSize?: number;
  highlightKey?: string;
}> = ({data, start = 0, linesPerSecond = 10, fontSize = 24, highlightKey}) => {
  const frame = useCurrentFrame();
  const text = JSON.stringify(data, null, 2);
  const lines = text.split('\n');
  const shown = Math.max(0, Math.floor(((frame - start) / 30) * linesPerSecond));

  return (
    <pre
      style={{
        fontFamily: MONO,
        fontSize,
        lineHeight: 1.55,
        color: C.ink,
        margin: 0,
        background: C.surface,
        border: `1px solid ${C.line}`,
        borderRadius: 12,
        padding: '26px 30px',
      }}
    >
      {lines.slice(0, shown).map((ln, i) => {
        const isHl = highlightKey && ln.includes(`"${highlightKey}"`);
        return (
          <div
            key={i}
            style={{
              background: isHl ? `${C.accent}1f` : 'transparent',
              borderRadius: 4,
              opacity: interpolate(frame - start - (i * 30) / linesPerSecond, [0, 6], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              }),
            }}
          >
            {colorize(ln)}
          </div>
        );
      })}
    </pre>
  );
};

function colorize(line: string): React.ReactNode {
  const m = line.match(/^(\s*)"([^"]+)":\s*(.*)$/);
  if (m) {
    const [, indent, key, rest] = m;
    return (
      <>
        {indent}
        <span style={{color: C.accent}}>&quot;{key}&quot;</span>
        <span style={{color: C.muted}}>: </span>
        {colorizeValue(rest)}
      </>
    );
  }
  return <span style={{color: C.muted}}>{line}</span>;
}

function colorizeValue(v: string): React.ReactNode {
  const trimmed = v.replace(/,\s*$/, '');
  const comma = v.endsWith(',') ? ',' : '';
  let color: string = C.ink;
  if (/^-?\d/.test(trimmed)) color = C.up;
  else if (trimmed === 'true') color = C.up;
  else if (trimmed === 'false') color = C.down;
  else if (trimmed === '{' || trimmed === '[' || trimmed === '}' || trimmed === ']')
    color = C.muted;
  return (
    <>
      <span style={{color}}>{trimmed}</span>
      <span style={{color: C.muted}}>{comma}</span>
    </>
  );
}
