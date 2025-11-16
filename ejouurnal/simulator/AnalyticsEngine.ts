/**
 * ANALYTICS ENGINE
 * Real-time analytics processing and aggregation
 */

interface SimulationData {
  users: any[];
  checkIns: any[];
  details: any[];
  analytics: any[];
  metadata: any;
}

interface CohortAnalysis {
  day: number;
  totalUsers: number;
  activeUsers: number;
  retentionRate: number;
  avgCheckInsPerActiveUser: number;
  meaningfulDays: number;
  premiumConversions: number;
  cumulativePremium: number;
}

interface FunnelMetrics {
  stage: string;
  users: number;
  percentage: number;
  dropOff: number;
}

export class AnalyticsEngine {
  private data: SimulationData;
  
  constructor(data: SimulationData) {
    this.data = data;
  }
  
  /**
   * Generate comprehensive analytics
   */
  generateAnalytics() {
    return {
      overview: this.getOverview(),
      cohortAnalysis: this.getCohortAnalysis(),
      funnelMetrics: this.getFunnelMetrics(),
      personaMetrics: this.getPersonaMetrics(),
      revenueProjection: this.getRevenueProjection(),
      engagementMetrics: this.getEngagementMetrics(),
      conversionFactors: this.getConversionFactors(),
      churnRisk: this.getChurnRisk(),
    };
  }
  
  private getOverview() {
    const { users, checkIns, details, analytics } = this.data;
    
    const activeUsers = new Set(checkIns.map((c: any) => c.userId)).size;
    const premiumUsers = users.filter((u: any) => u.isPremium).length;
    const totalRevenue = premiumUsers * 7.99 * 12; // Annual projection
    
    return {
      totalUsers: users.length,
      activeUsers,
      activationRate: (activeUsers / users.length * 100).toFixed(1) + '%',
      premiumUsers,
      conversionRate: (premiumUsers / users.length * 100).toFixed(1) + '%',
      totalCheckIns: checkIns.length,
      avgCheckInsPerUser: (checkIns.length / activeUsers).toFixed(1),
      totalDetailsLogged: details.length,
      avgFulfillmentScore: (users.reduce((sum: number, u: any) => sum + u.fulfillmentScore, 0) / users.length).toFixed(1),
      avgMDW: (users.reduce((sum: number, u: any) => sum + u.meaningfulDays, 0) / users.length).toFixed(2),
      projectedARR: '$' + totalRevenue.toLocaleString(),
    };
  }
  
  private getCohortAnalysis(): CohortAnalysis[] {
    const { users, checkIns, analytics, metadata } = this.data;
    const cohorts: CohortAnalysis[] = [];
    
    for (let day = 0; day < metadata.totalDays; day++) {
      const dayCheckIns = checkIns.filter((c: any) => c.day === day);
      const activeUsers = new Set(dayCheckIns.map((c: any) => c.userId)).size;
      const meaningfulDays = analytics.filter(
        (e: any) => e.eventType === 'meaningful_day' && e.day === day
      ).length;
      const conversions = analytics.filter(
        (e: any) => e.eventType === 'premium_conversion' && e.day === day
      ).length;
      const cumulativePremium = analytics.filter(
        (e: any) => e.eventType === 'premium_conversion' && e.day <= day
      ).length;
      
      cohorts.push({
        day: day + 1,
        totalUsers: users.length,
        activeUsers,
        retentionRate: (activeUsers / users.length * 100),
        avgCheckInsPerActiveUser: activeUsers > 0 ? dayCheckIns.length / activeUsers : 0,
        meaningfulDays,
        premiumConversions: conversions,
        cumulativePremium: cumulativePremium + users.filter((u: any) => u.isPremium && u.joinedDay === 0).length,
      });
    }
    
    return cohorts;
  }
  
  private getFunnelMetrics(): FunnelMetrics[] {
    const { users, checkIns, details, analytics } = this.data;
    
    const signedUp = users.length;
    const completedFirstCheckIn = new Set(checkIns.map((c: any) => c.userId)).size;
    const completed4CheckIns = Array.from(
      checkIns.reduce((map: Map<string, number>, c: any) => {
        map.set(c.userId, (map.get(c.userId) || 0) + 1);
        return map;
      }, new Map())
    ).filter(([_, count]) => count >= 4).length;
    
    const loggedDetails = new Set(details.map((d: any) => d.userId)).size;
    const hadMDW = users.filter((u: any) => u.meaningfulDays >= 1).length;
    const had3MDW = users.filter((u: any) => u.meaningfulDays >= 3).length;
    const convertedPremium = users.filter((u: any) => u.isPremium).length;
    
    const funnel = [
      { stage: '1. Signed Up', users: signedUp },
      { stage: '2. Completed 1st Check-in', users: completedFirstCheckIn },
      { stage: '3. Completed 4 Check-ins', users: completed4CheckIns },
      { stage: '4. Logged Details', users: loggedDetails },
      { stage: '5. Had 1+ MDW', users: hadMDW },
      { stage: '6. Had 3+ MDW', users: had3MDW },
      { stage: '7. Converted to Premium', users: convertedPremium },
    ];
    
    return funnel.map((f, i) => ({
      stage: f.stage,
      users: f.users,
      percentage: (f.users / signedUp * 100),
      dropOff: i > 0 ? funnel[i - 1].users - f.users : 0,
    }));
  }
  
