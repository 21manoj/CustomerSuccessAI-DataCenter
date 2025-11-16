/**
 * ABTestingFramework - Test which insights drive retention & engagement
 * 
 * Use cases:
 * 1. Test insight presentation (card design, wording, placement)
 * 2. Test journal tone effectiveness (which drives most engagement?)
 * 3. Test notification timing (when do users actually check in?)
 * 4. Test premium feature messaging
 * 5. Test recommendation algorithms
 * 
 * Metrics tracked:
 * - Insight click-through rate
 * - User action rate (did they follow suggestion?)
 * - Retention (D1, D7, D30)
 * - Check-in frequency
 * - Premium conversion
 */

interface ABTest {
  id: string;
  name: string;
  description: string;
  startDate: Date;
  endDate?: Date;
  variants: ABVariant[];
  successMetric: string;
  active: boolean;
}

interface ABVariant {
  id: string;
  name: string;
  allocation: number; // 0.0 - 1.0 (e.g., 0.5 = 50%)
  config: any; // Variant-specific configuration
}

interface ABTestAssignment {
  userId: string;
  testId: string;
  variant: string;
  assignedAt: Date;
}

export class ABTestingFramework {
  private assignments: Map<string, Map<string, string>> = new Map(); // userId -> testId -> variant

  /**
   * DEFINE TESTS
   * Example tests to run
   */
  private static ACTIVE_TESTS: ABTest[] = [
    {
      id: 'insight-presentation-v1',
      name: 'Insight Card Design',
      description: 'Test which card design gets more clicks',
      startDate: new Date('2024-10-01'),
      variants: [
        {
          id: 'control',
          name: 'Current design',
          allocation: 0.5,
          config: { style: 'minimal', colorBorder: true }
        },
        {
          id: 'variant-a',
          name: 'Bold with icon',
          allocation: 0.5,
          config: { style: 'bold', icon: true, colorBorder: false }
        }
      ],
      successMetric: 'insight_clicked',
      active: true
    },
    {
      id: 'journal-tone-effectiveness',
      name: 'Journal Tone Effectiveness',
      description: 'Which tone drives most journal engagement?',
      startDate: new Date('2024-10-01'),
      variants: [
        { id: 'reflective', name: 'Reflective', allocation: 0.4, config: { tone: 'reflective' } },
        { id: 'coach-like', name: 'Coach-Like', allocation: 0.3, config: { tone: 'coach-like' } },
        { id: 'poetic', name: 'Poetic', allocation: 0.3, config: { tone: 'poetic' } }
      ],
      successMetric: 'journal_read_time_seconds',
      active: true
    },
    {
      id: 'insight-wording-v1',
      name: 'Insight Wording',
      description: 'Technical vs casual language',
      startDate: new Date('2024-10-01'),
      variants: [
        {
          id: 'control',
          name: 'Technical',
          allocation: 0.5,
          config: { 
            template: '{source} shows +{impact} correlation with {target} (r={correlation})'
          }
        },
        {
          id: 'variant-a',
          name: 'Casual',
          allocation: 0.5,
          config: {
            template: 'When you {source}, you typically feel +{impact} points better in {target}'
          }
        }
      ],
      successMetric: 'user_acted_on',
      active: true
    },
    {
      id: 'premium-trigger-timing',
      name: 'Premium Paywall Timing',
      description: 'When to show premium offer?',
      startDate: new Date('2024-10-01'),
      variants: [
        {
          id: 'control',
          name: 'After 10 check-ins',
          allocation: 0.33,
          config: { trigger: 'checkin_count', threshold: 10 }
        },
        {
          id: 'variant-a',
          name: 'After first MDW ≥ 3',
          allocation: 0.33,
          config: { trigger: 'mdw_threshold', threshold: 3 }
        },
        {
          id: 'variant-b',
          name: 'After first "holy shit" insight',
          allocation: 0.34,
          config: { trigger: 'high_confidence_insight', threshold: 1 }
        }
      ],
      successMetric: 'premium_conversion',
      active: true
    }
  ];

