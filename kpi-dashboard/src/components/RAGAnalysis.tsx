import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  TrendingUp,
  Users,
  AlertTriangle,
  BarChart3,
  Target,
  Zap,
  Brain,
  Lightbulb,
  ChevronRight,
  RefreshCw,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  Activity,
  Calendar,
  LineChart,
  Server,
  Cpu,
  Thermometer,
  Shield,
  Gauge,
  Network,
  HardDrive,
  GitBranch,
  DollarSign,
} from 'lucide-react';
import { useSession } from '../contexts/SessionContext';
import { getCustomerIdentifier } from '../utils/api';

interface RAGResponse {
  query: string;
  query_type: string;
  customer_id: number;
  results_count: number;
  similarity_threshold: number;
  response: string;
  relevant_results: Array<{
    similarity: number;
    text: string;
    metadata?: {
      type?: string;
      account_id?: number;
      account_name?: string;
      revenue?: number;
      industry?: string;
      region?: string;
      category?: string;
      kpi_parameter?: string;
      data?: string;
      impact_level?: string;
      // Historical analysis properties
      trend_direction?: string;
      trend_strength?: number;
      volatility?: number;
      data_points?: number;
      date_range?: string;
      current_value?: number;
      previous_value?: number;
    };
  }>;
  // MCP enhancement fields
  mcp_enhanced?: boolean;
  mcp_sources?: string[];
  mcp_fallback?: boolean;
  mcp_error?: string;
  sources?: {
    local_database?: boolean;
    salesforce?: boolean;
    servicenow?: boolean;
    surveys?: boolean;
  };
  // Playbook enhancement fields
  playbook_enhanced?: boolean;
  enhancement_source?: string;
}

interface QueryTemplate {
  id: string;
  category: string;
  title: string;
  description: string;
  query: string;
  icon: React.ComponentType<any>;
  color: string;
  query_type: 'revenue_analysis' | 'account_analysis' | 'kpi_analysis' | 'general' | 'trend_analysis' | 'temporal_analysis';
  collection?: 'quantitative' | 'qualitative' | 'historical';  // Optional collection for hierarchical prompts
}

interface ConversationMessage {
  id: string;
  query: string;
  response: RAGResponse;
  timestamp: Date;
}

