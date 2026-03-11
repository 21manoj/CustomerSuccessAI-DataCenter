/**
 * SettingsTab — Feature flags and experimental toggles for the Test Runner.
 *
 * Flags are persisted in localStorage so they survive page reloads.
 * Each flag has a key, label, description, and default (off unless noted).
 */

import React from 'react';
import { AlertTriangle, Beaker, ToggleLeft, ToggleRight } from 'lucide-react';

// ---------------------------------------------------------------------------
// Feature Flag Definitions
// ---------------------------------------------------------------------------

export interface FeatureFlag {
  key: string;
  label: string;
  description: string;
  defaultValue: boolean;
  /** If true, show an "Experimental" badge */
  experimental?: boolean;
}

export const TEST_RUNNER_FLAGS: FeatureFlag[] = [
  {
    key: 'kpi_configuration',
    label: 'KPI Configuration',
    description:
      'Enable KPI/Pillar selection presets (Default, Medium, Minimal, Custom) in Scenario 1 Advanced Options. ' +
      'Allows onboarding customers with a reduced KPI set for lighter load or ROI-focused testing.',
    defaultValue: false,
    experimental: true,
  },
];

// ---------------------------------------------------------------------------
// Helpers to read/write flags from localStorage
// ---------------------------------------------------------------------------

const STORAGE_PREFIX = 'test_runner_flag_';

export function getFlagValue(key: string): boolean {
  const stored = localStorage.getItem(`${STORAGE_PREFIX}${key}`);
  if (stored !== null) return stored === 'true';
  const def = TEST_RUNNER_FLAGS.find(f => f.key === key);
  return def?.defaultValue ?? false;
}

export function setFlagValue(key: string, value: boolean): void {
  localStorage.setItem(`${STORAGE_PREFIX}${key}`, String(value));
}

/** Convenience: is KPI Configuration enabled? */
export function isKpiConfigEnabled(): boolean {
  return getFlagValue('kpi_configuration');
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SettingsTabProps {
  flags: Record<string, boolean>;
  onFlagChange: (key: string, value: boolean) => void;
}

const SettingsTab: React.FC<SettingsTabProps> = ({ flags, onFlagChange }) => {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            <Beaker className="w-4 h-4 text-indigo-600" />
            Feature Flags
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            Toggle experimental features for the Test Runner. Changes take effect immediately and persist across sessions.
          </p>
        </div>

        <div className="divide-y divide-gray-100">
          {TEST_RUNNER_FLAGS.map(flag => {
            const isOn = flags[flag.key] ?? flag.defaultValue;

            return (
              <div
                key={flag.key}
                className="px-6 py-4 flex items-start gap-4 hover:bg-gray-50 transition-colors"
              >
                {/* Toggle */}
                <button
                  onClick={() => onFlagChange(flag.key, !isOn)}
                  className="mt-0.5 flex-shrink-0 focus:outline-none"
                  aria-label={`Toggle ${flag.label}`}
                >
                  {isOn ? (
                    <ToggleRight className="w-8 h-8 text-indigo-600" />
                  ) : (
                    <ToggleLeft className="w-8 h-8 text-gray-300" />
                  )}
                </button>

                {/* Label + description */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-800">{flag.label}</span>
                    {flag.experimental && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-semibold uppercase tracking-wide">
                        <AlertTriangle className="w-3 h-3" />
                        Experimental
                      </span>
                    )}
                    <span
                      className={`text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ${
                        isOn
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {isOn ? 'ON' : 'OFF'}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{flag.description}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default SettingsTab;
