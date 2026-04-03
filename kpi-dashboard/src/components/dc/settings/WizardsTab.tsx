/**
 * WizardsTab — P1-B
 * ==================
 * Wizard A, B, C run controls with last-run metadata and inline status.
 *
 * API contracts:
 *   POST /api/data/trigger-wizard-a          → { message, duration_seconds }
 *   POST /api/admin/wizard-b/run             → { message } (may 404 — handled gracefully)
 *   GET  /api/admin/wizard-c/weights/current → { weights_updated_at, weights_source, ... }
 *   POST /api/admin/wizard-c/recalibrate     → { message }
 *   GET  /api/admin/summary                  → { wizard_a: { last_run, accounts_processed } }
 */

import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, CheckCircle, AlertCircle, Play } from 'lucide-react';

// ============================================================
// TYPES
// ============================================================

interface RunStatus {
  state: 'idle' | 'running' | 'success' | 'error';
  message: string | null;
}

interface WizardAMeta {
  last_run: string | null;
  accounts_processed: number | null;
}

interface WizardCMeta {
  weights_updated_at: string | null;
  weights_source: string | null;
}

// ============================================================
// HELPERS
// ============================================================

function formatRelative(iso: string | null): string {
  if (!iso) return 'Never';
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const diffH = Math.floor(diffMs / 3_600_000);
  if (diffH < 1) return 'Less than 1h ago';
  if (diffH < 24) return `${diffH}h ago`;
  const diffD = Math.floor(diffH / 24);
  return `${diffD}d ago`;
}

function InlineStatus({ status }: { status: RunStatus }) {
  if (status.state === 'idle') return null;
  if (status.state === 'running') {
    return (
      <span className="flex items-center space-x-1 text-sm text-gray-500">
        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
        <span>Running...</span>
      </span>
    );
  }
  if (status.state === 'success') {
    return (
      <span className="flex items-center space-x-1 text-sm text-green-600">
        <CheckCircle className="h-3.5 w-3.5" />
        <span>{status.message}</span>
      </span>
    );
  }
  return (
    <span className="flex items-center space-x-1 text-sm text-red-600">
      <AlertCircle className="h-3.5 w-3.5" />
      <span>{status.message}</span>
    </span>
  );
}

// ============================================================
// WIZARD CARD
// ============================================================

