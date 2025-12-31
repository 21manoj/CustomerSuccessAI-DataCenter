import React, { useState, useEffect } from 'react';
import HealthScoreCard from './dashboard/HealthScoreCard';
import PortfolioOverview from './dashboard/PortfolioOverview';
import SmartActionsPanel from './dashboard/SmartActionsPanel';
import HealthTrendChart from './dashboard/HealthTrendChart';
import CategoryBreakdownRadar from './dashboard/CategoryBreakdownRadar';
import QualityScoreDashboard from './dataQuality/QualityScoreDashboard';
import CoverageHeatMap from './dataQuality/CoverageHeatMap';
import AnomalyAlertList from './dataQuality/AnomalyAlertList';
import ValidationPipeline from './dataQuality/ValidationPipeline';
import {
  getAccountHealthScore,
  getPortfolioOverview,
  getHealthTrends,
  getSmartActions,
  SmartAction
} from '../utils/healthScoreApi';
import {
  getQualityMetrics,
  getCoverageData,
  getAnomalies,
  getPipelineStatus,
  Anomaly
} from '../utils/dataQualityApi';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './shared/Tabs';
import { useSession } from '../contexts/SessionContext';
import { apiCall } from '../utils/api';

const ExecutiveDashboard: React.FC = () => {
  const { session } = useSession();
  const [activeTab, setActiveTab] = useState<'health' | 'quality'>('health');
  const [loading, setLoading] = useState(true);
  
  // Health Score Data
  const [healthScoreData, setHealthScoreData] = useState<any>(null);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [trendsData, setTrendsData] = useState<any[]>([]);
  const [smartActions, setSmartActions] = useState<SmartAction[]>([]);
  
  // Data Quality Data
  const [qualityMetrics, setQualityMetrics] = useState<any>(null);
  const [coverageData, setCoverageData] = useState<any[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [pipelineStatus, setPipelineStatus] = useState<any>(null);

  useEffect(() => {
    if (session?.customer_id) {
      loadDashboardData();
    }
  }, [session]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Load health score data
      const accountsResponse = await apiCall('/api/accounts', {
        method: 'GET',
        headers: session?.customer_id ? {
          'X-Customer-ID': String(session.customer_id)
        } : {}
      });
      
      if (accountsResponse.ok) {
        const accounts = await accountsResponse.json();
        if (accounts.length > 0) {
          const firstAccount = accounts[0];
          const healthData = await getAccountHealthScore(firstAccount.account_id);
          setHealthScoreData(healthData);
          
          const trends = await getHealthTrends(firstAccount.account_id);
          setTrendsData(trends);
        }
      }
      
      const portfolio = await getPortfolioOverview();
      setPortfolioData(portfolio);
      
      const actions = await getSmartActions();
      setSmartActions(actions);
      
      // Load data quality data
      const quality = await getQualityMetrics();
      setQualityMetrics(quality);
      
      const coverage = await getCoverageData();
      setCoverageData(coverage);
      
      const anomalyList = await getAnomalies();
      setAnomalies(anomalyList);
      
      const pipeline = await getPipelineStatus();
      setPipelineStatus(pipeline);
      
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleActionClick = (action: SmartAction, actionType: string) => {
    console.log('Action clicked:', action, actionType);
    // Implement action handlers
  };

  const handleAnomalyFix = (anomaly: Anomaly) => {
    console.log('Fix anomaly:', anomaly);
    // Implement fix logic
  };

  const handleAnomalyIgnore = (anomaly: Anomaly) => {
    setAnomalies(anomalies.filter(a => a.id !== anomaly.id));
  };

  const handleAnomalyReview = (anomaly: Anomaly) => {
    console.log('Review anomaly:', anomaly);
    // Implement review logic
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Executive Dashboard</h1>
          <p className="mt-2 text-gray-600">Portfolio health overview and data quality insights</p>
        </div>

        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'health' | 'quality')}>
          <TabsList>
            <TabsTrigger value="health">Health Scores</TabsTrigger>
            <TabsTrigger value="quality">Data Quality</TabsTrigger>
          </TabsList>

          <TabsContent value="health" className="space-y-6">
            {/* Health Score Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {healthScoreData && (
                <HealthScoreCard
                  accountId={healthScoreData.accountId}
                  accountName="DeepMind Research"
                  healthScore={healthScoreData.healthScore}
                  categoryScores={healthScoreData.categoryScores}
                  trends={healthScoreData.trends}
                  riskCount={healthScoreData.riskCount}
                  healthyMetrics={healthScoreData.healthyMetrics}
                />
              )}
              
              {portfolioData && (
                <PortfolioOverview data={portfolioData} />
              )}
            </div>

            {/* Smart Actions */}
            {smartActions.length > 0 && (
              <SmartActionsPanel
                actions={smartActions}
                onActionClick={handleActionClick}
              />
            )}

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {trendsData.length > 0 && (
                <HealthTrendChart
                  data={trendsData}
                  showCategories={false}
                  timeRange="6m"
                />
              )}
              
              {healthScoreData && (
                <CategoryBreakdownRadar
                  scores={healthScoreData.categoryScores}
                  benchmarks={{
                    industry: {
                      reliability: 85,
                      efficiency: 80,
                      capacity: 75,
                      security: 90,
                      service: 85
                    },
                    topQuartile: {
                      reliability: 95,
                      efficiency: 92,
                      capacity: 88,
                      security: 98,
                      service: 94
                    }
                  }}
                />
              )}
            </div>
          </TabsContent>

          <TabsContent value="quality" className="space-y-6">
            {/* Data Quality Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {qualityMetrics && (
                <QualityScoreDashboard metrics={qualityMetrics} />
              )}
              
              {coverageData.length > 0 && (
                <CoverageHeatMap data={coverageData} />
              )}
            </div>

            {/* Anomalies */}
            {anomalies.length > 0 && (
              <AnomalyAlertList
                anomalies={anomalies}
                onFix={handleAnomalyFix}
                onIgnore={handleAnomalyIgnore}
                onReview={handleAnomalyReview}
              />
            )}

            {/* Pipeline Status */}
            {pipelineStatus && (
              <ValidationPipeline pipeline={pipelineStatus} />
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default ExecutiveDashboard;

