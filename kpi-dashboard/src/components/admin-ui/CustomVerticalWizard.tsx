import React, { useState, useCallback, useRef } from 'react';
import {
  ChevronRight, ChevronLeft, CheckCircle2, Upload, Download, Plus, Trash2,
  AlertTriangle, Layers, BarChart3, FileSpreadsheet, Eye, ArrowRight, Save,
} from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface PillarDef {
  code: string;
  name: string;
  weight_l2: number;
}

interface KpiDef {
  code: string;
  name: string;
  pillar: string;
  weight_l1: number;
  unit: string;
  higher_is_better: boolean;
  target: number;
  frequency: string;
  healthy_min: number;
  healthy_max: number;
  risk_min: number;
  risk_max: number;
  critical_min: number;
  critical_max: number;
}

interface FieldMapping {
  source_column: string;
  target_kpi_code: string;
  transform: 'none' | 'invert' | 'scale_100' | 'days_to_hours';
}

interface MappingTemplate {
  source_system: string;  // e.g., "gainsight", "churnzero", "custom"
  mappings: FieldMapping[];
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  kpi_count: number;
  pillar_count: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const UNITS = ['percentage', 'days', 'hours', 'count', 'ratio', 'score', 'numeric'];
const FREQUENCIES = ['daily', 'weekly', 'monthly', 'quarterly'];

function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
}

function buildCatalogJson(pillars: PillarDef[], kpis: KpiDef[]) {
  const pillarMap: Record<string, any> = {};
  for (const p of pillars) {
    pillarMap[p.code] = { name: p.name, weight_l2: p.weight_l2, kpi_count: kpis.filter(k => k.pillar === p.code).length };
  }
  const kpiMap: Record<string, any> = {};
  for (const k of kpis) {
    kpiMap[k.code] = {
      name: k.name,
      pillar: k.pillar,
      weight_l1: k.weight_l1,
      unit: k.unit,
      higher_is_better: k.higher_is_better,
      frequency: k.frequency,
      target: { operator: k.higher_is_better ? '>' : '<', value: k.target },
      ranges: {
        healthy: { min: k.healthy_min, max: k.healthy_max, color: 'green' },
        risk: { min: k.risk_min, max: k.risk_max, color: 'yellow' },
        critical: { min: k.critical_min, max: k.critical_max, color: 'red' },
      },
    };
  }
  return { pillars: pillarMap, kpis: kpiMap };
}

// ─── Step Components ─────────────────────────────────────────────────────────

const StepIdentity: React.FC<{
  name: string; slug: string; description: string; scope: string;
  onName: (v: string) => void; onSlug: (v: string) => void;
  onDescription: (v: string) => void; onScope: (v: string) => void;
}> = ({ name, slug, description, scope, onName, onSlug, onDescription, onScope }) => (
  <div className="space-y-5">
    <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
      <Layers size={22} className="text-indigo-500" /> Vertical Identity
    </h2>
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">Vertical Name *</label>
      <input
        className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        placeholder="e.g., Healthcare Provider"
        value={name}
        onChange={e => { onName(e.target.value); onSlug(slugify(e.target.value)); }}
      />
    </div>
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">Slug (auto-generated, editable)</label>
      <input
        className="w-full border border-gray-300 rounded-lg px-3 py-2 font-mono text-sm bg-gray-50"
        value={slug}
        onChange={e => onSlug(e.target.value)}
      />
    </div>
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
      <textarea
        className="w-full border border-gray-300 rounded-lg px-3 py-2 h-20 resize-none"
        placeholder="Brief description of this vertical..."
        value={description}
        onChange={e => onDescription(e.target.value)}
      />
    </div>
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">Scope</label>
      <div className="flex gap-4">
        {['platform', 'customer'].map(s => (
          <button
            key={s}
            onClick={() => onScope(s)}
            className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
              scope === s
                ? 'bg-indigo-50 border-indigo-500 text-indigo-700'
                : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {s === 'platform' ? 'Platform-level (all customers)' : 'Customer-specific'}
          </button>
        ))}
      </div>
    </div>
  </div>
);

