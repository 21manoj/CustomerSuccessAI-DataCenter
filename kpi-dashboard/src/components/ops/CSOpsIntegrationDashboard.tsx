/**
 * CS Ops Integration Dashboard
 * ==============================
 *
 * Operations dashboard for managing external data connectors,
 * monitoring sync health, and configuring playbook webhook triggers.
 *
 * Route: /dc-dashboard/ops
 *
 * Sections:
 * 1. Integration Health Overview — traffic-light status for all connectors
 * 2. Connector Management — CRUD for SFDC, HubSpot, Zendesk, n8n
 * 3. Sync Activity — real-time feed of ingest operations
 * 4. Playbook Triggers — outbound webhook configuration
 * 5. Data Quality — field mapping validation + freshness
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity, AlertTriangle, CheckCircle, Clock, Cloud, Database,
  ExternalLink, Filter, Globe, Loader2, MoreVertical, Pause,
  Play, Plus, RefreshCw, Settings, Trash2, Unplug, Zap,
  ArrowUpRight, ArrowDownRight, ChevronRight, Search, X,
  Workflow, Bell, Shield, BarChart3,
} from 'lucide-react';

// ============================================================
// Types
// ============================================================

interface Connector {
  connector_id: number;
  customer_id: number;
  connector_type: string;
  connector_name: string;
  description: string | null;
  auth_type: string;
  sync_direction: string;
  sync_frequency_minutes: number;
  sync_enabled: boolean;
  field_mapping: Record<string, any>;
  entity_mapping: Record<string, any>;
  status: string;
  status_message: string | null;
  last_sync_at: string | null;
  last_sync_status: string | null;
  last_sync_records: number;
  last_sync_errors: number;
  last_error_at: string | null;
  last_error_message: string | null;
  consecutive_errors: number;
  created_at: string | null;
  updated_at: string | null;
}

interface SyncLog {
  log_id: number;
  connector_id: number;
  sync_type: string;
  sync_status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  records_created: number;
  records_updated: number;
  records_skipped: number;
  records_errored: number;
  error_message: string | null;
  watermark_value: string | null;
}

interface IntegrationHealth {
  overall_status: string;
  connectors: { total: number; active: number; errored: number; stale: number };
  last_24h: { syncs: number; records_processed: number; errors?: number };
  pending_events: number;
  connector_details: Connector[];
}

interface PlaybookTrigger {
  trigger_id: number;
  trigger_name: string;
  trigger_type: string;
  trigger_condition: { metric: string; operator: string; threshold: number };
  webhook_url: string;
  enabled: boolean;
  cooldown_minutes: number;
  max_fires_per_day: number;
  last_fired_at: string | null;
  last_fire_status: string | null;
  account_filter: Record<string, any> | null;
  created_at: string | null;
}

interface ConnectorType {
  label: string;
  icon: string;
  color: string;
  auth_types: string[];
  entities: string[];
  docs_url: string | null;
}

// ============================================================
// Helpers
// ============================================================

const customerId = () => localStorage.getItem('customer_id') || '0';
const headers = () => ({
  'Content-Type': 'application/json',
  'X-Customer-ID': customerId(),
});

const STATUS_COLORS: Record<string, string> = {
  healthy: 'text-emerald-600 bg-emerald-50',
  active: 'text-emerald-600 bg-emerald-50',
  warning: 'text-amber-600 bg-amber-50',
  degraded: 'text-red-600 bg-red-50',
  error: 'text-red-600 bg-red-50',
  disabled: 'text-gray-400 bg-gray-50',
  paused: 'text-gray-500 bg-gray-100',
  no_connectors: 'text-gray-400 bg-gray-50',
  pending_setup: 'text-blue-600 bg-blue-50',
  stale: 'text-amber-600 bg-amber-50',
};

const CONNECTOR_ICONS: Record<string, React.ReactNode> = {
  sfdc: <Cloud className="h-5 w-5 text-[#00A1E0]" />,
  hubspot: <Globe className="h-5 w-5 text-[#FF7A59]" />,
  zendesk: <Shield className="h-5 w-5 text-[#03363D]" />,
  n8n: <Workflow className="h-5 w-5 text-[#EA4B71]" />,
  csv_upload: <Database className="h-5 w-5 text-gray-500" />,
  custom_webhook: <Zap className="h-5 w-5 text-purple-500" />,
};

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return 'never';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] || 'text-gray-600 bg-gray-100';
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {status === 'active' || status === 'healthy' ? <CheckCircle className="h-3 w-3 mr-1" /> :
       status === 'error' || status === 'degraded' ? <AlertTriangle className="h-3 w-3 mr-1" /> :
       <Clock className="h-3 w-3 mr-1" />}
      {status.replace('_', ' ')}
    </span>
  );
}

// ============================================================
// Main Component
// ============================================================

const CSOpsIntegrationDashboard: React.FC = () => {
  const [health, setHealth] = useState<IntegrationHealth | null>(null);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
  const [triggers, setTriggers] = useState<PlaybookTrigger[]>([]);
  const [connectorTypes, setConnectorTypes] = useState<Record<string, ConnectorType>>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'connectors' | 'activity' | 'triggers'>('overview');
  const [showAddConnector, setShowAddConnector] = useState(false);
  const [showAddTrigger, setShowAddTrigger] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // ============================================================
  // Data Fetching
  // ============================================================

  const fetchAll = useCallback(async () => {
    try {
      const [healthRes, connectorsRes, logsRes, triggersRes, typesRes] = await Promise.all([
        fetch('/api/integrations/health', { headers: headers() }),
        fetch('/api/integrations/connectors', { headers: headers() }),
        fetch('/api/integrations/sync-logs?limit=30', { headers: headers() }),
        fetch('/api/integrations/playbook-triggers', { headers: headers() }),
        fetch('/api/integrations/connector-types'),
      ]);

      if (healthRes.ok) setHealth(await healthRes.json());
      if (connectorsRes.ok) {
        const data = await connectorsRes.json();
        setConnectors(data.connectors || []);
      }
      if (logsRes.ok) {
        const data = await logsRes.json();
        setSyncLogs(data.logs || []);
      }
      if (triggersRes.ok) {
        const data = await triggersRes.json();
        setTriggers(data.triggers || []);
      }
      if (typesRes.ok) setConnectorTypes(await typesRes.json());
    } catch (err) {
      console.error('Failed to fetch integration data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchAll();
    setRefreshing(false);
  }, [fetchAll]);

  // ============================================================
  // Connector Actions
  // ============================================================

  const testConnector = useCallback(async (connectorId: number) => {
    const res = await fetch(`/api/integrations/connectors/${connectorId}/test`, {
      method: 'POST', headers: headers(),
    });
    if (res.ok) {
      const data = await res.json();
      alert(`Test ${data.test_status}: ${data.message}`);
      fetchAll();
    }
  }, [fetchAll]);

  const toggleConnector = useCallback(async (connector: Connector) => {
    await fetch(`/api/integrations/connectors/${connector.connector_id}`, {
      method: 'PUT',
      headers: headers(),
      body: JSON.stringify({ sync_enabled: !connector.sync_enabled }),
    });
    fetchAll();
  }, [fetchAll]);

  const deleteConnector = useCallback(async (connectorId: number) => {
    if (!confirm('Disable this connector?')) return;
    await fetch(`/api/integrations/connectors/${connectorId}`, {
      method: 'DELETE', headers: headers(),
    });
    fetchAll();
  }, [fetchAll]);

  const createConnector = useCallback(async (type: string, name: string, url: string) => {
    const res = await fetch('/api/integrations/connectors', {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({
        connector_type: type,
        connector_name: name,
        webhook_url: url || undefined,
      }),
    });
    if (res.ok) {
      const data = await res.json();
      alert(`Connector created!\n\nWebhook endpoint: ${data.webhook_endpoint}\nSecret: ${data.webhook_secret}\n\nSave this secret — it won't be shown again.`);
      setShowAddConnector(false);
      fetchAll();
    }
  }, [fetchAll]);

  // ============================================================
  // Trigger Actions
  // ============================================================

  const testTrigger = useCallback(async (triggerId: number) => {
    const res = await fetch(`/api/integrations/playbook-triggers/${triggerId}/test`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ health_score: 42, previous_health_score: 65 }),
    });
    if (res.ok) {
      const data = await res.json();
      alert(`Trigger test: ${data.test_status}\nLoopback mode: ${data.loopback_mode}`);
    }
  }, []);

  const createTrigger = useCallback(async (name: string, type: string, url: string, threshold: number) => {
    const res = await fetch('/api/integrations/playbook-triggers', {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({
        trigger_name: name,
        trigger_type: type,
        trigger_condition: { metric: 'health_score', operator: 'drops_below', threshold },
        webhook_url: url,
        cooldown_minutes: 60,
      }),
    });
    if (res.ok) {
      const data = await res.json();
      alert(`Trigger created!\nSecret: ${data.webhook_secret}\n\nSave this secret.`);
      setShowAddTrigger(false);
      fetchAll();
    }
  }, [fetchAll]);

  // ============================================================
  // Render
  // ============================================================

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Loading integration dashboard...</p>
        </div>
      </div>
    );
  }

  const activeConnectors = connectors.filter(c => c.status === 'active');
  const erroredConnectors = connectors.filter(c => c.consecutive_errors > 0);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Settings className="h-5 w-5 text-gray-500" />
              Integration Operations
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Manage external data connectors, sync health, and playbook triggers
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRefresh}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => setShowAddConnector(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Add Connector
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-4">
          {(['overview', 'connectors', 'activity', 'triggers'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                activeTab === tab
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {tab === 'overview' && <BarChart3 className="h-4 w-4 inline mr-1.5" />}
              {tab === 'connectors' && <Unplug className="h-4 w-4 inline mr-1.5" />}
              {tab === 'activity' && <Activity className="h-4 w-4 inline mr-1.5" />}
              {tab === 'triggers' && <Bell className="h-4 w-4 inline mr-1.5" />}
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6">
        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Health Cards */}
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-500">Overall Status</span>
                  <StatusBadge status={health?.overall_status || 'no_connectors'} />
                </div>
                <div className="text-2xl font-bold text-gray-900">
                  {health?.connectors.active || 0}
                  <span className="text-sm font-normal text-gray-400 ml-1">/ {health?.connectors.total || 0} active</span>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-500">Records (24h)</span>
                  <ArrowUpRight className="h-4 w-4 text-emerald-500" />
                </div>
                <div className="text-2xl font-bold text-gray-900">
                  {(health?.last_24h.records_processed || 0).toLocaleString()}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  across {health?.last_24h.syncs || 0} syncs
                </div>
              </div>

              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-500">Errors</span>
                  {(health?.connectors.errored || 0) > 0 ? (
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                  ) : (
                    <CheckCircle className="h-4 w-4 text-emerald-500" />
                  )}
                </div>
                <div className="text-2xl font-bold text-gray-900">
                  {health?.connectors.errored || 0}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  connectors with errors
                </div>
              </div>

              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-500">Pending Events</span>
                  <Clock className="h-4 w-4 text-amber-500" />
                </div>
                <div className="text-2xl font-bold text-gray-900">
                  {health?.pending_events || 0}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  awaiting processing
                </div>
              </div>
            </div>

            {/* Connector Status Grid */}
            <div className="bg-white rounded-xl border border-gray-200">
              <div className="px-5 py-4 border-b border-gray-100">
                <h3 className="text-sm font-semibold text-gray-700">Connector Status</h3>
              </div>
              <div className="divide-y divide-gray-100">
                {connectors.length === 0 ? (
                  <div className="p-8 text-center text-gray-400">
                    <Unplug className="h-8 w-8 mx-auto mb-2 opacity-40" />
                    <p>No connectors configured yet</p>
                    <button
                      onClick={() => setShowAddConnector(true)}
                      className="mt-3 text-blue-600 text-sm hover:underline"
                    >
                      Add your first connector
                    </button>
                  </div>
                ) : (
                  connectors.map(c => (
                    <div key={c.connector_id} className="px-5 py-3 flex items-center gap-4 hover:bg-gray-50">
                      <div className="flex-shrink-0">
                        {CONNECTOR_ICONS[c.connector_type] || <Database className="h-5 w-5 text-gray-400" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm text-gray-900 truncate">{c.connector_name}</span>
                          <StatusBadge status={c.status} />
                        </div>
                        <div className="text-xs text-gray-400 mt-0.5">
                          Last sync: {timeAgo(c.last_sync_at)} · {c.last_sync_records || 0} records
                          {c.consecutive_errors > 0 && (
                            <span className="text-red-500 ml-2">
                              {c.consecutive_errors} consecutive errors
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => testConnector(c.connector_id)}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                          title="Test connectivity"
                        >
                          <Zap className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => toggleConnector(c)}
                          className="p-1.5 text-gray-400 hover:text-amber-600 hover:bg-amber-50 rounded"
                          title={c.sync_enabled ? 'Pause sync' : 'Resume sync'}
                        >
                          {c.sync_enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Recent Sync Activity */}
            <div className="bg-white rounded-xl border border-gray-200">
              <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-700">Recent Sync Activity</h3>
                <button
                  onClick={() => setActiveTab('activity')}
                  className="text-xs text-blue-600 hover:underline"
                >
                  View all
                </button>
              </div>
              <div className="divide-y divide-gray-100">
                {syncLogs.length === 0 ? (
                  <div className="p-6 text-center text-gray-400 text-sm">
                    No sync activity yet
                  </div>
                ) : (
                  syncLogs.slice(0, 5).map(log => (
                    <div key={log.log_id} className="px-5 py-3 flex items-center gap-3">
                      {log.sync_status === 'success' ? (
                        <CheckCircle className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                      ) : log.sync_status === 'error' ? (
                        <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />
                      ) : (
                        <Clock className="h-4 w-4 text-amber-500 flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <span className="text-sm text-gray-700">
                          {log.sync_type} — {log.records_created} created, {log.records_updated} updated
                          {log.records_errored > 0 && (
                            <span className="text-red-500 ml-1">({log.records_errored} errors)</span>
                          )}
                        </span>
                      </div>
                      <span className="text-xs text-gray-400 flex-shrink-0">
                        {timeAgo(log.started_at)}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* CONNECTORS TAB */}
        {activeTab === 'connectors' && (
          <div className="space-y-4">
            {connectors.map(c => (
              <div key={c.connector_id} className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {CONNECTOR_ICONS[c.connector_type] || <Database className="h-6 w-6 text-gray-400" />}
                    <div>
                      <h3 className="font-semibold text-gray-900">{c.connector_name}</h3>
                      <p className="text-xs text-gray-500">{c.description || c.connector_type}</p>
                    </div>
                    <StatusBadge status={c.status} />
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => testConnector(c.connector_id)}
                      className="px-3 py-1.5 text-xs text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
                    >
                      Test
                    </button>
                    <button
                      onClick={() => toggleConnector(c)}
                      className="px-3 py-1.5 text-xs text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200"
                    >
                      {c.sync_enabled ? 'Pause' : 'Resume'}
                    </button>
                    <button
                      onClick={() => deleteConnector(c.connector_id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-4 mt-4">
                  <div>
                    <span className="text-xs text-gray-400">Last Sync</span>
                    <p className="text-sm font-medium">{timeAgo(c.last_sync_at)}</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-400">Records Synced</span>
                    <p className="text-sm font-medium">{c.last_sync_records}</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-400">Sync Frequency</span>
                    <p className="text-sm font-medium">
                      {c.sync_frequency_minutes === 0 ? 'Real-time (webhook)' : `Every ${c.sync_frequency_minutes}m`}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-400">Direction</span>
                    <p className="text-sm font-medium capitalize">{c.sync_direction}</p>
                  </div>
                </div>

                {c.last_error_message && (
                  <div className="mt-3 p-3 bg-red-50 rounded-lg">
                    <div className="flex items-center gap-1.5 text-red-600 text-xs font-medium mb-1">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      Last error ({timeAgo(c.last_error_at)})
                    </div>
                    <p className="text-xs text-red-500">{c.last_error_message}</p>
                  </div>
                )}

                {/* Field mapping summary */}
                {c.field_mapping && Object.keys(c.field_mapping).length > 0 && (
                  <div className="mt-3">
                    <span className="text-xs text-gray-400">Field Mappings</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {Object.keys(c.field_mapping).map(entity => (
                        <span key={entity} className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">
                          {entity}: {Object.keys(c.field_mapping[entity] || {}).length} fields
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {connectors.length === 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <Unplug className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium text-gray-700 mb-2">No Connectors Yet</h3>
                <p className="text-sm text-gray-400 mb-4">
                  Connect your CRM, support tools, and workflow automation
                </p>
                <button
                  onClick={() => setShowAddConnector(true)}
                  className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  Add First Connector
                </button>
              </div>
            )}
          </div>
        )}

        {/* ACTIVITY TAB */}
        {activeTab === 'activity' && (
          <div className="bg-white rounded-xl border border-gray-200">
            <div className="px-5 py-4 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-700">Sync Activity Log</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {syncLogs.length === 0 ? (
                <div className="p-8 text-center text-gray-400">
                  <Activity className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p>No sync activity recorded yet</p>
                </div>
              ) : (
                syncLogs.map(log => (
                  <div key={log.log_id} className="px-5 py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {log.sync_status === 'success' ? (
                          <CheckCircle className="h-5 w-5 text-emerald-500" />
                        ) : log.sync_status === 'error' ? (
                          <AlertTriangle className="h-5 w-5 text-red-500" />
                        ) : (
                          <Clock className="h-5 w-5 text-amber-500" />
                        )}
                        <div>
                          <span className="text-sm font-medium text-gray-900 capitalize">
                            {log.sync_type} sync
                          </span>
                          <StatusBadge status={log.sync_status} />
                        </div>
                      </div>
                      <span className="text-xs text-gray-400">{timeAgo(log.started_at)}</span>
                    </div>
                    <div className="ml-8 mt-2 grid grid-cols-5 gap-4 text-xs">
                      <div>
                        <span className="text-gray-400">Created</span>
                        <p className="font-medium text-emerald-600">{log.records_created}</p>
                      </div>
                      <div>
                        <span className="text-gray-400">Updated</span>
                        <p className="font-medium text-blue-600">{log.records_updated}</p>
                      </div>
                      <div>
                        <span className="text-gray-400">Skipped</span>
                        <p className="font-medium text-gray-500">{log.records_skipped}</p>
                      </div>
                      <div>
                        <span className="text-gray-400">Errors</span>
                        <p className={`font-medium ${log.records_errored > 0 ? 'text-red-600' : 'text-gray-400'}`}>
                          {log.records_errored}
                        </p>
                      </div>
                      <div>
                        <span className="text-gray-400">Duration</span>
                        <p className="font-medium text-gray-600">
                          {log.duration_seconds ? `${log.duration_seconds.toFixed(1)}s` : '-'}
                        </p>
                      </div>
                    </div>
                    {log.error_message && (
                      <div className="ml-8 mt-2 p-2 bg-red-50 rounded text-xs text-red-600">
                        {log.error_message}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TRIGGERS TAB */}
        {activeTab === 'triggers' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-semibold text-gray-700">Playbook Webhook Triggers</h3>
              <button
                onClick={() => setShowAddTrigger(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                Add Trigger
              </button>
            </div>

            {triggers.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <Bell className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium text-gray-700 mb-2">No Triggers Configured</h3>
                <p className="text-sm text-gray-400 mb-4">
                  Set up automated webhook triggers when health scores change
                </p>
                <button
                  onClick={() => setShowAddTrigger(true)}
                  className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  Create First Trigger
                </button>
              </div>
            ) : (
              triggers.map(t => (
                <div key={t.trigger_id} className="bg-white rounded-xl border border-gray-200 p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${t.enabled ? 'bg-blue-50' : 'bg-gray-100'}`}>
                        <Bell className={`h-5 w-5 ${t.enabled ? 'text-blue-600' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <h4 className="font-semibold text-gray-900">{t.trigger_name}</h4>
                        <p className="text-xs text-gray-500">
                          When {t.trigger_condition.metric}{' '}
                          {t.trigger_condition.operator.replace('_', ' ')}{' '}
                          {t.trigger_condition.threshold}
                        </p>
                      </div>
                      <StatusBadge status={t.enabled ? 'active' : 'disabled'} />
                    </div>
                    <button
                      onClick={() => testTrigger(t.trigger_id)}
                      className="px-3 py-1.5 text-xs text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
                    >
                      Test Fire
                    </button>
                  </div>
                  <div className="grid grid-cols-4 gap-4 mt-4 text-xs">
                    <div>
                      <span className="text-gray-400">Type</span>
                      <p className="font-medium capitalize">{t.trigger_type.replace('_', ' ')}</p>
                    </div>
                    <div>
                      <span className="text-gray-400">Cooldown</span>
                      <p className="font-medium">{t.cooldown_minutes}m</p>
                    </div>
                    <div>
                      <span className="text-gray-400">Last Fired</span>
                      <p className="font-medium">{timeAgo(t.last_fired_at)}</p>
                    </div>
                    <div>
                      <span className="text-gray-400">Max/Day</span>
                      <p className="font-medium">{t.max_fires_per_day}</p>
                    </div>
                  </div>
                  <div className="mt-3 text-xs text-gray-400 truncate">
                    Webhook: {t.webhook_url}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Add Connector Modal */}
      {showAddConnector && (
        <AddConnectorModal
          connectorTypes={connectorTypes}
          onClose={() => setShowAddConnector(false)}
          onCreate={createConnector}
        />
      )}

      {/* Add Trigger Modal */}
      {showAddTrigger && (
        <AddTriggerModal
          onClose={() => setShowAddTrigger(false)}
          onCreate={createTrigger}
        />
      )}
    </div>
  );
};


// ============================================================
// Add Connector Modal
// ============================================================

function AddConnectorModal({
  connectorTypes,
  onClose,
  onCreate,
}: {
  connectorTypes: Record<string, ConnectorType>;
  onClose: () => void;
  onCreate: (type: string, name: string, url: string) => void;
}) {
  const [type, setType] = useState('');
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold">Add Integration Connector</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Connector type selector */}
        <div className="mb-4">
          <label className="text-sm font-medium text-gray-700 block mb-2">Connector Type</label>
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(connectorTypes).map(([key, ct]) => (
              <button
                key={key}
                onClick={() => { setType(key); setName(ct.label); }}
                className={`p-3 rounded-lg border text-center text-sm transition-colors ${
                  type === key
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }`}
              >
                <div className="flex justify-center mb-1.5">
                  {CONNECTOR_ICONS[key] || <Database className="h-5 w-5" />}
                </div>
                {ct.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-4">
          <label className="text-sm font-medium text-gray-700 block mb-1">Connector Name</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="e.g. Production Salesforce"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {(type === 'n8n' || type === 'custom_webhook') && (
          <div className="mb-4">
            <label className="text-sm font-medium text-gray-700 block mb-1">Webhook URL</label>
            <input
              type="url"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://your-n8n.com/webhook/..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        )}

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
            Cancel
          </button>
          <button
            onClick={() => type && name && onCreate(type, name, url)}
            disabled={!type || !name}
            className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            Create Connector
          </button>
        </div>
      </div>
    </div>
  );
}


// ============================================================
// Add Trigger Modal
// ============================================================

function AddTriggerModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (name: string, type: string, url: string, threshold: number) => void;
}) {
  const [name, setName] = useState('');
  const [type, setType] = useState('health_drop');
  const [url, setUrl] = useState('');
  const [threshold, setThreshold] = useState(50);

  const triggerTypes = [
    { value: 'health_drop', label: 'Health Score Drop' },
    { value: 'health_critical', label: 'Health Critical (<50)' },
    { value: 'signal_detected', label: 'Signal Detected' },
    { value: 'renewal_approaching', label: 'Renewal Approaching' },
    { value: 'expansion_ready', label: 'Expansion Ready' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold">Add Playbook Trigger</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Trigger Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Critical Health Alert"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Trigger Type</label>
            <select
              value={type}
              onChange={e => setType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            >
              {triggerTypes.map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">
              Health Score Threshold
            </label>
            <input
              type="number"
              value={threshold}
              onChange={e => setThreshold(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">
              n8n Webhook URL
            </label>
            <input
              type="url"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://your-n8n.com/webhook/health-alert"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
            Cancel
          </button>
          <button
            onClick={() => name && url && onCreate(name, type, url, threshold)}
            disabled={!name || !url}
            className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            Create Trigger
          </button>
        </div>
      </div>
    </div>
  );
}


export default CSOpsIntegrationDashboard;
