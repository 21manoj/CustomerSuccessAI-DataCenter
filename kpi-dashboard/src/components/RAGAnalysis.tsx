import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
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
  Copy,
  RefreshCw,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  Activity,
  Calendar,
  LineChart,
} from 'lucide-react';
import { useSession } from '../contexts/SessionContext';

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
  const [vectorDb, setVectorDb] = useState<'working' | 'faiss' | 'qdrant' | 'historical' | 'temporal'>('working');
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

  // Pre-defined query templates
  const queryTemplates: QueryTemplate[] = [
    // Revenue Analysis
    {
      id: 'revenue-top-accounts',
      category: 'Revenue Analysis',
      title: 'Top Revenue Accounts',
      description: 'Identify accounts with the highest revenue',
      query: 'Which accounts have the highest revenue?',
      icon: TrendingUp,
      color: 'bg-green-500',
      query_type: 'revenue_analysis'
    },
    {
      id: 'revenue-total',
      category: 'Revenue Analysis',
      title: 'Total Revenue Overview',
      description: 'Get total revenue across all accounts',
      query: 'What is the total revenue across all accounts?',
      icon: BarChart3,
      color: 'bg-green-500',
      query_type: 'revenue_analysis'
    },
    {
      id: 'revenue-growth',
      category: 'Revenue Analysis',
      title: 'Revenue Growth Analysis',
      description: 'Analyze revenue growth patterns and trends',
      query: 'Show me revenue growth analysis and trends',
      icon: TrendingUp,
      color: 'bg-green-500',
      query_type: 'revenue_analysis'
    },
    {
      id: 'revenue-industry',
      category: 'Revenue Analysis',
      title: 'Industry Revenue Breakdown',
      description: 'Compare revenue performance by industry',
      query: 'How does revenue vary by industry?',
      icon: BarChart3,
      color: 'bg-green-500',
      query_type: 'revenue_analysis'
    },

    // Account Health & Performance
    {
      id: 'account-health',
      category: 'Account Health',
      title: 'Account Health Overview',
      description: 'Get comprehensive account health analysis',
      query: 'Show me account health scores and performance',
      icon: Users,
      color: 'bg-blue-500',
      query_type: 'account_analysis'
    },
    {
      id: 'account-risk',
      category: 'Account Health',
      title: 'At-Risk Accounts',
      description: 'Identify accounts that might be at risk of churn',
      query: 'Which accounts are at risk of churn?',
      icon: AlertTriangle,
      color: 'bg-red-500',
      query_type: 'account_analysis'
    },
    {
      id: 'account-performance',
      category: 'Account Health',
      title: 'Account Performance Ranking',
      description: 'Rank accounts by overall performance',
      query: 'Which accounts are performing best?',
      icon: Target,
      color: 'bg-blue-500',
      query_type: 'account_analysis'
    },
    {
      id: 'account-engagement',
      category: 'Account Health',
      title: 'Account Engagement Analysis',
      description: 'Analyze account engagement levels',
      query: 'Show me account engagement analysis',
      icon: Users,
      color: 'bg-blue-500',
      query_type: 'account_analysis'
    },

    // KPI Performance
    {
      id: 'kpi-top-performing',
      category: 'KPI Performance',
      title: 'Top Performing KPIs',
      description: 'Identify the best performing KPIs',
      query: 'What are the top performing KPIs?',
      icon: Target,
      color: 'bg-purple-500',
      query_type: 'kpi_analysis'
    },
    {
      id: 'kpi-customer-satisfaction',
      category: 'KPI Performance',
      title: 'Customer Satisfaction Analysis',
      description: 'Analyze customer satisfaction scores',
      query: 'Show me customer satisfaction analysis',
      icon: MessageSquare,
      color: 'bg-purple-500',
      query_type: 'kpi_analysis'
    },
    {
      id: 'kpi-categories',
      category: 'KPI Performance',
      title: 'KPI Category Performance',
      description: 'Compare performance across KPI categories',
      query: 'How are different KPI categories performing?',
      icon: BarChart3,
      color: 'bg-purple-500',
      query_type: 'kpi_analysis'
    },
    {
      id: 'kpi-trends',
      category: 'KPI Performance',
      title: 'KPI Trends & Patterns',
      description: 'Identify trends and patterns in KPI data',
      query: 'What are the key trends in our KPI performance?',
      icon: TrendingUp,
      color: 'bg-purple-500',
      query_type: 'kpi_analysis'
    },

    // Industry & Regional Analysis
    {
      id: 'industry-analysis',
      category: 'Industry Analysis',
      title: 'Industry Performance',
      description: 'Compare performance across industries',
      query: 'How do we perform across different industries?',
      icon: BarChart3,
      color: 'bg-orange-500',
      query_type: 'general'
    },
    {
      id: 'regional-analysis',
      category: 'Regional Analysis',
      title: 'Regional Performance',
      description: 'Analyze performance by geographic region',
      query: 'Show me regional performance analysis',
      icon: BarChart3,
      color: 'bg-orange-500',
      query_type: 'general'
    },

    // Historical Trend Analysis
    {
      id: 'historical-trends',
      category: 'Historical Analysis',
      title: 'Overall Trend Analysis',
      description: 'Analyze trends across all KPIs and accounts over time',
      query: 'Show me trends across all KPIs and accounts over time',
      icon: LineChart,
      color: 'bg-indigo-500',
      query_type: 'trend_analysis'
    },
    {
      id: 'kpi-trends-historical',
      category: 'Historical Analysis',
      title: 'KPI Trend Analysis',
      description: 'Analyze historical trends for specific KPIs',
      query: 'Show me historical trends in Time to First Value over time',
      icon: TrendingUp,
      color: 'bg-indigo-500',
      query_type: 'trend_analysis'
    },
    {
      id: 'account-trends-historical',
      category: 'Historical Analysis',
      title: 'Account Performance Trends',
      description: 'Track account performance changes over time',
      query: 'Show me how account performance has changed over time',
      icon: Users,
      color: 'bg-indigo-500',
      query_type: 'trend_analysis'
    },
    {
      id: 'health-evolution',
      category: 'Historical Analysis',
      title: 'Health Score Evolution',
      description: 'Track health score changes over time',
      query: 'How have health scores evolved over time?',
      icon: Activity,
      color: 'bg-indigo-500',
      query_type: 'trend_analysis'
    },
    {
      id: 'temporal-patterns',
      category: 'Historical Analysis',
      title: 'Temporal Patterns',
      description: 'Identify seasonal and cyclical patterns',
      query: 'What temporal patterns and seasonality do you see in the data?',
      icon: Calendar,
      color: 'bg-indigo-500',
      query_type: 'temporal_analysis'
    },
    {
      id: 'predictive-insights',
      category: 'Historical Analysis',
      title: 'Predictive Insights',
      description: 'Get predictions based on historical data',
      query: 'What predictions can you make based on historical trends?',
      icon: Clock,
      color: 'bg-indigo-500',
      query_type: 'trend_analysis'
    },

    // Monthly Revenue Analysis
    {
      id: 'monthly-revenue',
      category: 'Monthly Revenue Analysis',
      title: 'Monthly Revenue Breakdown',
      description: 'Get detailed monthly revenue analysis with account breakdowns',
      query: 'Which accounts have the highest revenue across last 4 months? please provide month details as well?',
      icon: Calendar,
      color: 'bg-purple-500',
      query_type: 'revenue_analysis'
    },
    {
      id: 'revenue-trends',
      category: 'Monthly Revenue Analysis',
      title: 'Revenue Trends & Patterns',
      description: 'Analyze revenue growth patterns and identify trends',
      query: 'Analyze revenue trends and patterns over the last 6 months',
      icon: TrendingUp,
      color: 'bg-purple-500',
      query_type: 'trend_analysis'
    },
    {
      id: 'top-accounts-monthly',
      category: 'Monthly Revenue Analysis',
      title: 'Top Accounts by Month',
      description: 'See which accounts performed best each month',
      query: 'Which accounts performed best each month? Show monthly rankings',
      icon: BarChart3,
      color: 'bg-purple-500',
      query_type: 'account_analysis'
    },

    // Strategic Insights
    {
      id: 'strategic-insights',
      category: 'Strategic Insights',
      title: 'Strategic Recommendations',
      description: 'Get AI-powered strategic recommendations',
      query: 'What strategic recommendations do you have for improving our business?',
      icon: Lightbulb,
      color: 'bg-yellow-500',
      query_type: 'general'
    },
    {
      id: 'growth-opportunities',
      category: 'Strategic Insights',
      title: 'Growth Opportunities',
      description: 'Identify potential growth opportunities',
      query: 'What growth opportunities do you see in our data?',
      icon: Zap,
      color: 'bg-yellow-500',
      query_type: 'general'
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
      } else if (vectorDb === 'qdrant') {
        endpoint = '/api/rag-qdrant/status';
      } else {
        endpoint = '/api/rag-openai/status';
      }
      
      const response = await fetch(endpoint, {
        method: 'GET',
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
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
            setIsKnowledgeBaseBuilt(true);
            localStorage.setItem('knowledgeBaseBuilt', 'true');
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
      } else if (vectorDb === 'qdrant') {
        endpoint = '/api/rag-qdrant/build';
      } else if (vectorDb === 'working') {
        // Direct RAG doesn't need build, just check status
        const statusResponse = await fetch('/api/direct-rag/status', {
          method: 'GET',
          headers: {
            'X-Customer-ID': session.customer_id.toString()
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
          'X-Customer-ID': session.customer_id.toString(),
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

  const executeQuery = async (query: string, queryType: string = 'general') => {
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
      } else if (vectorDb === 'qdrant') {
        endpoint = '/api/rag-qdrant/query';
      } else if (vectorDb === 'working') {
        endpoint = '/api/direct-rag/query';
      } else {
        endpoint = '/api/rag-openai/query';
      }
      
      // Include conversation context (last 3 exchanges)
      const recentHistory = conversationHistory.slice(-3).map(msg => ({
        query: msg.query,
        response: msg.response.response
      }));
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query,
          query_type: queryType,
          conversation_history: recentHistory
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to execute query');
      }
      
      const result = await response.json();
      
      if (result.error && result.error.includes('Knowledge base not built')) {
        setError('Knowledge base not built. Please build the knowledge base first by clicking the "Build Knowledge Base" button.');
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
    executeQuery(template.query, template.query_type);
  };

  const handleCustomQuery = () => {
    if (customQuery.trim()) {
      executeQuery(customQuery.trim());
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
            Ask intelligent questions about your KPI and account data, including historical trends and temporal analysis
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Vector Database Selector */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Analysis Type:</label>
            <select
              value={vectorDb}
              onChange={(e) => setVectorDb(e.target.value as 'working' | 'faiss' | 'qdrant' | 'historical' | 'temporal')}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isBuilding}
            >
              <option value="working">Working RAG System</option>
              <option value="qdrant">Current Data (Qdrant)</option>
              <option value="faiss">Current Data (FAISS)</option>
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
                 vectorDb === 'temporal' ? 'Monthly Analysis Ready' : 'Knowledge Base Ready')
              : (vectorDb === 'historical' ? 'Build Historical Analysis' : 
                 vectorDb === 'temporal' ? 'Build Monthly Analysis' : 'Build Knowledge Base')
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
                  <p className="text-sm mt-2">Ask questions about your accounts, KPIs, or playbooks</p>
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
                            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-md">📊 Database</span>
                          )}
                          {message.response.sources.salesforce && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-md">☁️ Salesforce</span>
                          )}
                          {message.response.sources.servicenow && (
                            <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded-md">🎫 ServiceNow</span>
                          )}
                          {message.response.sources.surveys && (
                            <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-md">📋 Surveys</span>
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
