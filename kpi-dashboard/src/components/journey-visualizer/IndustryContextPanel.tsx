/**
 * Industry Context Panel Component
 * ==================================
 * 
 * Shows industry context for the current week:
 * - Overall health status
 * - Pillar breakdown
 * - Recommendations
 * - Comparison to benchmarks
 */

import React from 'react';

interface WeekData {
  week_number: number;
  health_score: number;
  phase?: string;
  pillars?: Record<string, number>;
  data_quality?: number;
  coverage_pct?: number;
}

interface IndustryContextPanelProps {
  week: WeekData;
  isV2?: boolean;
}

const IndustryContextPanel: React.FC<IndustryContextPanelProps> = ({
  week,
  isV2 = false
}) => {
  const healthStatus = getHealthStatus(week.health_score);
  const recommendations = getRecommendations(week);
  
  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <h3 className="text-lg font-semibold text-gray-800">
          📊 Industry Context
        </h3>
      </div>
      
      <div className="p-6 space-y-4">
        {/* Overall Health Status */}
        <div>
          <div className="text-sm text-gray-600 mb-2">Overall Health</div>
          <div className="flex items-center gap-3">
            <div className={`
              w-16 h-16 rounded-full flex items-center justify-center text-2xl
              ${healthStatus.bgColor}
            `}>
              {healthStatus.icon}
            </div>
            <div>
              <div className={`text-xl font-bold ${healthStatus.textColor}`}>
                {healthStatus.label}
              </div>
              <div className="text-sm text-gray-500">
                Score: {week.health_score.toFixed(1)}/100
              </div>
            </div>
          </div>
          <div className="mt-2 text-sm text-gray-600">
            {healthStatus.description}
          </div>
        </div>
        
        {/* Pillar Breakdown */}
        {week.pillars && (
          <div className="border-t border-gray-200 pt-4">
            <div className="text-sm font-medium text-gray-700 mb-3">
              Pillar Scores
            </div>
            <div className="space-y-2">
              {Object.entries(week.pillars).map(([pillar, score]) => (
                <div key={pillar} className="flex items-center gap-2">
                  <div className="w-32 text-xs text-gray-600 truncate" title={formatPillarName(pillar)}>
                    {getPillarEmoji(pillar)} {formatPillarName(pillar)}
                  </div>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${getPillarColor(score)}`}
                      style={{ width: `${score}%` }}
                    />
                  </div>
                  <div className="w-10 text-xs font-medium text-right text-gray-700">
                    {score.toFixed(0)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Data Quality Indicator */}
        {week.data_quality !== undefined && (
          <div className="border-t border-gray-200 pt-4">
            <div className="text-sm font-medium text-gray-700 mb-2">
              Data Coverage
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${
                    (week.coverage_pct || 0) >= 40 ? 'bg-green-500' :
                    (week.coverage_pct || 0) >= 30 ? 'bg-blue-500' :
                    'bg-yellow-500'
                  }`}
                  style={{ width: `${week.coverage_pct || 0}%` }}
                />
              </div>
              <div className="text-sm font-medium text-gray-700">
                {(week.coverage_pct || 0).toFixed(0)}%
              </div>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {isV2 ? '✓ Industry-standard units tracked' : 'Normalized scores only'}
            </div>
          </div>
        )}
        
        {/* Recommendations */}
        {recommendations.length > 0 && (
          <div className="border-t border-gray-200 pt-4">
            <div className="text-sm font-medium text-gray-700 mb-2">
              💡 Recommendations
            </div>
            <ul className="space-y-2">
              {recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                  <span className="text-blue-600 mt-0.5">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Industry Benchmark */}
        <div className="border-t border-gray-200 pt-4">
          <div className="text-sm font-medium text-gray-700 mb-2">
            📈 Industry Benchmark
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="bg-gray-50 rounded p-3">
              <div className="text-gray-500 text-xs">Your Score</div>
              <div className="text-lg font-bold text-blue-600">
                {week.health_score.toFixed(0)}
              </div>
            </div>
            <div className="bg-gray-50 rounded p-3">
              <div className="text-gray-500 text-xs">Industry Avg</div>
              <div className="text-lg font-bold text-gray-700">
                72
              </div>
            </div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            {week.health_score > 72 
              ? '✓ Above industry average'
              : '⚠ Below industry average'
            }
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function getHealthStatus(healthScore: number) {
  if (healthScore >= 70) {
    return {
      label: 'Healthy',
      icon: '🟢',
      bgColor: 'bg-green-100',
      textColor: 'text-green-800',
      description: 'Customer is performing well. Continue current engagement strategy.'
    };
  } else if (healthScore >= 50) {
    return {
      label: 'At-Risk',
      icon: '⚠️',
      bgColor: 'bg-yellow-100',
      textColor: 'text-yellow-800',
      description: 'Customer needs attention. Proactive intervention recommended.'
    };
  } else {
    return {
      label: 'Critical',
      icon: '🚨',
      bgColor: 'bg-red-100',
      textColor: 'text-red-800',
      description: 'Immediate action required. Escalate to executive team.'
    };
  }
}

function getRecommendations(week: WeekData): string[] {
  const recommendations: string[] = [];
  
  // Health-based recommendations: critical (<50), at-risk (50-70), healthy (>=70)
  if (week.health_score < 50) {
    recommendations.push('Schedule immediate executive call to address critical issues');
    recommendations.push('Activate war room for incident resolution');
  } else if (week.health_score < 70) {
    recommendations.push('Increase touchpoint frequency with customer');
    recommendations.push('Review and address top pain points');
  }
  
  // Pillar-based recommendations
  if (week.pillars) {
    Object.entries(week.pillars).forEach(([pillar, score]) => {
      if (score < 50) {
        recommendations.push(getPillarRecommendation(pillar));
      }
    });
  }
  
  // Data quality recommendations
  if (week.coverage_pct && week.coverage_pct < 30) {
    recommendations.push('Improve data coverage by tracking more KPIs');
  }
  
  return recommendations.slice(0, 3); // Top 3 recommendations
}

function getPillarRecommendation(pillar: string): string {
  const recommendations: Record<string, string> = {
    'P1_deployment_velocity': 'Provide technical enablement and deployment support',
    'P2_operational_stability': 'Focus on incident reduction and proactive monitoring',
    'P3_ai_workload_performance': 'Optimize workload configurations and GPU utilization',
    'P4_channel_partner_health': 'Strengthen partner relationships and co-sell activities',
    'P5_expansion_readiness': 'Engage decision makers and showcase expansion ROI',
  };
  
  return recommendations[pillar] || 'Review and improve this pillar';
}

function formatPillarName(pillar: string): string {
  return pillar
    .replace(/^P\d+_/, '')
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function getPillarEmoji(pillar: string): string {
  const emojiMap: Record<string, string> = {
    'P1_deployment_velocity': '🚀',
    'P2_operational_stability': '🛡️',
    'P3_ai_workload_performance': '🤖',
    'P4_channel_partner_health': '🤝',
    'P5_expansion_readiness': '📈',
  };
  
  return emojiMap[pillar] || '📊';
}

function getPillarColor(score: number): string {
  if (score >= 70) return 'bg-green-500';
  if (score >= 50) return 'bg-yellow-500';
  return 'bg-red-500';
}

export default IndustryContextPanel;
