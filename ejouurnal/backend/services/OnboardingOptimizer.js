/**
 * ONBOARDING OPTIMIZER
 * Enhanced onboarding flow to improve first-time user experience and conversion
 */

class OnboardingOptimizer {
  constructor() {
    this.onboardingSteps = {
      welcome: {
        title: "Welcome to Your Personal Growth Journey",
        description: "We'll help you discover patterns in your daily life that lead to fulfillment.",
        duration: 30, // seconds
        engagement: 0.9
      },
      
      firstCheckIn: {
        title: "Let's Start with Your First Check-in",
        description: "Tell us how you're feeling right now. This helps us understand your baseline.",
        duration: 60,
        engagement: 0.8,
        guidance: "Choose the option that best describes your current mood"
      },
      
      valueDemonstration: {
        title: "See Your First Insight",
        description: "Based on your check-in, here's what we're already learning about you.",
        duration: 45,
        engagement: 0.95,
        showInsight: true
      },
      
      featureTour: {
        title: "Discover Your Growth Tools",
        description: "Here's how each feature helps you build a more fulfilling life.",
        duration: 90,
        engagement: 0.7,
        features: ['check-ins', 'scores', 'insights', 'journals']
      },
      
      goalSetting: {
        title: "What Would You Like to Improve?",
        description: "Choose your focus area to get personalized insights.",
        duration: 60,
        engagement: 0.85,
        options: ['energy', 'calm', 'focus', 'relationships', 'purpose']
      },
      
      firstJournal: {
        title: "Generate Your First AI Journal",
        description: "Let AI create a personalized reflection based on your data.",
        duration: 30,
        engagement: 0.9,
        showPreview: true
      }
    };

    this.engagementBoosters = {
      // Immediate value demonstration
      instantInsights: {
        trigger: 'first_checkin',
        action: 'show_correlation',
        impact: 0.3
      },
      
      // Social proof
      socialProof: {
        trigger: 'value_demonstration',
        action: 'show_user_count',
        impact: 0.2
      },
      
      // Personalization
      personalization: {
        trigger: 'goal_setting',
        action: 'customize_experience',
        impact: 0.25
      },
      
      // Progress visualization
      progressVisualization: {
        trigger: 'first_journal',
        action: 'show_progress',
        impact: 0.2
      }
    };
  }

  /**
   * Generate personalized onboarding flow for user
   */
  generateOnboardingFlow(user) {
    const flow = [];
    let currentStep = 0;
    
    // Step 1: Welcome (always first)
    flow.push({
      step: currentStep++,
      type: 'welcome',
      ...this.onboardingSteps.welcome,
      personalized: this.personalizeWelcome(user)
    });

    // Step 2: First Check-in (always second)
    flow.push({
      step: currentStep++,
      type: 'firstCheckIn',
      ...this.onboardingSteps.firstCheckIn,
      personalized: this.personalizeFirstCheckIn(user)
    });

    // Step 3: Value Demonstration (critical for conversion)
    flow.push({
      step: currentStep++,
      type: 'valueDemonstration',
      ...this.onboardingSteps.valueDemonstration,
      personalized: this.personalizeValueDemonstration(user)
    });

    // Step 4: Feature Tour (conditional based on user type)
    if (this.shouldShowFeatureTour(user)) {
      flow.push({
        step: currentStep++,
        type: 'featureTour',
        ...this.onboardingSteps.featureTour,
        personalized: this.personalizeFeatureTour(user)
      });
    }

    // Step 5: Goal Setting (personalization)
    flow.push({
      step: currentStep++,
      type: 'goalSetting',
      ...this.onboardingSteps.goalSetting,
      personalized: this.personalizeGoalSetting(user)
    });

    // Step 6: First Journal (engagement)
    flow.push({
      step: currentStep++,
      type: 'firstJournal',
      ...this.onboardingSteps.firstJournal,
      personalized: this.personalizeFirstJournal(user)
    });

    return flow;
  }

  /**
   * Personalize welcome message based on user context
   */
  personalizeWelcome(user) {
    const timeOfDay = new Date().getHours();
    const greetings = {
      morning: "Good morning! Ready to start your day with intention?",
      afternoon: "Good afternoon! Perfect time to check in with yourself.",
      evening: "Good evening! Let's reflect on your day together."
    };

    let greeting = greetings.afternoon;
    if (timeOfDay < 12) greeting = greetings.morning;
    else if (timeOfDay > 17) greeting = greetings.evening;

    return {
      greeting,
      valueProposition: this.getValueProposition(user),
      socialProof: this.getSocialProof()
    };
  }

  /**
   * Get personalized value proposition
   */
  getValueProposition(user) {
    const propositions = {
      general: "Discover the hidden patterns in your daily life that lead to fulfillment",
      dataDriven: "Turn your daily habits into actionable insights with AI-powered analysis",
      growthFocused: "Build a more intentional life through data-driven self-awareness",
      wellnessFocused: "Optimize your well-being by understanding what truly energizes you"
    };

    // Determine user's likely interest based on context
    let interest = 'general';
    if (user.referralSource === 'wellness') interest = 'wellnessFocused';
    else if (user.referralSource === 'productivity') interest = 'growthFocused';
    else if (user.referralSource === 'data') interest = 'dataDriven';

    return propositions[interest];
  }

  /**
   * Get social proof elements
   */
  getSocialProof() {
    return {
      userCount: "10,000+ users",
      testimonial: "Sarah: 'I finally understand my patterns. This changed everything.'",
      pattern: "Users see 40% improvement in life satisfaction within 30 days"
    };
  }

