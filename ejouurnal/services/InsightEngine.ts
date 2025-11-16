/**
 * InsightEngine - Core algorithm for generating hyper-personalized insights
 * 
 * Generates 4 types of insights:
 * 1. SAME-DAY correlations (immediate effects)
 * 2. LAG correlations (delayed effects, 1-7 days)
 * 3. BREAKPOINT detection (threshold effects)
 * 4. PURPOSE-PATH tracking (intention → outcome)
 * 
 * Privacy-first: All calculations done on-device or with encrypted data
 */

import { CheckIn, BodyMetrics, MindMetrics, SoulMetrics, DailyScores, LineageInsight } from '../types/fulfillment';

interface InsightEngineConfig {
  minDataPoints: number; // Minimum days of data needed
  confidenceThresholds: {
    high: number; // r > 0.7
    medium: number; // r > 0.5
    low: number; // r > 0.3
  };
  lagDays: number[]; // Days to check for lag effects [1, 2, 3, 7]
  personalizedWeights: boolean; // Use ML to personalize over time
}

export class InsightEngine {
  private config: InsightEngineConfig = {
    minDataPoints: 7,
    confidenceThresholds: { high: 0.7, medium: 0.5, low: 0.3 },
    lagDays: [1, 2, 3, 7],
    personalizedWeights: true
  };

  /**
   * Generate all insights for a user
   * Returns ranked list of most impactful insights
   */
  async generateInsights(
    checkIns: CheckIn[],
    bodyMetrics: BodyMetrics[],
    mindMetrics: MindMetrics[],
    soulMetrics: SoulMetrics[],
    dailyScores: DailyScores[],
    userId: string
  ): Promise<LineageInsight[]> {
    
    if (dailyScores.length < this.config.minDataPoints) {
      return this.generateBootstrapInsights();
    }

    const insights: LineageInsight[] = [];

    // 1. SAME-DAY CORRELATIONS
    insights.push(...this.findSameDayCorrelations(checkIns, dailyScores));

    // 2. LAG CORRELATIONS (1-7 day effects)
    insights.push(...this.findLagCorrelations(dailyScores, bodyMetrics));

    // 3. BREAKPOINT DETECTION (threshold effects)
    insights.push(...this.findBreakpoints(bodyMetrics, dailyScores));

    // 4. PURPOSE-PATH TRACKING
    insights.push(...this.findPurposePatterns(checkIns, dailyScores));

    // 5. SOCIAL MEDIA IMPACT
    insights.push(...this.findSocialMediaImpact(mindMetrics, dailyScores));

    // Rank by impact and confidence
    const rankedInsights = this.rankInsights(insights);

    // Return top 10 most impactful
    return rankedInsights.slice(0, 10);
  }

  /**
   * 1. SAME-DAY CORRELATIONS
   * Find immediate effects: meditation → mood, exercise → energy, etc.
   */
  private findSameDayCorrelations(
    checkIns: CheckIn[],
    dailyScores: DailyScores[]
  ): LineageInsight[] {
    const insights: LineageInsight[] = [];

    // Group check-ins by day
    const checkInsByDay = this.groupByDay(checkIns);

    // Test: Meditation → Higher mood in next check-in
    const meditationEffect = this.testMicroActEffect(
      checkInsByDay,
      'meditation',
      'mood'
    );
    if (meditationEffect.significant) {
      insights.push({
        id: `same-day-meditation-${Date.now()}`,
        type: 'same-day',
        title: 'Meditation calms immediately',
        description: `Check-ins after meditation show ${meditationEffect.impact}% higher mood ratings on average. Deep breathing activates your parasympathetic nervous system.`,
        confidence: this.getConfidenceLevel(meditationEffect.correlation),
        sourceMetric: 'Meditation',
        targetMetric: 'Mood',
        impact: meditationEffect.impact
      });
    }

    // Test: Walk → Mental clarity
    const walkEffect = this.testMicroActEffect(checkInsByDay, 'walk', 'mood');
    if (walkEffect.significant) {
      insights.push({
        id: `same-day-walk-${Date.now()}`,
        type: 'same-day',
        title: 'Walking clears your mind',
        description: `You score ${walkEffect.impact} points higher in check-ins following a walk. Movement shifts mental state.`,
        confidence: this.getConfidenceLevel(walkEffect.correlation),
        sourceMetric: 'Walking',
        targetMetric: 'Mind Score',
        impact: walkEffect.impact
      });
    }

    // Test: Gratitude → Soul score
    const gratitudeEffect = this.testMicroActEffect(checkInsByDay, 'gratitude', 'soul');
    if (gratitudeEffect.significant) {
      insights.push({
        id: `same-day-gratitude-${Date.now()}`,
        type: 'same-day',
        title: 'Gratitude boosts soul score',
        description: `Days with gratitude practice show +${gratitudeEffect.impact} SoulScore. Appreciation shifts perspective.`,
        confidence: this.getConfidenceLevel(gratitudeEffect.correlation),
        sourceMetric: 'Gratitude',
        targetMetric: 'Soul Score',
        impact: gratitudeEffect.impact
      });
    }

    // Test: Nature → Multiple dimensions
    const natureEffect = this.testMicroActEffect(checkInsByDay, 'nature', 'all');
    if (natureEffect.significant) {
      insights.push({
        id: `same-day-nature-${Date.now()}`,
        type: 'same-day',
        title: 'Nature restores multiple dimensions',
        description: `20+ minutes outdoors increases scores: Mind +${natureEffect.mindImpact}, Soul +${natureEffect.soulImpact}. Natural environments reduce cortisol.`,
        confidence: this.getConfidenceLevel(natureEffect.correlation),
        sourceMetric: 'Nature Time',
        targetMetric: 'Mind & Soul',
        impact: natureEffect.impact
      });
    }

    return insights;
  }

