/**
 * InsightEngine - Core algorithm for generating hyper-personalized insights
 * 
 * Generates 4 types of insights:
 * 1. SAME-DAY correlations (immediate effects)
 * 2. LAG correlations (delayed effects, 1-7 days)
 * 3. BREAKPOINT detection (threshold effects)
 * 4. PURPOSE-PATH tracking (intention → outcome)
 * 
 * Privacy-first: All calculations done server-side with encrypted data
 */

class InsightEngine {
  constructor() {
    this.config = {
      minDataPoints: 7,
      confidenceThresholds: { high: 0.7, medium: 0.5, low: 0.3 },
      lagDays: [1, 2, 3, 7],
      personalizedWeights: true
    };
  }

  /**
   * Generate all insights for a user
   * Returns ranked list of most impactful insights
   */
  async generateInsights(userData) {
    const { checkIns = [], details = [], scores = [], isPremium = false } = userData;
    
    // Need minimum 3 days of data
    if (checkIns.length < 6) {
      return this.generateBootstrapInsights();
    }

    const insights = [];

    // 1. SAME-DAY CORRELATIONS (FREE)
    insights.push(...this.findSameDayCorrelations(checkIns, scores));

    // 2. LAG CORRELATIONS (FREE)
    if (scores.length >= this.config.minDataPoints) {
      insights.push(...this.findLagCorrelations(scores, details));
    }

    // 3. BREAKPOINT DETECTION (PREMIUM GATE)
    if (scores.length >= 10) {
      const breakpointInsights = this.findBreakpoints(details, scores);
      if (isPremium) {
        insights.push(...breakpointInsights);
      } else {
        // Show premium gate
        insights.push({
          id: 'premium-gate-breakpoint',
          type: 'premium_gate',
          title: '🔒 Unlock Breakpoint Analysis',
          description: 'Discover your personal thresholds for sleep, exercise, and more. Premium members see where small changes create big impacts.',
          confidence: 'high',
          sourceMetric: 'Various',
          targetMetric: 'All Scores',
          impact: 0,
          isPremiumGate: true
        });
      }
    }

    // 4. PURPOSE-PATH TRACKING (PREMIUM ONLY)
    if (isPremium && scores.length >= 14) {
      insights.push(...this.findPurposePatterns(checkIns, scores));
    }

    // 5. SOCIAL MEDIA IMPACT
    if (details.length >= 5) {
      insights.push(...this.findSocialMediaImpact(details, scores));
    }

    // Rank by impact and confidence
    const rankedInsights = this.rankInsights(insights);

    // Return top 10 most impactful
    return rankedInsights.slice(0, 10);
  }

  /**
   * 1. SAME-DAY CORRELATIONS
   */
  findSameDayCorrelations(checkIns, scores) {
    const insights = [];

    // Group check-ins by day
    const checkInsByDay = this.groupByDay(checkIns);

    // Test: Gratitude → Mood
    const gratitudeDays = [];
    const noGratitudeDays = [];

    Object.entries(checkInsByDay).forEach(([date, dayCheckIns]) => {
      const hasGratitude = dayCheckIns.some(c => c.micro_act === 'Gratitude' || c.micro_act === 'gratitude');
      const avgMood = this.average(dayCheckIns.map(c => c.mood || 3));
      
      if (hasGratitude) {
        gratitudeDays.push(avgMood);
      } else {
        noGratitudeDays.push(avgMood);
      }
    });

    if (gratitudeDays.length >= 3 && noGratitudeDays.length >= 3) {
      const avgWith = this.average(gratitudeDays);
      const avgWithout = this.average(noGratitudeDays);
      const impact = Math.round((avgWith - avgWithout) * 20); // Convert to 0-100 scale

      if (Math.abs(impact) > 3) {
        insights.push({
          id: `same-day-gratitude-${Date.now()}`,
          type: 'same-day',
          title: 'Gratitude boosts your mood',
          description: `Days with gratitude practice show ${Math.abs(impact)}% higher mood scores. Your appreciation shifts perspective.`,
          confidence: 'high',
          sourceMetric: 'Gratitude',
          targetMetric: 'Mood',
          impact: Math.abs(impact)
        });
      }
    }

    // Test: Meditation → Mind score
    const meditationDays = [];
    const noMeditationDays = [];

    Object.entries(checkInsByDay).forEach(([date, dayCheckIns]) => {
      const hasMeditation = dayCheckIns.some(c => c.micro_act === 'Meditation' || c.micro_act === 'meditation');
      const avgMood = this.average(dayCheckIns.map(c => c.mood || 3));
      
      if (hasMeditation) {
        meditationDays.push(avgMood);
      } else {
        noMeditationDays.push(avgMood);
      }
    });

    if (meditationDays.length >= 3 && noMeditationDays.length >= 3) {
      const avgWith = this.average(meditationDays);
      const avgWithout = this.average(noMeditationDays);
      const impact = Math.round((avgWith - avgWithout) * 20);

      if (Math.abs(impact) > 5) {
        insights.push({
          id: `same-day-meditation-${Date.now()}`,
          type: 'same-day',
          title: 'Meditation calms immediately',
          description: `Check-ins after meditation are ${Math.abs(impact)}% more positive. Deep breathing activates your parasympathetic nervous system.`,
          confidence: 'high',
          sourceMetric: 'Meditation',
          targetMetric: 'Mind',
          impact: Math.abs(impact)
        });
      }
    }

    return insights;
  }

