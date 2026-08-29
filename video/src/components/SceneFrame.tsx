import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Grid} from './Grid';
import {Kicker} from './Kicker';
import {SANS, C} from '../theme';

export const SceneFrame: React.FC<{
  kicker?: string;
  children: React.ReactNode;
  center?: boolean;
}> = ({kicker, children, center}) => (
  <AbsoluteFill style={{fontFamily: SANS, color: C.ink}}>
    <Grid />
    {kicker ? (
      <div style={{position: 'absolute', top: 86, left: 120}}>
        <Kicker>{kicker}</Kicker>
      </div>
    ) : null}
    <AbsoluteFill
      style={{
        padding: center ? '150px 120px 120px' : '150px 120px 100px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: center ? 'center' : 'flex-start',
        gap: 36,
      }}
    >
      {children}
    </AbsoluteFill>
  </AbsoluteFill>
);
