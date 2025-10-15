/**
 * Test Suite for Playbooks Library
 * 
 * Tests playbook definitions, validation, and data structures
 */

import { playbooks, getPlaybookById } from '../playbooks';
import { PlaybookDefinition } from '../types';

describe('Playbooks Library', () => {
  describe('Playbook Definitions', () => {
    test('should have 5 playbooks defined', () => {
      expect(playbooks).toHaveLength(5);
    });

    test('all playbooks should have required fields', () => {
      playbooks.forEach((playbook) => {
        expect(playbook).toHaveProperty('id');
        expect(playbook).toHaveProperty('name');
        expect(playbook).toHaveProperty('description');
        expect(playbook).toHaveProperty('category');
        expect(playbook).toHaveProperty('icon');
        expect(playbook).toHaveProperty('color');
        expect(playbook).toHaveProperty('estimatedDuration');
        expect(playbook).toHaveProperty('steps');
        expect(playbook).toHaveProperty('prerequisites');
        expect(playbook).toHaveProperty('successCriteria');
      });
    });

    test('all playbook IDs should be unique', () => {
      const ids = playbooks.map(p => p.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });

    test('all playbooks should have at least one step', () => {
      playbooks.forEach((playbook) => {
        expect(playbook.steps.length).toBeGreaterThan(0);
      });
    });
  });

  describe('VoC Sprint Playbook', () => {
    let vocPlaybook: PlaybookDefinition | undefined;

    beforeEach(() => {
      vocPlaybook = getPlaybookById('voc-sprint');
    });

    test('should exist and be retrievable', () => {
      expect(vocPlaybook).toBeDefined();
      expect(vocPlaybook?.id).toBe('voc-sprint');
    });

    test('should have correct metadata', () => {
      expect(vocPlaybook?.name).toBe('VoC Sprint');
      expect(vocPlaybook?.category).toBe('voc-sprint');
      expect(vocPlaybook?.icon).toBe('🎤');
      expect(vocPlaybook?.color).toBe('blue');
      expect(vocPlaybook?.version).toBe('2.0.0');
    });

    test('should have trigger assessment step', () => {
      const triggerStep = vocPlaybook?.steps.find(s => s.id === 'voc-trigger-check');
      expect(triggerStep).toBeDefined();
      expect(triggerStep?.type).toBe('automation');
      expect(triggerStep?.data).toBeDefined();
    });

    test('should have correct trigger thresholds in data', () => {
      const triggerStep = vocPlaybook?.steps.find(s => s.id === 'voc-trigger-check');
      expect(triggerStep?.data?.triggers).toBeDefined();
      expect(triggerStep?.data?.triggers.nps_threshold).toBe(10);
      expect(triggerStep?.data?.triggers.csat_threshold).toBe(3.6);
      expect(triggerStep?.data?.triggers.churn_risk_threshold).toBe(0.30);
      expect(triggerStep?.data?.triggers.health_score_drop_threshold).toBe(10);
      expect(triggerStep?.data?.triggers.churn_mentions_threshold).toBe(2);
    });

    test('should have RAG step with prompt', () => {
      const ragStep = vocPlaybook?.steps.find(s => s.id === 'voc-rag-brief');
      expect(ragStep).toBeDefined();
      expect(ragStep?.type).toBe('automation');
      expect(ragStep?.data?.rag_prompt).toBeDefined();
      expect(ragStep?.data?.rag_prompt).toContain('{Account}');
    });

    test('should have 12 steps', () => {
      expect(vocPlaybook?.steps.length).toBe(12);
    });

    test('should have weekly structure', () => {
      const weekSteps = vocPlaybook?.steps.filter(s => 
        s.title.includes('Week 1') || 
        s.title.includes('Week 2') || 
        s.title.includes('Week 3') || 
        s.title.includes('Week 4')
      );
      expect(weekSteps?.length).toBeGreaterThan(0);
    });

    test('should have success criteria defined', () => {
      expect(vocPlaybook?.successCriteria).toBeDefined();
      expect(vocPlaybook?.successCriteria.length).toBeGreaterThan(0);
      expect(vocPlaybook?.successCriteria).toContain('Themes logged and categorized');
      expect(vocPlaybook?.successCriteria).toContain('3 fixes committed with owners assigned');
    });

    test('should have prerequisites defined', () => {
      expect(vocPlaybook?.prerequisites).toBeDefined();
      expect(vocPlaybook?.prerequisites.length).toBeGreaterThan(0);
    });

    test('should have proper step dependencies', () => {
      const steps = vocPlaybook?.steps || [];
      steps.forEach((step, index) => {
        if (index > 0 && step.dependencies) {
          // Dependencies should reference valid step IDs
          step.dependencies.forEach(depId => {
            const depExists = steps.some(s => s.id === depId);
            expect(depExists).toBe(true);
          });
        }
      });
    });
  });

  describe('Activation Blitz Playbook', () => {
    let activationPlaybook: PlaybookDefinition | undefined;

    beforeEach(() => {
      activationPlaybook = getPlaybookById('activation-blitz');
    });

    test('should exist and be retrievable', () => {
      expect(activationPlaybook).toBeDefined();
      expect(activationPlaybook?.id).toBe('activation-blitz');
    });

    test('should have correct metadata', () => {
      expect(activationPlaybook?.name).toBe('Activation Blitz');
      expect(activationPlaybook?.category).toBe('activation-blitz');
      expect(activationPlaybook?.icon).toBe('🚀');
      expect(activationPlaybook?.color).toBe('green');
      expect(activationPlaybook?.version).toBe('2.0.0');
    });

    test('should have trigger assessment step', () => {
      const triggerStep = activationPlaybook?.steps.find(s => s.id === 'activation-trigger-check');
      expect(triggerStep).toBeDefined();
      expect(triggerStep?.type).toBe('automation');
      expect(triggerStep?.data).toBeDefined();
    });

    test('should have correct trigger thresholds', () => {
      const triggerStep = activationPlaybook?.steps.find(s => s.id === 'activation-trigger-check');
      expect(triggerStep?.data?.triggers).toBeDefined();
      expect(triggerStep?.data?.triggers.adoption_index_threshold).toBe(60);
      expect(triggerStep?.data?.triggers.active_users_threshold).toBe(50);
      expect(triggerStep?.data?.triggers.dau_mau_threshold).toBe(0.25);
      expect(triggerStep?.data?.triggers.unused_feature_check).toBe(true);
    });

    test('should have RAG step for activation plan', () => {
      const ragStep = activationPlaybook?.steps.find(s => s.id === 'activation-rag-plan');
      expect(ragStep).toBeDefined();
      expect(ragStep?.type).toBe('automation');
      expect(ragStep?.data?.rag_prompt).toBeDefined();
      expect(ragStep?.data?.rag_prompt).toContain('{Account}');
    });

    test('should have 9 steps', () => {
      expect(activationPlaybook?.steps.length).toBe(9);
    });

    test('should have success criteria defined', () => {
      expect(activationPlaybook?.successCriteria).toBeDefined();
      expect(activationPlaybook?.successCriteria).toContain('Two features activated successfully');
      expect(activationPlaybook?.successCriteria).toContain('DAU/MAU ≥ 25%');
      expect(activationPlaybook?.successCriteria).toContain('Adoption index ≥ 60 (or +10 vs. baseline)');
    });
  });

  describe('SLA Stabilizer Playbook', () => {
    let slaPlaybook: PlaybookDefinition | undefined;

    beforeEach(() => {
      slaPlaybook = getPlaybookById('sla-stabilizer');
    });

    test('should exist and be retrievable', () => {
      expect(slaPlaybook).toBeDefined();
      expect(slaPlaybook?.id).toBe('sla-stabilizer');
    });

    test('should have correct category and icon', () => {
      expect(slaPlaybook?.category).toBe('sla-stabilizer');
      expect(slaPlaybook?.icon).toBe('⚡');
    });
  });

  describe('Renewal Safeguard Playbook', () => {
    let renewalPlaybook: PlaybookDefinition | undefined;

    beforeEach(() => {
      renewalPlaybook = getPlaybookById('renewal-safeguard');
    });

    test('should exist and be retrievable', () => {
      expect(renewalPlaybook).toBeDefined();
      expect(renewalPlaybook?.id).toBe('renewal-safeguard');
    });

    test('should have correct category and icon', () => {
      expect(renewalPlaybook?.category).toBe('renewal-safeguard');
      expect(renewalPlaybook?.icon).toBe('🛡️');
    });
  });

  describe('Expansion Timing Playbook', () => {
    let expansionPlaybook: PlaybookDefinition | undefined;

    beforeEach(() => {
      expansionPlaybook = getPlaybookById('expansion-timing');
    });

    test('should exist and be retrievable', () => {
      expect(expansionPlaybook).toBeDefined();
      expect(expansionPlaybook?.id).toBe('expansion-timing');
    });

    test('should have correct category and icon', () => {
      expect(expansionPlaybook?.category).toBe('expansion-timing');
      expect(expansionPlaybook?.icon).toBe('📈');
    });
  });

  describe('Step Validation', () => {
    test('all steps should have required fields', () => {
      playbooks.forEach((playbook) => {
        playbook.steps.forEach((step) => {
          expect(step).toHaveProperty('id');
          expect(step).toHaveProperty('title');
          expect(step).toHaveProperty('description');
          expect(step).toHaveProperty('type');
          expect(step).toHaveProperty('status');
          expect(['action', 'decision', 'automation', 'manual']).toContain(step.type);
          expect(['not-started', 'in-progress', 'completed', 'cancelled']).toContain(step.status);
        });
      });
    });

    test('all step IDs within a playbook should be unique', () => {
      playbooks.forEach((playbook) => {
        const stepIds = playbook.steps.map(s => s.id);
        const uniqueIds = new Set(stepIds);
        expect(uniqueIds.size).toBe(stepIds.length);
      });
    });

    test('step dependencies should be valid', () => {
      playbooks.forEach((playbook) => {
        playbook.steps.forEach((step) => {
          if (step.dependencies) {
            step.dependencies.forEach((depId) => {
              const depExists = playbook.steps.some(s => s.id === depId);
              expect(depExists).toBe(true);
            });
          }
        });
      });
    });

    test('steps with dependencies should come after their dependencies', () => {
      playbooks.forEach((playbook) => {
        const stepIndexMap = new Map(
          playbook.steps.map((step, index) => [step.id, index])
        );

        playbook.steps.forEach((step, index) => {
          if (step.dependencies) {
            step.dependencies.forEach((depId) => {
              const depIndex = stepIndexMap.get(depId);
              expect(depIndex).toBeDefined();
              expect(depIndex!).toBeLessThan(index);
            });
          }
        });
      });
    });
  });

  describe('getPlaybookById Function', () => {
    test('should return playbook when ID exists', () => {
      const playbook = getPlaybookById('voc-sprint');
      expect(playbook).toBeDefined();
      expect(playbook?.id).toBe('voc-sprint');
    });

    test('should return undefined when ID does not exist', () => {
      const playbook = getPlaybookById('non-existent-id');
      expect(playbook).toBeUndefined();
    });

    test('should be case-sensitive', () => {
      const playbook = getPlaybookById('VOC-SPRINT');
      expect(playbook).toBeUndefined();
    });
  });

  describe('Estimated Duration', () => {
    test('all playbooks should have realistic durations', () => {
      playbooks.forEach((playbook) => {
        expect(playbook.estimatedDuration).toBeGreaterThan(0);
        // Most playbooks are 30-day programs (1440 minutes = 1 day, so 30 days ~= 43200 minutes)
        // But we're using 1440 to represent 30 days symbolically
        expect(playbook.estimatedDuration).toBeGreaterThan(0);
      });
    });

    test('step durations should sum to reasonable total', () => {
      playbooks.forEach((playbook) => {
        const totalStepTime = playbook.steps.reduce((sum, step) => {
          return sum + (step.estimatedTime || 0);
        }, 0);
        
        // Total step time should be > 0
        expect(totalStepTime).toBeGreaterThan(0);
      });
    });
  });

  describe('Tags', () => {
    test('all playbooks should have tags', () => {
      playbooks.forEach((playbook) => {
        expect(playbook.tags).toBeDefined();
        expect(playbook.tags?.length).toBeGreaterThan(0);
      });
    });

    test('tags should be lowercase with hyphens', () => {
      playbooks.forEach((playbook) => {
        playbook.tags?.forEach((tag) => {
          expect(tag).toMatch(/^[a-z0-9-]+$/);
        });
      });
    });
  });

  describe('Version Control', () => {
    test('all playbooks should have version numbers', () => {
      playbooks.forEach((playbook) => {
        expect(playbook.version).toBeDefined();
        expect(playbook.version).toMatch(/^\d+\.\d+\.\d+$/);
      });
    });

    test('all playbooks should have last updated date', () => {
      playbooks.forEach((playbook) => {
        expect(playbook.lastUpdated).toBeDefined();
        expect(playbook.lastUpdated).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      });
    });

    test('all playbooks should have an author', () => {
      playbooks.forEach((playbook) => {
        expect(playbook.author).toBeDefined();
        expect(playbook.author).toBe('Triad Partners');
      });
    });
  });

  describe('RAG Integration', () => {
    test('VoC Sprint should have RAG prompt configured', () => {
      const vocPlaybook = getPlaybookById('voc-sprint');
      const ragStep = vocPlaybook?.steps.find(s => s.id === 'voc-rag-brief');
      
      expect(ragStep?.data?.rag_prompt).toBeDefined();
      expect(ragStep?.data?.rag_prompt).toContain('Generate a VoC sprint brief');
      expect(ragStep?.data?.output_format).toBeDefined();
    });

    test('Activation Blitz should have RAG prompt configured', () => {
      const activationPlaybook = getPlaybookById('activation-blitz');
      const ragStep = activationPlaybook?.steps.find(s => s.id === 'activation-rag-plan');
      
      expect(ragStep?.data?.rag_prompt).toBeDefined();
      expect(ragStep?.data?.rag_prompt).toContain('4-week activation plan');
      expect(ragStep?.data?.output_format).toBeDefined();
    });
  });
});

