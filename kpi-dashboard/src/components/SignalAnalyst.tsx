import React, { useState } from 'react';
import './SignalAnalyst.css';

/**
 * Signal Analyst Component
 * 
 * AI-powered account analysis showing churn risk, expansion opportunities,
 * and recommended actions.
 * 
 * Props:
 * - accountId: Account ID to analyze (e.g., 372)
 * - accountName: Account name for display (e.g., "CloudScale AI Labs")
 */
interface SignalAnalystProps {
  accountId: number | string;
  accountName?: string;
}

const SignalAnalyst: React.FC<SignalAnalystProps> = ({ accountId, accountName }) => {
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastAnalyzed, setLastAnalyzed] = useState<Date | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/signal-analyst/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include session cookie
        body: JSON.stringify({
          account_id: accountId,
          analysis_type: 'comprehensive',
          time_horizon_days: 60,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Analysis failed' }));
        throw new Error(errorData.error || 'Analysis failed');
      }

      const data = await response.json();
      setAnalysisResult(data);
      setLastAnalyzed(new Date());
    } catch (err) {
      console.error('Analysis error:', err);
      setError(err instanceof Error ? err.message : 'Failed to analyze account. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getHealthScoreColor = (score: number): string => {
    if (score >= 70) return '#10b981'; // Green
    if (score >= 50) return '#f59e0b'; // Yellow
    return '#ef4444'; // Red
  };

  const getChurnRiskLevel = (probability: number): { level: string; color: string } => {
    if (probability < 20) return { level: 'Low', color: '#10b981' };
    if (probability < 50) return { level: 'Medium', color: '#f59e0b' };
    return { level: 'High', color: '#ef4444' };
  };

  const formatConfidenceLevel = (level: string): string => {
    const levels: Record<string, string> = {
      very_high: 'Very High',
      high: 'High',
      medium: 'Medium',
      low: 'Low',
      very_low: 'Very Low',
    };
    return levels[level] || level;
  };

  const formatOutcome = (outcome: string): string => {
    const outcomes: Record<string, string> = {
      expansion: 'Expansion Opportunity',
      stable: 'Stable Account',
      at_risk: 'At Risk',
      churn: 'High Churn Risk',
    };
    return outcomes[outcome] || outcome;
  };

  const escapeHtml = (text: string): string => {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  };

  const formatMarkdown = (text: string): string => {
    if (!text) return '';

    // Escape HTML entities FIRST to prevent XSS
    let html = escapeHtml(text);

    // Convert markdown headers
    html = html.replace(/^### (.*$)/gim, '<h3 style="font-size: 1.125rem; font-weight: 600; margin-top: 1rem; margin-bottom: 0.5rem; color: #111827;">$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2 style="font-size: 1.25rem; font-weight: 700; margin-top: 1.5rem; margin-bottom: 0.75rem; color: #111827; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.5rem;">$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1 style="font-size: 1.5rem; font-weight: 700; margin-top: 1.5rem; margin-bottom: 1rem; color: #111827;">$1</h1>');

    // Convert bold **text** to <strong>
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong style="font-weight: 600; color: #111827;">$1</strong>');

    // Convert numbered lists
    html = html.replace(/^\d+\.\s+(.*$)/gim, '<li style="margin-bottom: 0.5rem; padding-left: 0.5rem;">$1</li>');
    html = html.replace(/(<li.*<\/li>\n?)+/g, '<ol style="margin-left: 1.5rem; margin-top: 0.5rem; margin-bottom: 0.5rem; list-style-type: decimal;">$&</ol>');

    // Convert bullet points
    html = html.replace(/^[-*]\s+(.*$)/gim, '<li style="margin-bottom: 0.5rem; padding-left: 0.5rem;">$1</li>');
    html = html.replace(/(<li.*<\/li>\n?)+/g, '<ul style="margin-left: 1.5rem; margin-top: 0.5rem; margin-bottom: 0.5rem; list-style-type: disc;">$&</ul>');

    // Convert line breaks
    html = html.replace(/\n\n/g, '</p><p style="margin-bottom: 1rem; line-height: 1.6; color: #374151;">');
    html = html.replace(/\n/g, '<br />');

    // Wrap in paragraphs if not already wrapped
    if (!html.startsWith('<')) {
      html = '<p style="margin-bottom: 1rem; line-height: 1.6; color: #374151;">' + html + '</p>';
    }

    return html;
  };

  return (
    <div className="signal-analyst-container">
      {/* Header Section */}
      <div className="signal-analyst-header">
        <div className="header-content">
          <div className="header-title">
            <h2>🤖 AI-Powered Account Analysis</h2>
            <p className="header-subtitle">
              Advanced churn prediction and expansion opportunity detection
            </p>
          </div>
          <button
            className="analyze-button"
            onClick={runAnalysis}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Analyzing...
              </>
            ) : (
              <>
                <span className="icon">⚡</span>
                Run Analysis
              </>
            )}
          </button>
        </div>
        
        {lastAnalyzed && (
          <div className="last-analyzed">
            Last analyzed: {lastAnalyzed.toLocaleString()}
          </div>
        )}
      </div>

      {/* Account Info */}
      {accountName && (
        <div className="account-info">
          <div className="info-item">
            <span className="info-label">Account:</span>
            <span className="info-value">{accountName}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Account ID:</span>
            <span className="info-value">#{accountId}</span>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          <div className="error-content">
            <div className="error-title">Analysis Failed</div>
            <div className="error-message">{error}</div>
          </div>
          <button className="error-dismiss" onClick={() => setError(null)}>
            ✕
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-container">
          <div className="loading-spinner-large"></div>
          <h3>Analyzing Account Signals...</h3>
          <p className="loading-text">
            Processing KPIs, customer interactions, and historical patterns
          </p>
          <div className="loading-steps">
            <div className="loading-step">✓ Gathering quantitative signals</div>
            <div className="loading-step">✓ Analyzing qualitative signals</div>
            <div className="loading-step active">⟳ Running AI prediction model</div>
          </div>
        </div>
      )}

      {/* Results Section */}
      {!loading && analysisResult && (
        <div className="results-container">
          {/* Key Metrics */}
          <div className="metrics-grid">
            {/* Health Score */}
            <div className="metric-card">
              <div className="metric-header">
                <span className="metric-icon">💚</span>
                <span className="metric-label">Health Score</span>
              </div>
              <div
                className="metric-value-large"
                style={{ color: getHealthScoreColor(analysisResult.health_score || 0) }}
              >
                {Math.round(analysisResult.health_score || 0)}
                <span className="metric-unit">/100</span>
              </div>
              <div className="metric-trend">
                {(analysisResult.health_score || 0) >= 70 ? '✅ Healthy' :
                 (analysisResult.health_score || 0) >= 50 ? '⚠️ Monitor' :
                 '🚨 Action Needed'}
              </div>
            </div>

            {/* Churn Probability */}
            <div className="metric-card">
              <div className="metric-header">
                <span className="metric-icon">📉</span>
                <span className="metric-label">Churn Risk</span>
              </div>
              <div className="metric-value-large">
                {Math.round(analysisResult.churn_probability || 0)}
                <span className="metric-unit">%</span>
              </div>
              <div
                className="metric-trend"
                style={{ color: getChurnRiskLevel(analysisResult.churn_probability || 0).color }}
              >
                {getChurnRiskLevel(analysisResult.churn_probability || 0).level} Risk
              </div>
            </div>

            {/* Expansion Probability */}
            {analysisResult.expansion_probability !== null && analysisResult.expansion_probability !== undefined && (
              <div className="metric-card">
                <div className="metric-header">
                  <span className="metric-icon">📈</span>
                  <span className="metric-label">Expansion Opportunity</span>
                </div>
                <div className="metric-value-large">
                  {Math.round(analysisResult.expansion_probability)}
                  <span className="metric-unit">%</span>
                </div>
                <div className="metric-trend">
                  {analysisResult.expansion_probability >= 70 ? '🎯 High Potential' :
                   analysisResult.expansion_probability >= 40 ? '💡 Moderate' :
                   '⏳ Low'}
                </div>
              </div>
            )}

            {/* Predicted Outcome */}
            <div className="metric-card">
              <div className="metric-header">
                <span className="metric-icon">🎯</span>
                <span className="metric-label">Predicted Outcome</span>
              </div>
              <div className="metric-value-text">
                {formatOutcome(analysisResult.predicted_outcome || 'stable')}
              </div>
              <div className="metric-confidence">
                Confidence: {formatConfidenceLevel(analysisResult.confidence?.confidence_level || 'medium')}
              </div>
            </div>
          </div>

          {/* AI Reasoning */}
          {analysisResult.reasoning && (
            <div className="reasoning-section">
              <h3 className="section-title">
                <span className="section-icon">🧠</span>
                AI Analysis
              </h3>
              <div className="reasoning-content" dangerouslySetInnerHTML={{ __html: formatMarkdown(analysisResult.reasoning) }} style={{ whiteSpace: 'normal' }} />
            </div>
          )}

          {/* Key Insights */}
          {analysisResult.key_insights && analysisResult.key_insights.length > 0 && (
            <div className="insights-section">
              <h3 className="section-title">
                <span className="section-icon">💡</span>
                Key Insights
              </h3>
              <div className="insights-grid">
                {(analysisResult.key_insights || []).map((insight: string, index: number) => (
                  <div key={index} className="insight-card">
                    <span className="insight-bullet">•</span>
                    <span className="insight-text">{insight}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Risk Drivers */}
          {analysisResult.risk_drivers && analysisResult.risk_drivers.length > 0 && (
            <div className="drivers-section risk-drivers">
              <h3 className="section-title">
                <span className="section-icon">⚠️</span>
                Risk Drivers
              </h3>
              <div className="drivers-list">
                {(analysisResult.risk_drivers || []).map((driver: any, index: number) => (
                  <div key={index} className="driver-item">
                    <div className="driver-header">
                      <span className="driver-name">{driver.driver_name}</span>
                      <span className={`driver-severity severity-${driver.severity}`}>
                        {driver.severity}
                      </span>
                    </div>
                    <div className="driver-description">{driver.description}</div>
                    <div className="driver-impact">
                      Impact: {Math.round((driver.impact_score || 0) * 100)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Growth Drivers */}
          {analysisResult.growth_drivers && analysisResult.growth_drivers.length > 0 && (
            <div className="drivers-section growth-drivers">
              <h3 className="section-title">
                <span className="section-icon">🚀</span>
                Growth Drivers
              </h3>
              <div className="drivers-list">
                {analysisResult.growth_drivers.map((driver: any, index: number) => (
                  <div key={index} className="driver-item">
                    <div className="driver-header">
                      <span className="driver-name">{driver.driver_name}</span>
                      <span className={`driver-strength strength-${driver.strength}`}>
                        {driver.strength}
                      </span>
                    </div>
                    <div className="driver-description">{driver.description}</div>
                    {driver.potential_score && (
                      <div className="driver-potential">
                        Potential: {Math.round(driver.potential_score * 100)}%
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Actions */}
          {analysisResult.recommended_actions && analysisResult.recommended_actions.length > 0 && (
            <div className="actions-section">
              <h3 className="section-title">
                <span className="section-icon">✅</span>
                Recommended Actions
              </h3>
              <div className="actions-grid">
                {(analysisResult.recommended_actions || []).map((action: any, index: number) => (
                  <div key={index} className="action-card">
                    <div className="action-header">
                      <span className={`action-priority priority-${action.priority}`}>
                        {action.priority}
                      </span>
                      <span className="action-timeline">{action.timeline}</span>
                    </div>
                    <div className="action-title">{action.action}</div>
                    <div className="action-rationale">{action.rationale}</div>
                    {action.expected_impact && (
                      <div className="action-impact">
                        Expected Impact: {action.expected_impact}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Analysis Metadata */}
          <div className="metadata-section">
            <div className="metadata-grid">
              <div className="metadata-item">
                <span className="metadata-label">Model Used:</span>
                <span className="metadata-value">{analysisResult.model_used || analysisResult._metadata?.model || 'gpt-4o'}</span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Analysis Duration:</span>
                <span className="metadata-value">
                  {((analysisResult.analysis_duration_ms || 0) / 1000).toFixed(1)}s
                </span>
              </div>
              <div className="metadata-item">
                <span className="metadata-label">Signals Analyzed:</span>
                <span className="metadata-value">
                  {analysisResult.signals_analyzed?.quantitative || 0} quantitative, {' '}
                  {analysisResult.signals_analyzed?.qualitative || 0} qualitative
                </span>
              </div>
              {analysisResult._metadata?.cost_tracked && (
                <div className="metadata-item">
                  <span className="metadata-label">Analysis Cost:</span>
                  <span className="metadata-value">~$0.0063</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && !analysisResult && !error && (
        <div className="empty-state">
          <div className="empty-icon">🤖</div>
          <h3>Ready to Analyze</h3>
          <p>
            Click "Run Analysis" to get AI-powered insights about this account's
            churn risk, expansion opportunities, and recommended actions.
          </p>
          <div className="empty-features">
            <div className="feature-item">
              <span className="feature-icon">✓</span>
              <span>Churn risk prediction</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">✓</span>
              <span>Expansion opportunity detection</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">✓</span>
              <span>AI-generated recommendations</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">✓</span>
              <span>Real-time analysis (~5 seconds)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SignalAnalyst;