const WizardCard: React.FC<{
  title: string;
  description: string;
  metaRows?: Array<{ label: string; value: string }>;
  actionLabel: string;
  status: RunStatus;
  onRun: () => void;
}> = ({ title, description, metaRows, actionLabel, status, onRun }) => (
  <div className="bg-white border border-gray-200 rounded-lg p-6">
    <div className="flex items-start justify-between">
      <div className="flex-1 pr-6">
        <h4 className="text-base font-semibold text-gray-900">{title}</h4>
        <p className="text-sm text-gray-500 mt-1">{description}</p>
        {metaRows && metaRows.length > 0 && (
          <dl className="mt-3 space-y-1">
            {metaRows.map(({ label, value }) => (
              <div key={label} className="flex items-center space-x-2 text-sm">
                <dt className="text-gray-400 min-w-[130px]">{label}:</dt>
                <dd className="text-gray-700 font-medium">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
      <div className="flex flex-col items-end space-y-2 shrink-0">
        <button
          onClick={onRun}
          disabled={status.state === 'running'}
          className="flex items-center space-x-1.5 px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-60 transition-colors"
        >
          {status.state === 'running'
            ? <RefreshCw className="h-4 w-4 animate-spin" />
            : <Play className="h-4 w-4" />}
          <span>{status.state === 'running' ? 'Running...' : actionLabel}</span>
        </button>
        <InlineStatus status={status} />
      </div>
    </div>
  </div>
);

// ============================================================
// MAIN COMPONENT
// ============================================================

interface WizardsTabProps {
  /** Super-admin context: pass target customer's ID. Self-service: omit (uses session). */
  customerId?: number;
}

const WizardsTab: React.FC<WizardsTabProps> = ({ customerId }) => {
  const apiUrl = (path: string) =>
    customerId ? `${path}?customer_id=${customerId}` : path;

  const [wizardAMeta, setWizardAMeta] = useState<WizardAMeta>({ last_run: null, accounts_processed: null });
  const [wizardCMeta, setWizardCMeta] = useState<WizardCMeta>({ weights_updated_at: null, weights_source: null });
  const [metaLoading, setMetaLoading] = useState(true);

  const [statusA, setStatusA] = useState<RunStatus>({ state: 'idle', message: null });
  const [statusB, setStatusB] = useState<RunStatus>({ state: 'idle', message: null });
  const [statusC, setStatusC] = useState<RunStatus>({ state: 'idle', message: null });

  // Clear status after 3s
  const autoReset = useCallback((setter: React.Dispatch<React.SetStateAction<RunStatus>>) => {
    setTimeout(() => setter({ state: 'idle', message: null }), 3000);
  }, []);

  // ── Load metadata ──
  useEffect(() => {
    (async () => {
      setMetaLoading(true);
      try {
        const [summaryRes, cRes] = await Promise.allSettled([
          fetch(apiUrl('/api/admin/summary'), { credentials: 'include' }),
          fetch(apiUrl('/api/admin/wizard-c/weights/current'), { credentials: 'include' }),
        ]);

        if (summaryRes.status === 'fulfilled' && summaryRes.value.ok) {
          const data = await summaryRes.value.json();
          if (data.wizard_a) {
            setWizardAMeta({
              last_run: data.wizard_a.last_run ?? null,
              accounts_processed: data.wizard_a.accounts_processed ?? null,
            });
          }
        }

        if (cRes.status === 'fulfilled' && cRes.value.ok) {
          const data = await cRes.value.json();
          setWizardCMeta({
            weights_updated_at: data.weights_updated_at ?? null,
            weights_source: data.weights_source ?? null,
          });
        }
      } catch (err) {
        console.error('Failed to load wizard metadata:', err);
      } finally {
        setMetaLoading(false);
      }
    })();
  }, []);

  // ── Run Wizard A ──
  const runWizardA = async () => {
    setStatusA({ state: 'running', message: null });
    try {
      const res = await fetch(apiUrl('/api/data/trigger-wizard-a'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        const msg = data.message
          ? `${data.message}${data.duration_seconds ? ` (${data.duration_seconds}s)` : ''}`
          : 'Wizard A completed';
        setStatusA({ state: 'success', message: msg });
        setWizardAMeta(prev => ({ ...prev, last_run: new Date().toISOString() }));
      } else if (res.status === 401) {
        setStatusA({ state: 'error', message: 'Session expired — please log in again' });
      } else {
        setStatusA({ state: 'error', message: data.message || data.error || 'Wizard A failed' });
      }
    } catch {
      setStatusA({ state: 'error', message: 'Network error — could not reach server' });
    } finally {
      autoReset(setStatusA);
    }
  };

  // ── Run Wizard B ──
  const runWizardB = async () => {
    setStatusB({ state: 'running', message: null });
    try {
      const res = await fetch(apiUrl('/api/data/trigger-wizard-b'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      if (res.status === 404) {
        setStatusB({ state: 'error', message: 'No data found — run Wizard A first' });
      } else if (res.ok) {
        const data = await res.json().catch(() => ({}));
        setStatusB({ state: 'success', message: data.message || 'Wizard B completed' });
      } else {
        const data = await res.json().catch(() => ({}));
        setStatusB({ state: 'error', message: data.error || 'Wizard B failed' });
      }
    } catch {
      setStatusB({ state: 'error', message: 'Network error — could not reach server' });
    } finally {
      autoReset(setStatusB);
    }
  };

  // ── Run Wizard C ──
  const runWizardC = async () => {
    setStatusC({ state: 'running', message: null });
    try {
      const res = await fetch(apiUrl('/api/admin/wizard-c/recalibrate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setStatusC({ state: 'success', message: data.message || 'Recalibration complete' });
        setWizardCMeta({ weights_updated_at: new Date().toISOString(), weights_source: 'learned' });
      } else {
        setStatusC({ state: 'error', message: data.error || 'Recalibration failed' });
      }
    } catch {
      setStatusC({ state: 'error', message: 'Network error — could not reach server' });
    } finally {
      autoReset(setStatusC);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Wizards</h3>
        <p className="text-sm text-gray-500 mt-1">
          Run intelligence wizards to classify story arcs, detect milestones, and calibrate KPI weights from historical data.
        </p>
      </div>

      {metaLoading && (
        <div className="flex items-center space-x-2 text-gray-400 text-sm">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>Loading wizard status...</span>
        </div>
      )}

      {/* Wizard A */}
      <WizardCard
        title="Wizard A — Arc Classification & Edge Generation"
        description="Classifies each account into a story arc (champion_loss, crisis_recovery, land_and_expand, etc.) and generates causal edges between context nodes."
        metaRows={[
          { label: 'Last run', value: formatRelative(wizardAMeta.last_run) },
          ...(wizardAMeta.accounts_processed !== null
            ? [{ label: 'Accounts processed', value: String(wizardAMeta.accounts_processed) }]
            : []),
        ]}
        actionLabel="Run Wizard A"
        status={statusA}
        onRun={runWizardA}
      />

      {/* Wizard B */}
      <WizardCard
        title="Wizard B — Pattern Detection & Milestones"
        description="Detects phase transitions and milestone events in account health trajectories. Identifies cliff drops, recovery inflection points, and stable phases."
        actionLabel="Run Wizard B"
        status={statusB}
        onRun={runWizardB}
      />

      {/* Wizard C */}
      <WizardCard
        title="Wizard C — Weight Calibration"
        description="Correlates KPI performance with health outcomes to calibrate KPI and pillar weights. Splits accounts into successful (health ≥ 70) vs unsuccessful (health < 50) cohorts."
        metaRows={[
          { label: 'Last calibration', value: formatRelative(wizardCMeta.weights_updated_at) },
          ...(wizardCMeta.weights_source
            ? [{ label: 'Source', value: wizardCMeta.weights_source }]
            : []),
        ]}
        actionLabel="Recalibrate"
        status={statusC}
        onRun={runWizardC}
      />
    </div>
  );
};

export default WizardsTab;