  /**
   * 2. LAG CORRELATIONS
   */
  findLagCorrelations(scores, details) {
    const insights = [];

    if (details.length < this.config.minDataPoints) return insights;

    // Sleep → Next-day scores
    for (const lag of [1, 2]) {
      const sleepValues = details.map(d => d.sleep_hours || 0);
      const scoreValues = scores.map(s => s.mind_score || 0);

      const lagCorr = this.calculateLagCorrelation(sleepValues, scoreValues, lag);

      if (lagCorr.significant && Math.abs(lagCorr.impact) > 5) {
        insights.push({
          id: `lag-sleep-mind-${lag}d-${Date.now()}`,
          type: 'lag',
          title: lag === 1 ? 'Good sleep boosts next-day clarity' : `Sleep has ${lag}-day impact`,
          description: `Sleeping ${lagCorr.threshold}+ hours shows +${Math.abs(lagCorr.impact)} mind clarity ${lag} day${lag > 1 ? 's' : ''} later. Your brain needs rest to function optimally.`,
          confidence: this.getConfidenceLevel(lagCorr.correlation),
          sourceMetric: 'Sleep Hours',
          targetMetric: 'Mind Score',
          lagDays: lag,
          impact: Math.abs(lagCorr.impact)
        });
        break; // Only show one sleep insight
      }
    }

    return insights;
  }

  /**
   * 3. BREAKPOINT DETECTION (PREMIUM)
   */
  findBreakpoints(details, scores) {
    const insights = [];

    if (details.length < 10) return insights;

    // Sleep breakpoint
    const sleepData = details.map((d, i) => ({
      x: d.sleep_hours || 0,
      date: new Date(d.created_at || Date.now())
    }));
    
    const mindData = scores.map((s, i) => ({
      y: s.mind_score || 0,
      date: new Date(s.created_at || Date.now())
    }));

    const sleepBreakpoint = this.detectBreakpoint(
      sleepData,
      mindData,
      { min: 5, max: 9, step: 0.5 }
    );

    if (sleepBreakpoint.detected) {
      const impact = Math.round(sleepBreakpoint.avgAbove - sleepBreakpoint.avgBelow);
      insights.push({
        id: `breakpoint-sleep-${Date.now()}`,
        type: 'breakpoint',
        title: 'Sleep threshold detected',
        description: `When sleep drops below ${sleepBreakpoint.threshold}h, your mind score drops by ~${Math.abs(impact)} points. Prioritize ${sleepBreakpoint.threshold + 0.5}+ hours for optimal clarity.`,
        confidence: this.getConfidenceLevel(sleepBreakpoint.confidence),
        sourceMetric: 'Sleep Hours',
        targetMetric: 'Mind Score',
        impact: Math.abs(impact),
        threshold: sleepBreakpoint.threshold
      });
    }

    return insights;
  }

  /**
   * 4. PURPOSE-PATH TRACKING (PREMIUM)
   */
  findPurposePatterns(checkIns, scores) {
    const insights = [];

    // Calculate micro-move completion rate
    const dailyMicroMoves = this.calculateDailyMicroMoves(checkIns);
    const purposeScores = scores.map(s => s.purpose_score || 0);

    if (dailyMicroMoves.length >= 7 && purposeScores.length >= 7) {
      const correlation = this.pearsonCorrelation(dailyMicroMoves, purposeScores);

      if (Math.abs(correlation) > this.config.confidenceThresholds.medium) {
        const avgImpact = this.calculateAverageImpact(dailyMicroMoves, purposeScores);
        
        insights.push({
          id: `purpose-momentum-${Date.now()}`,
          type: 'purpose-path',
          title: 'Micro-moves build purpose momentum',
          description: `Completing 2+ micro-moves daily increases your purpose score by +${avgImpact} points. Small consistent actions create direction.`,
          confidence: this.getConfidenceLevel(correlation),
          sourceMetric: 'Micro-Moves',
          targetMetric: 'Purpose Score',
          impact: avgImpact
        });
      }
    }

    return insights;
  }

