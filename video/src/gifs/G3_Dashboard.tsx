import React from 'react';
import {useCurrentFrame, interpolate} from 'remotion';
import {SceneFrame} from '../components/SceneFrame';
import {CountUp} from '../components/CountUp';
import {C, MONO, SANS} from '../theme';
import {DAY_GIF} from '../gifData';

const Tile: React.FC<{k: string; children: React.ReactNode}> = ({k, children}) => (
  <div
    style={{
      background: C.surface,
      border: `1px solid ${C.line}`,
      borderRadius: 14,
      padding: '22px 26px',
    }}
  >
    <div style={{fontFamily: MONO, fontSize: 16, letterSpacing: 2, textTransform: 'uppercase', color: C.muted}}>
      {k}
    </div>
    <div style={{fontFamily: MONO, fontSize: 44, color: C.ink, marginTop: 6}}>{children}</div>
  </div>
);

/** README GIF 3 — the day's operations, not a screenshot of dashboard/index.html (that page
 * is real and live at the URL in the README; this is the same brand look, counting up the
 * real 2 Sep numbers pulled from data/journal.jsonl). */
export const G3_Dashboard: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <SceneFrame kicker={`session ${DAY_GIF.date} · every tick logged`}>
      <div
        style={{
          fontFamily: SANS,
          fontSize: 30,
          color: C.ink,
          opacity: interpolate(frame, [0, 16], [0, 1], {extrapolateRight: 'clamp'}),
        }}
      >
        a full trading session, evaluated end to end
      </div>
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 18}}>
        <Tile k="signals evaluated">
          <CountUp to={DAY_GIF.signals} delay={20} />
        </Tile>
        <Tile k="underlyings">
          <CountUp to={DAY_GIF.underlyings} delay={32} />
        </Tile>
        <Tile k="shadow debates">
          <CountUp to={DAY_GIF.shadowDebates} delay={44} />
        </Tile>
        <Tile k="trades opened">
          <CountUp to={DAY_GIF.trades} delay={56} />
        </Tile>
        <Tile k="errors">
          <CountUp to={DAY_GIF.errors} delay={68} />
        </Tile>
        <Tile k="equity">
          <CountUp to={DAY_GIF.equity} delay={80} prefix="$" />
        </Tile>
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 22,
          color: C.muted,
          opacity: interpolate(frame, [180, 200], [0, 1], {extrapolateRight: 'clamp'}),
        }}
      >
        zero trades is a documented decision, not a silent one — see data/journal.jsonl
      </div>
    </SceneFrame>
  );
};
