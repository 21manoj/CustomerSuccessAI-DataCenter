/**
 * Playbooks Library - Main Export File
 * 
 * This file exports all playbook-related functionality
 * Import from here: import { PlaybookManager, playbooks } from '../lib'
 */

// Export main playbook manager
export { PlaybookManager } from './playbook-manager';

// Export playbook definitions
export { playbooks, getPlaybookById, getPlaybooksByCategory, getPlaybooksByTag } from './playbooks';

// Export playbook types
export type {
  Playbook,
  PlaybookDefinition,
  PlaybookStep,
  PlaybookExecution,
  PlaybookResult,
  PlaybookStatus,
  PlaybookContext
} from './types';

// Export utilities
export { 
  PlaybookUtils,
  PlaybookValidator,
  PlaybookRenderer 
} from './utils';

// Export hooks (if you have React hooks)
export { usePlaybooks, usePlaybookExecution } from './hooks';
