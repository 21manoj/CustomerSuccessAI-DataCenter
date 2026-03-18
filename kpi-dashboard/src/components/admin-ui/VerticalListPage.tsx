import React, { useEffect, useState, useCallback } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Save,
  FileText,
} from 'lucide-react';
import {
  fetchVerticals,
  fetchVerticalTemplates,
  fetchTemplate,
  updateTemplate,
  type VerticalInfo,
  type VerticalTemplate,
} from '../../api/adminApi';

// ---------------------------------------------------------------------------
// Vertical Accordion Item
// ---------------------------------------------------------------------------

interface VerticalAccordionProps {
  info: VerticalInfo;
}

const VerticalAccordion: React.FC<VerticalAccordionProps> = ({ info }) => {
  const [expanded, setExpanded] = useState(false);
  const [templates, setTemplates] = useState<VerticalTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selected config for editing
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [editJson, setEditJson] = useState('');
  const [currentVersion, setCurrentVersion] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTemplates(await fetchVerticalTemplates(info.vertical));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load templates');
    } finally {
      setLoading(false);
    }
  }, [info.vertical]);

  const handleToggle = () => {
    if (!expanded && templates.length === 0) {
      loadTemplates();
    }
    setExpanded((prev) => !prev);
  };

  const handleSelectConfig = async (configType: string) => {
    setSelectedType(configType);
    setSaveMsg(null);
    try {
      const tmpl = await fetchTemplate(info.vertical, configType);
      setEditJson(JSON.stringify(tmpl.config, null, 2));
      setCurrentVersion(tmpl.version);
    } catch {
      setEditJson('{}');
      setCurrentVersion(0);
    }
  };

  const handleSave = async () => {
    if (!selectedType) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const parsed = JSON.parse(editJson);
      await updateTemplate(info.vertical, selectedType, parsed);
      setSaveMsg(`Saved (version ${currentVersion + 1})`);
      setCurrentVersion((v) => v + 1);
      loadTemplates();
    } catch (err: unknown) {
      setSaveMsg(err instanceof Error ? err.message : 'Invalid JSON or save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Accordion header */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {expanded ? (
            <ChevronDown size={18} className="text-gray-400" />
          ) : (
            <ChevronRight size={18} className="text-gray-400" />
          )}
          <span className="text-base font-semibold text-gray-900">{info.vertical}</span>
          <span className="text-xs text-gray-400 font-normal">
            {info.template_count} config type{info.template_count !== 1 ? 's' : ''}
          </span>
        </div>
        <div className="flex flex-wrap gap-1">
          {info.config_types.slice(0, 5).map((ct) => (
            <span
              key={ct}
              className="inline-flex px-2 py-0.5 text-xs bg-indigo-50 text-indigo-600 rounded-full"
            >
              {ct}
            </span>
          ))}
          {info.config_types.length > 5 && (
            <span className="text-xs text-gray-400">+{info.config_types.length - 5} more</span>
          )}
        </div>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div className="border-t border-gray-100">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
              <span className="ml-2 text-sm text-gray-500">Loading templates...</span>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-8 gap-2 text-sm text-red-600">
              <AlertTriangle size={16} />
              {error}
              <button onClick={loadTemplates} className="text-indigo-600 hover:text-indigo-700 font-medium ml-2">
                Retry
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 divide-y lg:divide-y-0 lg:divide-x divide-gray-100">
              {/* Config type list */}
              <div className="p-4">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  Config Types
                </h4>
                <ul className="space-y-1">
                  {info.config_types.map((ct) => (
                    <li key={ct}>
                      <button
                        onClick={() => handleSelectConfig(ct)}
                        className={`w-full flex items-center gap-2 text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                          selectedType === ct
                            ? 'bg-indigo-50 text-indigo-700'
                            : 'text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        <FileText size={14} className="flex-shrink-0 text-gray-400" />
                        {ct}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Editor */}
              <div className="lg:col-span-2 p-4">
                {selectedType ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-semibold text-gray-900">{selectedType}</h4>
                        <p className="text-xs text-gray-400">Version {currentVersion}</p>
                      </div>
                      <button
                        onClick={handleSave}
                        disabled={saving}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {saving ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <Save size={14} />
                        )}
                        Save
                      </button>
                    </div>
                    <textarea
                      value={editJson}
                      onChange={(e) => setEditJson(e.target.value)}
                      rows={18}
                      spellCheck={false}
                      className="w-full font-mono text-xs p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none resize-y"
                    />
                    {saveMsg && (
                      <p className="text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded-lg">
                        {saveMsg}
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full text-sm text-gray-400 py-12">
                    Select a config type to view and edit.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const VerticalListPage: React.FC = () => {
  const [verticals, setVerticals] = useState<VerticalInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setVerticals(await fetchVerticals());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load verticals');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        <span className="ml-3 text-gray-500">Loading verticals...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertTriangle className="w-10 h-10 text-red-400 mb-3" />
        <p className="text-red-600 font-medium mb-4">{error}</p>
        <button
          onClick={load}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
        >
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Vertical Templates</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Manage default configuration templates per vertical
        </p>
      </div>

      {verticals.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center text-gray-400 text-sm">
          No verticals configured.
        </div>
      ) : (
        <div className="space-y-3">
          {verticals.map((v) => (
            <VerticalAccordion key={v.vertical} info={v} />
          ))}
        </div>
      )}
    </div>
  );
};

export default VerticalListPage;
