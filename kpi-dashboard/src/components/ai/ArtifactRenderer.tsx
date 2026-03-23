/**
 * ArtifactRenderer — Rich rendering for Ask AI v2 artifacts
 * ===========================================================
 * Renders structured artifacts returned by the Claude tool_use backend:
 *  - mermaid: Context graph diagrams via mermaid.js (lazy-loaded)
 *  - table: Sortable data tables matching dashboard dark theme
 *  - metric_card: Revenue/ROI metric cards matching CRO dashboard style
 *  - chart: Bar/line charts via Recharts
 *
 * Behind feature flag: FEATURE_ASK_AI_V2
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  ChevronDown, ChevronUp, Maximize2, X, Copy, Check,
  GitBranch, Table as TableIcon, BarChart3, Gauge,
  ArrowUpRight, ArrowDownRight, Minus,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid,
} from 'recharts';

// ── Types ────────────────────────────────────────────────────────────────────

export interface Artifact {
  type: 'mermaid' | 'table' | 'metric_card' | 'chart' | 'kpi_breakdown';
  title: string;
  content?: string;         // mermaid diagram code
  columns?: string[];       // table headers
  rows?: any[][];            // table data
  value?: string;            // metric_card primary value
  change?: string;           // metric_card delta
  metrics?: { label: string; value: string; color?: string }[];
  chart_type?: 'line' | 'bar' | 'area';
  data?: any[];              // Recharts-compatible data
}

// ── Artifact Type Icons ──────────────────────────────────────────────────────

const ARTIFACT_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  mermaid: GitBranch,
  table: TableIcon,
  metric_card: Gauge,
  chart: BarChart3,
  kpi_breakdown: BarChart3,
};

// ── Main Renderer ────────────────────────────────────────────────────────────

export const ArtifactRenderer: React.FC<{ artifact: Artifact }> = ({ artifact }) => {
  const [expanded, setExpanded] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const Icon = ARTIFACT_ICONS[artifact.type] || BarChart3;

  const content = (
    <div className={`${fullscreen ? 'p-6' : ''}`}>
      {artifact.type === 'mermaid' && <MermaidDiagram code={artifact.content || ''} />}
      {artifact.type === 'table' && <DataTable columns={artifact.columns || []} rows={artifact.rows || []} />}
      {artifact.type === 'metric_card' && <MetricCards metrics={artifact.metrics || []} />}
      {(artifact.type === 'chart' || artifact.type === 'kpi_breakdown') && (
        <ChartRenderer chartType={artifact.chart_type || 'bar'} data={artifact.data || []} />
      )}
    </div>
  );

  // Fullscreen modal
  if (fullscreen) {
    return (
      <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-8">
        <div className="bg-[#0d1117] border border-gray-700/50 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-auto">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700/50">
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4 text-cyan-400" />
              <span className="text-sm font-medium text-white">{artifact.title}</span>
            </div>
            <button onClick={() => setFullscreen(false)} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg">
              <X className="h-4 w-4" />
            </button>
          </div>
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="mt-2 bg-[#161b22] border border-gray-700/40 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#1a1f2e]/50 border-b border-gray-700/30">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-[10px] text-gray-400 hover:text-white transition-colors"
        >
          <Icon className="h-3 w-3 text-cyan-400/70" />
          <span className="font-medium">{artifact.title}</span>
          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </button>
        <button
          onClick={() => setFullscreen(true)}
          className="p-1 text-gray-500 hover:text-white hover:bg-white/10 rounded transition-colors"
          title="Expand"
        >
          <Maximize2 className="h-3 w-3" />
        </button>
      </div>
      {/* Content */}
      {expanded && <div className="p-3">{content}</div>}
    </div>
  );
};

// ── Mermaid Diagram ──────────────────────────────────────────────────────────

const MermaidDiagram: React.FC<{ code: string }> = ({ code }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    // Lazy-load mermaid
    import('mermaid').then(({ default: mermaid }) => {
      if (cancelled) return;
      mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        themeVariables: {
          darkMode: true,
          background: '#161b22',
          primaryColor: '#1f6feb',
          primaryTextColor: '#e6edf3',
          lineColor: '#484f58',
        },
        flowchart: { curve: 'basis', padding: 15, nodeSpacing: 30, rankSpacing: 40 },
        securityLevel: 'strict',
      });

      const id = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
      mermaid.render(id, code).then(({ svg: renderedSvg }) => {
        if (!cancelled) {
          setSvg(renderedSvg);
          setLoading(false);
        }
      }).catch(err => {
        if (!cancelled) {
          setError(`Diagram render error: ${err.message || err}`);
          setLoading(false);
        }
      });
    }).catch(err => {
      if (!cancelled) {
        setError(`Failed to load diagram library: ${err.message}`);
        setLoading(false);
      }
    });

    return () => { cancelled = true; };
  }, [code]);

  const copySource = useCallback(() => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [code]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-pulse text-xs text-gray-500">Rendering diagram...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-xs text-red-400 bg-red-900/10 rounded p-2">
        {error}
        <pre className="mt-2 text-[10px] text-gray-500 overflow-x-auto">{code.slice(0, 200)}...</pre>
      </div>
    );
  }

  return (
    <div className="relative">
      <div
        ref={containerRef}
        className="overflow-auto [&_svg]:mx-auto [&_svg]:min-h-[200px]"
        dangerouslySetInnerHTML={{ __html: svg }}
      />
      <button
        onClick={copySource}
        className="absolute top-1 right-1 p-1 text-gray-500 hover:text-white bg-[#161b22]/80 rounded transition-colors"
        title="Copy Mermaid source"
      >
        {copied ? <Check className="h-3 w-3 text-green-400" /> : <Copy className="h-3 w-3" />}
      </button>
    </div>
  );
};

