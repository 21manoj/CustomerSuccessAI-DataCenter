/**
 * Playbooks Utilities
 * 
 * Helper functions and utilities for playbook operations
 */

import { PlaybookDefinition, PlaybookExecution, PlaybookStep, PlaybookStatus } from './types';

export class PlaybookUtils {
  /**
   * Calculate estimated completion time for a playbook
   */
  static calculateEstimatedTime(playbook: PlaybookDefinition): number {
    return playbook.steps.reduce((total, step) => total + (step.estimatedTime || 0), 0);
  }

  /**
   * Get playbook progress percentage
   */
  static getProgressPercentage(execution: PlaybookExecution): number {
    if (execution.status === 'completed') return 100;
    if (execution.status === 'not-started') return 0;
    
    const totalSteps = execution.metadata.totalSteps || 1;
    const completedSteps = execution.results.filter(r => r.status === 'completed').length;
    
    return Math.round((completedSteps / totalSteps) * 100);
  }

  /**
   * Check if a step can be executed based on dependencies
   */
  static canExecuteStep(step: PlaybookStep, execution: PlaybookExecution): boolean {
    if (!step.dependencies || step.dependencies.length === 0) {
      return true;
    }

    const completedStepIds = execution.results
      .filter(r => r.status === 'completed')
      .map(r => r.stepId);

    return step.dependencies.every(depId => completedStepIds.includes(depId));
  }

  /**
   * Get next executable steps
   */
  static getNextExecutableSteps(playbook: PlaybookDefinition, execution: PlaybookExecution): PlaybookStep[] {
    const completedStepIds = execution.results
      .filter(r => r.status === 'completed')
      .map(r => r.stepId);

    return playbook.steps.filter(step => {
      if (completedStepIds.includes(step.id)) return false;
      return this.canExecuteStep(step, execution);
    });
  }

  /**
   * Format duration in minutes to human-readable format
   */
  static formatDuration(minutes: number): string {
    if (minutes < 60) {
      return `${minutes}m`;
    }
    
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    
    if (remainingMinutes === 0) {
      return `${hours}h`;
    }
    
    return `${hours}h ${remainingMinutes}m`;
  }

  /**
   * Get status color for UI
   */
  static getStatusColor(status: PlaybookStatus): string {
    switch (status) {
      case 'not-started': return 'gray';
      case 'in-progress': return 'blue';
      case 'completed': return 'green';
      case 'failed': return 'red';
      case 'paused': return 'yellow';
      case 'cancelled': return 'gray';
      default: return 'gray';
    }
  }

  /**
   * Get status icon for UI
   */
  static getStatusIcon(status: PlaybookStatus): string {
    switch (status) {
      case 'not-started': return '⏸️';
      case 'in-progress': return '🔄';
      case 'completed': return '✅';
      case 'failed': return '❌';
      case 'paused': return '⏸️';
      case 'cancelled': return '🚫';
      default: return '❓';
    }
  }
}

export class PlaybookValidator {
  /**
   * Validate playbook definition
   */
  static validatePlaybook(playbook: PlaybookDefinition): string[] {
    const errors: string[] = [];

    if (!playbook.id) errors.push('Playbook ID is required');
    if (!playbook.name) errors.push('Playbook name is required');
    if (!playbook.description) errors.push('Playbook description is required');
    if (!playbook.steps || playbook.steps.length === 0) {
      errors.push('Playbook must have at least one step');
    }

    // Validate steps
    playbook.steps?.forEach((step, index) => {
      if (!step.id) errors.push(`Step ${index + 1}: ID is required`);
      if (!step.title) errors.push(`Step ${index + 1}: Title is required`);
      if (!step.description) errors.push(`Step ${index + 1}: Description is required`);
    });

    return errors;
  }

  /**
   * Validate execution context
   */
  static validateContext(context: any): string[] {
    const errors: string[] = [];

    if (!context.customerId) errors.push('Customer ID is required');
    if (!context.userId) errors.push('User ID is required');
    if (!context.userName) errors.push('User name is required');

    return errors;
  }
}

export class PlaybookRenderer {
  /**
   * Generate HTML description from markdown-like text
   */
  static renderDescription(text: string): string {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  }

  /**
   * Generate step list HTML
   */
  static renderStepList(steps: PlaybookStep[]): string {
    return steps
      .map((step, index) => `
        <div class="playbook-step">
          <div class="step-number">${index + 1}</div>
          <div class="step-content">
            <h4>${step.title}</h4>
            <p>${this.renderDescription(step.description)}</p>
            <div class="step-meta">
              <span class="step-type">${step.type}</span>
              <span class="step-duration">${PlaybookUtils.formatDuration(step.estimatedTime || 0)}</span>
            </div>
          </div>
        </div>
      `)
      .join('');
  }

  /**
   * Generate progress bar HTML
   */
  static renderProgressBar(percentage: number, status: PlaybookStatus): string {
    const color = PlaybookUtils.getStatusColor(status);
    return `
      <div class="progress-bar">
        <div class="progress-fill" style="width: ${percentage}%; background-color: var(--${color}-500);"></div>
        <span class="progress-text">${percentage}%</span>
      </div>
    `;
  }
}
