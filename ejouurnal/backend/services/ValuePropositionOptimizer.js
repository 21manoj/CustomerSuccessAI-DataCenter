/**
 * VALUE PROPOSITION OPTIMIZER
 * Enhanced value proposition and benefits communication for premium features
 */

class ValuePropositionOptimizer {
  constructor() {
    this.valueProps = {
      // Core value propositions
      insights: {
        title: "Discover Your Hidden Patterns",
        description: "AI-powered insights reveal the connections between your daily choices and outcomes",
        benefits: [
          "See correlations you never noticed",
          "Understand what truly energizes you",
          "Predict your best days in advance"
        ],
        socialProof: "Users discover 3-5 new patterns within their first week"
      },
      
      personalization: {
        title: "Your Personal Growth Algorithm",
        description: "Every insight is tailored to your unique data and goals",
        benefits: [
          "Insights based on YOUR patterns, not generic advice",
          "Recommendations that actually work for you",
          "Progress tracking that matters to your life"
        ],
        socialProof: "95% of users say insights feel 'written just for me'"
      },
      
      progress: {
        title: "See Your Growth in Real-Time",
        description: "Track meaningful progress across all dimensions of your life",
        benefits: [
          "Quantify your personal growth",
          "Celebrate small wins that add up",
          "Stay motivated with visible progress"
        ],
        socialProof: "Users see 40% improvement in life satisfaction within 30 days"
      },
      
      efficiency: {
        title: "Optimize Your Daily Choices",
        description: "Make better decisions with data-driven insights",
        benefits: [
          "Stop guessing what works for you",
          "Focus on activities that actually matter",
          "Eliminate time-wasting habits"
        ],
        socialProof: "Users save 2+ hours per week by focusing on what works"
      }
    };

    this.premiumFeatures = {
      unlimitedJournals: {
        title: "Unlimited AI Journals",
        description: "Get personalized reflections in 4 different tones",
        value: "Save 30+ minutes daily on self-reflection",
        emotional: "Feel truly understood and supported"
      },
      
      deepInsights: {
        title: "Deep Lineage Analysis",
        description: "Advanced pattern detection and correlation analysis",
        value: "Discover insights that would take months to notice manually",
        emotional: "Finally understand why some days are better than others"
      },
      
      detailsTracking: {
        title: "Comprehensive Life Tracking",
        description: "Track sleep, nutrition, exercise, and social connections",
        value: "See the full picture of what affects your well-being",
        emotional: "Take control of all the factors that matter to you"
      },
      
      purposePrograms: {
        title: "Purpose Programs",
        description: "Guided 4-week tracks for specific life areas",
        value: "Structured path to meaningful change",
        emotional: "Feel like you have a personal coach guiding your growth"
      },
      
      coachSummaries: {
        title: "Professional Summaries",
        description: "Weekly PDF reports for you or your therapist",
        value: "Share your progress with healthcare providers",
        emotional: "Feel supported by your entire care team"
      }
    };

    this.pricingPsychology = {
      // Anchoring strategy
      anchor: {
        price: 29.99,
        label: "Premium+",
        description: "For power users and professionals"
      },
      
      // Recommended tier
      recommended: {
        price: 7.99,
        label: "Premium",
        description: "Most popular choice",
        savings: "Save 48% with annual billing"
      },
      
      // Free tier
      free: {
        price: 0,
        label: "Free",
        description: "Get started with basic features",
        limitations: "Limited to 3 journals and 7-day insights"
      }
    };
  }

  /**
   * Generate personalized value proposition for user
   */
  generateValueProposition(user, context = 'general') {
    const userProfile = this.analyzeUserProfile(user);
    const relevantValueProps = this.selectRelevantValueProps(userProfile, context);
    
    return {
      primary: relevantValueProps.primary,
      secondary: relevantValueProps.secondary,
      socialProof: this.generateSocialProof(userProfile),
      urgency: this.generateUrgency(userProfile),
      personalization: this.generatePersonalization(userProfile)
    };
  }

  /**
   * Analyze user profile for personalization
   */
  analyzeUserProfile(user) {
    return {
      persona: user.persona,
      engagement: this.calculateEngagement(user),
      goals: this.inferGoals(user),
      painPoints: this.identifyPainPoints(user),
      motivations: this.identifyMotivations(user)
    };
  }