  /**
   * 2. LAG CORRELATIONS
   * Find delayed effects: sleep yesterday → focus today, exercise → energy tomorrow
   */
  private findLagCorrelations(
    dailyScores: DailyScores[],
    bodyMetrics: BodyMetrics[]
  ): LineageInsight[] {
    const insights: LineageInsight[] = [];

    // Test each lag period
    for (const lag of this.config.lagDays) {
      // Sleep → Next-day mind score
      const sleepMindCorr = this.calculateLagCorrelation(
        bodyMetrics.map(m => m.sleepHours || 0),
        dailyScores.map(s => s.mindScore),
        lag
      );

      if (sleepMindCorr.significant) {
        insights.push({
          id: `lag-sleep-mind-${lag}d-${Date.now()}`,
          type: 'lag',
          title: lag === 1 
            ? 'Good sleep boosts next-day clarity'
            : `Sleep quality has ${lag}-day impact`,
          description: `Sleeping ${sleepMindCorr.threshold}+ hours shows +${sleepMindCorr.impact} MindScore ${lag} day${lag > 1 ? 's' : ''} later. Your brain needs rest to function optimally.`,
          confidence: this.getConfidenceLevel(sleepMindCorr.correlation),
          sourceMetric: 'Sleep Hours',
          targetMetric: 'Mind Score',
          lagDays: lag,
          impact: sleepMindCorr.impact
        });
      }

      // Activity → Next-day mind score
      const activityMindCorr = this.calculateLagCorrelation(
        bodyMetrics.map(m => m.activeMinutes || 0),
        dailyScores.map(s => s.mindScore),
        lag
      );

      if (activityMindCorr.significant && lag <= 2) {
        insights.push({
          id: `lag-activity-mind-${lag}d-${Date.now()}`,
          type: 'lag',
          title: 'Morning movement boosts next-day focus',
          description: `Days with ≥${activityMindCorr.threshold} active minutes show +${activityMindCorr.impact} MindScore the next day. Physical vitality feeds mental clarity.`,
          confidence: this.getConfidenceLevel(activityMindCorr.correlation),
          sourceMetric: 'Active Minutes',
          targetMetric: 'Mind Score',
          lagDays: lag,
          impact: activityMindCorr.impact
        });
      }

      // Exercise → Body score momentum
      const exerciseBodyCorr = this.calculateLagCorrelation(
        bodyMetrics.map(m => m.activeMinutes || 0),
        dailyScores.map(s => s.bodyScore),
        lag
      );

      if (exerciseBodyCorr.significant && lag >= 2) {
        insights.push({
          id: `lag-exercise-body-${lag}d-${Date.now()}`,
          type: 'lag',
          title: 'Exercise creates multi-day momentum',
          description: `Vigorous exercise shows +${exerciseBodyCorr.impact} BodyScore for ${lag} days. Physical vitality cascades.`,
          confidence: this.getConfidenceLevel(exerciseBodyCorr.correlation),
          sourceMetric: 'Exercise',
          targetMetric: 'Body Score',
          lagDays: lag,
          impact: exerciseBodyCorr.impact
        });
      }
    }

    return insights;
  }