const StepPillars: React.FC<{
  pillars: PillarDef[];
  onChange: (pillars: PillarDef[]) => void;
}> = ({ pillars, onChange }) => {
  const addPillar = () => {
    if (pillars.length >= 7) return;
    const code = `P${pillars.length + 1}`;
    onChange([...pillars, { code, name: '', weight_l2: 0 }]);
  };
  const removePillar = (idx: number) => {
    if (pillars.length <= 3) return;
    onChange(pillars.filter((_, i) => i !== idx));
  };
  const update = (idx: number, field: keyof PillarDef, val: any) => {
    const next = [...pillars];
    (next[idx] as any)[field] = val;
    onChange(next);
  };
  const normalize = () => {
    const total = pillars.reduce((s, p) => s + p.weight_l2, 0);
    if (total > 0) onChange(pillars.map(p => ({ ...p, weight_l2: Math.round((p.weight_l2 / total) * 1000) / 1000 })));
  };
  const totalWeight = pillars.reduce((s, p) => s + p.weight_l2, 0);

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
        <BarChart3 size={22} className="text-indigo-500" /> Define Pillars
      </h2>
      <p className="text-sm text-gray-500">Define 3-7 pillars. Weights must sum to 1.0.</p>

      <div className="space-y-3">
        {pillars.map((p, i) => (
          <div key={i} className="flex items-center gap-3 bg-gray-50 rounded-lg p-3">
            <span className="text-sm font-mono font-bold text-indigo-600 w-8">{p.code}</span>
            <input
              className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm"
              placeholder="Pillar name..."
              value={p.name}
              onChange={e => update(i, 'name', e.target.value)}
            />
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="0.05"
                min="0"
                max="1"
                className="w-20 border border-gray-300 rounded px-2 py-1.5 text-sm text-center"
                value={p.weight_l2}
                onChange={e => update(i, 'weight_l2', parseFloat(e.target.value) || 0)}
                onBlur={normalize}
              />
              <span className="text-xs text-gray-400">wt</span>
            </div>
            <button onClick={() => removePillar(i)} className="text-red-400 hover:text-red-600" disabled={pillars.length <= 3}>
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <button onClick={addPillar} disabled={pillars.length >= 7}
          className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800 disabled:opacity-40">
          <Plus size={16} /> Add Pillar
        </button>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${Math.abs(totalWeight - 1) < 0.01 ? 'text-green-600' : 'text-amber-600'}`}>
            Total: {totalWeight.toFixed(3)}
          </span>
          {Math.abs(totalWeight - 1) > 0.01 && (
            <button onClick={normalize} className="text-xs text-indigo-600 underline">Auto-normalize</button>
          )}
        </div>
      </div>

      {/* Weight bar visualization */}
      <div className="h-6 rounded-full overflow-hidden flex bg-gray-200">
        {pillars.map((p, i) => (
          <div
            key={i}
            className="h-full flex items-center justify-center text-[10px] font-bold text-white"
            style={{
              width: `${(p.weight_l2 / Math.max(totalWeight, 1)) * 100}%`,
              backgroundColor: ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'][i % 7],
            }}
          >
            {p.code}
          </div>
        ))}
      </div>
    </div>
  );
};

const StepKpis: React.FC<{
  pillars: PillarDef[];
  kpis: KpiDef[];
  onChange: (kpis: KpiDef[]) => void;
  onCsvParsed: (kpis: KpiDef[], pillars: PillarDef[]) => void;
}> = ({ pillars, kpis, onChange, onCsvParsed }) => {
  const [mode, setMode] = useState<'form' | 'csv'>('form');
  const [csvStatus, setCsvStatus] = useState<string>('');
  const [activePillar, setActivePillar] = useState(pillars[0]?.code || 'P1');
  const fileRef = useRef<HTMLInputElement>(null);

  const addKpi = (pillarCode: string) => {
    const existing = kpis.filter(k => k.pillar === pillarCode);
    const code = `${pillarCode}-KPI${existing.length + 1}`;
    onChange([...kpis, {
      code, name: '', pillar: pillarCode, weight_l1: 0, unit: 'percentage',
      higher_is_better: true, target: 0, frequency: 'monthly',
      healthy_min: 0, healthy_max: 100, risk_min: 0, risk_max: 0, critical_min: 0, critical_max: 0,
    }]);
  };

  const removeKpi = (code: string) => onChange(kpis.filter(k => k.code !== code));

  const updateKpi = (code: string, field: keyof KpiDef, val: any) => {
    onChange(kpis.map(k => k.code === code ? { ...k, [field]: val } : k));
  };

  const handleCsvUpload = async (file: File) => {
    setCsvStatus('Parsing...');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const resp = await fetch('/api/admin-ui/verticals/parse-csv', {
        method: 'POST',
        body: formData,
      });
      const data = await resp.json();
      if (data.error) {
        setCsvStatus(`Error: ${data.error}`);
        return;
      }
      // Convert catalog to KpiDef[] and PillarDef[]
      const parsedPillars: PillarDef[] = Object.entries(data.catalog.pillars).map(([code, p]: [string, any]) => ({
        code, name: p.name, weight_l2: p.weight_l2,
      }));
      const parsedKpis: KpiDef[] = Object.entries(data.catalog.kpis).map(([code, k]: [string, any]) => ({
        code, name: k.name, pillar: k.pillar, weight_l1: k.weight_l1, unit: k.unit,
        higher_is_better: k.higher_is_better, target: k.target?.value || 0, frequency: k.frequency,
        healthy_min: k.ranges?.healthy?.min || 0, healthy_max: k.ranges?.healthy?.max || 100,
        risk_min: k.ranges?.risk?.min || 0, risk_max: k.ranges?.risk?.max || 0,
        critical_min: k.ranges?.critical?.min || 0, critical_max: k.ranges?.critical?.max || 0,
      }));
      onCsvParsed(parsedKpis, parsedPillars);
      setCsvStatus(`Parsed ${data.kpi_count} KPIs across ${data.pillar_count} pillars` +
        (data.parse_errors?.length ? ` (${data.parse_errors.length} warnings)` : ''));
      setMode('form'); // Switch to form so they can review
    } catch (e) {
      setCsvStatus(`Upload failed: ${e}`);
    }
  };

  const downloadTemplate = async () => {
    try {
      const resp = await fetch('/api/admin-ui/verticals/csv-template');
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'kpi_catalog_template.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert('Failed to download template');
    }
  };

  const pillarKpis = kpis.filter(k => k.pillar === activePillar);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
        <FileSpreadsheet size={22} className="text-indigo-500" /> Define KPIs
      </h2>

      {/* Mode toggle */}
      <div className="flex gap-2 border-b border-gray-200 pb-2">
        <button onClick={() => setMode('form')}
          className={`px-3 py-1.5 text-sm rounded-t-lg ${mode === 'form' ? 'bg-indigo-50 text-indigo-700 font-medium border border-b-0 border-indigo-200' : 'text-gray-500'}`}>
          Form Builder
        </button>
        <button onClick={() => setMode('csv')}
          className={`px-3 py-1.5 text-sm rounded-t-lg ${mode === 'csv' ? 'bg-indigo-50 text-indigo-700 font-medium border border-b-0 border-indigo-200' : 'text-gray-500'}`}>
          CSV Upload
        </button>
      </div>

      {mode === 'csv' ? (
        <div className="space-y-4">
          <div
            className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-indigo-400 transition-colors cursor-pointer"
            onClick={() => fileRef.current?.click()}
            onDrop={e => { e.preventDefault(); if (e.dataTransfer.files[0]) handleCsvUpload(e.dataTransfer.files[0]); }}
            onDragOver={e => e.preventDefault()}
          >
            <Upload size={32} className="mx-auto text-gray-400 mb-3" />
            <p className="text-sm text-gray-600">Drag & drop CSV file or click to browse</p>
            <p className="text-xs text-gray-400 mt-1">Columns: kpi_code, name, pillar, weight_l1, unit, higher_is_better, target, ranges...</p>
            <input ref={fileRef} type="file" accept=".csv" className="hidden"
              onChange={e => { if (e.target.files?.[0]) handleCsvUpload(e.target.files[0]); }} />
          </div>
          <div className="flex items-center justify-between">
            <button onClick={downloadTemplate} className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800">
              <Download size={16} /> Download Template CSV
            </button>
            {csvStatus && <span className="text-sm text-gray-600">{csvStatus}</span>}
          </div>
        </div>
      ) : (
        <div>
          {/* Pillar tabs */}
          <div className="flex gap-1 mb-4 overflow-x-auto">
            {pillars.map(p => (
              <button key={p.code} onClick={() => setActivePillar(p.code)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap ${
                  activePillar === p.code ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}>
                {p.code}: {p.name || '(unnamed)'} ({kpis.filter(k => k.pillar === p.code).length})
              </button>
            ))}
          </div>

          {/* KPI rows */}
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {pillarKpis.map(k => (
              <div key={k.code} className="bg-gray-50 rounded-lg p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-indigo-500 w-16">{k.code}</span>
                  <input className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm" placeholder="KPI name"
                    value={k.name} onChange={e => updateKpi(k.code, 'name', e.target.value)} />
                  <input type="number" step="0.05" min="0" max="1" className="w-16 border border-gray-300 rounded px-2 py-1 text-sm text-center"
                    value={k.weight_l1} onChange={e => updateKpi(k.code, 'weight_l1', parseFloat(e.target.value) || 0)} />
                  <select className="border border-gray-300 rounded px-1 py-1 text-xs" value={k.unit}
                    onChange={e => updateKpi(k.code, 'unit', e.target.value)}>
                    {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                  </select>
                  <button onClick={() => updateKpi(k.code, 'higher_is_better', !k.higher_is_better)}
                    className={`text-xs px-2 py-1 rounded ${k.higher_is_better ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                    {k.higher_is_better ? 'Higher=Better' : 'Lower=Better'}
                  </button>
                  <button onClick={() => removeKpi(k.code)} className="text-red-400 hover:text-red-600"><Trash2 size={14} /></button>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-gray-500 w-12">Target:</span>
                  <input type="number" className="w-16 border border-gray-300 rounded px-1 py-0.5 text-xs" value={k.target}
                    onChange={e => updateKpi(k.code, 'target', parseFloat(e.target.value) || 0)} />
                  <span className="text-green-600 ml-2">Healthy:</span>
                  <input type="number" className="w-14 border rounded px-1 py-0.5 text-xs" value={k.healthy_min}
                    onChange={e => updateKpi(k.code, 'healthy_min', parseFloat(e.target.value) || 0)} />
                  <span>-</span>
                  <input type="number" className="w-14 border rounded px-1 py-0.5 text-xs" value={k.healthy_max}
                    onChange={e => updateKpi(k.code, 'healthy_max', parseFloat(e.target.value) || 0)} />
                  <span className="text-amber-600 ml-2">Risk:</span>
                  <input type="number" className="w-14 border rounded px-1 py-0.5 text-xs" value={k.risk_min}
                    onChange={e => updateKpi(k.code, 'risk_min', parseFloat(e.target.value) || 0)} />
                  <span>-</span>
                  <input type="number" className="w-14 border rounded px-1 py-0.5 text-xs" value={k.risk_max}
                    onChange={e => updateKpi(k.code, 'risk_max', parseFloat(e.target.value) || 0)} />
                  <span className="text-red-600 ml-2">Critical:</span>
                  <input type="number" className="w-14 border rounded px-1 py-0.5 text-xs" value={k.critical_min}
                    onChange={e => updateKpi(k.code, 'critical_min', parseFloat(e.target.value) || 0)} />
                  <span>-</span>
                  <input type="number" className="w-14 border rounded px-1 py-0.5 text-xs" value={k.critical_max}
                    onChange={e => updateKpi(k.code, 'critical_max', parseFloat(e.target.value) || 0)} />
                </div>
              </div>
            ))}
          </div>

          <button onClick={() => addKpi(activePillar)}
            className="mt-2 flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800">
            <Plus size={16} /> Add KPI to {activePillar}
          </button>
        </div>
      )}

      <div className="text-sm text-gray-500 mt-2">
        Total: {kpis.length} KPIs across {pillars.length} pillars
      </div>
    </div>
  );
};

