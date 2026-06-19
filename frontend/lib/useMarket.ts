// Sets data-market on <html> so --up/--down flip for 台股 (red-up). Call when the active market changes.
export function setMarket(market: string) {
  if (typeof document === "undefined") return;
  if (market === "tw_stock") document.documentElement.dataset.market = "tw";
  else delete document.documentElement.dataset.market;
}
