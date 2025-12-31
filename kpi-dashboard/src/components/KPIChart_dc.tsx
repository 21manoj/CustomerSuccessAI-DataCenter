/**
 * Data Center KPI Chart Component
 * Displays KPI trends and visualizations for DC tenants
 */

import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, Activity } from 'lucide-react';

interface KPIChartProps {
  tenantId: number | null;
  kpiId?: string;
  timeRange?: '7d' | '30d' | '90d';
}

const KPIChart_dc: React.FC<KPIChartProps> = ({ tenantId, kpiId, timeRange = '30d' }) => {
  const [chartData, setChartData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (tenantId) {
      loadChartData();
    }
  }, [tenantId, kpiId, timeRange]);

  const loadChartData = async () => {
    if (!tenantId) return;
    
    setLoading(true);
    try {
      // Mock data for now - replace with actual API call
      const mockData = generateMockData(timeRange);
      setChartData(mockData);
    } catch (error) {
      console.error('Error loading chart data:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateMockData = (range: string) => {
    const days = range === '7d' ? 7 : range === '30d' ? 30 : 90;
    const data = [];
    const today = new Date();
    
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      data.push({
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        value: Math.random() * 100,
        target: 70
      });
    }
    
    return data;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (!tenantId) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-12">
          <Activity className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Select a tenant to view KPI trends</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">KPI Trend</h3>
          <p className="text-sm text-gray-500 mt-1">Last {timeRange}</p>
        </div>
        <TrendingUp className="h-6 w-6 text-blue-600" />
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="value" 
            stroke="#3b82f6" 
            strokeWidth={2}
            name="Actual"
          />
          <Line 
            type="monotone" 
            dataKey="target" 
            stroke="#ef4444" 
            strokeWidth={2}
            strokeDasharray="5 5"
            name="Target"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default KPIChart_dc;

