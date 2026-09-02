/**
 * Real numbers for the three README GIFs — pulled straight from data/journal.jsonl on
 * 2 Sep 2026 (Wed, session 3 of 4), not fabricated for the demo. Unlike data.ts (the main
 * narrated video, which locks its numbers Thu 3 Sep at the close), these are a live snapshot:
 * re-run `scripts` below against the journal any time before final submission to refresh.
 *
 * Traceability:
 *  - STAND_DOWN_GIF  -> a real IWM `signal` event, stand_down: gex, rich VRP anyway
 *  - DEBATE_GIF      -> a real shadow debate (agent/desk.py:_maybe_shadow_debate), SPY,
 *                       2/3 quant confirm, Desk Head vetoes on the GEX/IV mismatch
 *  - DAY_GIF         -> the day's full signal/debate count, computed from the journal
 */

import {FPS} from './theme';

export const gsec = (s: number) => Math.round(s * FPS);

export const STAND_DOWN_GIF = {
  event: 'signal',
  underlying: 'IWM',
  vrp_ratio: 1.33,
  atm_iv: 0.1684,
  rv_hat: 0.1266,
  gex_norm: -0.6861,
  gex_state: -1,
  regime: 'chop',
  sell_premium: false,
  stand_down: 'gex',
  notes: 'IV 16.8% vs RV_hat 12.7% (ratio 1.33 vs 1.05); GEX_norm -0.686; STAND DOWN [gex]',
};

export const DEBATE_GIF = {
  underlying: 'SPY',
  shadow: true,
  quant: {verdict: 'confirm', reason: '2/3 models confirm iron_condor'},
  bull: {
    argument:
      'GEX is strongly negative at -0.106 normalized, well outside the typical range — high probability the underlying stays inside the condor.',
    cited: ['gex', 'gex_norm', 'skew'],
  },
  bear: {
    argument:
      'ATM IV 14.3% vs RV_hat 8.9% is a real gap — room for a large move. Regime is choppy, which raises whipsaw risk.',
    cited: ['gex', 'atm_iv', 'rv_hat', 'regime'],
  },
  adversarial: true,
  similarity: 0.082,
  head: {
    decision: 'veto',
    thesis: 'The GEX signal must be strong enough to overcome the high ATM IV and choppy regime for this trade to win.',
  },
};

export const DAY_GIF = {
  date: '2026-09-02',
  signals: 84,
  underlyings: 3,
  shadowDebates: 2,
  trades: 0,
  equity: 100000,
  errors: 0,
};