  private getPersonaMetrics() {
    const { users, checkIns, details } = this.data;
    const personas = ['engaged', 'casual', 'struggler', 'power-user'];
    
    return personas.map(persona => {
      const personaUsers = users.filter((u: any) => u.persona === persona);
      const count = personaUsers.length;
      
      const totalCheckIns = checkIns.filter((c: any) => 
        personaUsers.some((u: any) => u.userId === c.userId)
      ).length;
      
      const totalDetails = details.filter((d: any) =>
        personaUsers.some((u: any) => u.userId === d.userId)
      ).length;
      
      const premiumCount = personaUsers.filter((u: any) => u.isPremium).length;
      
      return {
        persona,
        count,
        percentage: (count / users.length * 100).toFixed(1) + '%',
        avgCheckIns: (totalCheckIns / count).toFixed(1),
        avgMDW: (personaUsers.reduce((sum: number, u: any) => sum + u.meaningfulDays, 0) / count).toFixed(2),
        avgFulfillment: (personaUsers.reduce((sum: number, u: any) => sum + u.fulfillmentScore, 0) / count).toFixed(1),
        premiumRate: (premiumCount / count * 100).toFixed(1) + '%',
        detailsLogRate: (totalDetails / totalCheckIns * 100).toFixed(1) + '%',
        avgStreak: (personaUsers.reduce((sum: number, u: any) => sum + u.longestStreak, 0) / count).toFixed(1),
      };
    });
  }
  
  private getRevenueProjection() {
    const { users, analytics } = this.data;
    
    const premiumCount = users.filter((u: any) => u.isPremium).length;
    const conversions = analytics.filter((e: any) => e.eventType === 'premium_conversion');
    
    const avgDaysToConvert = conversions.length > 0
      ? conversions.reduce((sum: number, c: any) => sum + c.day, 0) / conversions.length
      : 0;
    
    // Monthly pricing
    const monthlyPrice = 7.99;
    const annualPrice = 49.99;
    
    // Assume 70% choose annual
    const annualSubscribers = premiumCount * 0.7;
    const monthlySubscribers = premiumCount * 0.3;
    
    const mrr = (annualSubscribers * annualPrice / 12) + (monthlySubscribers * monthlyPrice);
    const arr = mrr * 12;
    
    // LTV calculation (assume 18 month avg lifetime)
    const avgLifetimeMonths = 18;
    const ltv = mrr * avgLifetimeMonths / premiumCount || 0;
    
    return {
      premiumUsers: premiumCount,
      conversionRate: (premiumCount / users.length * 100).toFixed(1) + '%',
      avgDaysToConvert: avgDaysToConvert.toFixed(1),
      mrr: '$' + mrr.toFixed(2),
      arr: '$' + arr.toFixed(2),
      ltv: '$' + ltv.toFixed(2),
      projectedYear1Revenue: '$' + (arr * 1).toFixed(2),
      projectedYear2Revenue: '$' + (arr * 2.5).toFixed(2), // Assuming 150% growth
    };
  }
  
  private getEngagementMetrics() {
    const { users, checkIns, details } = this.data;
    
    const activeUsers = new Set(checkIns.map((c: any) => c.userId)).size;
    
    // Daily Active Users (DAU) equivalent
    const avgDAU = activeUsers / this.data.metadata.totalDays;
    
    // Stickiness (DAU/MAU proxy)
    const stickiness = (avgDAU / activeUsers * 100);
    
    // L7 (7-day active users)
    const l7Users = Array.from(users).filter((u: any) => {
      const userCheckIns = checkIns.filter((c: any) => c.userId === u.userId && c.day >= 6);
      return userCheckIns.length > 0;
    }).length;
    
    const l7Retention = (l7Users / activeUsers * 100);
    
    return {
      dau: avgDAU.toFixed(0),
      activeUsers,
      stickiness: stickiness.toFixed(1) + '%',
      avgSessionsPerDay: (checkIns.length / this.data.metadata.totalDays / activeUsers).toFixed(1),
      avgSessionDuration: (checkIns.reduce((sum: number, c: any) => sum + c.durationSeconds, 0) / checkIns.length).toFixed(1) + 's',
      detailsLogRate: (details.length / checkIns.length * 100).toFixed(1) + '%',
      l7Retention: l7Retention.toFixed(1) + '%',
      powerUsers: users.filter((u: any) => u.totalCheckIns >= this.data.metadata.totalDays * 3).length,
    };
  }
  
