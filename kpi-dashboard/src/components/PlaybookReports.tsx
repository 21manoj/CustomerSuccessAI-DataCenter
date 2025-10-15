/**
 * Playbook Reports Component
 * 
 * Displays comprehensive reports for playbook executions
 * Shows RACI, outcomes, exit criteria, and detailed metrics
 */

import React, { useState, useEffect } from 'react';
import { FileText, Download, CheckCircle, XCircle, TrendingUp, Users, Target, Calendar } from 'lucide-react';

interface PlaybookReportsProps {
  customerId: number;
}

interface Report {
  execution_id: string;
  playbook_name: string;
  playbook_id: string;
  account_name: string;
  account_id?: number;
  report_generated_at: string;
  duration: string;
  status: string;
  themes_discovered?: any[];
  committed_fixes?: any[];
  raci_matrix?: Record<string, Record<string, string>>;
  outcomes_achieved?: Record<string, any>;
  exit_criteria?: any[];
  executive_summary: string;
  next_steps?: string[];
  activation_results?: any;
}

interface ExecutionSummary {
  execution_id: string;
  playbook_name: string;
  account_name: string;
  status: string;
  started_at: string;
  completed_at?: string;
  steps_completed: number;
  has_full_report: boolean;
}

export default function PlaybookReports({ customerId }: PlaybookReportsProps) {
  const [executions, setExecutions] = useState<ExecutionSummary[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);

  useEffect(() => {
    fetchExecutions();
    
    // Poll for new executions every 5 seconds for real-time updates
    const interval = setInterval(() => {
      fetchExecutions();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [customerId]);

  const fetchExecutions = async () => {
    try {
      const response = await fetch('/api/playbooks/reports', {
        headers: { 'X-Customer-ID': customerId.toString() }
      });
      if (response.ok) {
        const data = await response.json();
        setExecutions(data.reports || []);
      }
    } catch (error) {
      console.error('Failed to fetch executions:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchReport = async (executionId: string) => {
    try {
      setLoadingReport(true);
      const response = await fetch(`/api/playbooks/executions/${executionId}/report`, {
        headers: { 'X-Customer-ID': customerId.toString() }
      });
      if (response.ok) {
        const data = await response.json();
        setSelectedReport(data.report);
      }
    } catch (error) {
      console.error('Failed to fetch report:', error);
      alert('Failed to load report. Please try again.');
    } finally {
      setLoadingReport(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading reports...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <FileText className="h-8 w-8 text-blue-600" />
          Playbook Execution Reports
        </h2>
        <p className="text-gray-600">
          Comprehensive reports with RACI, outcomes, and exit criteria for all playbook executions
        </p>
      </div>

      {/* Executions List */}
      {executions.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
          <FileText className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Playbook Executions Yet</h3>
          <p className="text-gray-600">
            Start a playbook from the Playbooks tab to see execution reports here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {executions.map((execution) => (
            <div
              key={execution.execution_id}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => fetchReport(execution.execution_id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">{execution.playbook_name}</h3>
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
                      {execution.account_name}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      execution.status === 'completed' ? 'bg-green-100 text-green-800' :
                      execution.status === 'in-progress' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {execution.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      Started: {new Date(execution.started_at).toLocaleDateString()}
                    </span>
                    {execution.completed_at && (
                      <span>Completed: {new Date(execution.completed_at).toLocaleDateString()}</span>
                    )}
                    <span>{execution.steps_completed} steps completed</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {execution.has_full_report && (
                    <span className="text-green-600 text-sm font-medium">Report Available</span>
                  )}
                  <button className="text-blue-600 hover:text-blue-800 font-medium">
                    View Report →
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Report Modal */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-lg p-6 max-w-6xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            {loadingReport ? (
              <div className="flex items-center justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-gray-600">Generating report...</span>
              </div>
            ) : (
              <>
                {/* Header */}
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-1">
                      {selectedReport.playbook_name} - Execution Report
                    </h2>
                    <div className="flex items-center gap-3 text-sm text-gray-600">
                      <span className="font-medium">{selectedReport.account_name}</span>
                      <span>•</span>
                      <span>{new Date(selectedReport.report_generated_at).toLocaleString()}</span>
                      <span>•</span>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        selectedReport.status === 'Completed' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                      }`}>
                        {selectedReport.status}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedReport(null)}
                    className="text-gray-400 hover:text-gray-600 text-2xl"
                  >
                    ×
                  </button>
                </div>

                {/* Executive Summary */}
                <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                    <Target className="h-5 w-5 text-blue-600" />
                    Executive Summary
                  </h3>
                  <p className="text-gray-700 leading-relaxed">{selectedReport.executive_summary}</p>
                </div>

                {/* RACI Matrix */}
                {selectedReport.raci_matrix && (
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <Users className="h-5 w-5 text-purple-600" />
                      RACI Matrix
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Activity</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">CSM</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Product Manager</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Support Lead</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Executive Sponsor</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {Object.entries(selectedReport.raci_matrix).map(([activity, roles]) => (
                            <tr key={activity}>
                              <td className="px-4 py-3 text-sm font-medium text-gray-900">{activity}</td>
                              <td className="px-4 py-3 text-sm">
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  roles['CSM'] === 'Responsible' ? 'bg-blue-100 text-blue-800' :
                                  roles['CSM'] === 'Accountable' ? 'bg-purple-100 text-purple-800' :
                                  roles['CSM'] === 'Consulted' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-gray-100 text-gray-800'
                                }`}>
                                  {roles['CSM']}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-sm">
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  roles['Product Manager'] === 'Responsible' ? 'bg-blue-100 text-blue-800' :
                                  roles['Product Manager'] === 'Accountable' ? 'bg-purple-100 text-purple-800' :
                                  roles['Product Manager'] === 'Consulted' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-gray-100 text-gray-800'
                                }`}>
                                  {roles['Product Manager']}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-sm">
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  roles['Support Lead'] === 'Responsible' ? 'bg-blue-100 text-blue-800' :
                                  roles['Support Lead'] === 'Accountable' ? 'bg-purple-100 text-purple-800' :
                                  roles['Support Lead'] === 'Consulted' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-gray-100 text-gray-800'
                                }`}>
                                  {roles['Support Lead']}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-sm">
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  roles['Executive Sponsor'] === 'Responsible' ? 'bg-blue-100 text-blue-800' :
                                  roles['Executive Sponsor'] === 'Accountable' ? 'bg-purple-100 text-purple-800' :
                                  roles['Executive Sponsor'] === 'Consulted' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-gray-100 text-gray-800'
                                }`}>
                                  {roles['Executive Sponsor'] || '-'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Outcomes Achieved */}
                {selectedReport.outcomes_achieved && (
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-green-600" />
                      Outcomes Achieved
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {Object.entries(selectedReport.outcomes_achieved).map(([key, outcome]: [string, any]) => (
                        <div key={key} className="p-4 border border-gray-200 rounded-lg">
                          <h4 className="font-medium text-gray-900 mb-2">
                            {key.replace(/_/g, ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                          </h4>
                          <div className="space-y-1 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-600">Baseline:</span>
                              <span className="font-medium">{outcome.baseline}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Current:</span>
                              <span className="font-medium text-green-600">{outcome.current}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Improvement:</span>
                              <span className="font-semibold text-green-700">{outcome.improvement}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Target:</span>
                              <span>{outcome.target}</span>
                            </div>
                            <div className="mt-2">
                              <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                                outcome.status === 'Exceeded' ? 'bg-green-100 text-green-800' :
                                outcome.status === 'Achieved' ? 'bg-blue-100 text-blue-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {outcome.status}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Themes Discovered (VoC Sprint) */}
                {selectedReport.themes_discovered && (
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">Themes Discovered</h3>
                    <div className="space-y-3">
                      {selectedReport.themes_discovered.map((theme, idx) => (
                        <div key={idx} className="p-4 border border-gray-200 rounded-lg">
                          <div className="flex items-start justify-between mb-2">
                            <h4 className="font-medium text-gray-900">{theme.theme}</h4>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              theme.impact === 'High' ? 'bg-red-100 text-red-800' :
                              theme.impact === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {theme.impact} Impact
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mb-2">{theme.evidence}</p>
                          <div className="space-y-1">
                            {theme.customer_quotes.map((quote: string, qIdx: number) => (
                              <p key={qIdx} className="text-xs text-gray-500 italic pl-4 border-l-2 border-gray-300">
                                {quote}
                              </p>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Committed Fixes (VoC Sprint) */}
                {selectedReport.committed_fixes && (
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">Committed Fixes</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {selectedReport.committed_fixes.map((fix, idx) => (
                        <div key={idx} className="p-4 border-2 border-gray-200 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className={`px-2 py-1 rounded text-xs font-bold ${
                              fix.type === 'Now' ? 'bg-red-100 text-red-800' :
                              fix.type === 'Next Release' ? 'bg-blue-100 text-blue-800' :
                              'bg-green-100 text-green-800'
                            }`}>
                              {fix.type}
                            </span>
                            <span className={`text-xs font-medium ${
                              fix.status === 'Implemented' ? 'text-green-600' :
                              fix.status === 'In Progress' ? 'text-blue-600' :
                              'text-gray-600'
                            }`}>
                              {fix.status}
                            </span>
                          </div>
                          <h4 className="font-medium text-gray-900 mb-2">{fix.fix}</h4>
                          <div className="text-xs text-gray-600 space-y-1">
                            <p><strong>Owner:</strong> {fix.owner}</p>
                            <p><strong>Timeline:</strong> {fix.timeline}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Exit Criteria */}
                {selectedReport.exit_criteria && (
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <CheckCircle className="h-5 w-5 text-green-600" />
                      Exit Criteria
                    </h3>
                    <div className="space-y-2">
                      {selectedReport.exit_criteria.map((criterion, idx) => (
                        <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                          <div className="mt-0.5">
                            {criterion.status === 'Met' ? (
                              <CheckCircle className="h-5 w-5 text-green-600" />
                            ) : (
                              <XCircle className="h-5 w-5 text-gray-400" />
                            )}
                          </div>
                          <div className="flex-1">
                            <p className="font-medium text-gray-900">{criterion.criteria}</p>
                            <p className="text-sm text-gray-600 mt-1">{criterion.evidence}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Next Steps */}
                {selectedReport.next_steps && selectedReport.next_steps.length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">Next Steps</h3>
                    <ul className="space-y-2">
                      {selectedReport.next_steps.map((step, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-blue-600 font-bold">→</span>
                          <span className="text-gray-700">{step}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                  <button
                    onClick={() => setSelectedReport(null)}
                    className="px-4 py-2 text-gray-600 hover:text-gray-800"
                  >
                    Close
                  </button>
                  <button
                    onClick={() => alert('Export functionality coming soon!')}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    <Download className="h-4 w-4" />
                    Export Report
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