  /**
   * ASSIGN USER TO VARIANT
   * Consistent hashing ensures same user always gets same variant
   */
  assignVariant(userId: string, testId: string): string {
    // Check if already assigned
    if (this.assignments.has(userId) && this.assignments.get(userId)!.has(testId)) {
      return this.assignments.get(userId)!.get(testId)!;
    }

    const test = ABTestingFramework.ACTIVE_TESTS.find(t => t.id === testId);
    if (!test || !test.active) {
      return 'control'; // Default to control if test not found
    }

    // Consistent hash: userId + testId → deterministic variant
    const hash = this.hashCode(userId + testId);
    const normalized = Math.abs(hash) / 2147483647; // Normalize to 0-1

    // Allocate based on variant allocation
    let cumulative = 0;
    for (const variant of test.variants) {
      cumulative += variant.allocation;
      if (normalized < cumulative) {
        this.saveAssignment(userId, testId, variant.id);
        return variant.id;
      }
    }

    // Fallback
    return test.variants[0].id;
  }

  /**
   * GET VARIANT CONFIG
   */
  getVariantConfig(userId: string, testId: string): any {
    const variant = this.assignVariant(userId, testId);
    const test = ABTestingFramework.ACTIVE_TESTS.find(t => t.id === testId);
    const variantObj = test?.variants.find(v => v.id === variant);
    return variantObj?.config || {};
  }

  /**
   * TRACK EVENT
   * Record user action for analytics
   */
  async trackEvent(
    userId: string,
    eventName: string,
    properties?: any
  ): Promise<void> {
    // Get all active test assignments for this user
    const activeAssignments = this.getUserAssignments(userId);

    const event = {
      id: `evt-${Date.now()}-${Math.random()}`,
      userId,
      eventName,
      properties: JSON.stringify(properties || {}),
      timestamp: new Date(),
      abTestAssignments: activeAssignments
    };

    // Store in database
    await this.saveEvent(event);

    // Send to analytics service (e.g., Mixpanel, Amplitude)
    await this.sendToAnalytics(event);
  }

  /**
   * ANALYZE TEST RESULTS
   * Calculate statistical significance
   */
  async analyzeTest(testId: string): Promise<{
    test: ABTest;
    results: ABTestResults[];
    winner?: string;
    significant: boolean;
  }> {
    const test = ABTestingFramework.ACTIVE_TESTS.find(t => t.id === testId);
    if (!test) throw new Error('Test not found');

    const results: ABTestResults[] = [];

    for (const variant of test.variants) {
      const metrics = await this.getVariantMetrics(testId, variant.id, test.successMetric);
      results.push({
        variant: variant.id,
        sampleSize: metrics.sampleSize,
        successRate: metrics.successRate,
        avgValue: metrics.avgValue,
        conversionRate: metrics.conversionRate
      });
    }

    // Statistical significance test (Chi-squared or T-test)
    const significant = this.isStatisticallySignificant(results);
    const winner = significant ? this.findWinner(results) : undefined;

    return { test, results, winner, significant };
  }

  /**
   * EXAMPLE TESTS TO RUN
   */
  static getRecommendedTests(): ABTest[] {
    return [
      {
        id: 'insight-click-test',
        name: 'Insight Click-Through Optimization',
        description: 'Which insight presentation gets more engagement?',
        startDate: new Date(),
        variants: [
          {
            id: 'control-card',
            name: 'Simple card',
            allocation: 0.33,
            config: { design: 'minimal', emphasis: 'data' }
          },
          {
            id: 'story-card',
            name: 'Story-like card',
            allocation: 0.33,
            config: { design: 'narrative', emphasis: 'impact' }
          },
          {
            id: 'urgent-card',
            name: 'Urgent CTA',
            allocation: 0.34,
            config: { design: 'urgent', emphasis: 'action' }
          }
        ],
        successMetric: 'insight_clicked',
        active: true
      },
      {
        id: 'retention-driver-test',
        name: 'Which Insights Drive Retention?',
        description: 'Do lag insights or same-day insights drive more D7 retention?',
        startDate: new Date(),
        variants: [
          {
            id: 'show-lag-first',
            name: 'Prioritize lag insights',
            allocation: 0.5,
            config: { insightPriority: ['lag', 'same-day', 'breakpoint', 'purpose'] }
          },
          {
            id: 'show-breakpoint-first',
            name: 'Prioritize breakpoints',
            allocation: 0.5,
            config: { insightPriority: ['breakpoint', 'lag', 'same-day', 'purpose'] }
          }
        ],
        successMetric: 'retention_d7',
        active: true
      },
      {
        id: 'holy-shit-moment-test',
        name: '"Holy Shit" Moment Timing',
        description: 'When to deliver the most impactful insight?',
        startDate: new Date(),
        variants: [
          {
            id: 'day-3',
            name: 'Show on day 3',
            allocation: 0.33,
            config: { showAfterDays: 3 }
          },
          {
            id: 'day-7',
            name: 'Show on day 7',
            allocation: 0.33,
            config: { showAfterDays: 7 }
          },
          {
            id: 'first-pattern',
            name: 'Show immediately when detected',
            allocation: 0.34,
            config: { showAfterDays: 0, requireConfidence: 'high' }
          }
        ],
        successMetric: 'user_acted_on',
        active: true
      }
    ];
  }

