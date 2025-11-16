/**
 * LLMPromptEngine - Generate natural language insights and journals using AI
 * 
 * Supports:
 * - Daily journal generation (4 tone options)
 * - Insight explanations (make data human)
 * - Weekly summaries
 * - Personalized recommendations
 * 
 * Integrates with: OpenAI GPT-4, Anthropic Claude, or local LLMs
 */

import { CheckIn, DailyScores, LineageInsight, WeeklyIntention } from '../types/fulfillment';

type JournalTone = 'reflective' | 'factual' | 'coach-like' | 'poetic';

interface JournalData {
  date: Date;
  checkIns: CheckIn[];
  scores: DailyScores;
  bodyData: {
    sleepHours?: number;
    sleepQuality?: number;
    steps?: number;
    activeMinutes?: number;
    fuelQuality?: string;
  };
  mindData: {
    focusMinutes?: number;
    screenTime?: number;
    socialMediaMinutes?: number;
  };
  soulData: {
    microActs: string[];
    socialQuality?: string;
  };
  purposeData: {
    weeklyIntention?: string;
    microMovesCompleted: number;
    microMovesTotal: number;
    dailyPurposeCheck?: string;
  };
  patterns: {
    comparedToYesterday: any;
    comparedToLastWeek: any;
    topInsight?: LineageInsight;
  };
}

export class LLMPromptEngine {
  private apiKey: string;
  private provider: 'openai' | 'anthropic';

  constructor(provider: 'openai' | 'anthropic' = 'openai', apiKey: string) {
    this.provider = provider;
    this.apiKey = apiKey;
  }

  /**
   * DAILY JOURNAL GENERATION
   * Main prompt for creating end-of-day reflection
   */
  async generateDailyJournal(
    data: JournalData,
    tone: JournalTone = 'reflective'
  ): Promise<string> {
    const prompt = this.buildJournalPrompt(data, tone);
    return await this.callLLM(prompt, {
      maxTokens: 800,
      temperature: tone === 'poetic' ? 0.9 : 0.7,
      systemMessage: this.getSystemMessage(tone)
    });
  }