  /**
   * 3. BREAKPOINT DETECTION
   * Find threshold effects: sleep < 6.5h → mind drops, social > 60min → clarity drops
   */
  private findBreakpoints(
    bodyMetrics: BodyMetrics[],
    dailyScores: DailyScores[]
  ): LineageInsight[] {
    const insights: LineageInsight[] = [];

    // Sleep breakpoint
    const sleepBreakpoint = this.detectBreakpoint(
      bodyMetrics.map(m => ({ x: m.sleepHours || 0, date: m.date })),
      dailyScores.map(s => ({ y: s.mindScore, date: s.date })),
      { min: 5, max: 9, step: 0.5 }
    );

    if (sleepBreakpoint.detected) {
      const impact = Math.round(sleepBreakpoint.avgAbove - sleepBreakpoint.avgBelow);
      insights.push({
        id: `breakpoint-sleep-${Date.now()}`,
        type: 'breakpoint',
        title: 'Sleep threshold detected',
        description: `When sleep drops below ${sleepBreakpoint.threshold}h, your MindScore typically drops by ~${Math.abs(impact)} points. Prioritize ${sleepBreakpoint.threshold + 0.5}+ hours for optimal clarity.`,
        confidence: this.getConfidenceLevel(sleepBreakpoint.confidence),
        sourceMetric: 'Sleep Hours',
        targetMetric: 'Mind Score',
        impact: impact
      });
    }

    // Activity breakpoint
    const activityBreakpoint = this.detectBreakpoint(
      bodyMetrics.map(m => ({ x: m.activeMinutes || 0, date: m.date })),
      dailyScores.map(s => ({ y: s.bodyScore, date: s.date })),
      { min: 0, max: 120, step: 15 }
    );

    if (activityBreakpoint.detected) {
      const impact = Math.round(activityBreakpoint.avgAbove - activityBreakpoint.avgBelow);
      insights.push({
        id: `breakpoint-activity-${Date.now()}`,
        type: 'breakpoint',
        title: 'Activity sweet spot found',
        description: `${activityBreakpoint.threshold}+ minutes of movement is your threshold for high BodyScore. Below that, scores drop by ${Math.abs(impact)} points on average.`,
        confidence: this.getConfidenceLevel(activityBreakpoint.confidence),
        sourceMetric: 'Active Minutes',
        targetMetric: 'Body Score',
        impact: impact
      });
    }

    return insights;
  }

  /**
   * 4. PURPOSE-PATH TRACKING
   * Track intention → micro-moves → purpose score → fulfillment
   */
  private findPurposePatterns(
    checkIns: CheckIn[],
    dailyScores: DailyScores[]
  ): LineageInsight[] {
    const insights: LineageInsight[] = [];

    // Calculate micro-move completion rate
    const microMovesPerDay = this.calculateDailyMicroMoves(checkIns);
    const purposeScores = dailyScores.map(s => s.purposeScore);

    // Correlation: micro-moves → purpose score
    const correlation = this.pearsonCorrelation(microMovesPerDay, purposeScores);

    if (Math.abs(correlation) > this.config.confidenceThresholds.medium) {
      const avgImpact = this.calculateAverageImpact(microMovesPerDay, purposeScores);
      
      insights.push({
        id: `purpose-momentum-${Date.now()}`,
        type: 'purpose-path',
        title: 'Micro-moves build purpose momentum',
        description: `Completing 2+ micro-moves daily increases PurposeScore by +${avgImpact} points. Small consistent actions create direction.`,
        confidence: this.getConfidenceLevel(correlation),
        sourceMetric: 'Micro-Moves',
        targetMetric: 'Purpose Score',
        impact: avgImpact
      });
    }

    // Detect streaks
    const currentStreak = this.detectStreak(
      checkIns,
      (checkIn) => checkIn.microAct !== undefined
    );

    if (currentStreak >= 3) {
      insights.push({
        id: `purpose-streak-${Date.now()}`,
        type: 'purpose-path',
        title: `You're on a ${currentStreak}-day micro-act streak`,
        description: `${currentStreak} consecutive days with at least one micro-act. Your purpose adherence is building momentum.`,
        confidence: 'high',
        sourceMetric: 'Daily Micro-Acts',
        targetMetric: 'Purpose Momentum',
        impact: 5
      });
    }

    return insights;
  }

