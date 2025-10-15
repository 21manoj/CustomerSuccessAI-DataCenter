/**
 * React Hooks for Playbooks
 * 
 * Custom hooks for managing playbook state and operations
 */

import { useState, useEffect, useCallback } from 'react';
import { PlaybookDefinition, PlaybookExecution, PlaybookContext, PlaybookStatus } from './types';
import { PlaybookManager } from './playbook-manager';
import { playbooks, getPlaybookById } from './playbooks';

// Global playbook manager instance
const playbookManager = new PlaybookManager();

/**
 * Hook for managing playbook executions
 */
export function usePlaybooks(customerId: number) {
  const [executions, setExecutions] = useState<PlaybookExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load executions on mount
  useEffect(() => {
    const loadExecutions = async () => {
      try {
        setLoading(true);
        await playbookManager.loadExecutions(customerId);
        const customerExecutions = playbookManager.getCustomerExecutions(customerId);
        setExecutions(customerExecutions);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load executions');
      } finally {
        setLoading(false);
      }
    };

    if (customerId) {
      loadExecutions();
    }
  }, [customerId]);

  // Start new playbook
  const startPlaybook = useCallback(async (
    playbookId: string,
    context: PlaybookContext
  ): Promise<PlaybookExecution> => {
    try {
      const execution = await playbookManager.startPlaybook(playbookId, context);
      setExecutions(prev => [...prev, execution]);
      return execution;
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to start playbook');
    }
  }, []);

  // Update execution status
  const updateExecutionStatus = useCallback(async (
    executionId: string,
    status: PlaybookStatus
  ): Promise<void> => {
    try {
      await playbookManager.updateExecutionStatus(executionId, status);
      setExecutions(prev => 
        prev.map(exec => 
          exec.id === executionId ? { ...exec, status } : exec
        )
      );
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to update status');
    }
  }, []);

  // Execute step
  const executeStep = useCallback(async (
    executionId: string,
    stepId: string,
    data?: Record<string, any>
  ) => {
    try {
      const result = await playbookManager.executeStep(executionId, stepId, data);
      setExecutions(prev => 
        prev.map(exec => 
          exec.id === executionId 
            ? { ...exec, results: [...exec.results, result] }
            : exec
        )
      );
      return result;
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to execute step');
    }
  }, []);

  return {
    executions,
    loading,
    error,
    startPlaybook,
    updateExecutionStatus,
    executeStep,
    playbooks
  };
}

/**
 * Hook for managing a single playbook execution
 */
export function usePlaybookExecution(executionId: string) {
  const [execution, setExecution] = useState<PlaybookExecution | null>(null);
  const [playbook, setPlaybook] = useState<PlaybookDefinition | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!executionId) return;

    const loadExecution = () => {
      try {
        const exec = playbookManager.getExecution(executionId);
        if (exec) {
          setExecution(exec);
          const pb = getPlaybookById(exec.playbookId);
          setPlaybook(pb || null);
          setError(null);
        } else {
          setError('Execution not found');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load execution');
      } finally {
        setLoading(false);
      }
    };

    loadExecution();
  }, [executionId]);

  // Execute step
  const executeStep = useCallback(async (
    stepId: string,
    data?: Record<string, any>
  ) => {
    if (!execution) throw new Error('No execution found');

    try {
      const result = await playbookManager.executeStep(execution.id, stepId, data);
      setExecution(prev => prev ? {
        ...prev,
        results: [...prev.results, result]
      } : null);
      return result;
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to execute step');
    }
  }, [execution]);

  // Update status
  const updateStatus = useCallback(async (status: PlaybookStatus) => {
    if (!execution) throw new Error('No execution found');

    try {
      await playbookManager.updateExecutionStatus(execution.id, status);
      setExecution(prev => prev ? { ...prev, status } : null);
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to update status');
    }
  }, [execution]);

  return {
    execution,
    playbook,
    loading,
    error,
    executeStep,
    updateStatus
  };
}

/**
 * Hook for playbook definitions
 */
export function usePlaybookDefinitions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get playbook by ID
  const getPlaybook = useCallback((id: string): PlaybookDefinition | undefined => {
    return getPlaybookById(id);
  }, []);

  // Get playbooks by category
  const getPlaybooksByCategory = useCallback((category: string): PlaybookDefinition[] => {
    return playbooks.filter(pb => pb.category === category);
  }, []);

  // Get playbooks by tag
  const getPlaybooksByTag = useCallback((tag: string): PlaybookDefinition[] => {
    return playbooks.filter(pb => pb.tags.includes(tag));
  }, []);

  return {
    playbooks,
    getPlaybook,
    getPlaybooksByCategory,
    getPlaybooksByTag,
    loading,
    error
  };
}