const TRANSFORMS = [
  { value: 'none', label: 'As-is (no transform)' },
  { value: 'invert', label: 'Invert (100 - value)' },
  { value: 'scale_100', label: 'Scale to 100 (× 100)' },
  { value: 'days_to_hours', label: 'Days → Hours (× 24)' },
];

const SOURCE_SYSTEMS = ['gainsight', 'churnzero', 'hubspot', 'salesforce', 'zendesk', 'custom'];

const StepFieldMapping: React.FC<{
  kpis: KpiDef[];
  mapping: MappingTemplate;
  onChange: (mapping: MappingTemplate) => void;
}> = ({ kpis, mapping, onChange }) => {
  const fileRef = useRef<HTMLInputElement>(null);
  const [sourceColumns, setSourceColumns] = useState<string[]>([]);
  const [sampleData, setSampleData] = useState<Record<string, string>[]>([]);

  const handleSourceCsvUpload = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const lines = text.split('\n').filter(l => l.trim());
      if (lines.length < 1) return;
      const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
      setSourceColumns(headers);

      // Parse first 3 data rows for preview
      const samples: Record<string, string>[] = [];
      for (let i = 1; i < Math.min(4, lines.length); i++) {
        const vals = lines[i].split(',').map(v => v.trim().replace(/^"|"$/g, ''));
        const row: Record<string, string> = {};
        headers.forEach((h, j) => { row[h] = vals[j] || ''; });
        samples.push(row);
      }
      setSampleData(samples);

      // Auto-map: fuzzy match source columns to KPI names
      const autoMappings: FieldMapping[] = [];
      for (const col of headers) {
        const colLower = col.toLowerCase().replace(/[^a-z0-9]/g, '');
        let bestMatch = '';
        let bestScore = 0;
        for (const k of kpis) {
          const kpiLower = k.name.toLowerCase().replace(/[^a-z0-9]/g, '');
          // Simple substring match score
          let score = 0;
          if (colLower.includes(kpiLower) || kpiLower.includes(colLower)) score = 3;
          else {
            const words = k.name.toLowerCase().split(/\s+/);
            score = words.filter(w => colLower.includes(w) && w.length > 2).length;
          }
          if (score > bestScore) { bestScore = score; bestMatch = k.code; }
        }
        if (bestScore > 0) {
          autoMappings.push({ source_column: col, target_kpi_code: bestMatch, transform: 'none' });
        }
      }
      onChange({ ...mapping, mappings: autoMappings });
    };
    reader.readAsText(file);
  };

  const addMapping = () => {
    onChange({
      ...mapping,
      mappings: [...mapping.mappings, { source_column: '', target_kpi_code: '', transform: 'none' }],
    });
  };

  const removeMapping = (idx: number) => {
    onChange({ ...mapping, mappings: mapping.mappings.filter((_, i) => i !== idx) });
  };

  const updateMapping = (idx: number, field: keyof FieldMapping, val: string) => {
    const next = [...mapping.mappings];
    (next[idx] as any)[field] = val;
    onChange({ ...mapping, mappings: next });
  };

  const unmappedKpis = kpis.filter(k => !mapping.mappings.some(m => m.target_kpi_code === k.code));

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
        <ArrowRight size={22} className="text-indigo-500" /> Field Mapping (Migration)
      </h2>
      <p className="text-sm text-gray-500">
        Map columns from your source system (Gainsight, ChurnZero, etc.) to the KPIs you defined.
        This mapping template is saved and reused for ongoing data syncs via n8n.
      </p>

      {/* Source system selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">Source System:</label>
        <select
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          value={mapping.source_system}
          onChange={e => onChange({ ...mapping, source_system: e.target.value })}
        >
          {SOURCE_SYSTEMS.map(s => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
      </div>

      {/* Upload source CSV for column detection */}
      <div
        className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-indigo-400 transition-colors cursor-pointer"
        onClick={() => fileRef.current?.click()}
        onDrop={e => { e.preventDefault(); if (e.dataTransfer.files[0]) handleSourceCsvUpload(e.dataTransfer.files[0]); }}
        onDragOver={e => e.preventDefault()}
      >
        <Upload size={24} className="mx-auto text-gray-400 mb-2" />
        <p className="text-sm text-gray-600">Upload a sample CSV from your source system to auto-detect columns</p>
        <p className="text-xs text-gray-400 mt-1">We'll fuzzy-match column names to your KPI definitions</p>
        <input ref={fileRef} type="file" accept=".csv" className="hidden"
          onChange={e => { if (e.target.files?.[0]) handleSourceCsvUpload(e.target.files[0]); }} />
      </div>

      {sourceColumns.length > 0 && (
        <div className="text-sm text-green-600 flex items-center gap-1">
          <CheckCircle2 size={14} />
          Detected {sourceColumns.length} columns, auto-mapped {mapping.mappings.length} fields
        </div>
      )}

      {/* Mapping table */}
      {mapping.mappings.length > 0 && (
        <div className="space-y-2">
          <div className="grid grid-cols-[1fr,auto,1fr,auto,auto] gap-2 text-xs font-medium text-gray-500 px-2">
            <span>Source Column</span>
            <span></span>
            <span>Target KPI</span>
            <span>Transform</span>
            <span></span>
          </div>
          {mapping.mappings.map((m, i) => (
            <div key={i} className="grid grid-cols-[1fr,auto,1fr,auto,auto] gap-2 items-center bg-gray-50 rounded-lg p-2">
              <select
                className="border border-gray-300 rounded px-2 py-1 text-sm"
                value={m.source_column}
                onChange={e => updateMapping(i, 'source_column', e.target.value)}
              >
                <option value="">-- Select source column --</option>
                {sourceColumns.map(c => <option key={c} value={c}>{c}</option>)}
                {!sourceColumns.length && <option value={m.source_column}>{m.source_column}</option>}
              </select>
              <ArrowRight size={14} className="text-gray-400" />
              <select
                className="border border-gray-300 rounded px-2 py-1 text-sm"
                value={m.target_kpi_code}
                onChange={e => updateMapping(i, 'target_kpi_code', e.target.value)}
              >
                <option value="">-- Select KPI --</option>
                {kpis.map(k => <option key={k.code} value={k.code}>{k.code}: {k.name}</option>)}
              </select>
              <select
                className="border border-gray-300 rounded px-1 py-1 text-xs"
                value={m.transform}
                onChange={e => updateMapping(i, 'transform', e.target.value)}
              >
                {TRANSFORMS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
              <button onClick={() => removeMapping(i)} className="text-red-400 hover:text-red-600">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <button onClick={addMapping}
            className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800">
            <Plus size={14} /> Add Mapping
          </button>
        </div>
      )}

      {/* Sample data preview */}
      {sampleData.length > 0 && mapping.mappings.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Preview (first 3 rows)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border border-gray-200 rounded">
              <thead className="bg-gray-50">
                <tr>
                  {mapping.mappings.filter(m => m.source_column && m.target_kpi_code).map(m => (
                    <th key={m.target_kpi_code} className="px-2 py-1 text-left">
                      <div className="text-gray-400">{m.source_column}</div>
                      <div className="text-indigo-600 font-bold">{m.target_kpi_code}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sampleData.map((row, i) => (
                  <tr key={i} className="border-t border-gray-100">
                    {mapping.mappings.filter(m => m.source_column && m.target_kpi_code).map(m => (
                      <td key={m.target_kpi_code} className="px-2 py-1">
                        {row[m.source_column] || '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Unmapped KPIs warning */}
      {unmappedKpis.length > 0 && mapping.mappings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm">
          <div className="flex items-center gap-2 text-amber-700 font-medium mb-1">
            <AlertTriangle size={14} /> {unmappedKpis.length} KPI{unmappedKpis.length > 1 ? 's' : ''} not mapped
          </div>
          <div className="text-amber-600 text-xs">
            {unmappedKpis.map(k => k.code).join(', ')} — these won't receive data from the source system
          </div>
        </div>
      )}

      <p className="text-xs text-gray-400 flex items-center gap-1">
        <Save size={12} /> This mapping template will be saved with the vertical for reuse in n8n data syncs.
      </p>
    </div>
  );
};

const StepReview: React.FC<{
  name: string; slug: string; description: string; scope: string;
  pillars: PillarDef[]; kpis: KpiDef[];
  validation: ValidationResult | null;
  onValidate: () => void;
  onCreate: () => void;
  creating: boolean;
}> = ({ name, slug, description, scope, pillars, kpis, validation, onValidate, onCreate, creating }) => (
  <div className="space-y-5">
    <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
      <Eye size={22} className="text-indigo-500" /> Review & Create
    </h2>

    {/* Summary cards */}
    <div className="grid grid-cols-4 gap-3">
      <div className="bg-indigo-50 rounded-lg p-3 text-center">
        <div className="text-2xl font-bold text-indigo-700">{pillars.length}</div>
        <div className="text-xs text-indigo-600">Pillars</div>
      </div>
      <div className="bg-green-50 rounded-lg p-3 text-center">
        <div className="text-2xl font-bold text-green-700">{kpis.length}</div>
        <div className="text-xs text-green-600">KPIs</div>
      </div>
      <div className="bg-cyan-50 rounded-lg p-3 text-center">
        <div className="text-2xl font-bold text-cyan-700">{scope === 'platform' ? 'Global' : 'Custom'}</div>
        <div className="text-xs text-cyan-600">Scope</div>
      </div>
      <div className="bg-purple-50 rounded-lg p-3 text-center">
        <div className="text-2xl font-bold text-purple-700 font-mono text-sm">{slug}</div>
        <div className="text-xs text-purple-600">Slug</div>
      </div>
    </div>

    {/* Pillar table */}
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Pillars</h3>
      <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Code</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Name</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">Weight</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">KPIs</th>
          </tr>
        </thead>
        <tbody>
          {pillars.map(p => (
            <tr key={p.code} className="border-t border-gray-100">
              <td className="px-3 py-2 font-mono text-indigo-600">{p.code}</td>
              <td className="px-3 py-2">{p.name}</td>
              <td className="px-3 py-2 text-right">{(p.weight_l2 * 100).toFixed(1)}%</td>
              <td className="px-3 py-2 text-right">{kpis.filter(k => k.pillar === p.code).length}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    {/* Validation */}
    <div className="space-y-2">
      <button onClick={onValidate} className="flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800 font-medium">
        <CheckCircle2 size={16} /> Run Validation
      </button>
      {validation && (
        <div className={`rounded-lg p-3 text-sm ${validation.valid ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
          {validation.valid ? (
            <div className="flex items-center gap-2 text-green-700">
              <CheckCircle2 size={16} /> All checks passed — ready to create
            </div>
          ) : (
            <div className="space-y-1">
              {validation.errors.map((e, i) => (
                <div key={i} className="flex items-center gap-2 text-red-700">
                  <AlertTriangle size={14} /> {e}
                </div>
              ))}
            </div>
          )}
          {(validation.warnings || []).map((w, i) => (
            <div key={i} className="flex items-center gap-2 text-amber-700 mt-1">
              <AlertTriangle size={14} /> {w}
            </div>
          ))}
        </div>
      )}
    </div>

    {/* Create button */}
    <button
      onClick={onCreate}
      disabled={creating || !validation?.valid}
      className="w-full py-3 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
    >
      {creating ? (
        <span>Creating...</span>
      ) : (
        <>
          <CheckCircle2 size={18} />
          Create Vertical: {name || slug}
        </>
      )}
    </button>
  </div>
);

// ─── Main Wizard ─────────────────────────────────────────────────────────────

const STEPS = ['Identity', 'Pillars', 'KPIs', 'Field Mapping', 'Review'];

const CustomVerticalWizard: React.FC = () => {
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [scope, setScope] = useState('platform');
  const [pillars, setPillars] = useState<PillarDef[]>([
    { code: 'P1', name: '', weight_l2: 0.2 },
    { code: 'P2', name: '', weight_l2: 0.2 },
    { code: 'P3', name: '', weight_l2: 0.2 },
    { code: 'P4', name: '', weight_l2: 0.2 },
    { code: 'P5', name: '', weight_l2: 0.2 },
  ]);
  const [kpis, setKpis] = useState<KpiDef[]>([]);
  const [fieldMapping, setFieldMapping] = useState<MappingTemplate>({ source_system: 'custom', mappings: [] });
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState(false);
  const [error, setError] = useState('');

  const canNext = useCallback(() => {
    if (step === 0) return name.trim().length >= 3 && slug.trim().length >= 3;
    if (step === 1) return pillars.length >= 3 && pillars.every(p => p.name.trim());
    if (step === 2) return kpis.length >= 3;
    if (step === 3) return true;  // Field mapping is optional (skip if not migrating)
    return true;
  }, [step, name, slug, pillars, kpis]);

  const handleValidate = async () => {
    const catalog = buildCatalogJson(pillars, kpis);
    try {
      const resp = await fetch('/api/admin-ui/verticals/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ catalog }),
      });
      const data = await resp.json();
      setValidation(data);
    } catch (e) {
      setValidation({ valid: false, errors: [`Validation request failed: ${e}`], warnings: [], kpi_count: 0, pillar_count: 0 });
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    setError('');
    const catalog = buildCatalogJson(pillars, kpis);
    // Include field mapping template if any mappings were defined
    const payload: any = {
      vertical_slug: slug,
      label: name,
      description,
      scope,
      catalog,
    };
    if (fieldMapping.mappings.length > 0) {
      payload.field_mapping = fieldMapping;
    }
    try {
      const resp = await fetch('/api/admin-ui/verticals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (resp.ok) {
        setCreated(true);
      } else {
        setError(data.error || 'Creation failed');
      }
    } catch (e) {
      setError(`Request failed: ${e}`);
    } finally {
      setCreating(false);
    }
  };

  const handleCsvParsed = (parsedKpis: KpiDef[], parsedPillars: PillarDef[]) => {
    setKpis(parsedKpis);
    if (parsedPillars.length >= 3) setPillars(parsedPillars);
  };

  if (created) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center">
        <div className="w-20 h-20 mx-auto bg-green-100 rounded-full flex items-center justify-center mb-4">
          <CheckCircle2 size={40} className="text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Vertical Created</h2>
        <p className="text-gray-600 mb-1"><strong>{name}</strong> ({slug})</p>
        <p className="text-gray-500 text-sm">{pillars.length} pillars, {kpis.length} KPIs — {scope === 'platform' ? 'available to all customers' : 'customer-specific'}</p>
        <p className="text-gray-500 text-sm mt-4">The vertical is now available for customer onboarding and scoring.</p>
        <a href="/admin/verticals" className="inline-block mt-6 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
          View All Verticals
        </a>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Onboard Custom Vertical</h1>

      {/* Stepper */}
      <div className="flex items-center mb-8">
        {STEPS.map((s, i) => (
          <React.Fragment key={s}>
            <button
              onClick={() => i <= step ? setStep(i) : undefined}
              className={`flex items-center gap-2 ${i <= step ? 'cursor-pointer' : 'cursor-default'}`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                i < step ? 'bg-green-500 text-white'
                : i === step ? 'bg-indigo-600 text-white'
                : 'bg-gray-200 text-gray-500'
              }`}>
                {i < step ? <CheckCircle2 size={16} /> : i + 1}
              </div>
              <span className={`text-sm ${i === step ? 'font-semibold text-gray-900' : 'text-gray-500'}`}>{s}</span>
            </button>
            {i < STEPS.length - 1 && <div className="flex-1 h-px bg-gray-300 mx-3" />}
          </React.Fragment>
        ))}
      </div>

      {/* Step content */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 min-h-[400px]">
        {step === 0 && <StepIdentity name={name} slug={slug} description={description} scope={scope}
          onName={setName} onSlug={setSlug} onDescription={setDescription} onScope={setScope} />}
        {step === 1 && <StepPillars pillars={pillars} onChange={setPillars} />}
        {step === 2 && <StepKpis pillars={pillars} kpis={kpis} onChange={setKpis} onCsvParsed={handleCsvParsed} />}
        {step === 3 && <StepFieldMapping kpis={kpis} mapping={fieldMapping} onChange={setFieldMapping} />}
        {step === 4 && <StepReview name={name} slug={slug} description={description} scope={scope}
          pillars={pillars} kpis={kpis} validation={validation}
          onValidate={handleValidate} onCreate={handleCreate} creating={creating} />}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between mt-4">
        <button onClick={() => setStep(s => s - 1)} disabled={step === 0}
          className="flex items-center gap-1 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 disabled:opacity-30">
          <ChevronLeft size={16} /> Back
        </button>
        {error && <span className="text-sm text-red-600">{error}</span>}
        {step < 4 && (
          <button onClick={() => { setStep(s => s + 1); setValidation(null); }} disabled={!canNext()}
            className="flex items-center gap-1 px-5 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50">
            {step === 3 ? 'Skip / Next' : 'Next'} <ChevronRight size={16} />
          </button>
        )}
      </div>
    </div>
  );
};

export default CustomVerticalWizard;
