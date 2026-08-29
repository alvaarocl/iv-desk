import React from 'react';
import {SceneFrame} from '../components/SceneFrame';
import {FunnelBar} from '../components/FunnelBar';
import {Callout} from '../components/Callout';
import {FUNNEL, STAND_DOWN_PCT} from '../data';

export const S4_Funnel: React.FC = () => {
  const max = FUNNEL[0].n;
  return (
    <SceneFrame kicker="Discipline · 60 real sessions · 3 underlyings" center>
      <div style={{display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 60, alignItems: 'center'}}>
        <div style={{display: 'flex', flexDirection: 'column', gap: 24}}>
          {FUNNEL.map((f, i) => (
            <FunnelBar
              key={f.label}
              label={f.label}
              n={f.n}
              max={max}
              delay={16 + i * 22}
              highlight={i === FUNNEL.length - 1}
            />
          ))}
        </div>
        <Callout
          big={
            <>
              <span>{STAND_DOWN_PCT}</span>%
            </>
          }
          label="of sessions the desk stands down — every one with the exact gate and numbers in the journal"
          delay={130}
        />
      </div>
    </SceneFrame>
  );
};
