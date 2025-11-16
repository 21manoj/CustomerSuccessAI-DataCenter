/**
 * AI JOURNAL GENERATOR
 * Uses OpenAI GPT-4o-mini to generate personalized daily journals
 */

const OpenAI = require('openai');

class JournalGenerator {
  constructor() {
    this.openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });
  }

  /**
   * Generate daily journal based on user's check-ins and activities
   */
  async generateJournal(userData, tone = 'reflective') {
    const {
      checkIns = [],
      details = {},
      scores = {},
      weeklyIntention = '',
      microMoves = [],
      previousJournals = [],
      personalNotes = '',
      insights = [],
      isPremium = false,
    } = userData;

    // Build different prompts for free vs premium
    const prompt = isPremium
      ? this.buildPremiumPrompt(userData, tone)
      : this.buildPrompt(userData, tone);

    try {
      const completion = await this.openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: this.getSystemPrompt(tone),
          },
          {
            role: 'user',
            content: prompt,
          },
        ],
        temperature: tone === 'poetic' ? 0.9 : tone === 'factual' ? 0.3 : 0.7,
        max_tokens: 800,
      });

      return completion.choices[0].message.content;
    } catch (error) {
      console.error('Error generating journal:', error);
      // Fallback to template
      return this.generateTemplate(userData, tone);
    }
  }

  /**
   * System prompts for different tones - ENHANCED FOR ENGAGEMENT
   */
  getSystemPrompt(tone) {
    const prompts = {
      reflective: `You are a thoughtful, gentle journal writer who creates deeply personal daily summaries. Your goal is to help users feel SEEN and UNDERSTOOD. Create introspective content that reveals hidden patterns, celebrates small wins, and provides gentle insights. Be warm, insightful, and encouraging. Focus on emotional connections and personal growth. Use specific details from their data to make it feel truly personalized. End with a forward-looking insight that motivates continued engagement.`,
      
      'coach-like': `You are an energetic, supportive life coach who celebrates progress and drives action. Write motivating daily summaries that highlight wins, identify breakthrough moments, and suggest specific next steps. Be direct, enthusiastic, and data-driven. Use casual language and strategic emojis. Focus on momentum and growth. Make users feel like they're making real progress. End with a challenge or goal for tomorrow.`,
      
      poetic: `You are a contemplative writer who finds beauty and meaning in daily life. Create lyrical, metaphor-rich journals that transform data into meaningful narrative. Use imagery, rhythm, and emotional resonance. Be brief but profound. Connect the mundane to the meaningful. Help users see their day as part of a larger story. End with a beautiful, forward-looking metaphor.`,
      
      factual: `You are a precise data analyst who creates clear, actionable daily summaries. Present specific numbers, patterns, and comparisons in an engaging way. Be objective but not boring. Use bullet points and concrete observations. Highlight trends and correlations. Make data feel personal and relevant. End with a data-driven insight or recommendation.`,
      
      // NEW ENGAGEMENT-FOCUSED TONES
      'celebratory': `You are an enthusiastic cheerleader who celebrates every win, no matter how small. Write uplifting daily summaries that highlight achievements, positive patterns, and moments of growth. Be genuinely excited about their progress. Use encouraging language and celebrate their commitment to self-improvement. End with a celebration of what they accomplished today.`,
      
      'insightful': `You are a wise mentor who reveals hidden patterns and connections. Write analytical daily summaries that uncover surprising insights from their data. Connect dots between sleep, mood, activities, and outcomes. Reveal cause-and-effect relationships. Help users understand themselves better through data. End with a profound insight about their patterns.`,
      
      'motivational': `You are a high-energy motivator who drives action and momentum. Write dynamic daily summaries that challenge users to push further. Highlight areas for improvement while celebrating progress. Use powerful, action-oriented language. Set specific goals and challenges. End with a rallying cry for tomorrow's potential.`,
    };

    return prompts[tone] || prompts.reflective;
  }

  /**
   * Build premium prompt with advanced insights
   */
  buildPremiumPrompt(userData, tone) {
    const { checkIns = [], insights = [], weeklyIntention, microMoves = [] } = userData;
    
    let prompt = `Write a strategic, deeply personalized journal for a PREMIUM user.\n\n`;
    
    // Include premium insights
    if (insights && insights.length > 0) {
      prompt += `PREMIUM INSIGHT DATA:\n`;
      insights.forEach(insight => {
        if (insight.type === 'BREAKPOINT' || insight.type === 'breakpoint') {
          prompt += `- BREAKPOINT: ${insight.title}\n`;
          prompt += `  Description: ${insight.description}\n`;
        }
        if (insight.type === 'PURPOSE-PATH' || insight.type === 'purpose-path') {
          prompt += `- PURPOSE-PATH: ${insight.title}\n`;
          prompt += `  Description: ${insight.description}\n`;
        }
        if (insight.confidence) {
          prompt += `  Confidence: ${Math.round(insight.confidence * 100)}%\n`;
        }
      });
      prompt += `\n`;
    }
    
    prompt += `PREMIUM INSTRUCTIONS:\n`;
    prompt += `1. Use their personal thresholds and breakpoints in specific terms (e.g., "Your 6.8hr sleep threshold...")\n`;
    prompt += `2. Provide strategic guidance using PURPOSE-PATH data\n`;
    prompt += `3. Suggest ONE high-confidence micro-move based on their success patterns\n`;
    prompt += `4. Include predictive insight: "Based on your patterns, you'll likely feel X on Y day"\n`;
    prompt += `5. Connect their data to their weekly intention with specific actionable steps\n`;
    prompt += `6. Length: 250-350 words, transformational tone\n`;
    prompt += `7. Make them feel like a VIP with exclusive insights\n`;
    
    return prompt;
  }

  /**
   * Build the prompt from user data
   */
  buildPrompt(userData, tone) {
    const {
      checkIns = [],
      details = {},
      scores = {},
      weeklyIntention = '',
      microMoves = [],
      personalNotes = '',
      previousJournals = [],
      insights = [],
      date = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }),
    } = userData;

    // Calculate stats
    const avgMood = checkIns.length > 0 
      ? checkIns.reduce((sum, c) => sum + c.mood, 0) / checkIns.length 
      : 3;
    
    const microActs = checkIns.filter(c => c.microAct).map(c => c.microAct);
    const contexts = [...new Set(checkIns.flatMap(c => c.contexts || []))];

    let prompt = `Generate a ${tone} daily journal for ${date}.\n\n`;
    
    prompt += `CHECK-INS:\n`;
    prompt += `- Completed: ${checkIns.length}/4 check-ins\n`;
    prompt += `- Average mood: ${avgMood.toFixed(1)}/5\n`;
    if (contexts.length > 0) {
      prompt += `- Contexts: ${contexts.join(', ')}\n`;
    }
    if (microActs.length > 0) {
      prompt += `- Micro-acts: ${microActs.join(', ')}\n`;
    }
    prompt += `\n`;

    if (details.sleepHours) {
      prompt += `SLEEP & ACTIVITY:\n`;
      prompt += `- Sleep: ${details.sleepHours} hours (Quality: ${details.sleepQuality}/5)\n`;
      if (details.steps) {
        prompt += `- Activity: ${details.steps.toLocaleString()} steps\n`;
      }
      if (details.exerciseType) {
        let exerciseDetail = `- Exercise: ${details.exerciseDuration} min ${details.exerciseType}`;
        if (details.exerciseIntensity) {
          exerciseDetail += ` (${details.exerciseIntensity} intensity)`;
        }
        if (details.exerciseFeeling) {
          exerciseDetail += ` - Felt: ${details.exerciseFeeling}`;
        }
        prompt += exerciseDetail + `\n`;
      }
      if (details.hydration) {
        prompt += `- Hydration: ${details.hydration} glasses water\n`;
      }
      if (details.foodQuality) {
        prompt += `- Food quality: ${details.foodQuality}/5\n`;
      }
      if (details.socialMinutes) {
        prompt += `- Quality social time: ${details.socialMinutes} minutes\n`;
      }
      if (details.screenMinutes) {
        prompt += `- Screen time: ${Math.floor(details.screenMinutes / 60)}h ${details.screenMinutes % 60}min\n`;
      }
      prompt += `\n`;
    }

    if (details.breakfast || details.lunch || details.dinner || details.breakfastNotes || details.lunchNotes || details.dinnerNotes) {
      prompt += `NUTRITION:\n`;
      if (details.breakfast) prompt += `- Breakfast quality: ${details.breakfast}/5\n`;
      if (details.breakfastNotes) prompt += `  Details: ${details.breakfastNotes}\n`;
      if (details.lunch) prompt += `- Lunch quality: ${details.lunch}/5\n`;
      if (details.lunchNotes) prompt += `  Details: ${details.lunchNotes}\n`;
      if (details.dinner) prompt += `- Dinner quality: ${details.dinner}/5\n`;
      if (details.dinnerNotes) prompt += `  Details: ${details.dinnerNotes}\n`;
      prompt += `\n`;
      prompt += `IMPORTANT: If user provided meal details (e.g., "oatmeal with berries", "chicken salad"), analyze nutritional content:\n`;
      prompt += `- Identify macro-nutrients (protein, carbs, fats)\n`;
      prompt += `- Note micro-nutrients (iron, vitamins, fiber)\n`;
      prompt += `- Assess balance and provide gentle insights\n`;
      prompt += `- Be specific: "Your oatmeal with berries provided fiber and antioxidants"\n`;
      prompt += `\n`;
    }

    if (scores.body || scores.mind || scores.soul || scores.purpose) {
      prompt += `SCORES:\n`;
      if (scores.body) prompt += `- Body: ${scores.body}/100\n`;
      if (scores.mind) prompt += `- Mind: ${scores.mind}/100\n`;
      if (scores.soul) prompt += `- Soul: ${scores.soul}/100\n`;
      if (scores.purpose) prompt += `- Purpose: ${scores.purpose}/100\n`;
      if (scores.overall) prompt += `- Overall Fulfillment: ${scores.overall}/100\n`;
      prompt += `\n`;
    }

    if (weeklyIntention) {
      prompt += `WEEKLY INTENTION:\n`;
      prompt += `"${weeklyIntention}"\n`;
      if (microMoves.length > 0) {
        const completed = microMoves.filter(m => m.completed).length;
        prompt += `Micro-moves: ${completed}/${microMoves.length} completed\n`;
      }
      prompt += `\n`;
    }

    if (personalNotes) {
      prompt += `USER'S PERSONAL NOTES:\n`;
      prompt += `"${personalNotes}"\n`;
      prompt += `(Weave these thoughts naturally into the journal)\n`;
      prompt += `\n`;
    }

    if (previousJournals.length > 0) {
      prompt += `CONTEXT (Recent patterns):\n`;
      prompt += `- ${previousJournals.length} previous journal entries available\n`;
      prompt += `- Look for patterns and progress over time\n`;
      prompt += `\n`;
    }

    if (insights && insights.length > 0) {
      prompt += `AI INSIGHTS:\n`;
      insights.forEach((insight, idx) => {
        prompt += `${idx + 1}. ${insight.title} (${Math.round(insight.confidence * 100)}% confidence):\n`;
        prompt += `   ${insight.description}\n`;
      });
      prompt += `\n`;
      prompt += `CRITICAL: Weave these insights prominently into the journal naturally. Reference them as "patterns you've discovered" or "what the data reveals". Make insights feel like discoveries, not just facts.\n`;
      prompt += `\n`;
    }

    prompt += `INSTRUCTIONS:\n`;
    prompt += `- Write in ${tone} tone\n`;
    prompt += `- Length: 200-300 words (more engaging content)\n`;
    prompt += `- Make it deeply personal and specific to this data\n`;
    prompt += `- If user provided personal notes, integrate them naturally\n`;
    prompt += `- Focus on connections, insights, and emotional resonance\n`;
    prompt += `- Use specific details to create "aha moments"\n`;
    prompt += `- Highlight patterns and correlations that surprise them\n`;
    prompt += `- Celebrate small wins and progress\n`;
    prompt += `- End with an inspiring forward-looking thought or challenge\n`;
    prompt += `- Make them feel SEEN and UNDERSTOOD\n`;
    prompt += `- Create content they'll want to share or revisit\n`;

    return prompt;
  }

  /**
   * Fallback template generator (if API fails)
   */
  generateTemplate(userData, tone) {
    const { checkIns = [], scores = {}, details = {} } = userData;
    
    const avgMood = checkIns.length > 0 
      ? checkIns.reduce((sum, c) => sum + c.mood, 0) / checkIns.length 
      : 3;

    const moodText = avgMood >= 4 ? 'positive' : avgMood >= 3 ? 'balanced' : 'challenging';
    
    if (tone === 'factual') {
      return `Daily Summary - ${new Date().toLocaleDateString()}

Check-ins: ${checkIns.length}/4 completed
Average Mood: ${avgMood.toFixed(1)}/5 (${moodText})
Sleep: ${details.sleepHours || 'Not logged'} hours
Activity: ${details.steps || 'Not logged'} steps

Scores:
- Body: ${scores.body || 'N/A'}/100
- Mind: ${scores.mind || 'N/A'}/100
- Soul: ${scores.soul || 'N/A'}/100
- Purpose: ${scores.purpose || 'N/A'}/100
- Overall: ${scores.overall || 'N/A'}/100

Status: ${checkIns.length === 4 ? 'All check-ins complete' : `${4 - checkIns.length} check-ins remaining`}`;
    }

    // Default reflective template
    return `Today you completed ${checkIns.length} check-ins with an average mood of ${avgMood.toFixed(1)}/5. ${
      details.sleepHours ? `Your ${details.sleepHours} hours of sleep` : 'Your rest'
    } set the foundation for the day. ${
      checkIns.filter(c => c.microAct).length > 0 
        ? `You practiced ${checkIns.filter(c => c.microAct).map(c => c.microAct).join(' and ')}, building your inner strength.` 
        : ''
    }

Your fulfillment score of ${scores.overall || 'N/A'}/100 reflects ${
      scores.overall >= 70 ? 'strong alignment across all dimensions' : 'room for growth in key areas'
    }. ${
      checkIns.length === 4 
        ? 'Completing all four check-ins shows commitment to your journey.' 
        : 'Consider completing all check-ins tomorrow for deeper insights.'
    }

Tomorrow is another opportunity to build on today's foundation.`;
  }

  /**
   * Regenerate journal with new tone (preserving personal notes)
   */
  async regenerateJournal(existingJournal, newTone, personalNotes = '') {
    const userData = {
      ...existingJournal.userData,
      personalNotes,
    };

    return this.generateJournal(userData, newTone);
  }

  /**
   * Generate high-engagement journal with enhanced prompts
   */
  async generateEngagingJournal(userData, tone = 'reflective') {
    // Add engagement boosters to the prompt
    const enhancedUserData = {
      ...userData,
      engagementBoost: true,
      includeInsights: true,
      includePatterns: true,
      includeCelebrations: true,
    };

    const prompt = this.buildEnhancedPrompt(enhancedUserData, tone);

    try {
      const completion = await this.openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: this.getEnhancedSystemPrompt(tone),
          },
          {
            role: 'user',
            content: prompt,
          },
        ],
        temperature: tone === 'poetic' ? 0.9 : tone === 'factual' ? 0.3 : 0.7,
        max_tokens: 1000, // Increased for more engaging content
      });

      return completion.choices[0].message.content;
    } catch (error) {
      console.error('Error generating engaging journal:', error);
      return this.generateTemplate(userData, tone);
    }
  }

  /**
   * Enhanced system prompts for maximum engagement
   */
  getEnhancedSystemPrompt(tone) {
    const basePrompt = this.getSystemPrompt(tone);
    
    return `${basePrompt}

CRITICAL ENGAGEMENT REQUIREMENTS:
- Create content that users will want to read and share
- Use specific, surprising insights from their data
- Make them feel like the journal was written just for them
- Include at least one "wow, I never noticed that" moment
- Use emotional language that resonates
- Create a sense of progress and momentum
- End with something that makes them excited for tomorrow`;
  }

  /**
   * Build enhanced prompt with engagement focus
   */
  buildEnhancedPrompt(userData, tone) {
    const basePrompt = this.buildPrompt(userData, tone);
    
    return `${basePrompt}

ENGAGEMENT FOCUS:
- Look for surprising correlations in their data
- Highlight unique patterns that make them special
- Connect their actions to their feelings and outcomes
- Use their specific words and phrases from personal notes
- Create a narrative arc for their day
- Make predictions about tomorrow based on today's patterns
- Include specific, actionable insights they can use immediately`;
  }
}

module.exports = new JournalGenerator();

