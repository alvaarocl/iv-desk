import React from 'react';
import {useCurrentFrame, interpolate} from 'remotion';
import {SceneFrame} from '../components/SceneFrame';
import {JsonBlock} from '../components/JsonBlock';
import {C, MONO} from '../theme';
import {STAND_DOWN_GIF} from '../gifData';

/** README GIF 1 — the desk refusing to trade. Real IWM signal, 2 Sep: VRP is rich (1.33)
 * but dealer gamma vetoes it (-0.686). Loops clean: holds the last frame ~1s before the
 * composition ends, so a looping GIF doesn't jump-cut. */
export const G1_StandDown: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <SceneFrame kicker="data/journal.jsonl · live">
      <div
        style={{
          fontFamily: MONO,
          fontSize: 34,
          color: C.ink,
          opacity: interpolate(frame, [0, 14], [0, 1], {extrapolateRight: 'clamp'}),
        }}
      >
        rich premium (VRP 1.33) — vetoed anyway
      </div>
      <JsonBlock data={STAND_DOWN_GIF} start={16} linesPerSecond={16} fontSize={26} highlightKey="stand_down" />
      <div
        style={{
          fontFamily: MONO,
          fontSize: 24,
          color: C.down,
          opacity: interpolate(frame, [150, 170], [0, 1], {extrapolateRight: 'clamp'}),
        }}
      >
        dealers short gamma — selling premium here is how short-vol books blow up
      </div>
    </SceneFrame>
  );
};
