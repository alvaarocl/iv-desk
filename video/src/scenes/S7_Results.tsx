import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {SceneFrame} from '../components/SceneFrame';
import {CountUp} from '../components/CountUp';
import {C, MONO, SANS, snap} from '../theme';
import {RESULTS} from '../data';

const Sparkline: React.FC<{points: number[]}> = ({points}) => {
  const frame = useCurrentFrame();
  if (points.length < 2) return null;
  const w = 900;
  const h = 220;
  const lo = Math.min(...points, 100000);
  const hi = Math.max(...points, 100000);
  const span = hi - lo || 1;
  const grow = interpolate(frame, [12, 60], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
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

export const S7_Results: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pillS = snap(frame, fps, 6);

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
              opacity: Math.min(1, pillS),
              transform: `translateY(${(1 - pillS) * -10}px)`,
            }}
          >
            backtest — not the competition window
          </div>
          <div style={{fontFamily: MONO, fontWeight: 600, fontSize: 152, color: C.up, marginTop: 34}}>
            <CountUp to={b.pnl} prefix="+$" delay={24} durationInFrames={26} />
          </div>
          <div style={{fontFamily: SANS, fontSize: 30, color: C.muted, marginTop: 14,
            opacity: interpolate(frame, [40, 58], [0, 1], {extrapolateRight: 'clamp'})}}>
            held to expiry · {b.trades} trades · {b.sessions} real sessions · IV / RV median{' '}
            {b.ivrv_median.toFixed(2)}
          </div>
          <div
            style={{
              fontFamily: SANS,
              fontSize: 26,
              color: C.ink,
              marginTop: 40,
              maxWidth: 940,
              marginLeft: 'auto',
              marginRight: 'auto',
              opacity: interpolate(frame, [80, 100], [0, 1], {extrapolateRight: 'clamp'}),
              transform: `translateY(${interpolate(frame, [80, 100], [12, 0], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              })}px)`,
            }}
          >
            Four sessions of live P&amp;L is a coin flip. An agent that documents every trade it
            didn&rsquo;t take is not.
          </div>
        </div>
      </SceneFrame>
    );
  }

  const l = RESULTS.live;
  return (
    <SceneFrame kicker="Results · competition window · Mon–Thu" center>
      <div style={{textAlign: 'center'}}>
        <Sparkline points={l.equityCurve} />
        <div
          style={{
            fontFamily: MONO,
            fontWeight: 600,
            fontSize: 132,
            color: l.pnl >= 0 ? C.up : C.down,
            marginTop: 20,
          }}
        >
          <CountUp to={l.pnl} prefix={l.pnl >= 0 ? '+$' : '−$'} delay={24} />
        </div>
        <div style={{fontFamily: SANS, fontSize: 28, color: C.muted, marginTop: 12}}>
          {l.trades} trades · {l.winRate}% wins · {l.standDowns} documented stand-downs ·{' '}
          {l.predictionsCorrect} predictions correct
        </div>
        <div
          style={{
            fontFamily: SANS,
            fontSize: 26,
            color: C.ink,
            marginTop: 40,
            maxWidth: 940,
            marginLeft: 'auto',
            marginRight: 'auto',
            opacity: interpolate(frame, [80, 100], [0, 1], {extrapolateRight: 'clamp'}),
            transform: `translateY(${interpolate(frame, [80, 100], [12, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })}px)`,
          }}
        >
          {l.verdict}
        </div>
      </div>
    </SceneFrame>
  );
};