  /**
   * Calculate user engagement level
   */
  calculateEngagement(user) {
    const daysActive = user.daysActive || 1;
    const checkInsPerDay = user.totalCheckIns / daysActive;
    const journalsPerWeek = user.journalsGenerated / (daysActive / 7);
    
    if (checkInsPerDay >= 3 && journalsPerWeek >= 2) return 'high';
    if (checkInsPerDay >= 2 && journalsPerWeek >= 1) return 'medium';
    return 'low';
  }

  /**
   * Infer user goals from behavior
   */
  inferGoals(user) {
    const goals = [];
    
    if (user.meaningfulDays >= 3) goals.push('purpose');
    if (user.totalCheckIns >= 20) goals.push('consistency');
    if (user.journalsGenerated >= 3) goals.push('reflection');
    if (user.detailsSubmitted >= 5) goals.push('optimization');
    
    return goals.length > 0 ? goals : ['general_improvement'];
  }

  /**
   * Identify user pain points
   */
  identifyPainPoints(user) {
    const painPoints = [];
    
    if (user.meaningfulDays < 2) painPoints.push('lack_of_meaning');
    if (user.totalCheckIns < 10) painPoints.push('inconsistency');
    if (user.journalsGenerated < 2) painPoints.push('lack_of_insight');
    
    return painPoints;
  }

  /**
   * Identify user motivations
   */
  identifyMotivations(user) {
    const motivations = [];
    
    if (user.persona === 'power-user') motivations.push('optimization');
    if (user.persona === 'engaged') motivations.push('growth');
    if (user.persona === 'casual') motivations.push('improvement');
    if (user.persona === 'struggler') motivations.push('support');
    
    return motivations;
  }

  /**
   * Select relevant value propositions
   */
  selectRelevantValueProps(userProfile, context) {
    const relevantProps = [];
    
    // Always include insights for engaged users
    if (userProfile.engagement === 'high') {
      relevantProps.push(this.valueProps.insights);
    }
    
    // Add personalization for users with specific goals
    if (userProfile.goals.length > 1) {
      relevantProps.push(this.valueProps.personalization);
    }
    
    // Add progress for users tracking meaningful days
    if (userProfile.goals.includes('purpose')) {
      relevantProps.push(this.valueProps.progress);
    }
    
    // Add efficiency for power users
    if (userProfile.persona === 'power-user') {
      relevantProps.push(this.valueProps.efficiency);
    }
    
    return {
      primary: relevantProps[0] || this.valueProps.insights,
      secondary: relevantProps.slice(1)
    };
  }

  /**
   * Generate social proof elements
   */
  generateSocialProof(userProfile) {
    const socialProof = {
      userCount: "10,000+ users",
      testimonials: [],
      patterns: []
    };

    // Add relevant testimonials
    if (userProfile.persona === 'engaged') {
      socialProof.testimonials.push("Sarah: 'The insights changed everything. I finally understand my patterns.'");
    } else if (userProfile.persona === 'casual') {
      socialProof.testimonials.push("Mike: 'I was skeptical, but the data doesn't lie. Game changer.'");
    } else if (userProfile.persona === 'struggler') {
      socialProof.testimonials.push("Alex: 'This gave me hope when I felt stuck. The insights are so accurate.'");
    }

    // Add relevant patterns
    if (userProfile.engagement === 'high') {
      socialProof.patterns.push("Users with high engagement see 40% better outcomes");
    } else if (userProfile.goals.includes('purpose')) {
      socialProof.patterns.push("Users focused on purpose see 60% more meaningful days");
    }

    return socialProof;
  }

  /**
   * Generate urgency elements
   */
  generateUrgency(userProfile) {
    const urgency = {
      timeLimited: false,
      exclusive: false,
      scarcity: false
    };

    // Time-limited offers for high-value users
    if (userProfile.engagement === 'high' && userProfile.goals.length >= 2) {
      urgency.timeLimited = true;
      urgency.exclusive = true;
    }

    // Scarcity for engaged users
    if (userProfile.engagement === 'medium' && userProfile.persona === 'engaged') {
      urgency.scarcity = true;
    }

    return urgency;
  }

  /**
   * Generate personalization elements
   */
  generatePersonalization(userProfile) {
    return {
      personalizedMessage: this.generatePersonalizedMessage(userProfile),
      relevantFeatures: this.selectRelevantFeatures(userProfile),
      customPricing: this.generateCustomPricing(userProfile)
    };
  }