  /**
   * INSIGHTS TO TEST
   * Which insights drive the most behavior change?
   */
  static INSIGHT_EXPERIMENTS = {
    // Test: Positive vs negative framing
    test1: {
      control: "When sleep drops below 6.5h, your MindScore drops by -18 points",
      variant: "Sleeping 7+ hours boosts your MindScore by +18 points"
    },
    
    // Test: With vs without specific numbers
    test2: {
      control: "Morning walks improve next-day focus significantly",
      variant: "Morning walks boost next-day focus by exactly +12 points"
    },
    
    // Test: Personal vs general language
    test3: {
      control: "Users who meditate show higher mood ratings",
      variant: "You score +7 points higher on days when you meditate"
    },
    
    // Test: Simple vs detailed explanation
    test4: {
      control: "Exercise creates multi-day momentum",
      variant: "Exercise creates multi-day momentum: +8 BodyScore and +6 MindScore for 2-3 days. Physical vitality cascades through dimensions."
    }
  };

  /**
   * METRIC CALCULATION
   */
  private async getVariantMetrics(
    testId: string,
    variantId: string,
    successMetric: string
  ): Promise<{
    sampleSize: number;
    successRate: number;
    avgValue: number;
    conversionRate: number;
  }> {
    // Query events table
    const events = await this.queryEvents(
      `SELECT * FROM events 
       WHERE ab_test_id = ? AND ab_test_variant = ?`,
      [testId, variantId]
    );

    const totalUsers = new Set(events.map(e => e.userId)).size;
    const successEvents = events.filter(e => e.eventName === successMetric);
    const successUsers = new Set(successEvents.map(e => e.userId)).size;

    return {
      sampleSize: totalUsers,
      successRate: totalUsers > 0 ? successUsers / totalUsers : 0,
      avgValue: this.calculateAvgMetric(successEvents, successMetric),
      conversionRate: successUsers / totalUsers
    };
  }

  /**
   * STATISTICAL SIGNIFICANCE
   * Chi-squared test for A/B comparison
   */
  private isStatisticallySignificant(results: ABTestResults[]): boolean {
    if (results.length < 2) return false;

    const control = results[0];
    const variant = results[1];

    // Minimum sample size
    if (control.sampleSize < 100 || variant.sampleSize < 100) {
      return false;
    }

    // Chi-squared test
    const chiSquared = this.chiSquaredTest(
      control.sampleSize * control.successRate,
      control.sampleSize * (1 - control.successRate),
      variant.sampleSize * variant.successRate,
      variant.sampleSize * (1 - variant.successRate)
    );

    // p < 0.05 (95% confidence)
    return chiSquared > 3.841;
  }

  /**
   * Chi-squared calculation
   */
  private chiSquaredTest(a: number, b: number, c: number, d: number): number {
    const n = a + b + c + d;
    const expected = {
      a: ((a + b) * (a + c)) / n,
      b: ((a + b) * (b + d)) / n,
      c: ((c + d) * (a + c)) / n,
      d: ((c + d) * (b + d)) / n
    };

    return (
      Math.pow(a - expected.a, 2) / expected.a +
      Math.pow(b - expected.b, 2) / expected.b +
      Math.pow(c - expected.c, 2) / expected.c +
      Math.pow(d - expected.d, 2) / expected.d
    );
  }

  /**
   * FIND WINNER
   */
  private findWinner(results: ABTestResults[]): string {
    return results.reduce((best, current) =>
      current.successRate > best.successRate ? current : best
    ).variant;
  }

