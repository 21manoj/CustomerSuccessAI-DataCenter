/**
 * ForecastWithCI — Shared forecast-with-confidence-interval renderer
 * ===================================================================
 *
 * Single source of truth for rendering a Predictor v3 forecast point estimate
 * with its lower/upper 90% CI bounds and the (i) tooltip that surfaces the
 * platform's own ci_disclosure verbatim.
 *
 * Renders as:   98.8% (93.8% – 103.8%) (i)
 *
 * Pulls double duty across NRR (percent), expansion (currency) and unitless
 * (number) forecasts. The point estimate is the headline; the CI is muted
 * inline; the (i) icon is a hover popover surfacing ci_disclosure with
 * warning styling when ci_method === 'placeholder_uncalibrated'.
 *
 * CRITICAL UX RULE: when ci_method === 'placeholder_uncalibrated', the (i)
 * tooltip MUST be styled as a warning (amber) and MUST carry the platform's
 * own "do not threshold on the CI bounds" disclosure verbatim. Once real
 * bootstrap CIs land (Phase 1 task #4 in PLAN_nrr_predictor_v3.md), the same
 * component drops the warning styling automatically via the ciMethod prop.
 *
 * Fallback behaviour: when lower/upper bounds are absent or NaN, we render
 * only the point estimate without parens — the (i) icon stays so the
 * methodology blurb can still surface.
 *
 * Usage:
 *   <ForecastWithCI
 *     point={0.988}
 *     lower={0.938}
 *     upper={1.038}
 *     format="percent"
 *     ciMethod="placeholder_uncalibrated"
 *     ciDisclosure="Confidence intervals are placeholder uncalibrated bounds..."
 *   />
 *
 *   <ForecastWithCI
 *     point={1520077}
 *     lower={760038}
 *     upper={2280115}
 *     format="currency"
 *     ciMethod="placeholder_uncalibrated"
 *     ciDisclosure="..."
 *   />
 */

import React from 'react';
import { Info, AlertTriangle } from 'lucide-react';

export type ForecastFormat = 'percent' | 'currency' | 'number';

interface ForecastWithCIProps {
  /** Point estimate from the Predictor v3 API. Required. */
  point: number;
  /** Lower 90% CI bound. Undefined / NaN means "no CI available" — render point only. */
  lower?: number | null;
  /** Upper 90% CI bound. Undefined / NaN means "no CI available" — render point only. */
  upper?: number | null;
  /** How to format the numbers. NRR forecasts = percent, expansion ARR = currency. */
  format: ForecastFormat;
  /**
   * The ci_method string from the API. When equal to 'placeholder_uncalibrated',
   * the (i) tooltip is styled as a warning (amber) and we trust the platform's
   * own disclosure verbatim. Other values are treated as production CIs.
   */
  ciMethod?: string;
  /**
   * The ci_disclosure string from the API. Passed through verbatim — do not
   * paraphrase. When omitted, a neutral default blurb is shown.
   */
  ciDisclosure?: string;
  /**
   * Master switch for the (i) tooltip. Default = true. Set to false when the
   * call site renders the disclosure separately (e.g. tile-level footnote).
   */
  showDisclosureTooltip?: boolean;
  /**
   * Optional class applied to the point-estimate span. Lets the parent control
   * color (red for at-risk, green for healthy) without forking the component.
   */
  pointClassName?: string;
  /** Number of decimals for percent format. Default 1 (e.g. 98.8%). */
  percentDigits?: number;
}

/** Format a number per the requested format. Tolerant of NaN / null. */
function formatValue(value: number, format: ForecastFormat, percentDigits = 1): string {
  if (value == null || Number.isNaN(value)) return '—';
  switch (format) {
    case 'percent':
      // API returns NRR as a decimal (0.988). Render as 98.8%.
      return `${(value * 100).toFixed(percentDigits)}%`;
    case 'currency': {
      const abs = Math.abs(value);
      if (abs >= 1_000_000) {
        const m = value / 1_000_000;
        return `$${m % 1 === 0 ? m.toFixed(0) : m.toFixed(2)}M`;
      }
      if (abs >= 1_000) {
        const k = value / 1_000;
        return `$${k % 1 === 0 ? k.toFixed(0) : k.toFixed(0)}K`;
      }
      return `$${Math.round(value)}`;
    }
    case 'number':
    default:
      return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
  }
}

