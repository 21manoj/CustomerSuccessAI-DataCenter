/**
 * Playbooks Component
 * 
 * React component for displaying and managing playbooks
 * Uses the playbooks library from src/lib
 */

import React, { useState, useEffect } from 'react';
import { 
  usePlaybooks,
  playbooks as allPlaybooks,
  getPlaybookById
} from '../lib';
import type { PlaybookDefinition, PlaybookStatus } from '../lib';

interface PlaybooksProps {
  customerId: number;
}

interface Account {
  account_id: number;
  account_name: string;
  revenue: number;
  account_status: string;
  industry?: string;
  region?: string;
}

interface AccountRecommendation extends Account {
  needed: boolean;
  urgency_score: number;
  urgency_level: string;
  reasons: string[];
  metrics?: Record<string, any>;
}

export default function Playbooks({ customerId }: PlaybooksProps) {
  const [selectedPlaybook, setSelectedPlaybook] = useState<PlaybookDefinition | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountRecommendations, setAccountRecommendations] = useState<AccountRecommendation[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [showAccountSelector, setShowAccountSelector] = useState(false);
  const [playbookToStart, setPlaybookToStart] = useState<string | null>(null);
  
  const { 
    executions, 
    loading: executionsLoading, 
    startPlaybook, 
    executeStep,
    error: executionsError 
  } = usePlaybooks(customerId);
  
  // Local state for executions to allow real-time updates
  const [localExecutions, setLocalExecutions] = useState(executions);
  
  useEffect(() => {
    setLocalExecutions(executions);
  }, [executions]);
  
  // Use the imported playbooks directly
  const playbooks = allPlaybooks;
  const playbooksLoading = false;
  const playbooksError = null;
  const getPlaybook = getPlaybookById;

  // Fetch accounts on mount
  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const response = await fetch('/api/accounts', {
          headers: { 'X-Customer-ID': customerId.toString() }
        });
        if (response.ok) {
          const data = await response.json();
          // API returns array directly, not {accounts: [...]}
          const accountsList = Array.isArray(data) ? data : (data.accounts || []);
          setAccounts(accountsList);
          console.log('Loaded accounts:', accountsList.length);
        }
      } catch (error) {
        console.error('Failed to fetch accounts:', error);
      } finally {
        setLoadingAccounts(false);
      }
    };
    fetchAccounts();
  }, [customerId]);

  const handleStartPlaybookClick = async (playbookId: string) => {
    setPlaybookToStart(playbookId);
    setShowAccountSelector(true);
    setLoadingRecommendations(true);
    
    try {
      // Get playbook triggers
      const playbook = playbooks.find(p => p.id === playbookId);
      const triggerStep = playbook?.steps.find(s => s.id.includes('trigger-check'));
      const triggers = triggerStep?.data?.triggers || {};
      
      // Fetch recommendations
      const response = await fetch(`/api/playbooks/recommendations/${playbookId}`, {
        method: 'POST',
        headers: {
          'X-Customer-ID': customerId.toString(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ triggers })
      });
      
      if (response.ok) {
        const data = await response.json();
        setAccountRecommendations(data.recommendations || []);
      }
    } catch (error) {
      console.error('Failed to fetch recommendations:', error);
    } finally {
      setLoadingRecommendations(false);
    }
  };

  const handleAccountSelected = async (account: Account | null) => {
    if (!playbookToStart) return;
    
    setShowAccountSelector(false);
    await handleStartPlaybook(
      playbookToStart, 
      account?.account_id, 
      account?.account_name
    );
    setPlaybookToStart(null);
    setSelectedAccount(null);
  };

  const handleStartPlaybook = async (playbookId: string, accountId?: number, accountName?: string) => {
    try {
      const context = {
        customerId,
        accountId,
        accountName,
        userId: 1, // This should come from session
        userName: 'Current User', // This should come from session
        timestamp: new Date().toISOString(),
        metadata: {
          priority: 'normal',
          notes: `Started from Playbooks tab${accountName ? ` for ${accountName}` : ''}`
        }
      };
      
      const execution = await startPlaybook(playbookId, context);
      
      // Add to local executions at the top
      setLocalExecutions(prev => [execution, ...prev]);
      
      // Show success message with account name
      const playbookName = playbooks.find(p => p.id === playbookId)?.name || playbookId;
      const message = accountName 
        ? `Started ${playbookName} for ${accountName}` 
        : `Started ${playbookName} for all accounts`;
      alert(message);
    } catch (error) {
      console.error('Failed to start playbook:', error);
      alert('Failed to start playbook. Please try again.');
    }
  };

  const handleExecuteStep = async (executionId: string, stepId: string) => {
    try {
      await executeStep(executionId, stepId, {
        executedAt: new Date().toISOString(),
        notes: 'Step executed from UI'
      });
      
      // Update local executions to reflect step completion
      setLocalExecutions(prev => prev.map(exec => {
        if (exec.id === executionId) {
          const newResults = [...(exec.results || []), {
            stepId,
            status: 'completed' as PlaybookStatus,
            completedAt: new Date().toISOString(),
            data: {}
          }];
          return { ...exec, results: newResults };
        }
        return exec;
      }));
      
      // Trigger incremental report generation in background
      fetch(`/api/playbooks/executions/${executionId}/report`, {
        headers: { 'X-Customer-ID': customerId.toString() }
      }).catch(err => console.log('Report generation queued'));
      
    } catch (error) {
      console.error('Failed to execute step:', error);
      alert('Failed to execute step. Please try again.');
    }
  };

  const handleDeleteExecution = async (executionId: string) => {
    if (!window.confirm('Are you sure you want to delete this playbook execution?')) {
      return;
    }
    
    try {
      const response = await fetch(`/api/playbooks/executions/${executionId}`, {
        method: 'DELETE',
        headers: { 'X-Customer-ID': customerId.toString() }
      });
      
      if (response.ok) {
        // Remove from local state immediately (no page refresh)
        setLocalExecutions(prev => prev.filter(e => e.id !== executionId));
      } else {
        throw new Error('Failed to delete execution');
      }
    } catch (error) {
      console.error('Failed to delete execution:', error);
      alert('Failed to delete execution. Please try again.');
    }
  };

  if (playbooksLoading || executionsLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading playbooks...</span>
      </div>
    );
  }

  if (playbooksError || executionsError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex">
          <div className="text-red-600 mr-2">❌</div>
          <div>
            <h3 className="text-red-800 font-medium">Error Loading Playbooks</h3>
            <p className="text-red-700 text-sm mt-1">
              {playbooksError || executionsError}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Customer Success Playbooks</h2>
        <p className="text-gray-600">
          Strategic playbooks to drive customer success outcomes. Choose a playbook to get started.
        </p>
      </div>

      {/* Playbooks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {playbooks.map((playbook) => (
          <div 
            key={playbook.id} 
            className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => setSelectedPlaybook(playbook)}
          >
            <div className="flex items-center mb-4">
              <div className="text-3xl mr-3">{playbook.icon}</div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{playbook.name}</h3>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-${playbook.color}-100 text-${playbook.color}-800`}>
                  {playbook.estimatedDuration} min
                </span>
              </div>
            </div>
            
            <p className="text-gray-600 text-sm mb-4">{playbook.description}</p>
            
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">
                {playbook.steps.length} steps
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleStartPlaybookClick(playbook.id);
                }}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Start Playbook
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Active Executions */}
      {localExecutions.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Active Executions</h3>
          <div className="space-y-4">
            {localExecutions.map((execution) => {
              const playbook = getPlaybook(execution.playbookId);
              if (!playbook) return null;
              
              // Get trigger values from first step data
              const triggerStep = playbook.steps.find(s => s.id.includes('trigger-check'));
              const triggerValues = triggerStep?.data?.triggers || {};
              
              return (
                <div key={execution.id} className="border border-gray-200 rounded-lg p-4 bg-white shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center flex-1">
                      <span className="text-2xl mr-3">{playbook.icon}</span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-gray-900">{playbook.name}</h4>
                          {execution.context?.accountName && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
                              {execution.context.accountName}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          Started: {new Date(execution.startedAt).toLocaleString()} • ID: {execution.id.substring(0, 8)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        execution.status === 'completed' ? 'bg-green-100 text-green-800' :
                        execution.status === 'in-progress' ? 'bg-blue-100 text-blue-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {execution.status}
                      </span>
                      <button
                        onClick={() => handleDeleteExecution(execution.id)}
                        className="text-red-600 hover:text-red-800 hover:bg-red-50 p-1 rounded"
                        title="Delete execution"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  
                  {/* Trigger Values Display */}
                  {Object.keys(triggerValues).length > 0 && (
                    <div className="mb-3 p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs font-medium text-gray-700 mb-2">Trigger Conditions:</p>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(triggerValues).map(([key, value]) => (
                          <span key={key} className="inline-flex items-center px-2 py-1 bg-white border border-gray-200 rounded text-xs text-gray-700">
                            {key.replace(/_/g, ' ').replace(/threshold/gi, '').trim()}: <strong className="ml-1">{String(value)}</strong>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="mb-3">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                      <span>Progress</span>
                      <span>{execution.results.length} / {playbook.steps.length} steps</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${(execution.results.length / playbook.steps.length) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="flex space-x-2">
                    {playbook.steps.map((step) => (
                      <button
                        key={step.id}
                        onClick={() => handleExecuteStep(execution.id, step.id)}
                        className={`px-3 py-1 text-xs rounded-full ${
                          execution.results.some(r => r.stepId === step.id)
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                        disabled={execution.results.some(r => r.stepId === step.id)}
                      >
                        {step.title}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Account Selector Modal */}
      {showAccountSelector && playbookToStart && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-gray-900">
                Select Account for {playbooks.find(p => p.id === playbookToStart)?.name}
              </h3>
              <button
                onClick={() => {
                  setShowAccountSelector(false);
                  setPlaybookToStart(null);
                }}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            
            <p className="text-gray-600 mb-4">
              Choose a specific account or start for all accounts:
            </p>
            
            {loadingAccounts || loadingRecommendations ? (
              <div className="flex items-center justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-gray-600">
                  {loadingAccounts ? 'Loading accounts...' : 'Analyzing accounts...'}
                </span>
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto mb-4">
                {/* Summary of recommendations */}
                {accountRecommendations.length > 0 && (
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg mb-2">
                    <p className="text-sm text-blue-800">
                      <strong>{accountRecommendations.filter(a => a.needed).length}</strong> of {accountRecommendations.length} accounts need this playbook
                      <span className="ml-2">
                        (Critical: {accountRecommendations.filter(a => a.urgency_level === 'Critical').length}, 
                        High: {accountRecommendations.filter(a => a.urgency_level === 'High').length})
                      </span>
                    </p>
                  </div>
                )}
                
                {/* Option to run for all accounts */}
                <div
                  onClick={() => handleAccountSelected(null)}
                  className="p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">All Accounts</p>
                      <p className="text-sm text-gray-500">Run playbook for all {accounts.length} accounts</p>
                    </div>
                    <div className="text-blue-600 font-semibold">→</div>
                  </div>
                </div>
                
                {/* Individual account options with recommendations */}
                {(accountRecommendations.length > 0 ? accountRecommendations : accounts).map((account) => {
                  const recommendation = accountRecommendations.find(r => r.account_id === account.account_id);
                  const needed = recommendation?.needed || false;
                  const urgencyLevel = recommendation?.urgency_level || 'Low';
                  const reasons = recommendation?.reasons || [];
                  
                  return (
                    <div
                      key={account.account_id}
                      onClick={() => handleAccountSelected(account)}
                      className={`p-4 border-2 rounded-lg hover:border-blue-500 hover:bg-blue-50 cursor-pointer transition-colors ${
                        needed ? (
                          urgencyLevel === 'Critical' ? 'border-red-300 bg-red-50' :
                          urgencyLevel === 'High' ? 'border-orange-300 bg-orange-50' :
                          'border-yellow-300 bg-yellow-50'
                        ) : 'border-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-gray-900">{account.account_name}</p>
                            {needed && (
                              <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-bold ${
                                urgencyLevel === 'Critical' ? 'bg-red-600 text-white' :
                                urgencyLevel === 'High' ? 'bg-orange-600 text-white' :
                                'bg-yellow-600 text-white'
                              }`}>
                                🎯 {urgencyLevel.toUpperCase()} - NEEDED
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mt-1">
                            {account.industry} • {account.region} • ${(account.revenue || 0).toLocaleString()} revenue
                          </p>
                          {needed && reasons.length > 0 && (
                            <div className="mt-2 space-y-1">
                              {reasons.slice(0, 2).map((reason, idx) => (
                                <p key={idx} className="text-xs text-gray-700">
                                  • {reason}
                                </p>
                              ))}
                              {reasons.length > 2 && (
                                <p className="text-xs text-gray-500 italic">+{reasons.length - 2} more reasons</p>
                              )}
                            </div>
                          )}
                          <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium mt-2 ${
                            account.account_status === 'At Risk' ? 'bg-red-100 text-red-800' :
                            account.account_status === 'Active' ? 'bg-green-100 text-green-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {account.account_status}
                          </span>
                        </div>
                        <div className="text-blue-600 font-semibold ml-4">→</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowAccountSelector(false);
                  setPlaybookToStart(null);
                }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Playbook Details Modal */}
      {selectedPlaybook && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-gray-900">
                {selectedPlaybook.icon} {selectedPlaybook.name}
              </h3>
              <button
                onClick={() => setSelectedPlaybook(null)}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            
            <p className="text-gray-600 mb-6">{selectedPlaybook.description}</p>
            
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Details</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>Duration: {selectedPlaybook.estimatedDuration} minutes</li>
                  <li>Steps: {selectedPlaybook.steps.length}</li>
                  <li>Category: {selectedPlaybook.category}</li>
                  <li>Version: {selectedPlaybook.version}</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Prerequisites</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  {selectedPlaybook.prerequisites?.map((prereq, index) => (
                    <li key={index}>• {prereq}</li>
                  ))}
                </ul>
              </div>
            </div>
            
            <div className="mb-6">
              <h4 className="font-medium text-gray-900 mb-3">Steps</h4>
              <div className="space-y-3">
                {selectedPlaybook.steps.map((step, index) => (
                  <div key={step.id} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                    <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <h5 className="font-medium text-gray-900">{step.title}</h5>
                      <p className="text-sm text-gray-600 mt-1">{step.description}</p>
                      <div className="flex items-center mt-2 space-x-2">
                        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800">
                          {step.type}
                        </span>
                        <span className="text-xs text-gray-500">
                          {step.estimatedTime} min
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setSelectedPlaybook(null)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Close
              </button>
              <button
                onClick={() => {
                  handleStartPlaybook(selectedPlaybook.id);
                  setSelectedPlaybook(null);
                }}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Start Playbook
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
