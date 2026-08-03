/**
 * Settings Page
 * =============
 * 
 * Comprehensive settings management for CS Pulse:
 * - Feature Flags
 * - Weight Management (Pillar + KPI)
 * - Thresholds
 * - Event Severities
 * - Data Sources
 * - AI Configuration
 * - Learning Status
 */

import React, { useState, useEffect } from 'react';
import NavLogoutButton from '../shared/NavLogoutButton';
import {
  Settings, ToggleLeft, ToggleRight, Sliders, Database, Bell,
  Users, Key, Download, Upload, Info, ChevronDown, ChevronRight,
  Save, RotateCcw, AlertCircle, CheckCircle, Brain, Target,
  TrendingUp, Zap, Shield, Activity, BarChart2, RefreshCw
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface FeatureFlags {
  enable_signal_analyst: boolean;
  enable_rca_generator: boolean;
  enable_qualitative_signals: boolean;
  enable_what_if: boolean;
  enable_playbooks: boolean;
  enable_learning_loop: boolean;
  enable_notifications: boolean;
  enable_export: boolean;
  dark_mode: boolean;
}

interface Thresholds {
  healthy_min: number;
  at_risk_min: number;
  churn_alert_pct: number;
  expansion_alert_pct: number;
  prediction_horizon_days: number;
}

interface PillarWeights {
  P1_Performance: number;
  P2_Usage: number;
  P3_Business: number;
  P4_Relationship: number;
  P5_Growth: number;
}

interface EventSeverity {
  name: string;
  severity: number;
  health_impact: number;
  type: 'negative' | 'positive';
}

interface LearningStatus {
  mode: 'active' | 'frozen';
  iterations: number;
  target_iterations: number;
  current_accuracy: number;
  target_accuracy: number;
  convergence_month: number | null;
  last_update: string;
}

interface AppSettings {
  features: FeatureFlags;
  thresholds: Thresholds;
  pillar_weights: PillarWeights;
  kpi_weights: Record<string, Record<string, number>>;
  event_severities: EventSeverity[];
  learning: LearningStatus;
  ai_provider: 'gpt-4o' | 'claude-sonnet-4' | 'gpt-4';
  weights_source: 'bootstrap' | 'custom' | 'learned';
}

// ============================================================================
// DEFAULT VALUES
// ============================================================================

const DEFAULT_FEATURES: FeatureFlags = {
  enable_signal_analyst: true,
  enable_rca_generator: true,
  enable_qualitative_signals: true,
  enable_what_if: false,
  enable_playbooks: false,
  enable_learning_loop: true,
  enable_notifications: true,
  enable_export: true,
  dark_mode: false
};

const DEFAULT_THRESHOLDS: Thresholds = {
  healthy_min: 70,
  at_risk_min: 50,
  churn_alert_pct: 60,
  expansion_alert_pct: 50,
  prediction_horizon_days: 90
};

const DEFAULT_PILLAR_WEIGHTS: PillarWeights = {
  P1_Performance: 0.20,
  P2_Usage: 0.20,
  P3_Business: 0.15,
  P4_Relationship: 0.20,
  P5_Growth: 0.25
};

const DEFAULT_KPI_WEIGHTS: Record<string, Record<string, number>> = {
  P1_Performance: {
    'uptime_pct': 0.35,
    'response_time_ms': 0.25,
    'error_rate': 0.25,
    'sla_compliance': 0.15
  },
  P2_Usage: {
    'daily_active_users': 0.30,
    'feature_adoption': 0.25,
    'session_duration': 0.20,
    'login_frequency': 0.25
  },
  P3_Business: {
    'roi_score': 0.40,
    'cost_savings': 0.30,
    'value_realized': 0.30
  },
  P4_Relationship: {
    'nps_score': 0.35,
    'csat_score': 0.25,
    'engagement_score': 0.25,
    'executive_engagement': 0.15
  },
  P5_Growth: {
    'expansion_signals': 0.30,
    'upsell_readiness': 0.30,
    'referral_likelihood': 0.20,
    'contract_growth': 0.20
  }
};

const DEFAULT_EVENT_SEVERITIES: EventSeverity[] = [
  { name: 'Critical Outage (>4hr)', severity: 10, health_impact: -15, type: 'negative' },
  { name: 'Support Escalation', severity: 8, health_impact: -10, type: 'negative' },
  { name: 'Executive Sponsor Change', severity: 7, health_impact: -8, type: 'negative' },
  { name: 'Usage Drop >20%', severity: 8, health_impact: -12, type: 'negative' },
  { name: 'Missed SLA', severity: 6, health_impact: -5, type: 'negative' },
  { name: 'NPS Score Drop (>10pts)', severity: 5, health_impact: -5, type: 'negative' },
  { name: 'Late Payment (>30d)', severity: 3, health_impact: -3, type: 'negative' },
  { name: 'Feature Request Declined', severity: 4, health_impact: -2, type: 'negative' },
  { name: 'QBR Completed', severity: 6, health_impact: 5, type: 'positive' },
  { name: 'Expansion Discussion', severity: 8, health_impact: 8, type: 'positive' },
  { name: 'Reference/Testimonial', severity: 9, health_impact: 10, type: 'positive' }
];

const DEFAULT_LEARNING: LearningStatus = {
  mode: 'active',
  iterations: 47,
  target_iterations: 100,
  current_accuracy: 0.72,
  target_accuracy: 0.85,
  convergence_month: null,
  last_update: new Date().toISOString()
};

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

const Toggle: React.FC<{
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  label: string;
  description?: string;
}> = ({ enabled, onChange, label, description }) => (
  <div className="flex items-center justify-between py-3">
    <div>
      <p className="font-medium text-gray-900">{label}</p>
      {description && <p className="text-sm text-gray-500">{description}</p>}
    </div>
    <button
      onClick={() => onChange(!enabled)}
      className={`relative w-12 h-6 rounded-full transition-colors ${
        enabled ? 'bg-blue-600' : 'bg-gray-300'
      }`}
    >
      <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
        enabled ? 'translate-x-6' : 'translate-x-0'
      }`} />
    </button>
  </div>
);

const SliderInput: React.FC<{
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  label: string;
  unit?: string;
  showValue?: boolean;
}> = ({ value, onChange, min, max, step = 1, label, unit = '', showValue = true }) => (
  <div className="py-2">
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      {showValue && (
        <span className="text-sm text-gray-600">{value}{unit}</span>
      )}
    </div>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
    />
  </div>
);

const WeightBar: React.FC<{
  label: string;
  value: number;
  onChange: (value: number) => void;
  color: string;
}> = ({ label, value, onChange, color }) => (
  <div className="py-2">
    <div className="flex items-center justify-between mb-1">
      <span className="text-sm font-medium">{label}</span>
      <div className="flex items-center gap-2">
        <input
          type="number"
          min={5}
          max={50}
          value={Math.round(value * 100)}
          onChange={(e) => onChange(Number(e.target.value) / 100)}
          className="w-14 px-2 py-1 text-sm border rounded text-right"
        />
        <span className="text-sm text-gray-500">%</span>
      </div>
    </div>
    <div className="w-full bg-gray-200 rounded-full h-3">
      <div
        className={`h-3 rounded-full transition-all ${color}`}
        style={{ width: `${value * 100}%` }}
      />
    </div>
  </div>
);

const SectionHeader: React.FC<{
  icon: React.ReactNode;
  title: string;
  description?: string;
}> = ({ icon, title, description }) => (
  <div className="flex items-start gap-3 mb-4">
    <div className="p-2 bg-blue-100 rounded-lg text-blue-600">
      {icon}
    </div>
    <div>
      <h3 className="text-lg font-semibold">{title}</h3>
      {description && <p className="text-sm text-gray-500">{description}</p>}
    </div>
  </div>
);

// ============================================================================
// MAIN SETTINGS PAGE
// ============================================================================

const SettingsPage: React.FC = () => {
  // State
  const [activeSection, setActiveSection] = useState('features');
  const [features, setFeatures] = useState<FeatureFlags>(DEFAULT_FEATURES);
  const [thresholds, setThresholds] = useState<Thresholds>(DEFAULT_THRESHOLDS);
  const [pillarWeights, setPillarWeights] = useState<PillarWeights>(DEFAULT_PILLAR_WEIGHTS);
  const [kpiWeights, setKpiWeights] = useState(DEFAULT_KPI_WEIGHTS);
  const [eventSeverities, setEventSeverities] = useState(DEFAULT_EVENT_SEVERITIES);
  const [learning, setLearning] = useState<LearningStatus>(DEFAULT_LEARNING);
  const [aiProvider, setAiProvider] = useState<'gpt-4o' | 'claude-sonnet-4' | 'gpt-4'>('gpt-4o');
  const [weightsSource, setWeightsSource] = useState<'bootstrap' | 'custom' | 'learned'>('bootstrap');
  const [expandedPillar, setExpandedPillar] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);

  // Navigation items
  const navItems = [
    { id: 'features', label: 'Feature Flags', icon: <ToggleRight className="w-4 h-4" /> },
    { id: 'weights', label: 'Weight Management', icon: <Sliders className="w-4 h-4" /> },
    { id: 'thresholds', label: 'Thresholds', icon: <Target className="w-4 h-4" /> },
    { id: 'events', label: 'Event Severities', icon: <AlertCircle className="w-4 h-4" /> },
    { id: 'learning', label: 'Learning Status', icon: <Brain className="w-4 h-4" /> },
    { id: 'ai', label: 'AI Configuration', icon: <Zap className="w-4 h-4" /> },
    { id: 'data', label: 'Data Sources', icon: <Database className="w-4 h-4" /> },
  ];

  // Pillar colors
  const pillarColors: Record<string, string> = {
    P1_Performance: 'bg-blue-500',
    P2_Usage: 'bg-green-500',
    P3_Business: 'bg-purple-500',
    P4_Relationship: 'bg-amber-500',
    P5_Growth: 'bg-rose-500'
  };

  const pillarLabels: Record<string, string> = {
    P1_Performance: 'P1: Performance',
    P2_Usage: 'P2: Usage',
    P3_Business: 'P3: Business',
    P4_Relationship: 'P4: Relationship',
    P5_Growth: 'P5: Growth'
  };

  // Normalize weights to sum to 1
  const normalizeWeights = (weights: PillarWeights): PillarWeights => {
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    const normalized: any = {};
    for (const key of Object.keys(weights)) {
      normalized[key] = weights[key as keyof PillarWeights] / total;
    }
    return normalized;
  };

  // Handle pillar weight change
  const handlePillarWeightChange = (pillar: keyof PillarWeights, value: number) => {
    const newWeights = { ...pillarWeights, [pillar]: value };
    setPillarWeights(normalizeWeights(newWeights));
    setHasChanges(true);
  };

  // Handle save
  const handleSave = async () => {
    setSaving(true);
    try {
      // Save to backend
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          features,
          thresholds,
          pillar_weights: pillarWeights,
          kpi_weights: kpiWeights,
          event_severities: eventSeverities,
          learning,
          ai_provider: aiProvider,
          weights_source: weightsSource
        })
      });
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setSaving(false);
    }
  };

  // Handle reset
  const handleReset = () => {
    if (confirm('Reset all settings to defaults?')) {
      setFeatures(DEFAULT_FEATURES);
      setThresholds(DEFAULT_THRESHOLDS);
      setPillarWeights(DEFAULT_PILLAR_WEIGHTS);
      setKpiWeights(DEFAULT_KPI_WEIGHTS);
      setEventSeverities(DEFAULT_EVENT_SEVERITIES);
      setHasChanges(true);
    }
  };

  // Calculate total pillar weight
  const totalWeight = Object.values(pillarWeights).reduce((a, b) => a + b, 0);

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Settings className="w-6 h-6 text-gray-600" />
              <h1 className="text-xl font-bold">Settings</h1>
            </div>
            <div className="flex items-center gap-3">
              {hasChanges && (
                <span className="text-sm text-amber-600 flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  Unsaved changes
                </span>
              )}
              <button
                onClick={handleReset}
                className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded flex items-center gap-1"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
              <button
                onClick={handleSave}
                disabled={!hasChanges || saving}
                className={`px-4 py-1.5 text-sm rounded flex items-center gap-1 ${
                  hasChanges
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                }`}
              >
                {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-6">
          {/* Navigation */}
          <div className="w-56 flex-shrink-0">
            <nav className="bg-white rounded-lg shadow p-2">
              {navItems.map(item => (
                <button
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded text-sm ${
                    activeSection === item.id
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {item.icon}
                  {item.label}
                </button>
              ))}
              <div className="mt-4 pt-4 border-t border-gray-200">
                <NavLogoutButton variant="light-sidebar" className="px-3 py-2" />
              </div>
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 bg-white rounded-lg shadow p-6">
            {/* Feature Flags */}
            {activeSection === 'features' && (
              <div>
                <SectionHeader
                  icon={<ToggleRight className="w-5 h-5" />}
                  title="Feature Flags"
                  description="Enable or disable application features"
                />
                <div className="divide-y">
                  <Toggle
                    enabled={features.enable_signal_analyst}
                    onChange={(v) => { setFeatures({...features, enable_signal_analyst: v}); setHasChanges(true); }}
                    label="Signal Analyst"
                    description="AI-powered account health analysis"
                  />
                  <Toggle
                    enabled={features.enable_rca_generator}
                    onChange={(v) => { setFeatures({...features, enable_rca_generator: v}); setHasChanges(true); }}
                    label="RCA Generator"
                    description="Root cause analysis tab in journey view"
                  />
                  <Toggle
                    enabled={features.enable_qualitative_signals}
                    onChange={(v) => { setFeatures({...features, enable_qualitative_signals: v}); setHasChanges(true); }}
                    label="Qualitative Signals"
                    description="Email, meeting, and ticket analysis"
                  />
                  <Toggle
                    enabled={features.enable_what_if}
                    onChange={(v) => { setFeatures({...features, enable_what_if: v}); setHasChanges(true); }}
                    label="What-If Scenarios"
                    description="Scenario simulation for health impact"
                  />
                  <Toggle
                    enabled={features.enable_playbooks}
                    onChange={(v) => { setFeatures({...features, enable_playbooks: v}); setHasChanges(true); }}
                    label="Playbooks Engine"
                    description="Automated playbook triggers and tracking"
                  />
                  <Toggle
                    enabled={features.enable_learning_loop}
                    onChange={(v) => { setFeatures({...features, enable_learning_loop: v}); setHasChanges(true); }}
                    label="Learning Loop"
                    description="Adaptive weight adjustment based on outcomes"
                  />
                  <Toggle
                    enabled={features.enable_notifications}
                    onChange={(v) => { setFeatures({...features, enable_notifications: v}); setHasChanges(true); }}
                    label="Notifications"
                    description="Slack and email alerts"
                  />
                  <Toggle
                    enabled={features.enable_export}
                    onChange={(v) => { setFeatures({...features, enable_export: v}); setHasChanges(true); }}
                    label="Export"
                    description="Export to CSV and PDF"
                  />
                </div>
              </div>
            )}

            {/* Weight Management */}
            {activeSection === 'weights' && (
              <div>
                <SectionHeader
                  icon={<Sliders className="w-5 h-5" />}
                  title="Weight Management"
                  description="Configure pillar and KPI weights for health calculation"
                />

                {/* Weight Source */}
                <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Weight Source</p>
                      <p className="text-sm text-gray-500">Current weights are based on: {weightsSource}</p>
                    </div>
                    <select
                      value={weightsSource}
                      onChange={(e) => { setWeightsSource(e.target.value as any); setHasChanges(true); }}
                      className="px-3 py-1.5 border rounded"
                    >
                      <option value="bootstrap">Bootstrap (Supermicro)</option>
                      <option value="custom">Custom</option>
                      <option value="learned">Learned</option>
                    </select>
                  </div>
                </div>

                {/* Pillar Weights */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-medium">Pillar Weights (L2)</h4>
                    <span className={`text-sm ${Math.abs(totalWeight - 1) < 0.01 ? 'text-green-600' : 'text-red-600'}`}>
                      Total: {(totalWeight * 100).toFixed(0)}%
                    </span>
                  </div>
                  {Object.entries(pillarWeights).map(([pillar, weight]) => (
                    <WeightBar
                      key={pillar}
                      label={pillarLabels[pillar]}
                      value={weight}
                      onChange={(v) => handlePillarWeightChange(pillar as keyof PillarWeights, v)}
                      color={pillarColors[pillar]}
                    />
                  ))}
                </div>

                {/* KPI Weights */}
                <div>
                  <h4 className="font-medium mb-4">KPI Weights (L1)</h4>
                  {Object.entries(kpiWeights).map(([pillar, kpis]) => (
                    <div key={pillar} className="border rounded-lg mb-2">
                      <button
                        onClick={() => setExpandedPillar(expandedPillar === pillar ? null : pillar)}
                        className="w-full flex items-center justify-between p-3 hover:bg-gray-50"
                      >
                        <div className="flex items-center gap-2">
                          <div className={`w-3 h-3 rounded ${pillarColors[pillar]}`} />
                          <span className="font-medium">{pillarLabels[pillar]}</span>
                          <span className="text-sm text-gray-500">
                            ({(pillarWeights[pillar as keyof PillarWeights] * 100).toFixed(0)}%)
                          </span>
                        </div>
                        {expandedPillar === pillar ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </button>
                      {expandedPillar === pillar && (
                        <div className="px-4 pb-4 border-t bg-gray-50">
                          {Object.entries(kpis).map(([kpi, kpiWeight]) => (
                            <div key={kpi} className="flex items-center justify-between py-2">
                              <span className="text-sm">{kpi.replace(/_/g, ' ')}</span>
                              <div className="flex items-center gap-2">
                                <input
                                  type="range"
                                  min={5}
                                  max={50}
                                  value={kpiWeight * 100}
                                  onChange={(e) => {
                                    const newKpiWeights = { ...kpiWeights };
                                    newKpiWeights[pillar][kpi] = Number(e.target.value) / 100;
                                    setKpiWeights(newKpiWeights);
                                    setHasChanges(true);
                                  }}
                                  className="w-24"
                                />
                                <span className="text-sm text-gray-600 w-10">
                                  {(kpiWeight * 100).toFixed(0)}%
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Thresholds */}
            {activeSection === 'thresholds' && (
              <div>
                <SectionHeader
                  icon={<Target className="w-5 h-5" />}
                  title="Thresholds"
                  description="Configure health score thresholds and alert triggers"
                />
                <div className="space-y-6">
                  <div>
                    <h4 className="font-medium mb-3">Health Score Thresholds</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <SliderInput
                        label="Healthy Minimum"
                        value={thresholds.healthy_min}
                        onChange={(v) => { setThresholds({...thresholds, healthy_min: v}); setHasChanges(true); }}
                        min={60}
                        max={90}
                        unit=""
                      />
                      <SliderInput
                        label="At-Risk Minimum"
                        value={thresholds.at_risk_min}
                        onChange={(v) => { setThresholds({...thresholds, at_risk_min: v}); setHasChanges(true); }}
                        min={30}
                        max={70}
                        unit=""
                      />
                    </div>
                    <div className="mt-4 flex items-center gap-2">
                      <div className="flex-1 h-6 rounded-full overflow-hidden flex">
                        <div className="bg-red-500 h-full" style={{ width: `${thresholds.at_risk_min}%` }} />
                        <div className="bg-yellow-500 h-full" style={{ width: `${thresholds.healthy_min - thresholds.at_risk_min}%` }} />
                        <div className="bg-green-500 h-full" style={{ width: `${100 - thresholds.healthy_min}%` }} />
                      </div>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>0 (Critical)</span>
                      <span>{thresholds.at_risk_min} (At-Risk)</span>
                      <span>{thresholds.healthy_min} (Healthy)</span>
                      <span>100</span>
                    </div>
                  </div>

                  <div className="border-t pt-6">
                    <h4 className="font-medium mb-3">Alert Thresholds</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <SliderInput
                        label="Churn Alert Threshold"
                        value={thresholds.churn_alert_pct}
                        onChange={(v) => { setThresholds({...thresholds, churn_alert_pct: v}); setHasChanges(true); }}
                        min={30}
                        max={80}
                        unit="%"
                      />
                      <SliderInput
                        label="Expansion Alert Threshold"
                        value={thresholds.expansion_alert_pct}
                        onChange={(v) => { setThresholds({...thresholds, expansion_alert_pct: v}); setHasChanges(true); }}
                        min={30}
                        max={80}
                        unit="%"
                      />
                    </div>
                  </div>

                  <div className="border-t pt-6">
                    <h4 className="font-medium mb-3">Prediction Horizon</h4>
                    <SliderInput
                      label="Days ahead to predict"
                      value={thresholds.prediction_horizon_days}
                      onChange={(v) => { setThresholds({...thresholds, prediction_horizon_days: v}); setHasChanges(true); }}
                      min={30}
                      max={180}
                      step={30}
                      unit=" days"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Event Severities */}
            {activeSection === 'events' && (
              <div>
                <SectionHeader
                  icon={<AlertCircle className="w-5 h-5" />}
                  title="Event Severity Calibration"
                  description="Configure how different events impact health scores"
                />
                <div className="space-y-3">
                  {eventSeverities.map((event, index) => (
                    <div
                      key={index}
                      className={`p-4 rounded-lg border ${
                        event.type === 'negative' ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">{event.name}</span>
                        <span className={`text-sm font-medium ${
                          event.type === 'negative' ? 'text-red-600' : 'text-green-600'
                        }`}>
                          {event.health_impact > 0 ? '+' : ''}{event.health_impact} pts
                        </span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-gray-500 w-16">Severity:</span>
                        <input
                          type="range"
                          min={1}
                          max={10}
                          value={event.severity}
                          onChange={(e) => {
                            const newEvents = [...eventSeverities];
                            newEvents[index].severity = Number(e.target.value);
                            newEvents[index].health_impact = event.type === 'negative'
                              ? -Math.round(Number(e.target.value) * 1.5)
                              : Math.round(Number(e.target.value) * 1.1);
                            setEventSeverities(newEvents);
                            setHasChanges(true);
                          }}
                          className="flex-1"
                        />
                        <span className="text-sm font-medium w-8">{event.severity}/10</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Learning Status */}
            {activeSection === 'learning' && (
              <div>
                <SectionHeader
                  icon={<Brain className="w-5 h-5" />}
                  title="Learning Status"
                  description="Monitor and control the adaptive weight learning system"
                />
                
                <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="font-medium">Learning Mode</p>
                      <p className="text-sm text-gray-600">
                        {learning.mode === 'active' 
                          ? 'System is actively learning from outcomes'
                          : 'Learning is paused, using frozen weights'}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => { setLearning({...learning, mode: 'active'}); setHasChanges(true); }}
                        className={`px-3 py-1.5 rounded text-sm ${
                          learning.mode === 'active'
                            ? 'bg-blue-600 text-white'
                            : 'bg-white border text-gray-600'
                        }`}
                      >
                        Active Learning
                      </button>
                      <button
                        onClick={() => { setLearning({...learning, mode: 'frozen'}); setHasChanges(true); }}
                        className={`px-3 py-1.5 rounded text-sm ${
                          learning.mode === 'frozen'
                            ? 'bg-blue-600 text-white'
                            : 'bg-white border text-gray-600'
                        }`}
                      >
                        Frozen
                      </button>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">Iterations</p>
                    <p className="text-2xl font-bold">{learning.iterations} / {learning.target_iterations}</p>
                    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${(learning.iterations / learning.target_iterations) * 100}%` }}
                      />
                    </div>
                  </div>
                  
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">Current Accuracy</p>
                    <p className={`text-2xl font-bold ${
                      learning.current_accuracy >= learning.target_accuracy ? 'text-green-600' : 'text-amber-600'
                    }`}>
                      {(learning.current_accuracy * 100).toFixed(1)}%
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      Target: {(learning.target_accuracy * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>

                <div className="mt-6 flex gap-3">
                  <button className="px-4 py-2 bg-white border rounded hover:bg-gray-50 text-sm">
                    View Learning History
                  </button>
                  <button className="px-4 py-2 bg-white border rounded hover:bg-gray-50 text-sm">
                    Export Weights
                  </button>
                  <button className="px-4 py-2 bg-white border rounded hover:bg-gray-50 text-sm">
                    Import Weights
                  </button>
                </div>
              </div>
            )}

            {/* AI Configuration */}
            {activeSection === 'ai' && (
              <div>
                <SectionHeader
                  icon={<Zap className="w-5 h-5" />}
                  title="AI Configuration"
                  description="Configure the LLM provider for Signal Analyst"
                />
                
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium mb-2">LLM Provider</label>
                    <select
                      value={aiProvider}
                      onChange={(e) => { setAiProvider(e.target.value as any); setHasChanges(true); }}
                      className="w-full px-3 py-2 border rounded"
                    >
                      <option value="gpt-4o">GPT-4o (OpenAI) - $2.50/$10.00 per 1M tokens</option>
                      <option value="claude-sonnet-4">Claude Sonnet 4 (Anthropic) - $3.00/$15.00 per 1M tokens</option>
                      <option value="gpt-4">GPT-4 Turbo (OpenAI) - $10.00/$30.00 per 1M tokens</option>
                    </select>
                  </div>

                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">API Key Status</span>
                      <span className="flex items-center gap-1 text-green-600">
                        <CheckCircle className="w-4 h-4" />
                        Valid
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">sk-proj-****...****</p>
                    <button className="mt-2 text-sm text-blue-600 hover:underline">
                      Update API Key
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-500">Monthly Usage</p>
                      <p className="text-xl font-bold">$12.47</p>
                      <p className="text-sm text-gray-500">of $50.00 limit</p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-500">Avg Response Time</p>
                      <p className="text-xl font-bold">16.5s</p>
                      <p className="text-sm text-gray-500">per analysis</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Data Sources */}
            {activeSection === 'data' && (
              <div>
                <SectionHeader
                  icon={<Database className="w-5 h-5" />}
                  title="Data Sources"
                  description="Manage file imports and API connections"
                />
                
                <div className="space-y-6">
                  <div>
                    <h4 className="font-medium mb-3">File Imports</h4>
                    <div className="space-y-2">
                      {[
                        { name: 'accounts.csv', status: 'loaded', rows: 47, date: 'Jan 13, 2026' },
                        { name: 'kpis.csv', status: 'loaded', rows: 3220, date: 'Jan 13, 2026' },
                        { name: 'tickets.csv', status: 'not_loaded', rows: 0, date: '' },
                        { name: 'activities.csv', status: 'not_loaded', rows: 0, date: '' }
                      ].map((file, i) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center gap-3">
                            {file.status === 'loaded' ? (
                              <CheckCircle className="w-5 h-5 text-green-500" />
                            ) : (
                              <div className="w-5 h-5 border-2 border-gray-300 rounded" />
                            )}
                            <div>
                              <p className="font-medium">{file.name}</p>
                              {file.status === 'loaded' && (
                                <p className="text-xs text-gray-500">{file.rows} rows • {file.date}</p>
                              )}
                            </div>
                          </div>
                          <button className="px-3 py-1 text-sm bg-white border rounded hover:bg-gray-50">
                            {file.status === 'loaded' ? 'Re-upload' : 'Upload'}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="border-t pt-6">
                    <h4 className="font-medium mb-3">API Connections</h4>
                    <div className="space-y-2">
                      {[
                        { name: 'Salesforce', connected: false },
                        { name: 'HubSpot', connected: false },
                        { name: 'Zendesk', connected: true, records: 1247 },
                        { name: 'Jira', connected: false },
                        { name: 'Slack', connected: true, channel: '#cs-alerts' }
                      ].map((api, i) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center gap-3">
                            {api.connected ? (
                              <CheckCircle className="w-5 h-5 text-green-500" />
                            ) : (
                              <div className="w-5 h-5 border-2 border-gray-300 rounded" />
                            )}
                            <div>
                              <p className="font-medium">{api.name}</p>
                              {api.connected && (
                                <p className="text-xs text-gray-500">
                                  {'records' in api ? `${api.records} records` : api.channel}
                                </p>
                              )}
                            </div>
                          </div>
                          <button className={`px-3 py-1 text-sm rounded ${
                            api.connected
                              ? 'bg-red-100 text-red-700 hover:bg-red-200'
                              : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                          }`}>
                            {api.connected ? 'Disconnect' : 'Connect'}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
