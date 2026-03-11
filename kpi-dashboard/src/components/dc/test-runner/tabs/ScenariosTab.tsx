/**
 * ScenariosTab — Scenario selection, advanced options, run controls, monitor, history,
 * and continuous simulation mode.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Play,
  Loader2,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  SlidersHorizontal,
  Lock,
  Activity,
  Square,
  Timer,
  TrendingUp,
} from 'lucide-react';

import type {
  ScenarioMeta,
  AdvancedOptions,
  RunStatus,
  RunSummary,
  StoryArc,
  PatternMix,
  PillarWeights,
  SimulationStatus,
} from '../types';
import {
  PRESETS,
  DEFAULT_PATTERN_MIX,
  DEFAULT_WEIGHTS,
  DEFAULT_OPTIONS,
  INDUSTRIES,
  PILLAR_LABELS,
  DRIFT_PROFILES,
} from '../types';
import { testRunnerApi, platformApi, simulationApi, formatDuration } from '../api';
import RunMonitor from '../components/RunMonitor';
import RunHistory from '../components/RunHistory';

interface ScenariosTabProps {
  customerId: string;
  entitlements: Record<string, boolean>;
  onRunComplete?: () => void;
}

const ScenariosTab: React.FC<ScenariosTabProps> = ({
  customerId,
  entitlements,
  onRunComplete,
}) => {
  // Scenario list
  const [scenarios, setScenarios] = useState<ScenarioMeta[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Active run
  const [activeRun, setActiveRun] = useState<RunStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Advanced options
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [options, setOptions] = useState<AdvancedOptions>({ ...DEFAULT_OPTIONS });

  // Story arcs (for Scenario 8 dropdown)
  const [storyArcs, setStoryArcs] = useState<StoryArc[]>([]);

  // History
  const [history, setHistory] = useState<RunSummary[]>([]);

  // Simulation mode
  const [showSimulation, setShowSimulation] = useState(false);
  const [simInterval, setSimInterval] = useState(10);
  const [simDays, setSimDays] = useState(90);
  const [simProfile, setSimProfile] = useState('mixed');
  const [simStatus, setSimStatus] = useState<SimulationStatus | null>(null);
  const [simStarting, setSimStarting] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);
  const simPollRef = useRef<NodeJS.Timeout | null>(null);

  const hasAdvancedEntitlement = entitlements['test_runner_advanced'] ?? false;

  // ------- Load scenarios + history + story arcs on mount -------
  useEffect(() => {
    testRunnerApi.getScenarios().then(setScenarios).catch(() => {});
    testRunnerApi.getRuns().then(setHistory).catch(() => {});
    platformApi.getStoryArcs().then(setStoryArcs).catch(() => {});
  }, []);

  // ------- Polling (scenario runs) -------
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback((runId: string) => {
    stopPolling();
    const poll = async () => {
      try {
        const status = await testRunnerApi.getStatus(runId);
        setActiveRun(status);
        if (status.status === 'completed') {
          stopPolling();
          testRunnerApi.getRuns().then(setHistory).catch(() => {});
          onRunComplete?.();
        }
      } catch {
        // Ignore transient errors
      }
    };
    poll();
    pollRef.current = setInterval(poll, 3000);
  }, [stopPolling, onRunComplete]);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  // ------- Simulation polling -------
  const stopSimPolling = useCallback(() => {
    if (simPollRef.current) {
      clearInterval(simPollRef.current);
      simPollRef.current = null;
    }
  }, []);

  const startSimPolling = useCallback(() => {
    stopSimPolling();
    const poll = async () => {
      if (!customerId) return;
      try {
        const st = await simulationApi.status(customerId);
        setSimStatus(st);
        if (st.status !== 'running') {
          stopSimPolling();
          onRunComplete?.(); // Refresh platform state
        }
      } catch {
        // Ignore
      }
    };
    poll();
    simPollRef.current = setInterval(poll, 2000);
  }, [customerId, stopSimPolling, onRunComplete]);

  // Check simulation status on mount / customer change
  useEffect(() => {
    if (customerId) {
      simulationApi.status(customerId).then(st => {
        setSimStatus(st);
        if (st.is_running) {
          startSimPolling();
        }
      }).catch(() => {});
    }
    return () => stopSimPolling();
  }, [customerId, stopSimPolling]);

  // ------- Actions -------
  const toggleScenario = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === scenarios.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(scenarios.map(s => s.id)));
    }
  };

  // ------- Advanced Options helpers -------
  const setOption = <K extends keyof AdvancedOptions>(key: K, value: AdvancedOptions[K]) => {
    setOptions(prev => ({ ...prev, [key]: value }));
  };

  const applyPreset = (preset: typeof PRESETS[number]) => {
    setOptions(prev => ({
      ...prev,
      numAccounts: preset.numAccounts,
      industry: preset.industry,
      seed: preset.seed,
    }));
  };

  const patternMixTotal = Object.values(options.showcasePatternMix).reduce((a, b) => a + b, 0);
  const weightsTotal = Object.values(options.weights).reduce((a, b) => a + b, 0);
  const patternMixValid = Math.abs(patternMixTotal - 1.0) < 0.02;
  const weightsValid = Math.abs(weightsTotal - 1.0) < 0.02;

  // Scenario-aware booleans
  const hasOnboarding = selected.has('1');
  const hasCleanup = selected.has('4');
  const hasContextGraph = selected.has('8');
  const hasROISimulation = selected.has('9');

  const handleStart = async () => {
    const cid = customerId?.trim();
    // For new customer, the backend auto-generates; for existing, must have a value
    if (selected.size === 0) {
      setError('Select at least one scenario');
      return;
    }

    if (showAdvanced && hasOnboarding) {
      if (!patternMixValid) {
        setError(`Journey pattern mix must sum to 1.0 (currently ${patternMixTotal.toFixed(2)})`);
        return;
      }
      if (!weightsValid) {
        setError(`Pillar weights must sum to 1.0 (currently ${weightsTotal.toFixed(2)})`);
        return;
      }
    }

    setError(null);
    setStarting(true);

    try {
      const orderedIds = scenarios.map(s => s.id).filter(id => selected.has(id));
      const { run_id } = await testRunnerApi.startRun(orderedIds, cid || '500', showAdvanced ? options : undefined);
      startPolling(run_id);
    } catch (e: any) {
      setError(e.message || 'Failed to start');
    } finally {
      setStarting(false);
    }
  };

  // ------- Simulation actions -------
  const handleSimStart = async () => {
    if (!customerId) {
      setSimError('Select an existing customer first (simulation injects data into existing accounts)');
      return;
    }
    setSimError(null);
    setSimStarting(true);
    try {
      await simulationApi.start(customerId, simInterval, simDays, simProfile);
      startSimPolling();
    } catch (e: any) {
      setSimError(e.message || 'Failed to start simulation');
    } finally {
      setSimStarting(false);
    }
  };

  const handleSimStop = async () => {
    if (!customerId) return;
    try {
      await simulationApi.stop(customerId);
    } catch (e: any) {
      setSimError(e.message || 'Failed to stop simulation');
    }
  };

  // ------- Derived state -------
  const isRunning = activeRun?.status === 'running';
  const isSimRunning = simStatus?.is_running ?? false;

  return (
    <div className="space-y-6">
      {/* ── Simulation Mode Panel ── */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <button
          onClick={() => setShowSimulation(!showSimulation)}
          className="w-full px-6 py-4 flex items-center justify-between text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <span className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-600" />
            <span className="font-semibold">Simulation Mode</span>
            <span className="text-xs text-gray-400 font-normal">— Continuous KPI injection at configurable intervals</span>
            {isSimRunning && (
              <span className="ml-2 inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full animate-pulse">
                <Activity className="w-3 h-3" />
                Day {simStatus?.current_day}/{simStatus?.num_days}
              </span>
            )}
          </span>
          {showSimulation
            ? <ChevronDown className="w-4 h-4 text-gray-400" />
            : <ChevronRight className="w-4 h-4 text-gray-400" />
          }
        </button>

        {showSimulation && (
          <div className="px-6 pb-5 border-t border-gray-100 pt-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              {/* Interval */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <Timer className="w-3 h-3" />
                  Interval (seconds)
                </label>
                <input
                  type="number"
                  value={simInterval}
                  onChange={e => setSimInterval(Math.max(1, parseInt(e.target.value, 10) || 10))}
                  min={1}
                  max={300}
                  disabled={isSimRunning}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 disabled:bg-gray-100"
                />
                <p className="text-xs text-gray-400 mt-0.5">1 interval = 1 simulated day</p>
              </div>

              {/* Duration */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">
                  Duration (days)
                </label>
                <input
                  type="number"
                  value={simDays}
                  onChange={e => setSimDays(Math.max(1, Math.min(365, parseInt(e.target.value, 10) || 90)))}
                  min={1}
                  max={365}
                  disabled={isSimRunning}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 disabled:bg-gray-100"
                />
                <p className="text-xs text-gray-400 mt-0.5">Total: ~{formatDuration(simInterval * simDays)} wall-clock</p>
              </div>

              {/* Drift Profile */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" />
                  Drift Profile
                </label>
                <select
                  value={simProfile}
                  onChange={e => setSimProfile(e.target.value)}
                  disabled={isSimRunning}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 bg-white disabled:bg-gray-100"
                >
                  {DRIFT_PROFILES.map(p => (
                    <option key={p.id} value={p.id}>{p.label}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-400 mt-0.5">
                  {DRIFT_PROFILES.find(p => p.id === simProfile)?.description}
                </p>
              </div>

              {/* Controls */}
              <div className="flex flex-col justify-end">
                {!isSimRunning ? (
                  <button
                    onClick={handleSimStart}
                    disabled={simStarting || !customerId}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm transition-colors"
                  >
                    {simStarting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    {simStarting ? 'Starting...' : 'Start Simulation'}
                  </button>
                ) : (
                  <button
                    onClick={handleSimStop}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium text-sm transition-colors"
                  >
                    <Square className="w-4 h-4" />
                    Stop
                  </button>
                )}
                {!customerId && (
                  <p className="text-xs text-amber-600 mt-1">Select an existing customer first</p>
                )}
              </div>
            </div>

            {/* Simulation Progress */}
            {simStatus && simStatus.status !== 'idle' && (
              <div className={`rounded-lg p-3 text-sm ${
                isSimRunning ? 'bg-emerald-50 border border-emerald-200' :
                simStatus.status === 'completed' ? 'bg-green-50 border border-green-200' :
                simStatus.status === 'error' ? 'bg-red-50 border border-red-200' :
                'bg-gray-50 border border-gray-200'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">
                    {isSimRunning && '🔄 Running'}
                    {simStatus.status === 'completed' && '✅ Completed'}
                    {simStatus.status === 'stopped' && '⏹ Stopped'}
                    {simStatus.status === 'error' && '❌ Error'}
                  </span>
                  <span className="text-gray-500">
                    Day {simStatus.current_day} of {simStatus.num_days}
                    {simStatus.current_date && ` (${simStatus.current_date})`}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div
                    className={`rounded-full h-2 transition-all duration-500 ${
                      isSimRunning ? 'bg-emerald-500' :
                      simStatus.status === 'completed' ? 'bg-green-500' : 'bg-gray-400'
                    }`}
                    style={{ width: `${simStatus.num_days > 0 ? Math.round((simStatus.current_day / simStatus.num_days) * 100) : 0}%` }}
                  />
                </div>

                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>Elapsed: {formatDuration(simStatus.elapsed_seconds)}</span>
                  {simStatus.kpis_injected != null && <span>KPIs injected: {simStatus.kpis_injected?.toLocaleString()}</span>}
                  <span>Interval: {simStatus.interval_seconds}s</span>
                  <span>Profile: {simStatus.drift_profile}</span>
                </div>

                {simStatus.error && (
                  <p className="mt-2 text-xs text-red-600">{simStatus.error}</p>
                )}
              </div>
            )}

            {simError && (
              <div className="mt-2 flex items-center gap-1 text-sm text-red-600">
                <AlertTriangle className="w-4 h-4" />
                {simError}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Scenario Selector ── */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">Select Scenarios</h3>
          <button
            onClick={toggleAll}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            {selected.size === scenarios.length ? 'Deselect All' : 'Select All'}
          </button>
        </div>

        <div className="px-6 py-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          {scenarios.map(s => (
            <label
              key={s.id}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                selected.has(s.id)
                  ? 'border-blue-300 bg-blue-50/50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <input
                type="checkbox"
                checked={selected.has(s.id)}
                onChange={() => toggleScenario(s.id)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900 text-sm">
                    {s.id}. {s.name}
                  </span>
                  <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
                    {s.group}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{s.description}</p>
                <p className="text-xs text-gray-400 mt-0.5">~{s.est_minutes} min</p>
              </div>
            </label>
          ))}
        </div>

        {/* ── Advanced Options ── */}
        <div className="border-t border-gray-100">
          <button
            onClick={() => hasAdvancedEntitlement && setShowAdvanced(!showAdvanced)}
            className={`w-full px-6 py-3 flex items-center justify-between text-sm font-medium transition-colors ${
              hasAdvancedEntitlement
                ? 'text-gray-600 hover:bg-gray-50 cursor-pointer'
                : 'text-gray-400 cursor-not-allowed'
            }`}
            title={hasAdvancedEntitlement ? undefined : 'Upgrade to Professional tier to unlock Advanced Options'}
          >
            <span className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4" />
              Advanced Options
              {!hasAdvancedEntitlement && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-xs font-medium">
                  <Lock className="w-3 h-3" />
                  Professional
                </span>
              )}
            </span>
            {hasAdvancedEntitlement && (
              showAdvanced
                ? <ChevronDown className="w-4 h-4" />
                : <ChevronRight className="w-4 h-4" />
            )}
          </button>

          {showAdvanced && hasAdvancedEntitlement && (
            <div className="px-6 pb-4 space-y-5">

              {/* Presets */}
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                  Presets
                </label>
                <div className="flex gap-2 flex-wrap">
                  {PRESETS.map(p => (
                    <button
                      key={p.label}
                      onClick={() => applyPreset(p)}
                      className={`px-3 py-1.5 rounded-md border text-xs font-medium transition-colors ${
                        options.numAccounts === p.numAccounts
                          ? 'border-blue-400 bg-blue-50 text-blue-700'
                          : 'border-gray-200 text-gray-700 hover:bg-blue-50 hover:border-blue-300'
                      }`}
                      title={p.description}
                    >
                      {p.label} ({p.numAccounts})
                    </button>
                  ))}
                </div>
              </div>

              {/* Global Options */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Num Accounts</label>
                  <input
                    type="number"
                    value={options.numAccounts}
                    onChange={e => setOption('numAccounts', Math.max(1, parseInt(e.target.value, 10) || 3))}
                    min={1}
                    max={200}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Seed <span className="text-gray-400">(optional)</span>
                  </label>
                  <input
                    type="number"
                    value={options.seed ?? ''}
                    onChange={e => setOption('seed', e.target.value ? parseInt(e.target.value, 10) : null)}
                    placeholder="random"
                    className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Scenario 1: Onboarding Options */}
              {hasOnboarding && (
                <div className="border border-blue-200 bg-blue-50/30 rounded-lg p-4 space-y-4">
                  <h4 className="text-sm font-semibold text-blue-800 flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs font-bold">1</span>
                    Onboarding Options
                  </h4>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Industry</label>
                      <select
                        value={options.industry}
                        onChange={e => setOption('industry', e.target.value)}
                        className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      >
                        {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Mode</label>
                      <div className="flex gap-4 mt-1.5">
                        {(['demo', 'custom'] as const).map(mode => (
                          <label key={mode} className="flex items-center gap-1.5 text-sm cursor-pointer">
                            <input
                              type="radio"
                              name="onboarding_mode"
                              checked={options.onboardingMode === mode}
                              onChange={() => setOption('onboardingMode', mode)}
                              className="text-blue-600 focus:ring-blue-500"
                            />
                            {mode === 'demo' ? 'Demo (synthetic)' : 'Custom (user CSVs)'}
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Journey Pattern Mix */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-xs font-medium text-gray-500">Journey Pattern Mix</label>
                      <span className={`text-xs font-mono ${patternMixValid ? 'text-green-600' : 'text-red-600'}`}>
                        Total: {patternMixTotal.toFixed(2)} {patternMixValid ? '\u2713' : '(must = 1.0)'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {(Object.keys(DEFAULT_PATTERN_MIX) as Array<keyof PatternMix>).map(key => (
                        <div key={key}>
                          <div className="flex items-center justify-between mb-0.5">
                            <span className="text-xs text-gray-600 capitalize">{key}</span>
                            <span className="text-xs font-mono text-gray-500">
                              {(options.showcasePatternMix[key] * 100).toFixed(0)}%
                            </span>
                          </div>
                          <input
                            type="range"
                            min={0}
                            max={100}
                            step={5}
                            value={options.showcasePatternMix[key] * 100}
                            onChange={e => {
                              const newMix = { ...options.showcasePatternMix };
                              newMix[key] = parseInt(e.target.value, 10) / 100;
                              setOption('showcasePatternMix', newMix);
                            }}
                            className="w-full h-1.5 bg-gray-200 rounded-lg cursor-pointer accent-blue-600"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Pillar Weights */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-xs font-medium text-gray-500">Pillar Weights (DC2_S)</label>
                      <span className={`text-xs font-mono ${weightsValid ? 'text-green-600' : 'text-red-600'}`}>
                        Total: {weightsTotal.toFixed(2)} {weightsValid ? '\u2713' : '(must = 1.0)'}
                      </span>
                    </div>
                    <div className="grid grid-cols-5 gap-3">
                      {(Object.keys(DEFAULT_WEIGHTS) as Array<keyof PillarWeights>).map(key => (
                        <div key={key}>
                          <div className="flex items-center justify-between mb-0.5">
                            <span className="text-xs font-bold text-gray-600" title={PILLAR_LABELS[key]}>{key}</span>
                            <span className="text-xs font-mono text-gray-500">
                              {(options.weights[key] * 100).toFixed(0)}%
                            </span>
                          </div>
                          <input
                            type="range"
                            min={0}
                            max={100}
                            step={5}
                            value={options.weights[key] * 100}
                            onChange={e => {
                              const newW = { ...options.weights };
                              newW[key] = parseInt(e.target.value, 10) / 100;
                              setOption('weights', newW);
                            }}
                            className="w-full h-1.5 bg-gray-200 rounded-lg cursor-pointer accent-blue-600"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Scenario 4: Cleanup Options */}
              {hasCleanup && (
                <div className="border border-amber-200 bg-amber-50/30 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-amber-800 flex items-center gap-2 mb-2">
                    <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-100 text-amber-700 text-xs font-bold">4</span>
                    Cleanup Options
                  </h4>
                  <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={options.dryRun}
                      onChange={e => setOption('dryRun', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                    />
                    Dry Run (preview only — do not delete)
                  </label>
                  <p className="text-xs text-gray-500 mt-1 ml-6">
                    Shows what would be deleted without actually removing any data
                  </p>
                </div>
              )}

              {/* Scenario 8: Context Graph Options */}
              {hasContextGraph && (
                <div className="border border-purple-200 bg-purple-50/30 rounded-lg p-4 space-y-4">
                  <h4 className="text-sm font-semibold text-purple-800 flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-purple-100 text-purple-700 text-xs font-bold">8</span>
                    Context Graph Options
                  </h4>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Story Arc</label>
                      <select
                        value={options.arcId || ''}
                        onChange={e => setOption('arcId', e.target.value || undefined)}
                        className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 bg-white"
                      >
                        <option value="">Random (default)</option>
                        {storyArcs.map(arc => (
                          <option key={arc.arc_id} value={arc.arc_id}>
                            {arc.arc_name}
                          </option>
                        ))}
                      </select>
                      {options.arcId && storyArcs.length > 0 && (
                        <p className="text-xs text-purple-600 mt-1">
                          {storyArcs.find(a => a.arc_id === options.arcId)?.description || ''}
                        </p>
                      )}
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Num Accounts <span className="text-gray-400">(1-50)</span>
                      </label>
                      <input
                        type="number"
                        value={options.numAccounts}
                        onChange={e => setOption('numAccounts', Math.max(1, Math.min(50, parseInt(e.target.value, 10) || 10)))}
                        min={1}
                        max={50}
                        className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Scenario 9: ROI Simulation Options */}
              {hasROISimulation && (
                <div className="border border-emerald-200 bg-emerald-50/30 rounded-lg p-4 space-y-4">
                  <h4 className="text-sm font-semibold text-emerald-800 flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold">9</span>
                    ROI Simulation Options
                  </h4>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Months <span className="text-gray-400">(1-12)</span>
                      </label>
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min={1}
                          max={12}
                          step={1}
                          value={options.months || 6}
                          onChange={e => setOption('months', parseInt(e.target.value, 10))}
                          className="flex-1 h-1.5 bg-gray-200 rounded-lg cursor-pointer accent-emerald-600"
                        />
                        <span className="text-sm font-mono text-emerald-700 w-8 text-right">
                          {options.months || 6}
                        </span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Improvement % <span className="text-gray-400">(0.5-10)</span>
                      </label>
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min={0.5}
                          max={10}
                          step={0.5}
                          value={options.improvement || 2.5}
                          onChange={e => setOption('improvement', parseFloat(e.target.value))}
                          className="flex-1 h-1.5 bg-gray-200 rounded-lg cursor-pointer accent-emerald-600"
                        />
                        <span className="text-sm font-mono text-emerald-700 w-12 text-right">
                          {(options.improvement || 2.5).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Controls row */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center gap-4 flex-wrap">
          <button
            onClick={handleStart}
            disabled={isRunning || starting || selected.size === 0}
            className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm transition-colors"
          >
            {starting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {starting ? 'Starting...' : isRunning ? 'Running...' : 'Run Selected'}
          </button>

          <span className="text-sm text-gray-500">
            {selected.size} scenario{selected.size !== 1 ? 's' : ''} selected
          </span>

          {error && (
            <div className="flex items-center gap-1 text-sm text-red-600">
              <AlertTriangle className="w-4 h-4" />
              {error}
            </div>
          )}
        </div>
      </div>

      {/* ── Active Run Monitor ── */}
      {activeRun && <RunMonitor activeRun={activeRun} />}

      {/* ── Run History ── */}
      <RunHistory
        history={history}
        setHistory={setHistory}
        setActiveRun={setActiveRun}
      />
    </div>
  );
};

export default ScenariosTab;