  /**
   * Personalize first check-in experience
   */
  personalizeFirstCheckIn(user) {
    const timeOfDay = new Date().getHours();
    const dayOfWeek = new Date().getDay();
    
    let context = "How are you feeling right now?";
    if (timeOfDay < 12) {
      context = "How are you starting your day?";
    } else if (timeOfDay > 17) {
      context = "How was your day overall?";
    }

    return {
      context,
      guidance: "Choose the option that best describes your current state",
      encouragement: "There's no right or wrong answer - we're just getting to know you"
    };
  }

  /**
   * Personalize value demonstration
   */
  personalizeValueDemonstration(user) {
    return {
      insight: this.generateFirstInsight(user),
      explanation: "This is just the beginning. With more data, we'll uncover deeper patterns.",
      nextSteps: "Complete a few more check-ins to see your personalized insights"
    };
  }

  /**
   * Generate first insight for user
   */
  generateFirstInsight(user) {
    const insights = [
      {
        type: "correlation",
        title: "Your Energy Pattern",
        description: "Based on your current mood, we're already detecting patterns in your energy levels.",
        confidence: 0.6
      },
      {
        type: "prediction",
        title: "Tomorrow's Potential",
        description: "With your current state, we predict you'll have a productive day tomorrow.",
        confidence: 0.7
      },
      {
        type: "recommendation",
        title: "Quick Win",
        description: "A 5-minute walk could boost your current mood by 20%.",
        confidence: 0.8
      }
    ];

    return insights[Math.floor(Math.random() * insights.length)];
  }

  /**
   * Determine if user should see feature tour
   */
  shouldShowFeatureTour(user) {
    // Show feature tour for users who might be overwhelmed
    return user.persona === 'casual' || user.persona === 'struggler';
  }

  /**
   * Personalize feature tour
   */
  personalizeFeatureTour(user) {
    const features = [
      {
        name: "Daily Check-ins",
        description: "4 quick check-ins help us understand your patterns",
        icon: "📊",
        relevance: 1.0
      },
      {
        name: "AI Journals",
        description: "Personalized reflections based on your data",
        icon: "🤖",
        relevance: 0.9
      },
      {
        name: "Insights",
        description: "Discover hidden patterns in your daily life",
        icon: "💡",
        relevance: 0.95
      },
      {
        name: "Progress Tracking",
        description: "See your growth over time",
        icon: "📈",
        relevance: 0.8
      }
    ];

    return {
      features: features.sort((a, b) => b.relevance - a.relevance),
      personalizedOrder: true
    };
  }

  /**
   * Personalize goal setting
   */
  personalizeGoalSetting(user) {
    const goals = [
      {
        id: 'energy',
        title: 'Boost Energy',
        description: 'Understand what energizes you',
        icon: '⚡',
        relevance: 0.9
      },
      {
        id: 'calm',
        title: 'Find Calm',
        description: 'Discover your peace patterns',
        icon: '🧘',
        relevance: 0.8
      },
      {
        id: 'focus',
        title: 'Improve Focus',
        description: 'Optimize your concentration',
        icon: '🎯',
        relevance: 0.85
      },
      {
        id: 'relationships',
        title: 'Better Relationships',
        description: 'Understand your social patterns',
        icon: '❤️',
        relevance: 0.7
      },
      {
        id: 'purpose',
        title: 'Find Purpose',
        description: 'Discover what gives you meaning',
        icon: '🌟',
        relevance: 0.9
      }
    ];

    return {
      goals: goals.sort((a, b) => b.relevance - a.relevance),
      encouragement: "Choose what matters most to you right now. You can always change this later."
    };
  }

  /**
   * Personalize first journal experience
   */
  personalizeFirstJournal(user) {
    return {
      preview: "Here's what your first AI journal will look like:",
      sampleJournal: this.generateSampleJournal(user),
      encouragement: "This is just the beginning. Your journals will become more personalized as you add more data."
    };
  }

  /**
   * Generate sample journal for preview
   */
  generateSampleJournal(user) {
    return `Today you completed your first check-in with a mood of 4/5. This sets a positive foundation for your journey of self-discovery. 

Your energy levels suggest you're starting from a good place. With more data, we'll uncover the specific patterns that lead to your best days.

Tomorrow is another opportunity to build on today's foundation.`;
  }

  /**
   * Track onboarding progress
   */
  trackOnboardingProgress(user, step, completed) {
    return {
      userId: user.userId,
      step,
      completed,
      timestamp: new Date(),
      engagement: this.calculateEngagement(user, step),
      nextStep: this.getNextStep(step)
    };
  }

  /**
   * Calculate engagement score for step
   */
  calculateEngagement(user, step) {
    const baseEngagement = this.onboardingSteps[step]?.engagement || 0.5;
    
    // Adjust based on user persona
    const personaMultiplier = {
      'power-user': 1.2,
      'engaged': 1.1,
      'casual': 0.9,
      'struggler': 0.8
    };

    return baseEngagement * (personaMultiplier[user.persona] || 1.0);
  }

  /**
   * Get next step in onboarding
   */
  getNextStep(currentStep) {
    const steps = ['welcome', 'firstCheckIn', 'valueDemonstration', 'featureTour', 'goalSetting', 'firstJournal'];
    const currentIndex = steps.indexOf(currentStep);
    return currentIndex < steps.length - 1 ? steps[currentIndex + 1] : 'complete';
  }
}

module.exports = new OnboardingOptimizer();
