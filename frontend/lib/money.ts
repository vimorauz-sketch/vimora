/** Integer percentage of a minor-unit amount, half-up — mirrors the backend for previews only. */
export function pctOf(amountMinor: number, percent: number, currency: string): number {
  const raw = Math.floor((amountMinor * percent + 50) / 100);
  if (currency === "UZS") return Math.min(Math.ceil(raw / 100) * 100, amountMinor);
  return Math.min(raw, amountMinor);
}
