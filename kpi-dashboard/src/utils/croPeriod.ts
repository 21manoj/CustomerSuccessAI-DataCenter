/**
 * CRO dashboard period tabs (Q3 / Q4 / TTM) — calendar quarter anchors.
 */

export type CroPeriod = 'Q3' | 'Q4' | 'TTM';

export interface QuarterBucket {
  y: number;
  q: number;
  label: string;
}

export function getCalendarQuarter(d: Date = new Date()): QuarterBucket {
  const y = d.getFullYear();
  const q = Math.ceil((d.getMonth() + 1) / 3);
  return { y, q, label: `Q${q} ${y}` };
}

/** Prior calendar quarter. */
export function previousQuarter(b: QuarterBucket): QuarterBucket {
  const q = b.q === 1 ? 4 : b.q - 1;
  const y = b.q === 1 ? b.y - 1 : b.y;
  return { y, q, label: `Q${q} ${y}` };
}

/**
 * Map UI tab to the quarter treated as "this period".
 * Q4 = current calendar quarter; Q3 = prior calendar quarter; TTM = current quarter anchor for trend tile.
 */
export function periodToAnchorBucket(period: CroPeriod, ref: Date = new Date()): QuarterBucket {
  const cur = getCalendarQuarter(ref);
  if (period === 'Q4') return cur;
  if (period === 'Q3') return previousQuarter(cur);
  return cur;
}

export function periodDisplayLabel(period: CroPeriod, ref: Date = new Date()): string {
  if (period === 'TTM') {
    const end = ref;
    const start = new Date(ref);
    start.setMonth(start.getMonth() - 11);
    const fmt = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    return `TTM · ${fmt(start)} – ${fmt(end)}`;
  }
  return periodToAnchorBucket(period, ref).label;
}

/** Months (YYYY-MM) that fall inside a calendar quarter. */
export function monthsInQuarter(b: QuarterBucket): string[] {
  const startM = (b.q - 1) * 3 + 1;
  return [0, 1, 2].map((i) => `${b.y}-${String(startM + i).padStart(2, '0')}`);
}

/** Trailing 12 month keys ending at ref month (inclusive). */
export function trailingTwelveMonths(ref: Date = new Date()): string[] {
  const months: string[] = [];
  const d = new Date(ref.getFullYear(), ref.getMonth(), 1);
  for (let i = 11; i >= 0; i--) {
    const m = new Date(d.getFullYear(), d.getMonth() - i, 1);
    months.push(`${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, '0')}`);
  }
  return months;
}

export function monthInPeriod(month: string, period: CroPeriod, ref: Date = new Date()): boolean {
  if (period === 'TTM') {
    return trailingTwelveMonths(ref).includes(month);
  }
  return monthsInQuarter(periodToAnchorBucket(period, ref)).includes(month);
}
