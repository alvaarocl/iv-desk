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

// Scene durations (frames). Tuned ~10% over the narration word count. Total ~2:52.
export const SCENES = {
  hook: sec(17),
  signal: sec(33),
  desk: sec(32),
  discipline: sec(40),
  execution: sec(23),
  results: sec(20),
  close: sec(9),
};

export const TOTAL_FRAMES = Object.values(SCENES).reduce((a, b) => a + b, 0);

export const TITLE = {
  name: 'IV DESK',
  tagline: 'an options desk that knows when not to trade',
};

// A real `signal` journal record (SPY, weekend tape) — stands down on the VRP gate.
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

// From a real debate run (issue #32). Compressed for the screen.
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
  '≤ 8 concurrent positions   |   net delta band  ±0.30',
  '−3% daily-loss breaker   |   drawdown halt at 12%',
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
  cron: 'every 15 min · reconciles against Alpaca as the source of truth',
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
  };
} = {
  mode: 'backtest',
  backtest: {pnl: 484, trades: 11, sessions: 60, ivrv_median: 0.9},
  live: {
    pnl: 0,
    trades: 0,
    winRate: 0,
    standDowns: 0,
    predictionsCorrect: '0 / 0',
    equityCurve: [100000],
  },
};

export const CLOSE = {
  repo: 'github.com/alvaarocl/iv-desk',
  account: 'PA39HSCQE8S3',
  line: 'The journal is in the repo.',
};
