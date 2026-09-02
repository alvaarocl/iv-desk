import {loadFont as loadMono} from '@remotion/google-fonts/IBMPlexMono';
import {loadFont as loadSans} from '@remotion/google-fonts/IBMPlexSans';
import {spring} from 'remotion';

const mono = loadMono('normal', {weights: ['400', '500', '600']});
const sans = loadSans('normal', {weights: ['400', '500', '600', '700']});

export const MONO = mono.fontFamily;
export const SANS = sans.fontFamily;

// Operations-board palette — matches dashboard/index.html and docs/internal/estado.html.
export const C = {
  bg: '#13161b',
  surface: '#1b1f26',
  surface2: '#232830',
  ink: '#e9e7e1',
  muted: '#969ca6',
  line: '#2c323c',
  accent: '#e0a83d',
  up: '#5fb87a',
  down: '#cf6b5c',
  todo: '#667085',
} as const;

export const FPS = 60;

/** Snappy entrance — settles in ~10 frames with a tiny overshoot. Use everywhere. */
export const snap = (frame: number, fps: number, delay = 0) =>
  spring({
    frame: frame - delay,
    fps,
    config: {damping: 18, stiffness: 160, mass: 0.7},
  });

/** Softer, for hero numbers that should feel weighty, not bouncy. */
export const glide = (frame: number, fps: number, delay = 0, durationInFrames = 24) =>
  spring({frame: frame - delay, fps, durationInFrames, config: {damping: 26, stiffness: 90}});