  /**
   * BUILD JOURNAL PROMPT
   */
  private buildJournalPrompt(data: JournalData, tone: JournalTone): string {
    const dateStr = data.date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      month: 'long', 
      day: 'numeric',
      year: 'numeric'
    });

    return `Generate a ${tone} daily journal entry for ${dateStr}.

USER'S DAY AT A GLANCE:
━━━━━━━━━━━━━━━━━━━━━
Check-ins completed: ${data.checkIns.length}/4
Mood progression: ${this.describeMoodProgression(data.checkIns)}
Contexts encountered: ${this.extractContexts(data.checkIns)}
Micro-acts performed: ${data.soulData.microActs.join(', ') || 'None'}

BODY & ENERGY:
━━━━━━━━━━━━━━
Sleep: ${data.bodyData.sleepHours?.toFixed(1)}h (Quality: ${data.bodyData.sleepQuality}/5 stars)
Activity: ${data.bodyData.steps?.toLocaleString()} steps, ${data.bodyData.activeMinutes} active minutes
Fuel quality: ${data.bodyData.fuelQuality || 'Not logged'}
Body Score: ${data.scores.bodyScore}/100

MIND & CLARITY:
━━━━━━━━━━━━━━
Focus time: ${data.mindData.focusMinutes || 0} minutes
Screen time: ${this.formatMinutes(data.mindData.screenTime)} total
Social media: ${this.formatMinutes(data.mindData.socialMediaMinutes)} (${this.compareTo baseline(data.mindData.socialMediaMinutes, 70)})
Mind Score: ${data.scores.mindScore}/100

SOUL & CONNECTION:
━━━━━━━━━━━━━━━━━
Micro-acts: ${data.soulData.microActs.length} today (${data.soulData.microActs.join(', ')})
Social quality: ${data.soulData.socialQuality || 'Not logged'}
Soul Score: ${data.scores.soulScore}/100

PURPOSE & DIRECTION:
━━━━━━━━━━━━━━━━━━
Weekly intention: "${data.purposeData.weeklyIntention || 'Not set'}"
Micro-moves: ${data.purposeData.microMovesCompleted}/${data.purposeData.microMovesTotal} completed (${Math.round(data.purposeData.microMovesCompleted / data.purposeData.microMovesTotal * 100)}%)
Daily purpose check: ${data.purposeData.dailyPurposeCheck || 'Not completed'}
Purpose Score: ${data.scores.purposeScore}/100

PATTERNS & COMPARISONS:
━━━━━━━━━━━━━━━━━━━━━
Compared to yesterday: ${this.describeComparison(data.patterns.comparedToYesterday)}
Compared to last ${data.date.toLocaleDateString('en-US', { weekday: 'long' })}: ${this.describeComparison(data.patterns.comparedToLastWeek)}
${data.patterns.topInsight ? `Key insight: "${data.patterns.topInsight.title}" - ${data.patterns.topInsight.description}` : ''}

FULFILLMENT SUMMARY:
━━━━━━━━━━━━━━━━━━━
Overall Score: ${data.scores.fulfillmentScore}/100
Meaningful Day: ${data.scores.isMeaningfulDay ? 'Yes ✨ - all dimensions met thresholds' : 'Not yet - continue building'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INSTRUCTIONS:
Generate a ${tone} journal entry following this structure:

1. Opening reflection (how the day unfolded, starting with morning)
2. Body & Energy section (sleep, activity, fuel - weave into narrative)
3. Mind & Focus section (mood progression, screen time impact, clarity)
4. Soul & Connection section (micro-acts, social quality, what brought meaning)
5. Purpose & Direction section (progress on weekly intention, micro-moves)
6. Patterns & Insights (comparisons to past, correlations from data)
7. Tomorrow's Opportunity (forward-looking suggestion based on patterns)
8. Summary line (scores + meaningful day status)

${this.getToneGuidelines(tone)}

Length: 400-600 words
Voice: ${tone === 'reflective' ? 'Second person (You...)' : tone === 'factual' ? 'Third person, clinical' : tone === 'coach-like' ? 'Direct, encouraging' : 'First person, contemplative'}

Make it feel personal, insightful, and actionable. This journal should make the user think "holy shit, this app really knows me."`;
  }

  /**
   * TONE-SPECIFIC GUIDELINES
   */
  private getToneGuidelines(tone: JournalTone): string {
    switch (tone) {
      case 'reflective':
        return `
TONE: Reflective & Personal
- Use "You..." voice (second person)
- Be encouraging but honest
- Highlight patterns they might not have noticed
- Connect data to feelings: "You felt energized after that walk because..."
- End with forward-looking hope
Example: "You started the morning feeling good after solid sleep. That energy carried through..."`;

      case 'factual':
        return `
TONE: Factual & Clinical
- Use data-first language
- Present numbers clearly
- Objective observations, no emotional language
- Clinical accuracy
- Bullet points acceptable
Example: "Sleep: 7.5h (Quality: 4/5). Activity: 8,234 steps. Mood average: 80/100..."`;

      case 'coach-like':
        return `
TONE: Coach-Like & Motivational
- Direct, encouraging voice
- Celebrate wins: "Great job on..."
- Identify opportunities: "Consider trying..."
- Action-oriented: concrete next steps
- Build momentum mindset
Example: "You crushed it with 7.5h sleep! That's 3 days in a row. Keep that streak alive..."`;

      case 'poetic':
        return `
TONE: Poetic & Contemplative
- Literary, metaphorical language
- First person perspective ("I rose with dawn...")
- Lyrical phrasing
- Emphasize beauty and meaning
- Philosophical reflections
Example: "October's amber light filtered through consciousness at dawn..."`;
    }
  }

  /**
   * SYSTEM MESSAGE (sets AI persona)
   */
  private getSystemMessage(tone: JournalTone): string {
    const baseMessage = `You are a personal journal writer for a fulfillment tracking app. Your job is to transform behavioral data into meaningful narrative that helps users understand themselves better.

Key principles:
- Make patterns visible that users can't see themselves
- Connect dots between body, mind, soul, and purpose
- Be data-grounded but human in expression
- Create "aha!" moments: "holy shit, social media really does drain me"
- Forward-looking: what to try tomorrow
- Privacy-conscious: never judge, only observe and suggest`;

    const toneSpecific = {
      reflective: 'Write in a warm, personal tone. You are a supportive friend who sees patterns.',
      factual: 'Write in a clinical, data-focused tone. You are a quantified-self analyst.',
      'coach-like': 'Write in an encouraging, motivational tone. You are a performance coach.',
      poetic: 'Write in a literary, contemplative tone. You are a mindful observer of life.'
    };

    return `${baseMessage}\n\n${toneSpecific[tone]}`;
  }

  /**
   * INSIGHT EXPLANATION
   * Convert technical correlation to human language
   */
  async explainInsight(insight: LineageInsight): Promise<string> {
    const prompt = `Explain this data pattern in simple, engaging language:

Type: ${insight.type}
Finding: ${insight.sourceMetric} → ${insight.targetMetric} (${insight.impact > 0 ? '+' : ''}${insight.impact} points)
${insight.lagDays ? `Lag: ${insight.lagDays} day(s)` : ''}
Confidence: ${insight.confidence}

Make it:
1. Clear (ELI5 level)
2. Actionable (what to do with this info)
3. Memorable (use metaphor or analogy)
4. Personal (address the user directly)

Length: 2-3 sentences max.`;

    return await this.callLLM(prompt, {
      maxTokens: 150,
      temperature: 0.7
    });
  }

  /**
   * WEEKLY SUMMARY
   * Synthesize week's worth of data into key themes
   */
  async generateWeeklySummary(
    weekData: {
      dailyJournals: string[];
      topInsights: LineageInsight[];
      mdwCount: number;
      avgScores: any;
      intention: string;
      microMovesCompleted: number;
    }
  ): Promise<string> {
    const prompt = `Generate a weekly summary report.

WEEK OVERVIEW:
Meaningful Days: ${weekData.mdwCount}/7
Average Scores: Body ${weekData.avgScores.body}, Mind ${weekData.avgScores.mind}, Soul ${weekData.avgScores.soul}, Purpose ${weekData.avgScores.purpose}

WEEKLY INTENTION:
"${weekData.intention}"
Progress: ${weekData.microMovesCompleted}/3 micro-moves completed

TOP INSIGHTS THIS WEEK:
${weekData.topInsights.map((ins, i) => `${i + 1}. ${ins.title} (${ins.impact > 0 ? '+' : ''}${ins.impact} pts)`).join('\n')}

DAILY THEMES:
${weekData.dailyJournals.map((j, i) => `Day ${i + 1}: ${j.split('\n')[0].substring(0, 100)}...`).join('\n')}

Create a cohesive weekly narrative that:
1. Celebrates wins (MDW count, patterns discovered)
2. Identifies the week's core theme or challenge
3. Shows progress on weekly intention
4. Highlights most important insight
5. Suggests focus for next week

Length: 200-300 words
Tone: Reflective and forward-looking`;

    return await this.callLLM(prompt, {
      maxTokens: 500,
      temperature: 0.7
    });
  }

  /**
   * PERSONALIZED RECOMMENDATION
   * "What to try next" based on insights
   */
  async generateRecommendation(
    topInsights: LineageInsight[],
    currentScores: DailyScores,
    weeklyIntention?: string
  ): Promise<string> {
    const lowestDimension = this.findLowestDimension(currentScores);
    const mostImpactfulInsight = topInsights[0];

    const prompt = `Generate a personalized recommendation.

CURRENT STATE:
Lowest dimension: ${lowestDimension.name} (${lowestDimension.score}/100)
Most impactful pattern: ${mostImpactfulInsight?.title} (${mostImpactfulInsight?.impact} pts impact)
Weekly intention: "${weeklyIntention || 'Not set'}"

Create ONE specific, actionable recommendation that:
1. Addresses the lowest dimension
2. Uses the most impactful insight
3. Aligns with weekly intention
4. Is realistic (takes <30 min)
5. Has clear success criteria

Format:
🎯 [Action Title]
[2-3 sentence explanation of why this will help]
[Specific instructions: when, how long, what to do]

Example:
🎯 Try a 20-minute morning walk tomorrow
Your data shows morning movement boosts next-day focus by +12 points. Walking before 10am activates your body without over-stressing it, setting up mental clarity for the full day.
Tomorrow: Set alarm for 7am, walk around the block for 20 minutes, come back and do your morning check-in.`;

    return await this.callLLM(prompt, {
      maxTokens: 200,
      temperature: 0.7
    });
  }

  /**
   * COACH SUMMARY (Premium Feature)
   * Generate PDF summary for therapist/coach
   */
  async generateCoachSummary(
    userId: string,
    weekData: any,
    userConsent: boolean
  ): Promise<string> {
    if (!userConsent) {
      throw new Error('User has not consented to coach sharing');
    }

    const prompt = `Generate a professional summary for this user's therapist/coach.

WEEKLY DATA:
[Same data as weekly summary, but formatted for clinical audience]

Create a structured report:
1. Overview (MDW, overall trends)
2. Strengths (what's working well)
3. Challenges (what needs support)
4. Patterns (clinically relevant observations)
5. Recommendations (for therapeutic discussion)

Tone: Professional, clinical, respectful
Privacy: NO personal identifying details, only behavioral patterns
Length: 300-400 words`;

    return await this.callLLM(prompt, {
      maxTokens: 600,
      temperature: 0.5 // Lower temp for clinical accuracy
    });
  }

  /**
   * CALL LLM API
   */
  private async callLLM(
    prompt: string,
    options: {
      maxTokens: number;
      temperature: number;
      systemMessage?: string;
    }
  ): Promise<string> {
    if (this.provider === 'openai') {
      return await this.callOpenAI(prompt, options);
    } else {
      return await this.callAnthropic(prompt, options);
    }
  }

  /**
   * OpenAI GPT-4 Integration
   */
  private async callOpenAI(prompt: string, options: any): Promise<string> {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        model: 'gpt-4-turbo-preview',
        messages: [
          {
            role: 'system',
            content: options.systemMessage || 'You are a helpful assistant.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        max_tokens: options.maxTokens,
        temperature: options.temperature
      })
    });

    const data = await response.json();
    return data.choices[0].message.content;
  }

  /**
   * Anthropic Claude Integration
   */
  private async callAnthropic(prompt: string, options: any): Promise<string> {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.apiKey,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-3-sonnet-20240229',
        max_tokens: options.maxTokens,
        messages: [
          {
            role: 'user',
            content: `${options.systemMessage}\n\n${prompt}`
          }
        ],
        temperature: options.temperature
      })
    });

    const data = await response.json();
    return data.content[0].text;
  }

  /**
   * HELPER: Describe mood progression
   */
  private describeMoodProgression(checkIns: CheckIn[]): string {
    const moods = checkIns.map(c => c.mood);
    const moodEmojis: Record<string, string> = {
      'very-low': '😢',
      'low': '😕',
      'neutral': '😐',
      'good': '🙂',
      'great': '😊'
    };

    return moods.map(m => moodEmojis[m] || '😐').join(' → ');
  }

  /**
   * HELPER: Extract contexts
   */
  private extractContexts(checkIns: CheckIn[]): string {
    const allContexts = checkIns.flatMap(c => c.contexts);
    const contextCounts = new Map<string, number>();
    
    allContexts.forEach(ctx => {
      contextCounts.set(ctx, (contextCounts.get(ctx) || 0) + 1);
    });

    return Array.from(contextCounts.entries())
      .map(([ctx, count]) => `${ctx} (${count}x)`)
      .join(', ');
  }

  /**
   * HELPER: Format minutes
   */
  private formatMinutes(minutes?: number): string {
    if (!minutes) return '0 min';
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  }

  /**
   * HELPER: Compare to baseline
   */
  private compareToBaseline(value: number, baseline: number): string {
    const diff = value - baseline;
    if (diff > 5) return `+${diff}m above baseline`;
    if (diff < -5) return `${diff}m below baseline`;
    return 'at baseline';
  }

  /**
   * HELPER: Describe comparison
   */
  private describeComparison(comparison: any): string {
    if (!comparison) return 'No comparison data';
    
    const diff = comparison.scoreDiff;
    if (diff > 5) return `+${diff} points higher`;
    if (diff < -5) return `${diff} points lower`;
    return 'Similar scores';
  }

  /**
   * HELPER: Find lowest dimension
   */
  private findLowestDimension(scores: DailyScores): { name: string; score: number } {
    const dimensions = [
      { name: 'Body', score: scores.bodyScore },
      { name: 'Mind', score: scores.mindScore },
      { name: 'Soul', score: scores.soulScore },
      { name: 'Purpose', score: scores.purposeScore }
    ];

    return dimensions.reduce((lowest, current) => 
      current.score < lowest.score ? current : lowest
    );
  }
}

/**
 * EXAMPLE USAGE:
 * 
 * const promptEngine = new LLMPromptEngine('openai', process.env.OPENAI_API_KEY);
 * 
 * // Generate daily journal
 * const journal = await promptEngine.generateDailyJournal(journalData, 'reflective');
 * 
 * // Explain an insight
 * const explanation = await promptEngine.explainInsight(insight);
 * 
 * // Generate weekly summary
 * const weeklySummary = await promptEngine.generateWeeklySummary(weekData);
 * 
 * // Get personalized recommendation
 * const recommendation = await promptEngine.generateRecommendation(insights, scores, intention);
 */

export default LLMPromptEngine;

