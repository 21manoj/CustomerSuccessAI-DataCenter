/**
 * ForecastWithCI — unit tests.
 *
 * Three core cases per spec (May 17 FDE eval task):
 *  1. NRR percent forecast with CI (Spica Labs: 98.8% (93.8% – 103.8%))
 *  2. Expansion currency forecast with CI (Polaris Cloud: $1.52M ($760K – $2.28M))
 *  3. No-CI fallback when bounds are absent (point only)
 *
 * Plus regression checks:
 *  - placeholder_uncalibrated surfaces warning styling + disclosure verbatim
 *  - real CI methods do not show the warning
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ForecastWithCI } from './ForecastWithCI';

describe('ForecastWithCI', () => {
  const PLACEHOLDER_DISCLOSURE =
    'Confidence intervals are placeholder uncalibrated bounds (static ±0.05 around point). ' +
    'Real bootstrap CIs are pending (Phase 1 task #4). Use the point estimate; ' +
    'do not threshold on the CI bounds.';

  it('renders NRR percent with CI (Spica Labs shape)', () => {
    render(
      <ForecastWithCI
        point={0.988}
        lower={0.938}
        upper={1.038}
        format="percent"
        ciMethod="placeholder_uncalibrated"
        ciDisclosure={PLACEHOLDER_DISCLOSURE}
      />
    );
    expect(screen.getByText('98.8%')).toBeInTheDocument();
    // CI bounds appear as one text node "(93.8% – 103.8%)"
    expect(screen.getByText(/93\.8%.*103\.8%/)).toBeInTheDocument();
  });

  it('renders expansion currency with CI (Polaris Cloud shape)', () => {
    render(
      <ForecastWithCI
        point={1_520_077}
        lower={760_038}
        upper={2_280_115}
        format="currency"
        ciMethod="placeholder_uncalibrated"
        ciDisclosure={PLACEHOLDER_DISCLOSURE}
      />
    );
    expect(screen.getByText('$1.52M')).toBeInTheDocument();
    expect(screen.getByText(/\$760K.*\$2\.28M/)).toBeInTheDocument();
  });

  it('renders point only when CI bounds are absent (no-CI fallback)', () => {
    render(
      <ForecastWithCI
        point={0.95}
        format="percent"
      />
    );
    expect(screen.getByText('95.0%')).toBeInTheDocument();
    // No "(X% – Y%)" range when bounds missing
    expect(screen.queryByText(/–/)).not.toBeInTheDocument();
  });

  it('uses warning icon (AlertTriangle) when ci_method is placeholder_uncalibrated', () => {
    render(
      <ForecastWithCI
        point={0.988}
        lower={0.938}
        upper={1.038}
        format="percent"
        ciMethod="placeholder_uncalibrated"
        ciDisclosure={PLACEHOLDER_DISCLOSURE}
      />
    );
    expect(screen.getByTestId('forecast-ci-warning-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('forecast-ci-info-icon')).not.toBeInTheDocument();
  });

  it('uses neutral info icon when ci_method is real (e.g. bootstrap)', () => {
    render(
      <ForecastWithCI
        point={0.988}
        lower={0.938}
        upper={1.038}
        format="percent"
        ciMethod="bootstrap_500"
        ciDisclosure="Calibrated bootstrap CI from 500 resamples."
      />
    );
    expect(screen.getByTestId('forecast-ci-info-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('forecast-ci-warning-icon')).not.toBeInTheDocument();
  });

  it('surfaces the API-provided ci_disclosure verbatim in the tooltip', () => {
    render(
      <ForecastWithCI
        point={0.988}
        lower={0.938}
        upper={1.038}
        format="percent"
        ciMethod="placeholder_uncalibrated"
        ciDisclosure={PLACEHOLDER_DISCLOSURE}
      />
    );
    // Tooltip text is in the DOM (hidden via opacity/visibility classes,
    // but present so screen readers + Testing Library can see it).
    expect(
      screen.getByText(/do not threshold on the CI bounds/i)
    ).toBeInTheDocument();
  });

  it('omits the (i) icon entirely when showDisclosureTooltip=false', () => {
    render(
      <ForecastWithCI
        point={0.988}
        lower={0.938}
        upper={1.038}
        format="percent"
        ciMethod="placeholder_uncalibrated"
        showDisclosureTooltip={false}
      />
    );
    expect(screen.queryByTestId('forecast-ci-warning-icon')).not.toBeInTheDocument();
    expect(screen.queryByTestId('forecast-ci-info-icon')).not.toBeInTheDocument();
  });

  it('renders "—" for NaN point (defensive)', () => {
    render(
      <ForecastWithCI point={NaN} format="percent" />
    );
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('applies pointClassName to the headline number', () => {
    render(
      <ForecastWithCI
        point={0.988}
        format="percent"
        pointClassName="text-emerald-400"
      />
    );
    const el = screen.getByText('98.8%');
    expect(el).toHaveClass('text-emerald-400');
  });
});