  private getConversionFactors() {
    const { users } = this.data;
    
    const premiumUsers = users.filter((u: any) => u.isPremium);
    const freeUsers = users.filter((u: any) => !u.isPremium);
    
    const avgMDWPremium = premiumUsers.reduce((sum: number, u: any) => sum + u.meaningfulDays, 0) / premiumUsers.length || 0;
    const avgMDWFree = freeUsers.reduce((sum: number, u: any) => sum + u.meaningfulDays, 0) / freeUsers.length || 0;
    
    const avgCheckInsPremium = premiumUsers.reduce((sum: number, u: any) => sum + u.totalCheckIns, 0) / premiumUsers.length || 0;
    const avgCheckInsFree = freeUsers.reduce((sum: number, u: any) => sum + u.totalCheckIns, 0) / freeUsers.length || 0;
    
    const avgStreakPremium = premiumUsers.reduce((sum: number, u: any) => sum + u.longestStreak, 0) / premiumUsers.length || 0;
    const avgStreakFree = freeUsers.reduce((sum: number, u: any) => sum + u.longestStreak, 0) / freeUsers.length || 0;
    
    return {
      mdwImpact: {
        premium: avgMDWPremium.toFixed(2),
        free: avgMDWFree.toFixed(2),
        lift: ((avgMDWPremium / avgMDWFree - 1) * 100).toFixed(1) + '%',
      },
      checkInImpact: {
        premium: avgCheckInsPremium.toFixed(1),
        free: avgCheckInsFree.toFixed(1),
        lift: ((avgCheckInsPremium / avgCheckInsFree - 1) * 100).toFixed(1) + '%',
      },
      streakImpact: {
        premium: avgStreakPremium.toFixed(1),
        free: avgStreakFree.toFixed(1),
        lift: ((avgStreakPremium / avgStreakFree - 1) * 100).toFixed(1) + '%',
      },
      conversionTriggers: {
        '3+ MDW': users.filter((u: any) => u.isPremium && u.meaningfulDays >= 3).length,
        'High Engagement': users.filter((u: any) => u.isPremium && u.totalCheckIns >= 20).length,
        'Long Streak': users.filter((u: any) => u.isPremium && u.longestStreak >= 5).length,
      },
    };
  }
  
  private getChurnRisk() {
    const { users, checkIns, metadata } = this.data;
    
    const lastThreeDays = [metadata.totalDays - 3, metadata.totalDays - 2, metadata.totalDays - 1];
    
    const churnRisk = users.map((u: any) => {
      const recentCheckIns = checkIns.filter(
        (c: any) => c.userId === u.userId && lastThreeDays.includes(c.day)
      ).length;
      
      const recentActivity = recentCheckIns / 3;
      const previousActivity = u.totalCheckIns / metadata.totalDays;
      
      const activityDrop = previousActivity > 0 
        ? (previousActivity - recentActivity) / previousActivity
        : 0;
      
      let risk: 'low' | 'medium' | 'high' = 'low';
      if (recentCheckIns === 0) risk = 'high';
      else if (activityDrop > 0.5) risk = 'high';
      else if (activityDrop > 0.3) risk = 'medium';
      
      return {
        userId: u.userId,
        persona: u.persona,
        isPremium: u.isPremium,
        risk,
        recentActivity,
        previousActivity,
        activityDrop: (activityDrop * 100).toFixed(1) + '%',
      };
    });
    
    const highRisk = churnRisk.filter(r => r.risk === 'high');
    const mediumRisk = churnRisk.filter(r => r.risk === 'medium');
    const lowRisk = churnRisk.filter(r => r.risk === 'low');
    
    const premiumHighRisk = highRisk.filter(r => r.isPremium).length;
    
    return {
      summary: {
        highRisk: highRisk.length,
        mediumRisk: mediumRisk.length,
        lowRisk: lowRisk.length,
        premiumAtRisk: premiumHighRisk,
      },
      topRisks: highRisk.slice(0, 10),
    };
  }
}