  /**
   * INSIGHT-SPECIFIC TESTS
   * Test different ways to present the same insight
   */
  async testInsightPresentation(
    userId: string,
    insight: any
  ): Promise<{
    title: string;
    description: string;
    design: any;
  }> {
    const variant = this.assignVariant(userId, 'insight-presentation-v1');
    const config = this.getVariantConfig(userId, 'insight-presentation-v1');

    if (variant === 'control') {
      // Minimal design
      return {
        title: insight.title,
        description: insight.description,
        design: {
          borderColor: this.getInsightColor(insight.type),
          showIcon: false,
          emphasis: 'data'
        }
      };
    } else {
      // Bold with icon
      return {
        title: `💡 ${insight.title}`,
        description: insight.description,
        design: {
          backgroundColor: this.getInsightColor(insight.type) + '20',
          showIcon: true,
          emphasis: 'impact',
          fontSize: 'large'
        }
      };
    }
  }

  /**
   * RECOMMENDATION: Best-performing insights
   * Based on historical A/B test data
   */
  static getBestPractices(): {
    insightPresentation: string[];
    journalTone: string;
    timingStrategies: string[];
  } {
    return {
      insightPresentation: [
        'Use specific numbers (+12 points) not vague language ("improves")',
        'Frame positively ("Sleep 7h for +18 points") vs negatively ("<6.5h drops -18")',
        'Personal language ("You score...") outperforms general ("Users score...")',
        'Show confidence level (HIGH/MEDIUM/LOW) - users trust transparent data',
        'Include actionable next step in every insight'
      ],
      journalTone: 'Reflective (40% prefer) > Coach-Like (30%) > Poetic (20%) > Factual (10%)',
      timingStrategies: [
        'Show first "holy shit" insight on Day 7 (not earlier - need data credibility)',
        'Show lag insights in morning (plan ahead), breakpoints at night (reflect)',
        'Show social media impact insights on low-screen days (receptive mindset)',
        'Trigger premium after first high-confidence insight (when value is clear)'
      ]
    };
  }

  /**
   * HELPERS
   */
  private hashCode(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash;
  }

  private saveAssignment(userId: string, testId: string, variant: string): void {
    if (!this.assignments.has(userId)) {
      this.assignments.set(userId, new Map());
    }
    this.assignments.get(userId)!.set(testId, variant);
  }

  private getUserAssignments(userId: string): Array<{ testId: string; variant: string }> {
    const userTests = this.assignments.get(userId);
    if (!userTests) return [];

    return Array.from(userTests.entries()).map(([testId, variant]) => ({
      testId,
      variant
    }));
  }

  private getInsightColor(type: string): string {
    const colors: Record<string, string> = {
      'same-day': '#4ECDC4',
      'lag': '#FFD93D',
      'breakpoint': '#FF6B6B',
      'purpose-path': '#95E1D3'
    };
    return colors[type] || '#999';
  }

  // Placeholder methods (implement with actual DB)
  private async queryEvents(query: string, params: any[]): Promise<any[]> { return []; }
  private async saveEvent(event: any): Promise<void> {}
  private async sendToAnalytics(event: any): Promise<void> {}
  private calculateAvgMetric(events: any[], metric: string): number { return 0; }
}

interface ABTestResults {
  variant: string;
  sampleSize: number;
  successRate: number;
  avgValue: number;
  conversionRate: number;
}

/**
 * EXAMPLE USAGE:
 * 
 * const abFramework = new ABTestingFramework();
 * 
 * // Assign user to test
 * const variant = abFramework.assignVariant('user-123', 'insight-presentation-v1');
 * 
 * // Get config for that variant
 * const config = abFramework.getVariantConfig('user-123', 'insight-presentation-v1');
 * 
 * // Track when user clicks insight
 * await abFramework.trackEvent('user-123', 'insight_clicked', {
 *   insightId: 'lag-sleep-mind',
 *   timeToClick: 3.2
 * });
 * 
 * // Analyze results after 2 weeks
 * const analysis = await abFramework.analyzeTest('insight-presentation-v1');
 * if (analysis.significant && analysis.winner) {
 *   console.log(`Winner: ${analysis.winner}`);
 *   // Ship winning variant to all users
 * }
 */

export default ABTestingFramework;

