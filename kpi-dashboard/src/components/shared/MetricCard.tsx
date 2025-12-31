import React from 'react';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'stable';
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, change, trend, icon: Icon, color }) => (
  <div className="bg-white rounded-xl shadow-lg border-2 border-gray-200/60 p-6 hover:shadow-xl hover:border-blue-300/50 transition-all duration-300 hover:-translate-y-1">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide">{title}</p>
        <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
        <div className="flex items-center mt-3">
          {trend === 'up' && <ArrowUp className="h-4 w-4 text-green-500 mr-1" />}
          {trend === 'down' && <ArrowDown className="h-4 w-4 text-red-500 mr-1" />}
          {trend === 'stable' && <Minus className="h-4 w-4 text-gray-500 mr-1" />}
          <span className={`text-sm font-semibold ${
            trend === 'up' ? 'text-green-600' : 
            trend === 'down' ? 'text-red-600' : 'text-gray-600'
          }`}>
            {change}
          </span>
        </div>
      </div>
      <div className={`p-4 rounded-xl ${color} shadow-md`}>
        <Icon className="h-7 w-7 text-white" />
      </div>
    </div>
  </div>
);

export default MetricCard;
