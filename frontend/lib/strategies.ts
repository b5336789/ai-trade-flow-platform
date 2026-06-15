// Strategy parameter defaults (keys match the backend constructor kwargs).
export const STRATEGY_PARAMS: Record<string, Record<string, number>> = {
  ma_cross: { fast: 10, slow: 20 },
  rsi: { window: 14 },
  macd: { window_fast: 12, window_slow: 26, window_sign: 9 },
  bollinger: { window: 20, window_dev: 2 },
};

export const STRATEGY_NAMES = Object.keys(STRATEGY_PARAMS);

// Default grids used by the "Optimize" button (kept small to stay under the combo cap).
export const OPTIMIZE_GRID: Record<string, Record<string, number[]>> = {
  ma_cross: { fast: [5, 10, 15], slow: [20, 30, 40] },
  rsi: { window: [7, 14, 21] },
  macd: { window_fast: [8, 12], window_slow: [21, 26], window_sign: [9] },
  bollinger: { window: [10, 20], window_dev: [2, 2.5] },
};

