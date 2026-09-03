/**
 * Every string and number the video shows. THIS is the only file to touch on Thu 3 Sep:
 * flip `results.mode` to "live" and fill the live block, then `npm run render`.
 *
 * All figures below are traceable:
 *  - funnel / trades / P&L  -> backtest/RESULTS.md (60 real sessions, calibrated config)
 *  - debate transcript      -> a real run against Featherless (issue #32)
 *  - risk gates             -> agent/config.py + agent/risk.py
 */

import {FPS} from './theme';

const sec = (s: number) => Math.round(s * FPS);

// Per-scene lengths (frames @ 60fps). Sized to the narration + kept moving throughout, so
// nothing sits static. TransitionSeries overlaps eat ~0.3s per cut. Total render ~3:10.
export const SCENES = {
  hook: sec(21),
  signal: sec(35),
  desk: sec(33),
  funnel: sec(25),
  risk: sec(21),
  execution: sec(25),
  results: sec(23),
  close: sec(11),
};

export const TRANSITION = 18; // frames of overlap between scenes

export const TITLE = {
  name: 'IV DESK',
  tagline: 'an options desk that knows when not to trade',
};

// A real `signal` journal record (weekend tape) — stands down on the VRP gate.
export const HOOK_SIGNAL = {
  event: 'signal',
  underlying: 'SPY',
  sell_premium: false,
  vrp_ratio: 0.9,
  gex_norm: -0.02,
  regime: 'chop',
  stand_down: 'vrp',
  notes: 'IV 16.6% vs RV_hat 16.6%; ratio 0.90 < 1.05',
};

export const GATES = [
  {
    name: 'VRP ratio',
    rule: 'ATM_IV / RV_hat  ≥  1.05',
    value: '0.90',
    detail: 'implied vol under realized — no premium to sell',
    pass: false,
  },
  {
    name: 'Dealer gamma',
    rule: 'gamma exposure  ≥  0.03',
    value: '−0.02',
    detail: 'dealers short gamma — trending, not mean-reverting',
    pass: false,
  },
  {
    name: 'Regime',
    rule: 'not trending',
    value: 'chop',
    detail: 'ADX / EMA read — range-bound, this gate is clear',
    pass: true,
  },
];

// From a real debate run (issue #32).
export const DEBATE = {
  quant: [
    {model: 'Qwen2.5-32B', vote: 'confirm'},
    {model: 'Hermes-3-70B', vote: 'confirm'},
    {model: 'Mistral-Nemo', vote: 'confirm'},
  ],
  verdict: '3 / 3 confirm',
  bull: {cited: ['gex', 'atm_iv', 'rv_hat', 'skew', 'regime']},
  bear: {cited: ['gex_state', 'atm_iv', 'rv_hat', 'regime']},
  head: {
    decision: 'approve',
    contracts: 3,
    cap: 3,
    thesis: 'SPY stays range-bound between 626 and 639 through 2026-09-03',
    prediction: {low: 625, high: 640, date: '2026-09-03'},
  },
  clamp: 'contracts = max(0, min(int(head.contracts), cap))',
};

// backtest/RESULTS.md, calibrated config
export const FUNNEL = [
  {label: 'underlying-sessions evaluated', n: 174},
  {label: 'VRP ratio ≥ 1.05', n: 48},
  {label: 'dealer gamma + regime', n: 13},
  {label: 'trades opened', n: 11},
];

export const STAND_DOWN_PCT = 94; // 163 of 174

export const RISK_LINES = [
  'per-trade max loss  ≤  0.5% NAV',
  'portfolio open risk  ≤  10% NAV',
  '≤ 8 concurrent positions   ·   net delta band  ±0.30',
  '−3% daily-loss breaker   ·   drawdown halt at 12%',
  'macro-event blackout: 2h before a print, 45m after',
  'no LLM path into evaluate()  —  ever',
];

export const EXECUTION = {
  legs: [
    {k: 'sell put', v: '628'},
    {k: 'buy put', v: '626'},
    {k: 'sell call', v: '637'},
    {k: 'buy call', v: '639'},
  ],
  order: 'alpaca api POST /v2/orders   { "order_class": "mleg", "limit_price": "-0.54" }',
  exits: ['take profit  —  50% of credit', 'stop  —  2× credit', 'time  —  close on expiry day'],
  cron: 'a 15-minute cron · reconciles against Alpaca every tick',
};

// --- RESULTS: flip to "live" on Thu 3 Sep -------------------------------------
export const RESULTS: {
  mode: 'backtest' | 'live';
  backtest: {pnl: number; trades: number; sessions: number; ivrv_median: number};
  live: {
    pnl: number;
    trades: number;
    winRate: number;
    standDowns: number;
    predictionsCorrect: string;
    equityCurve: number[];
    // One sentence, written by hand Thu night — the framing genuinely differs by outcome, so
    // this is not auto-templated from the numbers above. Two honest drafts to start from:
    //   0 trades:  "Three sessions in, dealer gamma stayed negative on SPY, QQQ and IWM almost
    //               the entire window — the desk declined rich premium (VRP up to 1.6x) it
    //               judged unsafe to sell. That is the strategy working, not a bot that never
    //               fired."
    //   >=1 trade: "The desk opened {trades} trade(s) and stood down {standDowns} times over
    //               four sessions — every one of those refusals is in the journal with the
    //               gate that caused it. Four sessions is a coin flip either way; the record of
    //               why is not."
    verdict: string;
  };
} = {
  mode: 'live',
  backtest: {pnl: 484, trades: 11, sessions: 60, ivrv_median: 0.9},
  live: {
    pnl: 318.85,
    trades: 1,
    winRate: 100,
    standDowns: 295,
    predictionsCorrect: '1 / 1',
    // Sampled from data/equity.csv (31 points): flat through three sessions of stand-downs,
    // then the one QQQ trade opens Thu afternoon and rides to the close.
    equityCurve: [
      100000, 100000, 100000, 100000, 100000, 100000, 100000, 100000, 100000, 100000, 100000,
      100000, 100000, 100000, 100000, 100000, 100000, 100000, 100000, 100000, 100000, 100000,
      100047.2, 100111.2, 100111.2, 100191.2, 100159.2, 100247.2, 100303.2, 100319.2, 100318.85,
    ],
    verdict:
      'The desk opened one trade in four sessions — a QQQ iron condor, cleared by every gate ' +
      'and a live debate — and it closed inside every strike, the exact outcome the structure ' +
      'was built for. 295 other times, it looked and said no, with a reason.',
  },
};

export const CLOSE = {
  repo: 'github.com/alvaarocl/iv-desk',
  account: 'PA39HSCQE8S3',
  line: 'The journal is in the repo — every signal, every refusal, every trade.',
};
