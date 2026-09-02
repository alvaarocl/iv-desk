import React from 'react';
import {Composition, AbsoluteFill} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {slide} from '@remotion/transitions/slide';
import {wipe} from '@remotion/transitions/wipe';
import {C, FPS} from './theme';
import {SCENES, TRANSITION} from './data';
import {S1_Hook} from './scenes/S1_Hook';
import {S2_Signal} from './scenes/S2_Signal';
import {S3_Desk} from './scenes/S3_Desk';
import {S4_Funnel} from './scenes/S4_Funnel';
import {S5_Risk} from './scenes/S5_Risk';
import {S6_Execution} from './scenes/S6_Execution';
import {S7_Results} from './scenes/S7_Results';
import {S8_Close} from './scenes/S8_Close';
import {G1_StandDown} from './gifs/G1_StandDown';
import {G2_Debate} from './gifs/G2_Debate';
import {G3_Dashboard} from './gifs/G3_Dashboard';
import {gsec} from './gifData';

const timing = linearTiming({durationInFrames: TRANSITION});

const Film: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: C.bg}}>
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={SCENES.hook}>
        <S1_Hook />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={slide({direction: 'from-right'})} timing={timing} />

      <TransitionSeries.Sequence durationInFrames={SCENES.signal}>
        <S2_Signal />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={slide({direction: 'from-right'})} timing={timing} />

      <TransitionSeries.Sequence durationInFrames={SCENES.desk}>
        <S3_Desk />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={wipe({direction: 'from-left'})} timing={timing} />

      <TransitionSeries.Sequence durationInFrames={SCENES.funnel}>
        <S4_Funnel />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={slide({direction: 'from-bottom'})} timing={timing} />

      <TransitionSeries.Sequence durationInFrames={SCENES.risk}>
        <S5_Risk />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={slide({direction: 'from-right'})} timing={timing} />

      <TransitionSeries.Sequence durationInFrames={SCENES.execution}>
        <S6_Execution />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={slide({direction: 'from-right'})} timing={timing} />

      <TransitionSeries.Sequence durationInFrames={SCENES.results}>
        <S7_Results />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={wipe({direction: 'from-bottom-right'})} timing={timing} />

      <TransitionSeries.Sequence durationInFrames={SCENES.close}>
        <S8_Close />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  </AbsoluteFill>
);

const TOTAL =
  Object.values(SCENES).reduce((a, b) => a + b, 0) - 7 * TRANSITION;

// README GIFs — separate short compositions, not part of the narrated Film above. Each holds
// its last frame for ~1s before ending so `ffmpeg -loop 0` doesn't jump-cut on repeat. Render
// with `npm run gifs`, then convert with the ffmpeg recipe in assets/GIFS.md.
const GIF_FPS = 60;
const GIF_W = 1600;
const GIF_H = 900;

export const Root: React.FC = () => (
  <>
    <Composition
      id="IVDesk"
      component={Film}
      durationInFrames={TOTAL}
      fps={FPS}
      width={1920}
      height={1080}
    />
    <Composition
      id="Gif1StandDown"
      component={G1_StandDown}
      durationInFrames={gsec(6.5)}
      fps={GIF_FPS}
      width={GIF_W}
      height={GIF_H}
    />
    <Composition
      id="Gif2Debate"
      component={G2_Debate}
      durationInFrames={gsec(8)}
      fps={GIF_FPS}
      width={GIF_W}
      height={GIF_H}
    />
    <Composition
      id="Gif3Dashboard"
      component={G3_Dashboard}
      durationInFrames={gsec(6.5)}
      fps={GIF_FPS}
      width={GIF_W}
      height={GIF_H}
    />
  </>
);
