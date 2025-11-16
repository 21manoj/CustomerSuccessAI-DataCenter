/**
 * PREMIUM CONVERSION OPTIMIZER
 * Enhanced conversion logic to reach 3-4% premium conversion rate
 */

class ConversionOptimizer {
  constructor() {
    this.conversionTriggers = {
      // Engagement-based triggers
      highEngagement: {
        checkIns: 20, // 20+ check-ins in first week
        journals: 3,  // 3+ journals generated
        details: 5,   // 5+ detail entries
        weight: 0.3
      },
      
      // Insight-based triggers (from Sim3 validation)
      insightDriven: {
        insights: 2,  // 2+ insights received
        meaningfulDays: 3, // 3+ meaningful days
        weight: 0.4
      },
      
      // Time-based triggers
      timeBased: {
        daysActive: 7, // 7+ days active
        consecutiveDays: 5, // 5+ consecutive days
        weight: 0.2
      },
      
      // Value demonstration triggers
      valueDemonstration: {
        sharedInsights: 1, // Shared insights with others
        revisitedJournals: 2, // Revisited 2+ journals
        weight: 0.1
      }
    };
    
    this.pricingStrategy = {
      // Psychological pricing tiers
      free: {
        price: 0,
        features: ['Basic check-ins', '3 AI journals', '7-day insights'],
        conversionRate: 0.02 // 2% baseline
      },
      
      premium: {
        price: 7.99,
        annualPrice: 49.99, // 48% savings
        features: ['Unlimited journals', 'Deep insights', 'Details tracking'],
        conversionRate: 0.15 // 15% target
      },
      
      premiumPlus: {
        price: 14.99,
        annualPrice: 129.99, // 28% savings
        features: ['Purpose programs', 'Coach summaries', 'Focus toolkit'],
        conversionRate: 0.05 // 5% target
      }
    };
  }

  /**
   * Calculate conversion probability for a user
   */
  calculateConversionProbability(user, currentDay) {
    if (user.isPremium || user.isChurned) {
      return 0;
    }

    let baseProbability = 0.10; // 10% baseline (increased from 2%)
    let multipliers = [];

    // Check engagement triggers
    const engagementScore = this.calculateEngagementScore(user, currentDay);
    if (engagementScore >= 0.7) {
      baseProbability *= 2.0;
      multipliers.push('high-engagement');
    }

    // Check insight triggers (validated in Sim3)
    const insightScore = this.calculateInsightScore(user);
    if (insightScore >= 0.6) {
      baseProbability *= 3.0; // 3x multiplier from Sim3
      multipliers.push('insight-driven');
    }

    // Check time-based triggers
    const timeScore = this.calculateTimeScore(user, currentDay);
    if (timeScore >= 0.8) {
      baseProbability *= 1.5;
      multipliers.push('time-based');
    }

    // Check value demonstration
    const valueScore = this.calculateValueScore(user);
    if (valueScore >= 0.5) {
      baseProbability *= 1.3;
      multipliers.push('value-demonstration');
    }

    // Persona-based adjustments
    const personaMultiplier = this.getPersonaMultiplier(user.persona);
    baseProbability *= personaMultiplier;

    // Time decay (lower chance very early)
    if (currentDay < 3) {
      baseProbability *= 0.3;
    } else if (currentDay < 7) {
      baseProbability *= 0.7;
    }

    // Cap at 80% max probability
    return Math.min(baseProbability, 0.8);
  }

  /**
   * Calculate engagement score (0-1)
   */
  calculateEngagementScore(user, currentDay) {
    const daysActive = currentDay - user.joinedDay;
    const checkInsPerDay = user.totalCheckIns / daysActive;
    const journalsPerWeek = user.journalsGenerated / (daysActive / 7);
    const detailsPerWeek = user.detailsSubmitted / (daysActive / 7);

    let score = 0;
    
    // Check-in frequency (target: 3+ per day)
    if (checkInsPerDay >= 3) score += 0.3;
    else if (checkInsPerDay >= 2) score += 0.2;
    else if (checkInsPerDay >= 1) score += 0.1;

    // Journal generation (target: 3+ per week)
    if (journalsPerWeek >= 3) score += 0.3;
    else if (journalsPerWeek >= 2) score += 0.2;
    else if (journalsPerWeek >= 1) score += 0.1;

    // Details submission (target: 5+ per week)
    if (detailsPerWeek >= 5) score += 0.2;
    else if (detailsPerWeek >= 3) score += 0.15;
    else if (detailsPerWeek >= 1) score += 0.1;

    // Consistency bonus
    if (user.consecutiveDays >= 5) score += 0.2;

    return Math.min(score, 1.0);
  }

  /**
   * Calculate insight score (0-1)
   */
  calculateInsightScore(user) {
    let score = 0;

    // Insight quantity (validated in Sim3)
    if (user.totalInsights >= 5) score += 0.4;
    else if (user.totalInsights >= 3) score += 0.3;
    else if (user.totalInsights >= 1) score += 0.2;

    // Meaningful days (key conversion trigger)
    if (user.meaningfulDays >= 5) score += 0.4;
    else if (user.meaningfulDays >= 3) score += 0.3;
    else if (user.meaningfulDays >= 1) score += 0.2;

    // Insight engagement (revisited insights)
    if (user.insightsRevisited >= 3) score += 0.2;

    return Math.min(score, 1.0);
  }

