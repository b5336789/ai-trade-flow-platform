// Strategy parameter defaults (keys match the backend constructor kwargs).
export const STRATEGY_PARAMS: Record<string, Record<string, number>> = {
  ma_cross: { fast: 10, slow: 20 },
  rsi: { window: 14 },
  macd: { window_fast: 12, window_slow: 26, window_sign: 9 },
  bollinger: { window: 20, window_dev: 2 },
};

export const STRATEGY_NAMES = Object.keys(STRATEGY_PARAMS);