/** Stable check for a usable CI bound (handles null / undefined / NaN). */
function isUsable(n: number | null | undefined): n is number {
  return typeof n === 'number' && !Number.isNaN(n);
}

const DEFAULT_PLACEHOLDER_DISCLOSURE =
  'Confidence intervals are placeholder uncalibrated bounds (static ±0.05 around point). ' +
  'Real bootstrap CIs are pending (Phase 1 task #4). Use the point estimate; ' +
  'do not threshold on the CI bounds.';

const DEFAULT_REAL_DISCLOSURE =
  'Confidence interval reflects model uncertainty from the calibrated bootstrap fit.';

const ForecastWithCI: React.FC<ForecastWithCIProps> = ({
  point,
  lower,
  upper,
  format,
  ciMethod,
  ciDisclosure,
  showDisclosureTooltip = true,
  pointClassName = '',
  percentDigits = 1,
}) => {
  const isPlaceholder = ciMethod === 'placeholder_uncalibrated';
  const hasCI = isUsable(lower) && isUsable(upper);

  const pointStr = formatValue(point, format, percentDigits);
  const lowerStr = hasCI ? formatValue(lower as number, format, percentDigits) : null;
  const upperStr = hasCI ? formatValue(upper as number, format, percentDigits) : null;

  // Disclosure text — prefer API-provided string, else fall back to defaults
  // keyed on ciMethod so the user sees something coherent either way.
  const tooltipText =
    ciDisclosure ||
    (isPlaceholder ? DEFAULT_PLACEHOLDER_DISCLOSURE : DEFAULT_REAL_DISCLOSURE);

  // Tooltip styling: warning amber for placeholder, neutral gray otherwise.
  // Per task spec — amber border (warning), not red (error). The CI is real,
  // it's just not calibrated yet, so a softer warning is the right level.
  const tooltipBorderClass = isPlaceholder
    ? 'border-amber-500/60 bg-amber-950/95 text-amber-100'
    : 'border-gray-600 bg-gray-800 text-white';
  const iconClass = isPlaceholder
    ? 'text-amber-400 group-hover:text-amber-300'
    : 'text-gray-400 group-hover:text-blue-400';

  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      <span className={pointClassName}>{pointStr}</span>
      {hasCI && (
        <span className="text-[11px] text-gray-500 font-normal">
          ({lowerStr} &ndash; {upperStr})
        </span>
      )}
      {showDisclosureTooltip && (
        <span className="relative inline-flex items-center group cursor-help">
          {isPlaceholder ? (
            <AlertTriangle
              className={`w-3 h-3 ${iconClass} transition-colors`}
              aria-label="CI methodology disclosure"
              data-testid="forecast-ci-warning-icon"
            />
          ) : (
            <Info
              className={`w-3 h-3 ${iconClass} transition-colors`}
              aria-label="CI methodology disclosure"
              data-testid="forecast-ci-info-icon"
            />
          )}
          {/* Tooltip bubble. Positioned above by default; uses Tailwind
              group-hover for show/hide. Width capped at 18rem so long
              disclosures stay readable. */}
          <span
            role="tooltip"
            className={`absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50
                        invisible group-hover:visible opacity-0 group-hover:opacity-100
                        transition-all duration-150 pointer-events-none group-hover:pointer-events-auto`}
          >
            <span
              className={`block w-72 rounded-lg border ${tooltipBorderClass}
                          text-[11px] leading-relaxed py-2 px-3 shadow-xl whitespace-normal`}
            >
              {isPlaceholder && (
                <span className="block font-semibold text-amber-300 mb-1">
                  CI is uncalibrated
                </span>
              )}
              {tooltipText}
            </span>
          </span>
        </span>
      )}
    </span>
  );
};

export default ForecastWithCI;
export { ForecastWithCI };