const RAGAnalysis: React.FC = () => {
  const { session } = useSession();
  const [isLoading, setIsLoading] = useState(false);
  const [isBuilding, setIsBuilding] = useState(false);
  const [error, setError] = useState('');
  const [response, setResponse] = useState<RAGResponse | null>(null);
  const [customQuery, setCustomQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<QueryTemplate | null>(null);
  const [isKnowledgeBaseBuilt, setIsKnowledgeBaseBuilt] = useState(false);
  const [vectorDb, setVectorDb] = useState<'working' | 'faiss' | 'qdrant' | 'qdrant-cloud' | 'historical' | 'temporal'>('working');
  const [isHistoricalBuilt, setIsHistoricalBuilt] = useState(false);
  const statusCheckRef = useRef<boolean>(false);
  
  // Conversation history state
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const conversationEndRef = useRef<HTMLDivElement>(null);
  
  // Load conversation history from localStorage on mount
  useEffect(() => {
    const savedHistory = localStorage.getItem(`rag_conversation_${session?.customer_id}`);
    if (savedHistory) {
      try {
        const parsed = JSON.parse(savedHistory);
        setConversationHistory(parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        })));
      } catch (e) {
        console.error('Failed to load conversation history:', e);
      }
    }
  }, [session?.customer_id]);
  
  // Save conversation history to localStorage whenever it changes
  useEffect(() => {
    if (session?.customer_id && conversationHistory.length > 0) {
      localStorage.setItem(
        `rag_conversation_${session.customer_id}`,
        JSON.stringify(conversationHistory)
      );
    }
  }, [conversationHistory, session?.customer_id]);
  
  // Scroll to bottom when new messages arrive
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationHistory]);

  // Check knowledge base status on component load and when vector DB changes
  useEffect(() => {
    if (session?.customer_id) {
      checkKnowledgeBaseStatus();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.customer_id, vectorDb]);

  // Check status only, no auto-build
  useEffect(() => {
    if (session?.customer_id) {
      checkKnowledgeBaseStatus();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.customer_id]);

  // Pre-defined query templates — Data Center focused
  const queryTemplates: QueryTemplate[] = [
    // Infrastructure & Capacity
    {
      id: 'gpu-utilization',
      category: 'Infrastructure & Capacity',
      title: 'GPU Utilization Analysis',
      description: 'GPU utilization rates across accounts, identify over/under-utilized',
      query: 'What is the GPU utilization across all accounts? Which accounts have underutilized or overloaded GPUs?',
      icon: Cpu,
      color: 'bg-emerald-500',
      query_type: 'kpi_analysis',
      collection: 'quantitative'
    },
    {
      id: 'rack-capacity',
      category: 'Infrastructure & Capacity',
      title: 'Rack Capacity & Density',
      description: 'Rack utilization and density metrics across accounts',
      query: 'Show me rack capacity utilization and density metrics across accounts',
      icon: Server,
      color: 'bg-emerald-500',
      query_type: 'kpi_analysis',
      collection: 'quantitative'
    },
    {
      id: 'power-cooling',
      category: 'Infrastructure & Capacity',
      title: 'Power & Cooling Efficiency',
      description: 'PUE, cooling efficiency, and energy cost analysis',
      query: 'Analyze power usage effectiveness (PUE) and cooling efficiency across data center accounts',
      icon: Thermometer,
      color: 'bg-emerald-500',
      query_type: 'kpi_analysis',
      collection: 'quantitative'
    },
    {
      id: 'infra-health',
      category: 'Infrastructure & Capacity',
      title: 'Infrastructure Health Overview',
      description: 'Overall infrastructure health scores and alerts',
      query: 'Give me an overview of infrastructure health scores and which accounts need immediate attention',
      icon: Server,
      color: 'bg-emerald-500',
      query_type: 'account_analysis',
      collection: 'quantitative'
    },

    // AI Workload Performance
    {
      id: 'training-completion',
      category: 'AI Workload Performance',
      title: 'Training Completion Rate',
      description: 'AI training job completion rates and failure analysis',
      query: 'What are the AI training completion rates? Which accounts have the most failed or delayed training jobs?',
      icon: Brain,
      color: 'bg-violet-500',
      query_type: 'kpi_analysis',
      collection: 'quantitative'
    },
    {
      id: 'inference-latency',
      category: 'AI Workload Performance',
      title: 'Inference Latency Analysis',
      description: 'Inference latency metrics and SLA compliance',
      query: 'Analyze inference latency metrics across accounts and identify any SLA violations',
      icon: Gauge,
      color: 'bg-violet-500',
      query_type: 'kpi_analysis',
      collection: 'quantitative'
    },
    {
      id: 'workload-diversity',
      category: 'AI Workload Performance',
      title: 'Workload Diversity & Mix',
      description: 'Workload diversity index and compute type distribution',
      query: 'Show me the workload diversity index and compute mix (training vs inference vs HPC) across accounts',
      icon: HardDrive,
      color: 'bg-violet-500',
      query_type: 'kpi_analysis',
      collection: 'quantitative'
    },
    {
      id: 'model-throughput',
      category: 'AI Workload Performance',
      title: 'Model Throughput Trends',
      description: 'Model throughput and scaling velocity',
      query: 'What are the model throughput trends and which accounts are scaling their AI workloads fastest?',
      icon: TrendingUp,
      color: 'bg-violet-500',
      query_type: 'trend_analysis',
      collection: 'historical'
    },

    // Account Health & Risk
    {
      id: 'account-health',
      category: 'Account Health & Risk',
      title: 'Account Health Overview',
      description: 'Health scores — critical, at-risk, and healthy accounts',
      query: 'Show me account health scores and identify which accounts are critical (below 50), at-risk (50-69), or healthy (70+)',
      icon: Activity,
      color: 'bg-blue-500',
      query_type: 'account_analysis',
      collection: 'quantitative'
    },
    {
      id: 'churn-risk',
      category: 'Account Health & Risk',
      title: 'Churn Risk Assessment',
      description: 'Accounts with highest churn probability and key risk signals',
      query: 'Which accounts are at highest risk of churn? What are the key risk signals and revenue at risk?',
      icon: AlertTriangle,
      color: 'bg-red-500',
      query_type: 'account_analysis',
      collection: 'quantitative'
    },
    {
      id: 'account-ranking',
      category: 'Account Health & Risk',
      title: 'Account Performance Ranking',
      description: 'Rank accounts by health score, highlight biggest movers',
      query: 'Rank all accounts by overall health score and highlight the biggest improvers and decliners',
      icon: Target,
      color: 'bg-blue-500',
      query_type: 'account_analysis',
      collection: 'quantitative'
    },
    {
      id: 'engagement-signals',
      category: 'Account Health & Risk',
      title: 'Customer Engagement Signals',
      description: 'Support tickets, executive alignment, NPS, and engagement',
      query: 'Analyze customer engagement signals including support ticket trends, executive alignment, and NPS scores',
      icon: Users,
      color: 'bg-blue-500',
      query_type: 'account_analysis',
      collection: 'quantitative'
    },

    // Revenue & Expansion Intelligence
    {
      id: 'revenue-at-risk',
      category: 'Revenue & Expansion',
      title: 'Revenue at Risk',
      description: 'Total ARR at risk from churn and contraction signals',
      query: 'What is the total revenue at risk? Which accounts have the highest churn probability and ARR exposure?',
      icon: DollarSign,
      color: 'bg-amber-500',
      query_type: 'revenue_analysis',
      collection: 'quantitative'
    },
    {
      id: 'expansion-opportunities',
      category: 'Revenue & Expansion',
      title: 'Expansion Opportunities',
      description: 'Growth signals from capacity utilization and workload demand',
      query: 'Identify expansion opportunities based on GPU utilization trends, capacity headroom, and workload growth patterns',
      icon: Zap,
      color: 'bg-amber-500',
      query_type: 'revenue_analysis',
      collection: 'quantitative'
    },
    {
      id: 'context-graph-signals',
      category: 'Revenue & Expansion',
      title: 'Context Graph Signals',
      description: 'Revenue decisions and outcomes from context graph data',
      query: 'What revenue decisions and outcomes have been captured? Show me context graph signals including decisions, outcomes, and their revenue impact',
      icon: GitBranch,
      color: 'bg-amber-500',
      query_type: 'revenue_analysis',
      collection: 'quantitative'
    },
    {
      id: 'stakeholder-analysis',
      category: 'Revenue & Expansion',
      title: 'Stakeholder Influence Map',
      description: 'Key stakeholders, roles, influence, and sentiment',
      query: 'Show me key stakeholders across accounts — their roles (champion, detractor, exec sponsor), influence scores, and sentiment trends',
      icon: Users,
      color: 'bg-amber-500',
      query_type: 'account_analysis',
      collection: 'quantitative'
    },

    // Operational Excellence
    {
      id: 'sla-compliance',
      category: 'Operational Excellence',
      title: 'SLA Compliance Analysis',
      description: 'SLA adherence rates and violation patterns',
      query: 'Analyze SLA compliance rates across accounts and identify systemic SLA violations or patterns',
      icon: Shield,
      color: 'bg-cyan-500',
      query_type: 'kpi_analysis',
      collection: 'quantitative'
    },
    {
      id: 'uptime-availability',
      category: 'Operational Excellence',
      title: 'Uptime & Availability',
      description: 'Uptime metrics, incidents, and availability trends',
      query: 'What are the uptime and availability metrics? Which accounts have had the most incidents or downtime?',
      icon: Network,
      color: 'bg-cyan-500',
      query_type: 'kpi_analysis',
      collection: 'quantitative'
    },
    {
      id: 'support-tickets',
      category: 'Operational Excellence',
      title: 'Support Ticket Trends',
      description: 'Ticket volume, resolution time, and escalation patterns',
      query: 'Show me support ticket volume trends, average resolution time, and escalation patterns across accounts',
      icon: MessageSquare,
      color: 'bg-cyan-500',
      query_type: 'kpi_analysis',
      collection: 'quantitative'
    },

    // Historical Trends & Predictions
    {
      id: 'health-evolution',
      category: 'Historical Trends',
      title: 'Health Score Evolution',
      description: 'Health score trajectory over the last 6 months',
      query: 'How have account health scores evolved over the last 6 months? Show improving and declining trends',
      icon: LineChart,
      color: 'bg-indigo-500',
      query_type: 'trend_analysis',
      collection: 'historical'
    },
    {
      id: 'kpi-trends-historical',
      category: 'Historical Trends',
      title: 'Infrastructure KPI Trends',
      description: 'Historical trends for key infrastructure KPIs',
      query: 'Show me historical trends for key infrastructure KPIs — GPU utilization, PUE, uptime, and training completion rate',
      icon: TrendingUp,
      color: 'bg-indigo-500',
      query_type: 'trend_analysis',
      collection: 'historical'
    },
    {
      id: 'capacity-forecast',
      category: 'Historical Trends',
      title: 'Capacity Planning Forecast',
      description: 'Predict capacity needs based on utilization trends',
      query: 'Based on historical utilization trends, which accounts will need capacity upgrades in the next quarter?',
      icon: BarChart3,
      color: 'bg-indigo-500',
      query_type: 'trend_analysis',
      collection: 'historical'
    },
    {
      id: 'predictive-risk',
      category: 'Historical Trends',
      title: 'Predictive Risk Insights',
      description: 'Churn and health predictions from historical patterns',
      query: 'What predictions can you make about churn risk and health trajectory based on historical trends?',
      icon: Clock,
      color: 'bg-indigo-500',
      query_type: 'trend_analysis',
      collection: 'historical'
    },
    {
      id: 'seasonal-patterns',
      category: 'Historical Trends',
      title: 'Seasonal Workload Patterns',
      description: 'Cyclical patterns in workload demand and infrastructure',
      query: 'What temporal patterns and seasonality do you see in workload demand, GPU utilization, and infrastructure metrics?',
      icon: Calendar,
      color: 'bg-indigo-500',
      query_type: 'temporal_analysis',
      collection: 'historical'
    }
  ];

  // Group templates by category
  const templatesByCategory = queryTemplates.reduce((acc, template) => {
    if (!acc[template.category]) {
      acc[template.category] = [];
    }
    acc[template.category].push(template);
    return acc;
  }, {} as Record<string, QueryTemplate[]>);

  const checkKnowledgeBaseStatus = async () => {
    if (!session?.customer_id || isBuilding || statusCheckRef.current) return;
    
    statusCheckRef.current = true;
    
    try {
      let endpoint: string;
      
      if (vectorDb === 'historical') {
        endpoint = '/api/rag-historical/status';
      } else if (vectorDb === 'temporal') {
        endpoint = '/api/rag-temporal/status';
      } else if (vectorDb === 'qdrant' || vectorDb === 'qdrant-cloud') {
        endpoint = '/api/rag-qdrant/status';
      } else if (vectorDb === 'working') {
        endpoint = '/api/direct-rag/status';
      } else {
        endpoint = '/api/rag-openai/status';
      }
      
      const response = await fetch(endpoint, {
        method: 'GET',
        headers: {
          'X-Customer-ID': getCustomerIdentifier(session),
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const result = await response.json();
        
        if (vectorDb === 'historical') {
          if (result.is_built) {
            setIsHistoricalBuilt(true);
            localStorage.setItem('historicalBuilt', 'true');
          } else {
            setIsHistoricalBuilt(false);
            localStorage.removeItem('historicalBuilt');
          }
        } else {
          if (result.is_built) {
            // Check if rebuild is needed (e.g., products missing)
            if (result.needs_rebuild || (result.has_products === false && result.points_count > 0)) {
              // Knowledge base exists but is missing product data - enable rebuild
              setIsKnowledgeBaseBuilt(false);
              localStorage.removeItem('knowledgeBaseBuilt');
              // Set error message to indicate rebuild is needed
              setError('Knowledge base exists but is missing product data. Please rebuild to include products.');
            } else {
              setIsKnowledgeBaseBuilt(true);
              localStorage.setItem('knowledgeBaseBuilt', 'true');
              // Clear any previous error if rebuild is not needed
              if (error && error.includes('missing product data')) {
                setError('');
              }
            }
          } else {
            setIsKnowledgeBaseBuilt(false);
            localStorage.removeItem('knowledgeBaseBuilt');
          }
        }
      }
    } catch (err) {
      console.log('Status check failed:', err);
    } finally {
      statusCheckRef.current = false;
    }
  };

  const buildKnowledgeBase = async () => {
    if (!session?.customer_id) return;
    
    // Check if already built before starting
    if (isKnowledgeBaseBuilt || isHistoricalBuilt) {
      console.log('Knowledge base already built, skipping...');
      return;
    }
    
    setIsBuilding(true);
    setError('');
    
    try {
      let endpoint: string;
      
      if (vectorDb === 'historical') {
        endpoint = '/api/rag-historical/build';
      } else if (vectorDb === 'temporal') {
        endpoint = '/api/rag-temporal/build';
      } else if (vectorDb === 'qdrant' || vectorDb === 'qdrant-cloud') {
        endpoint = '/api/rag-qdrant/build';
      } else if (vectorDb === 'working') {
        // Direct RAG doesn't need build, just check status
        const statusResponse = await fetch('/api/direct-rag/status', {
          method: 'GET',
          headers: {
            'X-Customer-ID': getCustomerIdentifier(session)
          }
        });
        
        if (statusResponse.ok) {
          const statusData = await statusResponse.json();
          setIsKnowledgeBaseBuilt(true);
          setError('');
          return;
        } else {
          throw new Error('Failed to check direct RAG status');
        }
      } else {
        endpoint = '/api/rag-openai/build';
      }
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'X-Customer-ID': getCustomerIdentifier(session),
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to build knowledge base');
      }
      
      const result = await response.json();
      
      if (vectorDb === 'historical') {
        setIsHistoricalBuilt(true);
        localStorage.setItem('historicalBuilt', 'true');
      } else {
        setIsKnowledgeBaseBuilt(true);
        localStorage.setItem('knowledgeBaseBuilt', 'true');
      }
      
      console.log('Knowledge base built:', result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to build knowledge base');
    } finally {
      setIsBuilding(false);
    }
  };

  const executeQuery = async (query: string, queryType: string = 'general', template?: QueryTemplate) => {
    if (!session?.customer_id) return;
    
    setIsLoading(true);
    setError('');
    setResponse(null);
    
    try {
      let endpoint: string;
      
      if (vectorDb === 'historical') {
        endpoint = '/api/rag-historical/query';
      } else if (vectorDb === 'temporal') {
        endpoint = '/api/rag-temporal/query';
      } else if (vectorDb === 'qdrant' || vectorDb === 'qdrant-cloud') {
        endpoint = '/api/rag-qdrant/query';
      } else if (vectorDb === 'working') {
        endpoint = '/api/direct-rag/query';
      } else {
        endpoint = '/api/rag-openai/query';
      }
      
      // Include conversation context (last 3 exchanges) with customer_id for security
      const recentHistory = conversationHistory.slice(-3).map(msg => ({
        query: msg.query,
        response: msg.response.response,
        customer_id: session.customer_id  // Add customer_id for backend validation
      }));
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'X-Customer-ID': getCustomerIdentifier(session),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query,
          query_type: queryType,
          collection: template?.collection,  // Include collection if available from template parameter
          conversation_history: recentHistory
        })
      });
      
      if (!response.ok) {
        // Try to get the actual error message from the response
        let errorMessage = 'Failed to execute query';
        try {
          const errorData = await response.json();
          if (errorData.error) {
            errorMessage = errorData.error;
          }
        } catch (e) {
          // If response is not JSON, use status text
          errorMessage = response.statusText || 'Failed to execute query';
        }
        throw new Error(errorMessage);
      }
      
      const result = await response.json();
      
      if (result.error) {
        // Check for specific error types
        if (result.error.includes('Knowledge base not built')) {
          setError('Knowledge base not built. Please build the knowledge base first by clicking the "Build Knowledge Base" button.');
          return;
        }
        if (result.error.includes('API key') || result.error.includes('OpenAI') || result.error.includes('401') || result.error.includes('Incorrect API key')) {
          setError('OpenAI API key is missing or invalid. Please configure your OpenAI API key in Settings > OpenAI Key Settings.');
          return;
        }
        // For other errors, show the actual error message
        setError(result.error);
        return;
      }
      
      // Add to conversation history
      const newMessage: ConversationMessage = {
        id: Date.now().toString(),
        query,
        response: result,
        timestamp: new Date()
      };
      setConversationHistory(prev => [...prev, newMessage]);
      
      setResponse(result);
      setCustomQuery(''); // Clear input after successful query
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute query');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTemplateClick = (template: QueryTemplate) => {
    setSelectedTemplate(template);
    setCustomQuery(template.query);
    // Pass template to executeQuery so collection can be included
    executeQuery(template.query, template.query_type, template);
  };

  const handleCustomQuery = () => {
    if (customQuery.trim()) {
      executeQuery(customQuery.trim(), 'general', undefined);  // No template for custom queries
    }
  };
  
  const clearConversation = () => {
    setConversationHistory([]);
    setResponse(null);
    localStorage.removeItem(`rag_conversation_${session?.customer_id}`);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const formatResponse = (response: string) => {
    // Simple formatting for better readability
    if (!response) {
      return <p className="mb-2 text-gray-500">No response available</p>;
    }
    return response
      .split('\n')
      .map((line, index) => (
        <p key={index} className="mb-2">
          {line}
        </p>
      ));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Brain className="h-8 w-8 text-blue-600" />
            AI Insights
          </h2>
          <p className="text-gray-600 mt-1">
            Ask questions about infrastructure health, workload performance, revenue intelligence, and account risk
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Vector Database Selector */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Analysis Type:</label>
            <select
              value={vectorDb}
              onChange={(e) => setVectorDb(e.target.value as 'working' | 'faiss' | 'qdrant' | 'qdrant-cloud' | 'historical' | 'temporal')}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isBuilding}
            >
              <option value="qdrant-cloud">Qdrant Cloud (Recommended)</option>
              <option value="qdrant">Qdrant (Local/Self-hosted)</option>
              <option value="faiss">FAISS (In-Memory Fallback)</option>
              <option value="working">Working RAG System (Simple)</option>
              <option value="historical">Historical Analysis</option>
              <option value="temporal">Monthly Revenue Analysis</option>
            </select>
          </div>
          
          <button
            onClick={buildKnowledgeBase}
            disabled={isBuilding || (vectorDb === 'historical' ? isHistoricalBuilt : isKnowledgeBaseBuilt)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isBuilding ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (vectorDb === 'historical' ? isHistoricalBuilt : isKnowledgeBaseBuilt) ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {(vectorDb === 'historical' ? isHistoricalBuilt : isKnowledgeBaseBuilt) 
              ? (vectorDb === 'historical' ? 'Historical Data Ready' : 
                 vectorDb === 'temporal' ? 'Monthly Analysis Ready' : 
                 vectorDb === 'qdrant-cloud' ? 'Qdrant Cloud Ready' :
                 'Knowledge Base Ready')
              : (vectorDb === 'historical' ? 'Build Historical Analysis' : 
                 vectorDb === 'temporal' ? 'Build Monthly Analysis' : 
                 vectorDb === 'qdrant-cloud' ? 'Build Qdrant Cloud Knowledge Base' :
                 'Build Knowledge Base')
            }
          </button>
        </div>
      </div>

      {/* Knowledge Base Status */}
      {(isKnowledgeBaseBuilt || isHistoricalBuilt) && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span className="text-green-800 font-medium">
              {vectorDb === 'historical' 
                ? 'Historical analysis data is ready for trend queries' 
                : vectorDb === 'temporal'
                ? 'Monthly revenue analysis is ready for temporal queries'
                : vectorDb === 'qdrant-cloud'
                ? 'Qdrant Cloud knowledge base is ready for queries'
                : 'Knowledge base is ready for queries'
              }
            </span>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <XCircle className="h-5 w-5 text-red-600" />
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Query Templates */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 sticky top-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-yellow-500" />
              Quick Query Templates
            </h3>
            
            <div className="space-y-4 overflow-y-auto" style={{maxHeight: 'calc(100vh - 250px)'}}>
              {Object.entries(templatesByCategory).map(([category, templates]) => (
                <div key={category}>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">{category}</h4>
                  <div className="space-y-2">
                    {templates.map((template) => (
                      <button
                        key={template.id}
                        onClick={() => handleTemplateClick(template)}
                        className={`w-full p-3 rounded-lg border-2 transition-all duration-200 hover:scale-105 hover:shadow-md text-left ${
                          selectedTemplate?.id === template.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`p-2 rounded-lg ${template.color} text-white`}>
                            <template.icon className="h-4 w-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h5 className="font-medium text-gray-900 text-sm">
                              {template.title}
                            </h5>
                            <p className="text-xs text-gray-600 mt-1">
                              {template.description}
                            </p>
                          </div>
                          <ChevronRight className="h-4 w-4 text-gray-400" />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Conversation Interface */}
        <div className="lg:col-span-2 space-y-6">
          {/* Conversation Thread */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col" style={{height: 'calc(100vh - 280px)'}}>
            {/* Conversation Header */}
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-blue-500" />
                AI Conversation
              </h3>
              {conversationHistory.length > 0 && (
                <button
                  onClick={clearConversation}
                  className="text-sm text-gray-500 hover:text-red-600 px-3 py-1 rounded-md hover:bg-red-50"
                >
                  Clear Conversation
                </button>
              )}
            </div>
            
            {/* Conversation Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {conversationHistory.length === 0 && !isLoading && (
                <div className="text-center py-12 text-gray-400">
                  <MessageSquare className="h-16 w-16 mx-auto mb-4 opacity-20" />
                  <p className="text-lg">Start a conversation</p>
                  <p className="text-sm mt-2">Ask about infrastructure health, GPU utilization, churn risk, or revenue intelligence</p>
                </div>
              )}
              
              {conversationHistory.map((message) => (
                <div key={message.id} className="space-y-3">
                  {/* User Query */}
                  <div className="flex justify-end">
                    <div className="max-w-3/4 bg-blue-600 text-white rounded-lg p-3 shadow-sm">
                      <p className="text-sm">{message.query}</p>
                      <span className="text-xs opacity-75 mt-1 block">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                  
                  {/* AI Response */}
                  <div className="flex justify-start">
                    <div className="max-w-3/4 bg-gray-50 rounded-lg p-4 shadow-sm border border-gray-200">
                      <div className="flex items-start gap-2 mb-2">
                        <Brain className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <div className="text-sm text-gray-800 prose prose-sm max-w-none">
                            {formatResponse(message.response.response || '')}
                          </div>
                        </div>
                      </div>
                      
                      {/* Data Source Badges */}
                      {message.response.mcp_enhanced && message.response.sources && (
                        <div className="mt-3 flex flex-wrap gap-2 pt-2 border-t border-gray-200">
                          <span className="text-xs text-gray-500">Sources:</span>
                          {message.response.sources.local_database && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-md">📊 KPI Database</span>
                          )}
                          {message.response.sources.salesforce && (
                            <span className="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs rounded-md">🖥️ DCIM</span>
                          )}
                          {message.response.sources.servicenow && (
                            <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded-md">📡 Monitoring</span>
                          )}
                          {message.response.sources.surveys && (
                            <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-md">🔗 Context Graph</span>
                          )}
                        </div>
                      )}
                      
                      {/* Playbook Enhancement Badge */}
                      {message.response.playbook_enhanced && (
                        <div className="mt-2 pt-2 border-t border-gray-200">
                          <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-md">
                            ✓ Enhanced with Playbook Insights
                          </span>
                        </div>
                      )}
                      
                      <span className="text-xs text-gray-400 mt-2 block">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
              
              {/* Loading State */}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="max-w-3/4 bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                      <span className="text-gray-600">AI is thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={conversationEndRef} />
            </div>
            
            {/* Input Area */}
            <div className="p-4 border-t border-gray-200 bg-gray-50">
              <div className="flex gap-3">
                <textarea
                  value={customQuery}
                  onChange={(e) => setCustomQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleCustomQuery();
                    }
                  }}
                  placeholder="Ask a question... (Shift+Enter for new line)"
                  className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={2}
                />
                <button
                  onClick={handleCustomQuery}
                  disabled={!customQuery.trim() || isLoading}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed h-fit self-end"
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    'Send'
                  )}
                </button>
              </div>
              <div className="text-xs text-gray-500 mt-2">
                Press Enter to send, Shift+Enter for new line
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default RAGAnalysis;