  /**
   * Generate personalized message
   */
  generatePersonalizedMessage(userProfile) {
    const messages = {
      highEngagement: "You're clearly committed to growth. Premium will amplify your progress.",
      mediumEngagement: "You're building momentum. Premium will help you maintain it.",
      lowEngagement: "You're just getting started. Premium will accelerate your journey.",
      purposeFocused: "Your focus on purpose is inspiring. Premium will deepen your insights.",
      optimizationFocused: "You're clearly results-oriented. Premium will give you the data you need."
    };

    let messageType = 'lowEngagement';
    if (userProfile.engagement === 'high') messageType = 'highEngagement';
    else if (userProfile.engagement === 'medium') messageType = 'mediumEngagement';
    
    if (userProfile.goals.includes('purpose')) messageType = 'purposeFocused';
    else if (userProfile.persona === 'power-user') messageType = 'optimizationFocused';

    return messages[messageType];
  }

  /**
   * Select relevant premium features
   */
  selectRelevantFeatures(userProfile) {
    const features = [];
    
    // Always include core features
    features.push(this.premiumFeatures.unlimitedJournals);
    features.push(this.premiumFeatures.deepInsights);
    
    // Add relevant features based on profile
    if (userProfile.goals.includes('optimization')) {
      features.push(this.premiumFeatures.detailsTracking);
    }
    
    if (userProfile.goals.includes('purpose')) {
      features.push(this.premiumFeatures.purposePrograms);
    }
    
    if (userProfile.persona === 'power-user') {
      features.push(this.premiumFeatures.coachSummaries);
    }
    
    return features;
  }

  /**
   * Generate custom pricing based on user profile
   */
  generateCustomPricing(userProfile) {
    const basePricing = this.pricingPsychology.recommended;
    
    // Add discounts for high-value users
    if (userProfile.engagement === 'high' && userProfile.goals.length >= 2) {
      return {
        ...basePricing,
        discount: "20% off for committed users",
        finalPrice: 6.39,
        savings: "Save $1.60/month"
      };
    }
    
    return basePricing;
  }

  /**
   * Generate conversion offer
   */
  generateConversionOffer(user, context = 'general') {
    const valueProp = this.generateValueProposition(user, context);
    const features = this.selectRelevantFeatures(this.analyzeUserProfile(user));
    const pricing = this.generateCustomPricing(this.analyzeUserProfile(user));
    
    return {
      valueProposition: valueProp,
      features: features,
      pricing: pricing,
      callToAction: this.generateCallToAction(user),
      objections: this.anticipateObjections(user)
    };
  }

  /**
   * Generate call to action
   */
  generateCallToAction(user) {
    const userProfile = this.analyzeUserProfile(user);
    
    const ctas = {
      highEngagement: "Unlock Your Full Potential",
      mediumEngagement: "Take Your Growth to the Next Level",
      lowEngagement: "Start Your Transformation Today",
      purposeFocused: "Deepen Your Purpose Journey",
      optimizationFocused: "Get the Data You Need"
    };

    let ctaType = 'lowEngagement';
    if (userProfile.engagement === 'high') ctaType = 'highEngagement';
    else if (userProfile.engagement === 'medium') ctaType = 'mediumEngagement';
    
    if (userProfile.goals.includes('purpose')) ctaType = 'purposeFocused';
    else if (userProfile.persona === 'power-user') ctaType = 'optimizationFocused';

    return {
      primary: ctas[ctaType],
      secondary: "Start your 7-day free trial",
      urgency: "Limited time offer"
    };
  }

  /**
   * Anticipate and address objections
   */
  anticipateObjections(user) {
    const objections = [];
    
    // Common objections
    objections.push({
      objection: "I'm not sure if this will work for me",
      response: "That's why we offer a 7-day free trial. See the value before you commit.",
      socialProof: "95% of users see value within their first week"
    });
    
    objections.push({
      objection: "I don't have time for another app",
      response: "Our users save 2+ hours per week by focusing on what actually works.",
      socialProof: "Users report feeling more efficient, not more busy"
    });
    
    objections.push({
      objection: "I'm not sure about the price",
      response: "Less than a coffee per day for insights that could change your life.",
      socialProof: "Users say the insights are worth 10x the price"
    });
    
    return objections;
  }
}

module.exports = new ValuePropositionOptimizer();