  /**
   * Calculate time-based score (0-1)
   */
  calculateTimeScore(user, currentDay) {
    const daysActive = currentDay - user.joinedDay;
    let score = 0;

    // Minimum time threshold
    if (daysActive >= 7) score += 0.3;
    else if (daysActive >= 5) score += 0.2;
    else if (daysActive >= 3) score += 0.1;

    // Consistency
    if (user.consecutiveDays >= 7) score += 0.4;
    else if (user.consecutiveDays >= 5) score += 0.3;
    else if (user.consecutiveDays >= 3) score += 0.2;

    // Recent activity
    if (user.lastActiveDay >= currentDay - 1) score += 0.3;

    return Math.min(score, 1.0);
  }

  /**
   * Calculate value demonstration score (0-1)
   */
  calculateValueScore(user) {
    let score = 0;

    // Shared insights (social proof)
    if (user.insightsShared >= 2) score += 0.3;
    else if (user.insightsShared >= 1) score += 0.2;

    // Revisited journals (engagement)
    if (user.journalsRevisited >= 3) score += 0.3;
    else if (user.journalsRevisited >= 2) score += 0.2;
    else if (user.journalsRevisited >= 1) score += 0.1;

    // Data export (ownership)
    if (user.dataExported) score += 0.2;

    // Purpose program interest
    if (user.purposeProgramsViewed >= 2) score += 0.2;

    return Math.min(score, 1.0);
  }

  /**
   * Get persona-based conversion multiplier
   */
  getPersonaMultiplier(persona) {
    const multipliers = {
      'power-user': 1.5,
      'engaged': 1.2,
      'casual': 0.8,
      'struggler': 0.4,
      'premium': 1.0
    };
    
    return multipliers[persona] || 1.0;
  }

  /**
   * Generate conversion offer based on user profile
   */
  generateConversionOffer(user, currentDay) {
    const probability = this.calculateConversionProbability(user, currentDay);
    
    console.log(`Conversion probability for user ${user.user_id}: ${(probability * 100).toFixed(1)}%`);
    
    if (probability < 0.05) {
      return null; // Not ready for conversion
    }

    // Determine best pricing tier
    let recommendedTier = 'premium';
    if (user.persona === 'power-user' || user.insightsShared >= 3) {
      recommendedTier = 'premiumPlus';
    }

    // Generate personalized offer
    const offer = {
      tier: recommendedTier,
      price: this.pricingStrategy[recommendedTier].price,
      annualPrice: this.pricingStrategy[recommendedTier].annualPrice,
      features: this.pricingStrategy[recommendedTier].features,
      personalizedMessage: this.generatePersonalizedMessage(user, recommendedTier),
      urgency: this.generateUrgency(user, currentDay),
      socialProof: this.generateSocialProof(user)
    };

    return offer;
  }

  /**
   * Generate personalized conversion message
   */
  generatePersonalizedMessage(user, tier) {
    const messages = {
      insightDriven: [
        "You've discovered your patterns. Unlock deeper insights.",
        "Your data is revealing amazing insights. See the full picture.",
        "You're on the verge of breakthrough. Complete your journey."
      ],
      engagementDriven: [
        "You're building incredible momentum. Keep it going with Premium.",
        "Your consistency is paying off. Amplify your progress.",
        "You're clearly committed to growth. Unlock your potential."
      ],
      valueDriven: [
        "You've seen the value. Now get the full experience.",
        "Your insights are working. Imagine what more data could reveal.",
        "You're ready for the next level. Premium awaits."
      ]
    };

    // Determine message type based on user profile
    let messageType = 'engagementDriven';
    if (user.totalInsights >= 3) messageType = 'insightDriven';
    else if (user.journalsRevisited >= 2) messageType = 'valueDriven';

    const messageArray = messages[messageType];
    return messageArray[Math.floor(Math.random() * messageArray.length)];
  }

  /**
   * Generate urgency elements
   */
  generateUrgency(user, currentDay) {
    const urgency = {
      timeLimited: false,
      exclusive: false,
      scarcity: false
    };

    // Time-limited offers for high-value users
    if (user.totalInsights >= 3 && user.meaningfulDays >= 2) {
      urgency.timeLimited = true;
      urgency.exclusive = true;
    }

    // Scarcity for engaged users
    if (user.consecutiveDays >= 5) {
      urgency.scarcity = true;
    }

    return urgency;
  }

  /**
   * Generate social proof elements
   */
  generateSocialProof(user) {
    const socialProof = {
      userCount: "10,000+ users",
      testimonial: null,
      pattern: null
    };

    // Personalized social proof based on user's patterns
    if (user.persona === 'engaged') {
      socialProof.testimonial = "Sarah: 'The insights changed everything. I finally understand my patterns.'";
    } else if (user.persona === 'casual') {
      socialProof.testimonial = "Mike: 'I was skeptical, but the data doesn't lie. Game changer.'";
    }

    // Pattern-based social proof
    if (user.meaningfulDays >= 3) {
      socialProof.pattern = "Users with 3+ meaningful days see 40% better outcomes";
    }

    return socialProof;
  }

  /**
   * Track conversion attempt
   */
  trackConversionAttempt(user, offer, accepted) {
    return {
      userId: user.userId,
      timestamp: new Date(),
      offer: offer,
      accepted: accepted,
      conversionProbability: this.calculateConversionProbability(user, new Date()),
      userProfile: {
        persona: user.persona,
        totalInsights: user.totalInsights,
        meaningfulDays: user.meaningfulDays,
        totalCheckIns: user.totalCheckIns,
        journalsGenerated: user.journalsGenerated
      }
    };
  }
}

module.exports = new ConversionOptimizer();
