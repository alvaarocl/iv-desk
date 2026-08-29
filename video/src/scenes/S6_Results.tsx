import React from 'react';
import {useCurrentFrame, interpolate} from 'remotion';
import {SceneFrame} from '../components/SceneFrame';
import {CountUp} from '../components/CountUp';
import {C, MONO, SANS} from '../theme';
import {RESULTS} from '../data';

const Sparkline: React.FC<{points: number[]}> = ({points}) => {
  const frame = useCurrentFrame();
  if (points.length < 2) return null;
  const w = 900;
  const h = 220;
  const lo = Math.min(...points, 100000);
  const hi = Math.max(...points, 100000);
  const span = hi - lo || 1;
  const grow = interpolate(frame, [10, 46], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const n = Math.max(2, Math.floor(points.length * grow));
  const d = points
    .slice(0, n)
    .map((p, i) => `${(i / (points.length - 1)) * w},${h - ((p - lo) / span) * h}`)
    .join(' ');
  return (
    <svg width={w} height={h} style={{overflow: 'visible'}}>
      <polyline points={d} fill="none" stroke={C.up} strokeWidth={3} />
    </svg>
  );
};

export const S6_Results: React.FC = () => {
  const frame = useCurrentFrame();
  const fadeLabel = interpolate(frame, [6, 22], [0, 1], {extrapolateRight: 'clamp'});

  if (RESULTS.mode === 'backtest') {
    const b = RESULTS.backtest;
    return (
      <SceneFrame kicker="Results" center>
        <div style={{textAlign: 'center'}}>
          <div
            style={{
              fontFamily: MONO,
              fontSize: 20,
              letterSpacing: 3,
              textTransform: 'uppercase',
              color: C.accent,
              border: `1px solid ${C.accent}`,
              borderRadius: 999,
              padding: '6px 18px',
              display: 'inline-block',
              opacity: fadeLabel,
            }}
          >
            backtest — not the competition window
          </div>
          <div style={{fontFamily: MONO, fontWeight: 600, fontSize: 150, color: C.up, marginTop: 34}}>
            <CountUp to={b.pnl} prefix="+$" delay={20} />
          </div>
          <div style={{fontFamily: SANS, fontSize: 30, color: C.muted, marginTop: 14}}>
            held to expiry · {b.trades} trades · {b.sessions} real sessions · IV / RV median{' '}
            {b.ivrv_median.toFixed(2)}
          </div>
          <div
            style={{
              fontFamily: SANS,
              fontSize: 26,
              color: C.ink,
              marginTop: 40,
              maxWidth: 900,
              marginLeft: 'auto',
              marginRight: 'auto',
              opacity: interpolate(frame, [70, 90], [0, 1], {extrapolateRight: 'clamp'}),
            }}
          >
            Four sessions of live P&amp;L is a coin flip. An agent that documents every trade it
            didn&rsquo;t take is not.
          </div>
        </div>
      </SceneFrame>
    );
  }

  // mode === 'live' — filled Thu 3 Sep
  const l = RESULTS.live;
  return (
    <SceneFrame kicker="Results · competition window · Mon–Thu" center>
      <div style={{textAlign: 'center'}}>
        <Sparkline points={l.equityCurve} />
        <div
          style={{
            fontFamily: MONO,
            fontWeight: 600,
            fontSize: 130,
            color: l.pnl >= 0 ? C.up : C.down,
            marginTop: 20,
          }}
        >
          <CountUp to={l.pnl} prefix={l.pnl >= 0 ? '+$' : '−$'} delay={20} />
        </div>
        <div style={{fontFamily: SANS, fontSize: 28, color: C.muted, marginTop: 12}}>
          {l.trades} trades · {l.winRate}% wins · {l.standDowns} documented stand-downs ·{' '}
          {l.predictionsCorrect} predictions correct
        </div>
      </div>
    </SceneFrame>
  );
};