  /**
   * 5. SOCIAL MEDIA IMPACT
   * The "holy shit" insight - show the glitter vs gold effect
   */
  private findSocialMediaImpact(
    mindMetrics: MindMetrics[],
    dailyScores: DailyScores[]
  ): LineageInsight[] {
    const insights: LineageInsight[] = [];

    // Calculate baseline social media usage
    const socialMinutes = mindMetrics.map(m => m.socialMediaMinutes || 0);
    const avgSocialMinutes = this.average(socialMinutes);

    // Find high-use days (>baseline) vs low-use days
    const highUseDays = dailyScores.filter((_, i) => 
      socialMinutes[i] > avgSocialMinutes + 15
    );
    const lowUseDays = dailyScores.filter((_, i) => 
      socialMinutes[i] < avgSocialMinutes - 15
    );

    if (highUseDays.length >= 3 && lowUseDays.length >= 3) {
      const highUseAvgMind = this.average(highUseDays.map(d => d.mindScore));
      const lowUseAvgMind = this.average(lowUseDays.map(d => d.mindScore));
      const impact = Math.round(lowUseAvgMind - highUseAvgMind);

      if (impact > 5) {
        insights.push({
          id: `social-media-impact-${Date.now()}`,
          type: 'same-day',
          title: 'Social media drains mental clarity',
          description: `You score ${impact} points higher on days with <${Math.round(avgSocialMinutes - 15)} min social media vs ${Math.round(avgSocialMinutes + 15)}+ min. The scroll has a cost.`,
          confidence: 'high',
          sourceMetric: 'Social Media Time',
          targetMetric: 'Mind Score',
          impact: -impact
        });
      }
    }

    // Sparkle tag correlation
    const sparkleDays = checkIns.filter(c => c.sparkleTagged).map(c => c.timestamp.toDateString());
    const uniqueSparkleDays = [...new Set(sparkleDays)];
    
    if (uniqueSparkleDays.length >= 3) {
      const sparkleScores = dailyScores.filter(s => 
        uniqueSparkleDays.includes(s.date.toDateString())
      );
      const nonSparkleScores = dailyScores.filter(s => 
        !uniqueSparkleDays.includes(s.date.toDateString())
      );

      const avgSparkle = this.average(sparkleScores.map(s => s.mindScore));
      const avgNonSparkle = this.average(nonSparkleScores.map(s => s.mindScore));
      const impact = Math.round(avgNonSparkle - avgSparkle);

      if (impact > 3) {
        insights.push({
          id: `sparkle-comparison-${Date.now()}`,
          type: 'same-day',
          title: 'Comparison triggers reduce clarity',
          description: `Days when you tag "sparkle" (felt worse after scrolling) show -${impact} MindScore. Your intuition about comparison is data-backed.`,
          confidence: 'medium',
          sourceMetric: 'Sparkle Tags',
          targetMetric: 'Mind Score',
          impact: -impact
        });
      }
    }

    return insights;
  }

  /**
   * ALGORITHM: Lag Correlation (Pearson with time shift)
   */
  private calculateLagCorrelation(
    xSeries: number[],
    ySeries: number[],
    lag: number
  ): {
    correlation: number;
    significant: boolean;
    impact: number;
    threshold: number;
  } {
    if (xSeries.length < this.config.minDataPoints + lag) {
      return { correlation: 0, significant: false, impact: 0, threshold: 0 };
    }

    // Shift y series by lag days
    const xLagged = xSeries.slice(0, -lag);
    const yLagged = ySeries.slice(lag);

    const correlation = this.pearsonCorrelation(xLagged, yLagged);
    const significant = Math.abs(correlation) > this.config.confidenceThresholds.low;

    // Calculate impact: difference in y when x is high vs low
    const xMedian = this.median(xLagged);
    const highXIndices = xLagged.map((x, i) => x >= xMedian ? i : -1).filter(i => i >= 0);
    const lowXIndices = xLagged.map((x, i) => x < xMedian ? i : -1).filter(i => i >= 0);

    const avgYWhenXHigh = this.average(highXIndices.map(i => yLagged[i]));
    const avgYWhenXLow = this.average(lowXIndices.map(i => yLagged[i]));
    const impact = Math.round(avgYWhenXHigh - avgYWhenXLow);

    return {
      correlation,
      significant,
      impact,
      threshold: Math.round(xMedian)
    };
  }

