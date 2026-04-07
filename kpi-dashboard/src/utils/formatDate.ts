/**
 * Date formatting utilities — converts UTC server timestamps to local time.
 *
 * Backend stores all timestamps as UTC (datetime.utcnow().isoformat()).
 * These helpers ensure the browser displays them in the user's local timezone.
 */

/**
 * Format a UTC timestamp string to local date+time with timezone label.
 * Handles both ISO strings with and without 'Z' suffix.
 *
 * @example formatDateTime('2026-04-07T01:32:31') → "4/7/2026, 6:32:31 PM PDT"
 */
export function formatDateTime(utcString: string | null | undefined): string {
  if (!utcString) return '--';
  // Append 'Z' if missing to force UTC interpretation
  const iso = utcString.endsWith('Z') || utcString.includes('+') ? utcString : utcString + 'Z';
  try {
    return new Date(iso).toLocaleString(undefined, { timeZoneName: 'short' });
  } catch {
    return utcString;
  }
}

/**
 * Format a UTC timestamp to local date only (no time).
 *
 * @example formatDate('2026-04-07T01:32:31') → "4/7/2026"
 */
export function formatDate(utcString: string | null | undefined): string {
  if (!utcString) return '--';
  const iso = utcString.endsWith('Z') || utcString.includes('+') ? utcString : utcString + 'Z';
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return utcString;
  }
}

/**
 * Format a UTC timestamp to short local time (for compact displays).
 *
 * @example formatShortDateTime('2026-04-07T01:32:31') → "Apr 7, 6:32 PM"
 */
export function formatShortDateTime(utcString: string | null | undefined): string {
  if (!utcString) return '--';
  const iso = utcString.endsWith('Z') || utcString.includes('+') ? utcString : utcString + 'Z';
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return utcString;
  }
}