  /**
   * 5. SOCIAL MEDIA IMPACT
   */
  findSocialMediaImpact(details, scores) {
    const insights = [];

    const screenTimeData = details.map(d => d.screen_time_minutes || 0);
    const mindScores = scores.map(s => s.mind_score || 0);

    if (screenTimeData.length < 5) return insights;

    const avgScreenTime = this.average(screenTimeData);
    
    const highScreenDays = [];
    const lowScreenDays = [];

    screenTimeData.forEach((time, i) => {
      if (time > avgScreenTime + 30) {
        highScreenDays.push(mindScores[i] || 0);
      } else if (time < avgScreenTime - 30) {
        lowScreenDays.push(mindScores[i] || 0);
      }
    });

    if (highScreenDays.length >= 3 && lowScreenDays.length >= 3) {
      const avgHigh = this.average(highScreenDays);
      const avgLow = this.average(lowScreenDays);
      const impact = Math.round(avgLow - avgHigh);

      if (impact > 5) {
        insights.push({
          id: `social-media-impact-${Date.now()}`,
          type: 'same-day',
          title: 'Screen time drains mental clarity',
          description: `You score ${impact} points higher on days with <${Math.round(avgScreenTime - 30)} min screen time vs ${Math.round(avgScreenTime + 30)}+ min. The scroll has a cost.`,
          confidence: 'high',
          sourceMetric: 'Screen Time',
          targetMetric: 'Mind Score',
          impact: impact
        });
      }
    }

    return insights;
  }

  /**
   * ALGORITHM: Lag Correlation
   */
  calculateLagCorrelation(xSeries, ySeries, lag) {
    if (xSeries.length < this.config.minDataPoints + lag) {
      return { correlation: 0, significant: false, impact: 0, threshold: 0 };
    }

    // Shift y series by lag days
    const xLagged = xSeries.slice(0, -lag);
    const yLagged = ySeries.slice(lag);

    const correlation = this.pearsonCorrelation(xLagged, yLagged);
    const significant = Math.abs(correlation) > this.config.confidenceThresholds.low;

    // Calculate impact
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
   * ALGORITHM: Breakpoint Detection
   */
  detectBreakpoint(xData, yData, range) {
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
   * RANKING: Sort insights by impact × confidence
   */
  rankInsights(insights) {
    return insights.sort((a, b) => {
      const scoreA = Math.abs(a.impact) * this.confidenceToNumber(a.confidence);
      const scoreB = Math.abs(b.impact) * this.confidenceToNumber(b.confidence);
      return scoreB - scoreA;
    });
  }

  /**
   * UTILITY FUNCTIONS
   */

  groupByDay(checkIns) {
    const map = {};
    checkIns.forEach(checkIn => {
      const date = new Date(checkIn.created_at);
      const dateStr = date.toDateString();
      if (!map[dateStr]) {
        map[dateStr] = [];
      }
      map[dateStr].push(checkIn);
    });
    return map;
  }

  alignByDate(xData, yData) {
    const result = [];
    
    xData.forEach(xPoint => {
      const yPoint = yData.find(y => 
        new Date(y.date).toDateString() === new Date(xPoint.date).toDateString()
      );
      if (yPoint) {
        result.push({ x: xPoint.x, y: yPoint.y, date: xPoint.date });
      }
    });

    return result;
  }

  average(arr) {
    return arr.length === 0 ? 0 : arr.reduce((a, b) => a + b, 0) / arr.length;
  }

  median(arr) {
    const sorted = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 === 0
      ? (sorted[mid - 1] + sorted[mid]) / 2
      : sorted[mid];
  }

  standardDeviation(arr) {
    const avg = this.average(arr);
    const squareDiffs = arr.map(value => Math.pow(value - avg, 2));
    const avgSquareDiff = this.average(squareDiffs);
    return Math.sqrt(avgSquareDiff);
  }

  pearsonCorrelation(x, y) {
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

  calculateDailyMicroMoves(checkIns) {
    const byDay = this.groupByDay(checkIns);
    const dailyCounts = [];

    Object.values(byDay).forEach(dayCheckIns => {
      const microActCount = dayCheckIns.filter(c => c.micro_act).length;
      dailyCounts.push(microActCount);
    });

    return dailyCounts;
  }

  calculateAverageImpact(x, y) {
    const grouped = new Map();
    
    x.forEach((xVal, i) => {
      if (!grouped.has(xVal)) {
        grouped.set(xVal, []);
      }
      grouped.get(xVal).push(y[i]);
    });

    const impacts = [];
    grouped.forEach((yVals, xVal) => {
      if (xVal > 0) {
        const avgY = this.average(yVals);
        const baselineY = this.average(y);
        impacts.push(avgY - baselineY);
      }
    });

    return Math.round(this.average(impacts));
  }

  getConfidenceLevel(correlation) {
    const abs = Math.abs(correlation);
    if (abs >= this.config.confidenceThresholds.high) return 'high';
    if (abs >= this.config.confidenceThresholds.medium) return 'medium';
    return 'low';
  }

  confidenceToNumber(confidence) {
    return confidence === 'high' ? 1.0 : confidence === 'medium' ? 0.7 : 0.4;
  }

  /**
   * Bootstrap insights for new users
   */
  generateBootstrapInsights() {
    return [
      {
        id: 'bootstrap-1',
        type: 'same-day',
        title: 'Keep checking in to unlock insights',
        description: 'After 3-7 days of data, we\'ll start showing you personalized patterns and correlations.',
        confidence: 'high',
        sourceMetric: 'Check-ins',
        targetMetric: 'Insights',
        impact: 0
      }
    ];
  }
}

module.exports = new InsightEngine();