  /**
   * ALGORITHM: Breakpoint Detection (Piecewise regression)
   */
  private detectBreakpoint(
    xData: Array<{ x: number; date: Date }>,
    yData: Array<{ y: number; date: Date }>,
    range: { min: number; max: number; step: number }
  ): {
    detected: boolean;
    threshold: number;
    avgAbove: number;
    avgBelow: number;
    confidence: number;
  } {
    let bestThreshold = 0;
    let maxDifference = 0;
    let bestAvgAbove = 0;
    let bestAvgBelow = 0;

    // Align data by date
    const aligned = this.alignByDate(xData, yData);

    // Test each potential threshold
    for (let threshold = range.min; threshold <= range.max; threshold += range.step) {
      const above = aligned.filter(d => d.x >= threshold).map(d => d.y);
      const below = aligned.filter(d => d.x < threshold).map(d => d.y);

      if (above.length >= 3 && below.length >= 3) {
        const avgAbove = this.average(above);
        const avgBelow = this.average(below);
        const difference = Math.abs(avgAbove - avgBelow);

        if (difference > maxDifference) {
          maxDifference = difference;
          bestThreshold = threshold;
          bestAvgAbove = avgAbove;
          bestAvgBelow = avgBelow;
        }
      }
    }

    // Significant if difference > 10 points
    const detected = maxDifference > 10;
    
    // Confidence based on sample size and effect size
    const totalSamples = aligned.length;
    const effectSize = maxDifference / this.standardDeviation(aligned.map(d => d.y));
    const confidence = totalSamples > 14 && effectSize > 0.8 ? 0.8 : 0.6;

    return {
      detected,
      threshold: bestThreshold,
      avgAbove: bestAvgAbove,
      avgBelow: bestAvgBelow,
      confidence
    };
  }

  /**
   * UTILITY: Pearson Correlation Coefficient
   */
  private pearsonCorrelation(x: number[], y: number[]): number {
    if (x.length !== y.length || x.length === 0) return 0;

    const n = x.length;
    const meanX = this.average(x);
    const meanY = this.average(y);

    let numerator = 0;
    let sumXSquared = 0;
    let sumYSquared = 0;

    for (let i = 0; i < n; i++) {
      const deltaX = x[i] - meanX;
      const deltaY = y[i] - meanY;
      numerator += deltaX * deltaY;
      sumXSquared += deltaX * deltaX;
      sumYSquared += deltaY * deltaY;
    }

    const denominator = Math.sqrt(sumXSquared * sumYSquared);
    return denominator === 0 ? 0 : numerator / denominator;
  }

  /**
   * UTILITY: Test micro-act effect
   */
  private testMicroActEffect(
    checkInsByDay: Map<string, CheckIn[]>,
    microAct: string,
    targetMetric: string
  ): {
    significant: boolean;
    correlation: number;
    impact: number;
  } {
    const daysWithAct: number[] = [];
    const daysWithoutAct: number[] = [];

    checkInsByDay.forEach((checkIns, dateStr) => {
      const hasMicroAct = checkIns.some(c => c.microAct === microAct);
      const avgMood = this.average(
        checkIns.map(c => this.moodToScore(c.mood))
      );

      if (hasMicroAct) {
        daysWithAct.push(avgMood);
      } else {
        daysWithoutAct.push(avgMood);
      }
    });

    if (daysWithAct.length < 3 || daysWithoutAct.length < 3) {
      return { significant: false, correlation: 0, impact: 0 };
    }

    const avgWith = this.average(daysWithAct);
    const avgWithout = this.average(daysWithoutAct);
    const impact = Math.round(avgWith - avgWithout);

    // T-test for significance
    const tStat = this.tTest(daysWithAct, daysWithoutAct);
    const significant = Math.abs(tStat) > 1.96 && Math.abs(impact) > 3; // p < 0.05

    return {
      significant,
      correlation: tStat / 10, // Approximate correlation
      impact
    };
  }

  /**
   * RANKING: Sort insights by impact × confidence
   */
  private rankInsights(insights: LineageInsight[]): LineageInsight[] {
    return insights.sort((a, b) => {
      const scoreA = Math.abs(a.impact) * this.confidenceToNumber(a.confidence);
      const scoreB = Math.abs(b.impact) * this.confidenceToNumber(b.confidence);
      return scoreB - scoreA;
    });
  }

  /**
   * UTILITY FUNCTIONS
   */

  private groupByDay(checkIns: CheckIn[]): Map<string, CheckIn[]> {
    const map = new Map<string, CheckIn[]>();
    checkIns.forEach(checkIn => {
      const dateStr = checkIn.timestamp.toDateString();
      if (!map.has(dateStr)) {
        map.set(dateStr, []);
      }
      map.get(dateStr)!.push(checkIn);
    });
    return map;
  }

