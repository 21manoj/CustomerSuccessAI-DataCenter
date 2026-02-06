import React, { useState, useEffect } from 'react';
import {
  Scale,
  TrendingUp,
  AlertTriangle,
  RefreshCw,
  Settings,
  CheckCircle,
  Play,
  BarChart3
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis
} from 'recharts';

// ============================================================
// TYPES
// ============================================================

interface PillarWeight {
  name: string;
  weight: number;
  source: string;
}

interface WeightsData {
  weights: Record<string, PillarWeight>;
  accuracy: number;
  last_calibration: string | null;
  source: string;
}

interface HistoryPoint {
  date: string;
  accuracy: number;
  source: string;
}

interface EnsembleData {
  ensemble: {
    v3_weight: number;
    llm_weight: number;
    description: string;
  };
  v3_components: Record<string, number>;
  llm_components: Record<string, number>;
}

// ============================================================
// MAIN COMPONENT
// ============================================================

const WizardCWeights: React.FC = () => {
  const [weightsData, setWeightsData] = useState<WeightsData | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [ensemble, setEnsemble] = useState<EnsembleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [recalibrating, setRecalibrating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);

      // Fetch current weights
      const weightsRes = await fetch('/api/admin/wizard-c/weights/current');
      if (!weightsRes.ok) throw new Error('Failed to fetch weights');
      const weights = await weightsRes.json();
      setWeightsData(weights);

      // Fetch history
      const historyRes = await fetch('/api/admin/wizard-c/weights/history');
      if (!historyRes.ok) throw new Error('Failed to fetch history');
      const historyData = await historyRes.json();
      setHistory(historyData.history || []);

      // Fetch ensemble
      const ensembleRes = await fetch('/api/admin/wizard-c/ensemble');
      if (!ensembleRes.ok) throw new Error('Failed to fetch ensemble');
      const ensembleData = await ensembleRes.json();
      setEnsemble(ensembleData);

      setError(null);
    } catch (err) {
      console.error('Error fetching Wizard C data:', err);
      setError('Failed to load weight calibration data');
    } finally {
      setLoading(false);
    }
  };

  const handleRecalibrate = async () => {
    try {
      setRecalibrating(true);
      const response = await fetch('/api/admin/wizard-c/recalibrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) throw new Error('Failed to trigger recalibration');

      const result = await response.json();
      alert(`Recalibration ${result.status}! Task ID: ${result.task_id}\n\n${result.message}`);
      
      // Refresh data after a delay
      setTimeout(fetchData, 2000);
    } catch (err) {
      console.error('Error triggering recalibration:', err);
      alert('Failed to trigger recalibration. Please try again.');
    } finally {
      setRecalibrating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-700 mb-4">{error}</p>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  // Prepare radar chart data
  const radarData = weightsData ? Object.entries(weightsData.weights).map(([key, pillar]) => ({
    pillar: key,
    name: pillar.name,
    weight: pillar.weight * 100,
    fullMark: 100
  })) : [];

  // Accuracy Over Time: backend may return accuracy in 0–1 or 0–100; chart uses 0–100
  const toPct = (v: number) => (v != null && v <= 1 ? v * 100 : v ?? 0);
  const chartHistory = (history?.length
    ? history.map((p) => ({ ...p, accuracy: toPct(typeof p.accuracy === 'number' ? p.accuracy : 0) }))
    : weightsData && typeof weightsData.accuracy === 'number' && weightsData.accuracy > 0
      ? [{ date: new Date().toISOString().slice(0, 10), accuracy: toPct(weightsData.accuracy), source: weightsData.source || 'current' }]
      : []
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Weight Calibration</h2>
          <p className="text-sm text-gray-500">
            L2 pillar weights and model accuracy from Wizard C
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center space-x-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleRecalibrate}
            disabled={recalibrating}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 flex items-center space-x-2 disabled:opacity-50"
          >
            {recalibrating ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            <span>{recalibrating ? 'Running...' : 'Recalibrate Weights'}</span>
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
            <span className={`text-xs px-2 py-1 rounded-full ${
              weightsData?.source === 'learned' 
                ? 'bg-green-100 text-green-800' 
                : 'bg-yellow-100 text-yellow-800'
            }`}>
              {weightsData?.source === 'learned' ? 'Optimized' : 'Bootstrap'}
            </span>
          </div>
          <h3 className="text-3xl font-bold text-gray-900 mb-1">
            {weightsData && typeof weightsData.accuracy === 'number' && weightsData.accuracy > 0
              ? `${(weightsData.accuracy * 100).toFixed(0)}%`
              : 'N/A'}
          </h3>
          <p className="text-sm text-gray-500">Model Accuracy (bootstrap ~70% until Wizard C runs)</p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Scale className="w-6 h-6 text-blue-600" />
            </div>
          </div>
          <h3 className="text-3xl font-bold text-gray-900 mb-1">5</h3>
          <p className="text-sm text-gray-500">Pillars Configured</p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <BarChart3 className="w-6 h-6 text-purple-600" />
            </div>
          </div>
          <h3 className="text-lg font-bold text-gray-900 mb-1">
            {weightsData?.last_calibration 
              ? new Date(weightsData.last_calibration).toLocaleDateString()
              : 'Never'}
          </h3>
          <p className="text-sm text-gray-500">Last Calibration</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Pillar Weight Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="pillar" />
              <PolarRadiusAxis angle={30} domain={[0, 30]} />
              <Radar
                name="Weight %"
                dataKey="weight"
                stroke="#8b5cf6"
                fill="#8b5cf6"
                fillOpacity={0.5}
              />
              <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Accuracy History */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Accuracy Over Time</h3>
          {chartHistory.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                <Tooltip formatter={(value: number) => `${Number(value).toFixed(1)}%`} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={{ fill: '#8b5cf6' }}
                  name="Accuracy"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500 text-sm">
              No accuracy history yet. Run recalibration or load weights to see trends.
            </div>
          )}
        </div>
      </div>

      {/* Weight Details Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Pillar Weights (L2)</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Pillar</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Name</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Weight</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Source</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Impact</th>
              </tr>
            </thead>
            <tbody>
              {weightsData && Object.entries(weightsData.weights).map(([key, pillar]) => (
                <tr key={key} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4">
                    <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">{key}</span>
                  </td>
                  <td className="py-3 px-4 font-medium text-gray-900">{pillar.name}</td>
                  <td className="py-3 px-4">
                    <div className="flex items-center space-x-2">
                      <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-purple-600 rounded-full"
                          style={{ width: `${pillar.weight * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">{(pillar.weight * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      pillar.source === 'learned'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {pillar.source}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      pillar.weight > 0.23
                        ? 'bg-green-100 text-green-800'
                        : pillar.weight > 0.18
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {pillar.weight > 0.23 ? 'High' : pillar.weight > 0.18 ? 'Medium' : 'Low'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ensemble Weights */}
      {ensemble && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Ensemble Configuration</h3>
          <p className="text-sm text-gray-500 mb-4">{ensemble.ensemble.description}</p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* V3 Quantitative */}
            <div className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-900">V3 Quantitative</h4>
                <span className="text-lg font-bold text-blue-600">
                  {(ensemble.ensemble.v3_weight * 100).toFixed(0)}%
                </span>
              </div>
              <div className="space-y-2">
                {Object.entries(ensemble.v3_components).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">{key.replace(/_/g, ' ')}</span>
                    <span className="font-medium">{(value * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* LLM Qualitative */}
            <div className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-900">LLM Qualitative</h4>
                <span className="text-lg font-bold text-purple-600">
                  {(ensemble.ensemble.llm_weight * 100).toFixed(0)}%
                </span>
              </div>
              <div className="space-y-2">
                {Object.entries(ensemble.llm_components).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">{key.replace(/_/g, ' ')}</span>
                    <span className="font-medium">{(value * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recommendations */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="font-semibold text-blue-900 mb-3 flex items-center space-x-2">
          <Settings className="w-5 h-5" />
          <span>Recalibration Recommendations</span>
        </h3>
        <ul className="space-y-2 text-sm text-blue-800">
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Run monthly recalibration to adapt to changing customer patterns</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>After major product launches or market shifts, recalibrate immediately</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Need 20+ prediction samples for reliable weight learning</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Compare predicted vs actual outcomes to validate accuracy</span>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default WizardCWeights;