// ── Data Table ───────────────────────────────────────────────────────────────

const DataTable: React.FC<{ columns: string[]; rows: any[][] }> = ({ columns, rows }) => {
  const [sortCol, setSortCol] = useState<number | null>(null);
  const [sortAsc, setSortAsc] = useState(true);

  const sortedRows = React.useMemo(() => {
    if (sortCol === null) return rows;
    return [...rows].sort((a, b) => {
      const va = a[sortCol];
      const vb = b[sortCol];
      // Try numeric sort
      const na = typeof va === 'number' ? va : parseFloat(String(va).replace(/[$,%]/g, ''));
      const nb = typeof vb === 'number' ? vb : parseFloat(String(vb).replace(/[$,%]/g, ''));
      if (!isNaN(na) && !isNaN(nb)) {
        return sortAsc ? na - nb : nb - na;
      }
      // String sort
      const sa = String(va || '');
      const sb = String(vb || '');
      return sortAsc ? sa.localeCompare(sb) : sb.localeCompare(sa);
    });
  }, [rows, sortCol, sortAsc]);

  const handleSort = (idx: number) => {
    if (sortCol === idx) {
      setSortAsc(!sortAsc);
    } else {
      setSortCol(idx);
      setSortAsc(true);
    }
  };

  if (rows.length === 0) {
    return <div className="text-xs text-gray-500 text-center py-3">No data available</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[10px]">
        <thead>
          <tr className="border-b border-gray-700/50">
            {columns.map((col, i) => (
              <th
                key={i}
                onClick={() => handleSort(i)}
                className="text-left px-2 py-1.5 text-gray-400 font-medium cursor-pointer hover:text-white transition-colors select-none"
              >
                {col}
                {sortCol === i && (
                  <span className="ml-1 text-cyan-400">{sortAsc ? '↑' : '↓'}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row, ri) => (
            <tr key={ri} className="border-b border-gray-800/30 hover:bg-[#1a1f2e]/50 transition-colors">
              {row.map((cell, ci) => (
                <td key={ci} className="px-2 py-1.5 text-gray-300">
                  {formatCell(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

function formatCell(value: any): React.ReactNode {
  if (value === null || value === undefined || value === '') return <span className="text-gray-600">—</span>;

  // Health score coloring
  if (typeof value === 'number' && value >= 0 && value <= 100) {
    const color = value >= 70 ? 'text-green-400' : value >= 50 ? 'text-amber-400' : 'text-red-400';
    return <span className={`font-medium ${color}`}>{Math.round(value)}</span>;
  }

  // Status badges
  const str = String(value);
  if (['critical', 'at_risk', 'healthy'].includes(str.toLowerCase())) {
    const colors: Record<string, string> = {
      critical: 'bg-red-500/20 text-red-400',
      at_risk: 'bg-amber-500/20 text-amber-400',
      healthy: 'bg-green-500/20 text-green-400',
    };
    return (
      <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${colors[str.toLowerCase()] || ''}`}>
        {str}
      </span>
    );
  }

  return str;
}

// ── Metric Cards ─────────────────────────────────────────────────────────────

const MetricCards: React.FC<{
  metrics: { label: string; value: string; color?: string }[];
}> = ({ metrics }) => {
  const colorMap: Record<string, string> = {
    red: 'text-red-400 border-red-500/30 bg-red-500/5',
    green: 'text-green-400 border-green-500/30 bg-green-500/5',
    blue: 'text-blue-400 border-blue-500/30 bg-blue-500/5',
    cyan: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/5',
    amber: 'text-amber-400 border-amber-500/30 bg-amber-500/5',
  };

  return (
    <div className="grid grid-cols-2 gap-2" style={{ gridTemplateColumns: metrics.length === 3 ? 'repeat(3, 1fr)' : undefined }}>
      {metrics.map((m, i) => {
        const cls = colorMap[m.color || 'blue'] || colorMap.blue;
        return (
          <div key={i} className={`rounded-lg border px-3 py-2 ${cls}`}>
            <div className="text-[9px] text-gray-400 mb-0.5">{m.label}</div>
            <div className="text-sm font-bold">{m.value}</div>
          </div>
        );
      })}
    </div>
  );
};

// ── Chart Renderer ───────────────────────────────────────────────────────────

const ChartRenderer: React.FC<{
  chartType: 'line' | 'bar' | 'area';
  data: any[];
}> = ({ chartType, data }) => {
  if (!data || data.length === 0) {
    return <div className="text-xs text-gray-500 text-center py-3">No chart data</div>;
  }

  // Detect the value key (first numeric field that isn't 'name')
  const valueKey = Object.keys(data[0] || {}).find(k => k !== 'name' && typeof data[0][k] === 'number') || 'score';

  const chartProps = {
    data,
    margin: { top: 5, right: 10, bottom: 5, left: 0 },
  };

  const tooltipStyle = {
    contentStyle: { backgroundColor: '#1a1f2e', border: '1px solid #374151', borderRadius: '8px', fontSize: '11px' },
    labelStyle: { color: '#9ca3af' },
  };

  return (
    <div className="h-[160px]">
      <ResponsiveContainer width="100%" height="100%">
        {chartType === 'line' ? (
          <LineChart {...chartProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 10 }} />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
            <Tooltip {...tooltipStyle} />
            <Line type="monotone" dataKey={valueKey} stroke="#06b6d4" strokeWidth={2} dot={{ fill: '#06b6d4', r: 3 }} />
          </LineChart>
        ) : (
          <BarChart {...chartProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 10 }} />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
            <Tooltip {...tooltipStyle} />
            <Bar dataKey={valueKey} fill="#06b6d4" radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
};

export default ArtifactRenderer;
