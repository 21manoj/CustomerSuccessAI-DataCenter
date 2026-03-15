/**
 * KPIGlossaryDrawer — Slide-out KPI glossary panel
 * ==================================================
 *
 * Shows all KPIs for the current tier with friendly names, descriptions,
 * and current health status. Triggered by (?) button or keyboard shortcut.
 *
 * Usage:
 *   <KPIGlossaryDrawer isOpen={open} onClose={() => setOpen(false)} />
 */

import React, { useState, useEffect } from 'react';
import { X, HelpCircle, Search } from 'lucide-react';
import { classify, classifyColor, classifyLabel } from '../../utils/healthThresholds';

interface KPIDefinition {
  kpi_code: string;
  kpi_name: string;
  pillar: string;
  pillar_name: string;
  description: string;
  weight_l1: number;
}

interface KPIGlossaryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const PILLAR_COLORS: Record<string, string> = {
  P1: 'bg-blue-100 text-blue-700',
  P2: 'bg-green-100 text-green-700',
  P3: 'bg-purple-100 text-purple-700',
  P4: 'bg-amber-100 text-amber-700',
  P5: 'bg-teal-100 text-teal-700',
};

const KPIGlossaryDrawer: React.FC<KPIGlossaryDrawerProps> = ({ isOpen, onClose }) => {
  const [kpis, setKpis] = useState<KPIDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (isOpen && kpis.length === 0) {
      fetchKPIs();
    }
  }, [isOpen]);

  // Keyboard shortcut: ? to toggle
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only trigger if not typing in an input
      if (e.key === '?' && !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName)) {
        e.preventDefault();
        if (isOpen) onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const fetchKPIs = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/dc2s/config/kpi-definitions', {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        // Handle both array and object response formats
        const kpiList = Array.isArray(data) ? data : (data.kpis || data.definitions || []);
        setKpis(kpiList);
      }
    } catch (err) {
      console.error('Error fetching KPI definitions:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredKPIs = kpis.filter(kpi => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      kpi.kpi_name.toLowerCase().includes(q) ||
      kpi.kpi_code.toLowerCase().includes(q) ||
      kpi.pillar_name?.toLowerCase().includes(q) ||
      kpi.description?.toLowerCase().includes(q)
    );
  });

  // Group by pillar
  const groupedKPIs = filteredKPIs.reduce<Record<string, KPIDefinition[]>>((acc, kpi) => {
    const pillar = kpi.pillar || 'Other';
    if (!acc[pillar]) acc[pillar] = [];
    acc[pillar].push(kpi);
    return acc;
  }, {});

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[420px] bg-white shadow-2xl z-50 flex flex-col border-l border-gray-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-2">
            <HelpCircle className="h-5 w-5 text-blue-500" />
            <h2 className="text-lg font-semibold text-gray-900">KPI Glossary</h2>
          </div>
          <div className="flex items-center space-x-2">
            <kbd className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">?</kbd>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="px-6 py-3 border-b border-gray-100">
          <div className="flex items-center bg-gray-50 rounded-lg px-3 py-2">
            <Search className="h-4 w-4 text-gray-400 mr-2" />
            <input
              type="text"
              placeholder="Search KPIs..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="flex-1 bg-transparent text-sm outline-none text-gray-700 placeholder-gray-400"
            />
          </div>
        </div>

        {/* KPI List */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="text-center py-8 text-gray-400">
              Loading KPI definitions...
            </div>
          ) : filteredKPIs.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              {kpis.length === 0 ? 'No KPI definitions available' : 'No matching KPIs'}
            </div>
          ) : (
            Object.entries(groupedKPIs).sort().map(([pillar, pillarKPIs]) => (
              <div key={pillar} className="mb-6">
                <div className="flex items-center space-x-2 mb-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${PILLAR_COLORS[pillar] || 'bg-gray-100 text-gray-700'}`}>
                    {pillar}
                  </span>
                  <span className="text-sm font-medium text-gray-600">
                    {pillarKPIs[0]?.pillar_name || pillar}
                  </span>
                </div>
                <div className="space-y-3">
                  {pillarKPIs.map(kpi => (
                    <div key={kpi.kpi_code} className="bg-gray-50 rounded-lg p-3 hover:bg-gray-100 transition-colors">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-900">{kpi.kpi_name}</span>
                        <span className="text-xs text-gray-400 font-mono">{kpi.kpi_code}</span>
                      </div>
                      {kpi.description && (
                        <p className="text-xs text-gray-500 leading-relaxed">{kpi.description}</p>
                      )}
                      {kpi.weight_l1 !== undefined && (
                        <div className="mt-1.5 flex items-center space-x-2">
                          <span className="text-[10px] text-gray-400">Weight: {(kpi.weight_l1 * 100).toFixed(0)}%</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 text-xs text-gray-400">
          {filteredKPIs.length} KPIs shown
        </div>
      </div>
    </>
  );
};

export default KPIGlossaryDrawer;
