/**
 * Journey Visualizer V2 - Main Component
 * ========================================
 * 
 * UPDATED to support unified KPI system:
 * - Displays raw values with units (8,500 hours, not just 85)
 * - Handles sparse KPIs (only shows tracked KPIs)
 * - Shows data quality indicators
 * - Backwards compatible with V1 data
 * 
 * NEW FEATURES:
 * - Industry context panels
 * - Enhanced tooltips
 * - Data quality badges
 * - Missing KPI indicators
 * - Coverage trends
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiCall } from '../../utils/api';

// Import new V2 components
import KPICard from './KPICard';
import DataQualityBadge from './DataQualityBadge';
import IndustryContextPanel from './IndustryContextPanel';
import WeekTimeline from './WeekTimeline';
import CoverageTrends from './CoverageTrends';

// Types
interface RawKPI {
  value: number;
  unit: string;
}

interface WeekData {
  week_number: number;
  date: string;
  health_score: number;
  phase: string;
  
  // V2: Support both formats
  kpis?: Record<string, number>;           // V1 format (normalized only)
  raw_kpis?: Record<string, RawKPI>;       // V2 format (raw values)
  normalized_kpis?: Record<string, number>; // V2 format (normalized)
  
  // V2: Data quality
  data_quality?: number;
  coverage_pct?: number;
  missing_kpis?: string[];
  available_kpis?: string[];
  
  // Pillars
  pillars?: Record<string, number>;
  
  // Events
  events?: Array<{
    event_type: string;
    description: string;
    sentiment: string;
  }>;
}

interface JourneyData {
  account_id: string;
  account_name: string;
  weekly_data: WeekData[];
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const JourneyVisualizerV2: React.FC = () => {
  const { accountId } = useParams<{ accountId: string }>();
  const navigate = useNavigate();
  
  // State
  const [journeyData, setJourneyData] = useState<JourneyData | null>(null);
  const [selectedWeek, setSelectedWeek] = useState<number>(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Settings
  const [showIndustryContext, setShowIndustryContext] = useState(true);
  const [showMissingKPIs, setShowMissingKPIs] = useState(false);
  const [groupByPillar, setGroupByPillar] = useState(true);
  
  // Load journey data
  useEffect(() => {
    loadJourneyData();
  }, [accountId]);
  
  const loadJourneyData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log(`[Journey] Loading data for account: ${accountId}`);
      
      // Use the API utility to ensure correct base URL and credentials
      const response = await apiCall(`/api/journey/${accountId}`, {
        credentials: 'include' // Include cookies for authentication
      });
      
      console.log(`[Journey] Response status: ${response.status} ${response.statusText}`);
      console.log(`[Journey] Response headers:`, Object.fromEntries(response.headers.entries()));
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[Journey] Error response body:`, errorText);
        
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { error: errorText || `HTTP ${response.status}: Failed to load journey data` };
        }
        
        throw new Error(errorData.error || errorData.message || `HTTP ${response.status}: Failed to load journey data`);
      }
      
      const data = await response.json();
      console.log(`[Journey] Successfully loaded data:`, { 
        account_id: data.account_id, 
        total_weeks: data.total_weeks,
        weekly_data_count: data.weekly_data?.length 
      });
      setJourneyData(data);
      
    } catch (err: any) {
      console.error('[Journey] Error loading journey data:', err);
      console.error('[Journey] Error details:', {
        message: err.message,
        stack: err.stack,
        name: err.name
      });
      setError(err.message || 'An error occurred while loading journey data');
    } finally {
      setLoading(false);
    }
  };
  
  // Get current week data
  const currentWeek = journeyData?.weekly_data?.[selectedWeek - 1];
  
  // Determine if this is V1 or V2 data
  const isV2Data = currentWeek?.raw_kpis !== undefined;
  
  // Get KPIs to display (prefer normalized_kpis, fallback to kpis)
  const kpisToDisplay = currentWeek?.normalized_kpis || currentWeek?.kpis || {};
  
  // Get raw KPIs (V2 only)
  const rawKPIs = currentWeek?.raw_kpis || {};
  
  // Group KPIs by pillar
  const kpisByPillar = groupByPillar ? groupKPIsByPillar(kpisToDisplay) : null;
  
  // ========================================================================
  // RENDER
  // ========================================================================
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading journey data...</p>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h3 className="text-red-800 font-bold mb-2">Error Loading Data</h3>
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }
  
  if (!journeyData || !currentWeek) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center text-gray-600">
          <p>No journey data available</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {journeyData.account_name}
            </h1>
            <p className="text-sm text-gray-500">
              Account ID: {journeyData.account_id}
            </p>
          </div>
          
          {/* Data Format Badge */}
          <div className="flex items-center gap-3">
            {isV2Data && (
              <div className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                ✓ V2 Data (Industry Units)
              </div>
            )}
            
            <button
              onClick={() => navigate('/dashboard')}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
            >
              ← Back
            </button>
          </div>
        </div>
      </div>
      
      {/* Week Timeline */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <WeekTimeline
          weeks={journeyData.weekly_data}
          selectedWeek={selectedWeek}
          onWeekSelect={setSelectedWeek}
        />
      </div>
      
      {/* Main Content */}
      <div className="container mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: KPIs */}
          <div className="lg:col-span-2 space-y-6">
            {/* Week Header */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    Week {currentWeek.week_number}
                  </h2>
                  <p className="text-sm text-gray-500">{currentWeek.date}</p>
                </div>
                
                <div className="text-right">
                  <div className="text-3xl font-bold text-blue-600">
                    {currentWeek.health_score.toFixed(1)}
                  </div>
                  <div className="text-sm text-gray-500">Health Score</div>
                </div>
              </div>
              
              {/* Data Quality Badge */}
              {currentWeek.data_quality !== undefined && (
                <DataQualityBadge
                  coverage={currentWeek.coverage_pct || 0}
                  dataQuality={currentWeek.data_quality}
                  missingKPIs={currentWeek.missing_kpis || []}
                  showMissing={showMissingKPIs}
                  onToggleMissing={() => setShowMissingKPIs(!showMissingKPIs)}
                />
              )}
            </div>
            
            {/* Settings */}
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showIndustryContext}
                    onChange={(e) => setShowIndustryContext(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-sm text-gray-700">Show Industry Context</span>
                </label>
                
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={groupByPillar}
                    onChange={(e) => setGroupByPillar(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-sm text-gray-700">Group by Pillar</span>
                </label>
              </div>
            </div>
            
            {/* KPI Cards */}
            {groupByPillar && kpisByPillar ? (
              // Grouped by pillar
              Object.entries(kpisByPillar).map(([pillar, pillarKPIs]) => (
                <div key={pillar} className="space-y-3">
                  <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                    {getPillarEmoji(pillar)} {formatPillarName(pillar)}
                    <span className="text-sm font-normal text-gray-500">
                      ({Object.keys(pillarKPIs).length} KPIs tracked)
                    </span>
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(pillarKPIs).map(([kpiName, normalizedValue]) => (
                      <KPICard
                        key={kpiName}
                        name={kpiName}
                        rawValue={rawKPIs[kpiName]}
                        normalizedValue={normalizedValue}
                        showIndustryContext={showIndustryContext}
                        isV2={isV2Data}
                      />
                    ))}
                  </div>
                </div>
              ))
            ) : (
              // Not grouped - show all KPIs
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(kpisToDisplay).map(([kpiName, normalizedValue]) => (
                  <KPICard
                    key={kpiName}
                    name={kpiName}
                    rawValue={rawKPIs[kpiName]}
                    normalizedValue={normalizedValue}
                    showIndustryContext={showIndustryContext}
                    isV2={isV2Data}
                  />
                ))}
              </div>
            )}
          </div>
          
          {/* Right Column: Context & Trends */}
          <div className="space-y-6">
            {/* Industry Context Panel */}
            {showIndustryContext && (
              <IndustryContextPanel
                week={currentWeek}
                isV2={isV2Data}
              />
            )}
            
            {/* Coverage Trends */}
            {currentWeek.coverage_pct !== undefined && (
              <CoverageTrends
                weeks={journeyData.weekly_data}
                currentWeek={selectedWeek}
              />
            )}
            
            {/* Events */}
            {currentWeek.events && currentWeek.events.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  📅 Events This Week
                </h3>
                
                <div className="space-y-3">
                  {currentWeek.events.map((event, idx) => (
                    <div key={idx} className="border-l-4 border-blue-500 pl-4 py-2">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="font-medium text-gray-900">
                            {event.event_type}
                          </div>
                          <div className="text-sm text-gray-600 mt-1">
                            {event.description}
                          </div>
                        </div>
                        <div className={`
                          px-2 py-1 rounded text-xs font-medium
                          ${getSentimentColor(event.sentiment)}
                        `}>
                          {event.sentiment}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function groupKPIsByPillar(kpis: Record<string, number>): Record<string, Record<string, number>> {
  const grouped: Record<string, Record<string, number>> = {};
  
  // KPI to pillar mapping (simplified - in production, load from config)
  const kpiPillarMap: Record<string, string> = {
    'deployment_success_rate': 'P1_deployment_velocity',
    'time_to_first_cluster': 'P1_deployment_velocity',
    'api_adoption_rate': 'P1_deployment_velocity',
    
    'rma_frequency_rate': 'P2_operational_stability',
    'mtbf': 'P2_operational_stability',
    'critical_incident_rate': 'P2_operational_stability',
    'unplanned_downtime': 'P2_operational_stability',
    
    'gpu_utilization_rate': 'P3_ai_workload_performance',
    'training_job_completion': 'P3_ai_workload_performance',
    'model_deployment_success': 'P3_ai_workload_performance',
    
    'partner_engagement_score': 'P4_channel_partner_health',
    'cosell_activity': 'P4_channel_partner_health',
    'partner_satisfaction': 'P4_channel_partner_health',
    
    'expansion_probability_90d': 'P5_expansion_readiness',
    'capacity_utilization_trajectory': 'P5_expansion_readiness',
    'decision_maker_engagement': 'P5_expansion_readiness',
  };
  
  Object.entries(kpis).forEach(([kpiName, value]) => {
    const pillar = kpiPillarMap[kpiName] || 'Other';
    
    if (!grouped[pillar]) {
      grouped[pillar] = {};
    }
    
    grouped[pillar][kpiName] = value;
  });
  
  return grouped;
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

function getSentimentColor(sentiment: string): string {
  const colorMap: Record<string, string> = {
    'very_positive': 'bg-green-100 text-green-800',
    'positive': 'bg-green-50 text-green-700',
    'neutral': 'bg-gray-100 text-gray-700',
    'negative': 'bg-orange-100 text-orange-800',
    'very_negative': 'bg-red-100 text-red-800',
  };
  
  return colorMap[sentiment] || 'bg-gray-100 text-gray-700';
}

export default JourneyVisualizerV2;