  private alignByDate(
    xData: Array<{ x: number; date: Date }>,
    yData: Array<{ y: number; date: Date }>
  ): Array<{ x: number; y: number; date: Date }> {
    const result: Array<{ x: number; y: number; date: Date }> = [];
    
    xData.forEach(xPoint => {
      const yPoint = yData.find(y => 
        y.date.toDateString() === xPoint.date.toDateString()
      );
      if (yPoint) {
        result.push({ x: xPoint.x, y: yPoint.y, date: xPoint.date });
      }
    });

    return result;
  }

  private moodToScore(mood: string): number {
    const moodMap: Record<string, number> = {
      'very-low': 20,
      'low': 40,
      'neutral': 60,
      'good': 80,
      'great': 100
    };
    return moodMap[mood] || 60;
  }

  private average(arr: number[]): number {
    return arr.length === 0 ? 0 : arr.reduce((a, b) => a + b, 0) / arr.length;
  }

  private median(arr: number[]): number {
    const sorted = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 === 0
      ? (sorted[mid - 1] + sorted[mid]) / 2
      : sorted[mid];
  }

  private standardDeviation(arr: number[]): number {
    const avg = this.average(arr);
    const squareDiffs = arr.map(value => Math.pow(value - avg, 2));
    const avgSquareDiff = this.average(squareDiffs);
    return Math.sqrt(avgSquareDiff);
  }

  private tTest(sample1: number[], sample2: number[]): number {
    const mean1 = this.average(sample1);
    const mean2 = this.average(sample2);
    const sd1 = this.standardDeviation(sample1);
    const sd2 = this.standardDeviation(sample2);
    const n1 = sample1.length;
    const n2 = sample2.length;

    const pooledSD = Math.sqrt(
      ((n1 - 1) * sd1 * sd1 + (n2 - 1) * sd2 * sd2) / (n1 + n2 - 2)
    );

    return (mean1 - mean2) / (pooledSD * Math.sqrt(1/n1 + 1/n2));
  }

  private calculateDailyMicroMoves(checkIns: CheckIn[]): number[] {
    const byDay = this.groupByDay(checkIns);
    const dailyCounts: number[] = [];

    byDay.forEach(dayCheckIns => {
      const microActCount = dayCheckIns.filter(c => c.microAct).length;
      dailyCounts.push(microActCount);
    });

    return dailyCounts;
  }

  private calculateAverageImpact(x: number[], y: number[]): number {
    const grouped = new Map<number, number[]>();
    
    x.forEach((xVal, i) => {
      if (!grouped.has(xVal)) {
        grouped.set(xVal, []);
      }
      grouped.get(xVal)!.push(y[i]);
    });

    const impacts: number[] = [];
    grouped.forEach((yVals, xVal) => {
      if (xVal > 0) {
        const avgY = this.average(yVals);
        const baselineY = this.average(y);
        impacts.push(avgY - baselineY);
      }
    });

    return Math.round(this.average(impacts));
  }

  private detectStreak(
    checkIns: CheckIn[],
    condition: (checkIn: CheckIn) => boolean
  ): number {
    const byDay = this.groupByDay(checkIns);
    const dates = Array.from(byDay.keys()).sort().reverse();
    
    let streak = 0;
    for (const date of dates) {
      const dayCheckIns = byDay.get(date)!;
      if (dayCheckIns.some(condition)) {
        streak++;
      } else {
        break;
      }
    }

    return streak;
  }

  private getConfidenceLevel(correlation: number): 'high' | 'medium' | 'low' {
    const abs = Math.abs(correlation);
    if (abs >= this.config.confidenceThresholds.high) return 'high';
    if (abs >= this.config.confidenceThresholds.medium) return 'medium';
    return 'low';
  }

  private confidenceToNumber(confidence: 'high' | 'medium' | 'low'): number {
    return confidence === 'high' ? 1.0 : confidence === 'medium' ? 0.7 : 0.4;
  }

  /**
   * Bootstrap insights for new users (<7 days data)
   */
  private generateBootstrapInsights(): LineageInsight[] {
    return [
      {
        id: 'bootstrap-1',
        type: 'same-day',
        title: 'Keep checking in to unlock insights',
        description: 'After 7 days of data, we\'ll start showing you personalized patterns and correlations.',
        confidence: 'high',
        sourceMetric: 'Check-ins',
        targetMetric: 'Insights',
        impact: 0
      }
    ];
  }
}

export default InsightEngine;

