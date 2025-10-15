/**
 * Playbook Manager
 * 
 * Core class for managing playbook execution, state, and API interactions
 */

import { Playbook, PlaybookExecution, PlaybookContext, PlaybookStatus, PlaybookResult } from './types';

export class PlaybookManager {
  private executions: Map<string, PlaybookExecution> = new Map();

  /**
   * Start a new playbook execution
   */
  async startPlaybook(
    playbookId: string, 
    context: PlaybookContext
  ): Promise<PlaybookExecution> {
    const execution: PlaybookExecution = {
      id: this.generateExecutionId(),
      playbookId,
      accountId: context.accountId,
      customerId: context.customerId,
      status: 'in-progress',
      startedAt: new Date().toISOString(),
      results: [],
      context: {
        customerId: context.customerId,
        accountId: context.accountId,
        accountName: context.accountName,
        userId: context.userId,
        userName: context.userName,
        timestamp: context.timestamp,
        metadata: context.metadata
      },
      metadata: {
        ...context.metadata,
        userId: context.userId,
        userName: context.userName
      }
    };

    this.executions.set(execution.id, execution);
    
    // Save to backend
    await this.saveExecution(execution);
    
    return execution;
  }

  /**
   * Execute a specific step in a playbook
   */
  async executeStep(
    executionId: string, 
    stepId: string, 
    data?: Record<string, any>
  ): Promise<PlaybookResult> {
    const execution = this.executions.get(executionId);
    if (!execution) {
      throw new Error(`Execution ${executionId} not found`);
    }

    // Create step result
    const result: PlaybookResult = {
      stepId,
      status: 'completed',
      completedAt: new Date().toISOString(),
      data,
      notes: ''
    };

    // Update execution
    execution.results.push(result);
    await this.saveExecution(execution);

    return result;
  }

  /**
   * Get playbook execution by ID
   */
  getExecution(executionId: string): PlaybookExecution | undefined {
    return this.executions.get(executionId);
  }

  /**
   * Get all executions for a customer
   */
  getCustomerExecutions(customerId: number): PlaybookExecution[] {
    return Array.from(this.executions.values())
      .filter(execution => execution.customerId === customerId);
  }

  /**
   * Update execution status
   */
  async updateExecutionStatus(
    executionId: string, 
    status: PlaybookStatus
  ): Promise<void> {
    const execution = this.executions.get(executionId);
    if (!execution) {
      throw new Error(`Execution ${executionId} not found`);
    }

    execution.status = status;
    if (status === 'completed') {
      execution.completedAt = new Date().toISOString();
    }

    await this.saveExecution(execution);
  }

  /**
   * Load executions from backend
   */
  async loadExecutions(customerId: number): Promise<void> {
    try {
      const response = await fetch(`/api/playbooks/executions?customer_id=${customerId}`, {
        headers: {
          'X-Customer-ID': customerId.toString(),
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        data.executions.forEach((execution: PlaybookExecution) => {
          this.executions.set(execution.id, execution);
        });
      }
    } catch (error) {
      console.error('Failed to load executions:', error);
    }
  }

  /**
   * Save execution to backend
   */
  private async saveExecution(execution: PlaybookExecution): Promise<void> {
    try {
      const response = await fetch('/api/playbooks/executions', {
        method: 'POST',
        headers: {
          'X-Customer-ID': execution.customerId.toString(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(execution)
      });

      if (!response.ok) {
        throw new Error(`Failed to save execution: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Failed to save execution:', error);
      throw error;
    }
  }

  /**
   * Generate unique execution ID
   */
  private generateExecutionId(): string {
    return `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get execution progress percentage
   */
  getExecutionProgress(execution: PlaybookExecution): number {
    if (execution.status === 'completed') return 100;
    if (execution.status === 'not-started') return 0;
    
    const totalSteps = execution.metadata.totalSteps || 1;
    const completedSteps = execution.results.filter(r => r.status === 'completed').length;
    
    return Math.round((completedSteps / totalSteps) * 100);
  }

  /**
   * Get current step for execution
   */
  getCurrentStep(execution: PlaybookExecution): string | null {
    if (execution.status === 'completed') return null;
    
    const completedStepIds = execution.results
      .filter(r => r.status === 'completed')
      .map(r => r.stepId);
    
    // This would need to be enhanced with actual playbook step logic
    return execution.currentStep || null;
  }
}
