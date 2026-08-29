import React from 'react';
import {Composition, Series, AbsoluteFill} from 'remotion';
import {C, FPS} from './theme';
import {SCENES, TOTAL_FRAMES} from './data';
import {S1_Hook} from './scenes/S1_Hook';
import {S2_Signal} from './scenes/S2_Signal';
import {S3_Desk} from './scenes/S3_Desk';
import {S4_Discipline} from './scenes/S4_Discipline';
import {S5_Execution} from './scenes/S5_Execution';
import {S6_Results} from './scenes/S6_Results';
import {S7_Close} from './scenes/S7_Close';

const Film: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: C.bg}}>
    <Series>
      <Series.Sequence durationInFrames={SCENES.hook}>
        <S1_Hook />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENES.signal}>
        <S2_Signal />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENES.desk}>
        <S3_Desk />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENES.discipline}>
        <S4_Discipline />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENES.execution}>
        <S5_Execution />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENES.results}>
        <S6_Results />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SCENES.close}>
        <S7_Close />
      </Series.Sequence>
    </Series>
  </AbsoluteFill>
);

export const Root: React.FC = () => (
  <Composition
    id="IVDesk"
    component={Film}
    durationInFrames={TOTAL_FRAMES}
    fps={FPS}
    width={1920}
    height={1080}
  />
);
