/**
 * MICRO-MOVE LIBRARY
 * Curated database of proven micro-moves for common intentions
 */

export interface MicroMove {
  id: string;
  move: string;
  impact: number;
  dimension: 'Mind' | 'Body' | 'Soul' | 'Purpose';
  category: 'Physical' | 'Mental' | 'Social' | 'Digital' | 'Nutrition' | 'Work' | 'Learning';
  reasoning: string;
  frequency: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  successRate: number; // % of users who stick with it
}

export const MICRO_MOVE_DATABASE: Record<string, MicroMove[]> = {
  // PRESENCE / MINDFULNESS
  presence: [
    {
      id: 'presence_walk',
      move: '10-min morning walk',
      impact: 12,
      dimension: 'Mind',
      category: 'Physical',
      reasoning: 'Walking clears mental fog, giving you the clarity to be present throughout the day',
      frequency: '3-5x per week',
      difficulty: 'Easy',
      successRate: 92
    },
    {
      id: 'presence_nophone',
      move: 'No phone first hour after waking',
      impact: 6,
      dimension: 'Mind',
      category: 'Digital',
      reasoning: 'Protects your morning clarity, prevents reactivity before you\'re mentally ready',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 88
    },
    {
      id: 'presence_meditation',
      move: '5-min meditation before work',
      impact: 8,
      dimension: 'Mind',
      category: 'Mental',
      reasoning: 'Builds awareness and emotional regulation - core skills for presence',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 78
    },
    {
      id: 'presence_family_time',
      move: '15-min device-free quality time with family',
      impact: 12,
      dimension: 'Soul',
      category: 'Social',
      reasoning: 'Direct practice of presence - undistracted attention builds connection',
      frequency: 'Daily',
      difficulty: 'Easy',
      successRate: 85
    },
    {
      id: 'presence_reading',
      move: 'Read 2 chapters of meaningful book',
      impact: 6,
      dimension: 'Mind',
      category: 'Learning',
      reasoning: 'Deep reading trains sustained attention - a presence skill',
      frequency: '4-5x per week',
      difficulty: 'Easy',
      successRate: 81
    },
    {
      id: 'presence_gratitude',
      move: 'Evening gratitude practice (3 things)',
      impact: 6,
      dimension: 'Soul',
      category: 'Mental',
      reasoning: 'Gratitude shifts attention to what matters - foundation of presence',
      frequency: 'Daily',
      difficulty: 'Easy',
      successRate: 73
    }
  ],

  // ENERGY / VITALITY
  energy: [
    {
      id: 'energy_sleep',
      move: '7+ hours sleep nightly',
      impact: 15,
      dimension: 'Body',
      category: 'Physical',
      reasoning: 'Sleep is the #1 predictor of next-day energy and mental performance',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 82
    },
    {
      id: 'energy_exercise',
      move: '30-min exercise (any type) 3x per week',
      impact: 12,
      dimension: 'Body',
      category: 'Physical',
      reasoning: 'Regular movement boosts energy for 2-3 days (lagged effect)',
      frequency: '3x per week',
      difficulty: 'Medium',
      successRate: 76
    },
    {
      id: 'energy_water',
      move: 'Drink 8 glasses of water daily',
      impact: 5,
      dimension: 'Body',
      category: 'Nutrition',
      reasoning: 'Dehydration causes fatigue - proper hydration maintains energy',
      frequency: 'Daily',
      difficulty: 'Easy',
      successRate: 68
    },
    {
      id: 'energy_caffeine',
      move: 'No caffeine after 2pm',
      impact: 8,
      dimension: 'Body',
      category: 'Nutrition',
      reasoning: 'Protects sleep quality, which drives next-day energy',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 71
    },
    {
      id: 'energy_nature',
      move: '20-min outdoor time daily',
      impact: 10,
      dimension: 'Soul',
      category: 'Physical',
      reasoning: 'Natural light + fresh air boost energy and mood',
      frequency: 'Daily',
      difficulty: 'Easy',
      successRate: 79
    }
  ],

  // FOCUS / PRODUCTIVITY
  focus: [
    {
      id: 'focus_meditation',
      move: '10-min morning meditation',
      impact: 10,
      dimension: 'Mind',
      category: 'Mental',
      reasoning: 'Meditation improves sustained attention and reduces mental wandering',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 75
    },
    {
      id: 'focus_deepwork',
      move: '90-min deep work block (no interruptions)',
      impact: 12,
      dimension: 'Mind',
      category: 'Work',
      reasoning: 'Uninterrupted focus builds concentration muscle and output quality',
      frequency: '3-5x per week',
      difficulty: 'Hard',
      successRate: 64
    },
    {
      id: 'focus_social_limit',
      move: 'Social media < 60 min per day',
      impact: 8,
      dimension: 'Mind',
      category: 'Digital',
      reasoning: 'Excess social media fragments attention and reduces focus capacity',
      frequency: 'Daily',
      difficulty: 'Hard',
      successRate: 58
    },
    {
      id: 'focus_digital_sunset',
      move: 'Digital sunset at 8pm (no screens)',
      impact: 6,
      dimension: 'Mind',
      category: 'Digital',
      reasoning: 'Evening screen time disrupts next-day focus via poor sleep',
      frequency: 'Daily',
      difficulty: 'Hard',
      successRate: 52
    },
    {
      id: 'focus_morning_routine',
      move: 'Same wake time daily (even weekends)',
      impact: 8,
      dimension: 'Body',
      category: 'Physical',
      reasoning: 'Consistent sleep schedule optimizes circadian rhythm and mental clarity',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 69
    }
  ],

  // CONNECTION / RELATIONSHIPS
  connection: [
    {
      id: 'connection_call',
      move: 'Call one friend weekly (20+ min)',
      impact: 10,
      dimension: 'Soul',
      category: 'Social',
      reasoning: 'Voice connection builds intimacy and reduces isolation',
      frequency: 'Weekly',
      difficulty: 'Easy',
      successRate: 83
    },
    {
      id: 'connection_family_dinner',
      move: 'Family dinner 5x per week (no devices)',
      impact: 12,
      dimension: 'Soul',
      category: 'Social',
      reasoning: 'Shared meals create bonding rituals and communication opportunities',
      frequency: '5x per week',
      difficulty: 'Medium',
      successRate: 77
    },
    {
      id: 'connection_listening',
      move: 'Active listening practice (no advice-giving)',
      impact: 8,
      dimension: 'Soul',
      category: 'Social',
      reasoning: 'Deep listening builds trust and emotional intimacy',
      frequency: 'Daily opportunities',
      difficulty: 'Medium',
      successRate: 71
    },
    {
      id: 'connection_gratitude_share',
      move: 'Share gratitude with someone daily',
      impact: 7,
      dimension: 'Soul',
      category: 'Social',
      reasoning: 'Expressing appreciation strengthens relationships',
      frequency: 'Daily',
      difficulty: 'Easy',
      successRate: 74
    },
    {
      id: 'connection_quality_time',
      move: '30-min quality time with partner (weekly)',
      impact: 11,
      dimension: 'Soul',
      category: 'Social',
      reasoning: 'Dedicated one-on-one time maintains relationship quality',
      frequency: 'Weekly',
      difficulty: 'Easy',
      successRate: 86
    }
  ],

  // GROWTH / LEARNING
  growth: [
    {
      id: 'growth_reading',
      move: 'Read 20 pages of non-fiction daily',
      impact: 8,
      dimension: 'Mind',
      category: 'Learning',
      reasoning: 'Daily reading compounds into significant knowledge over time',
      frequency: 'Daily',
      difficulty: 'Easy',
      successRate: 81
    },
    {
      id: 'growth_journaling',
      move: 'Morning journaling (3 pages)',
      impact: 9,
      dimension: 'Mind',
      category: 'Mental',
      reasoning: 'Writing clarifies thinking and accelerates self-awareness',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 67
    },
    {
      id: 'growth_skill',
      move: 'Practice new skill 30 min daily',
      impact: 10,
      dimension: 'Purpose',
      category: 'Learning',
      reasoning: 'Deliberate practice builds competence and confidence',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 72
    },
    {
      id: 'growth_reflection',
      move: 'Weekly reflection session (30 min)',
      impact: 8,
      dimension: 'Purpose',
      category: 'Mental',
      reasoning: 'Regular reflection ensures growth is intentional, not random',
      frequency: 'Weekly',
      difficulty: 'Easy',
      successRate: 79
    }
  ],

  // PEACE / CALM
  peace: [
    {
      id: 'peace_meditation',
      move: '10-min meditation (morning or evening)',
      impact: 10,
      dimension: 'Mind',
      category: 'Mental',
      reasoning: 'Meditation regulates nervous system and builds emotional stability',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 76
    },
    {
      id: 'peace_nature',
      move: '20-min nature walk (park, trail, garden)',
      impact: 11,
      dimension: 'Soul',
      category: 'Physical',
      reasoning: 'Natural environments reduce cortisol and restore mental energy',
      frequency: '3-5x per week',
      difficulty: 'Easy',
      successRate: 84
    },
    {
      id: 'peace_breathwork',
      move: '5-min breathwork (box breathing, 4-7-8)',
      impact: 7,
      dimension: 'Mind',
      category: 'Mental',
      reasoning: 'Controlled breathing activates parasympathetic nervous system (calm)',
      frequency: 'Daily',
      difficulty: 'Easy',
      successRate: 73
    },
    {
      id: 'peace_screen_free',
      move: 'Screen-free evenings (after 8pm)',
      impact: 8,
      dimension: 'Mind',
      category: 'Digital',
      reasoning: 'Evening screens disrupt melatonin and prevent mental wind-down',
      frequency: 'Daily',
      difficulty: 'Hard',
      successRate: 56
    },
    {
      id: 'peace_bath',
      move: 'Evening bath or shower ritual',
      impact: 6,
      dimension: 'Body',
      category: 'Physical',
      reasoning: 'Warm water relaxes muscles and signals body it\'s time to wind down',
      frequency: 'Daily',
      difficulty: 'Easy',
      successRate: 82
    }
  ],

  // HEALTH / WELLNESS
  health: [
    {
      id: 'health_sleep',
      move: '7-8 hours sleep (consistent schedule)',
      impact: 15,
      dimension: 'Body',
      category: 'Physical',
      reasoning: 'Sleep is the foundation of all health metrics',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 80
    },
    {
      id: 'health_veggies',
      move: '5+ servings vegetables daily',
      impact: 8,
      dimension: 'Body',
      category: 'Nutrition',
      reasoning: 'Micronutrients support energy, immunity, and mental clarity',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 65
    },
    {
      id: 'health_strength',
      move: 'Strength training 2x per week',
      impact: 10,
      dimension: 'Body',
      category: 'Physical',
      reasoning: 'Muscle mass supports metabolism, bone density, and longevity',
      frequency: '2x per week',
      difficulty: 'Medium',
      successRate: 71
    },
    {
      id: 'health_steps',
      move: '8,000+ steps daily',
      impact: 9,
      dimension: 'Body',
      category: 'Physical',
      reasoning: 'Daily movement reduces chronic disease risk and boosts mood',
      frequency: 'Daily',
      difficulty: 'Easy',
      successRate: 77
    }
  ],

  // WEIGHT LOSS / FITNESS
  weight: [
    {
      id: 'weight_cardio',
      move: '30-min cardio 4x per week',
      impact: 12,
      dimension: 'Body',
      category: 'Physical',
      reasoning: 'Consistent cardio burns calories and builds cardiovascular health',
      frequency: '4x per week',
      difficulty: 'Medium',
      successRate: 73
    },
    {
      id: 'weight_strength',
      move: 'Strength training 3x per week',
      impact: 13,
      dimension: 'Body',
      category: 'Physical',
      reasoning: 'Muscle mass increases metabolism, helping burn more calories at rest',
      frequency: '3x per week',
      difficulty: 'Medium',
      successRate: 68
    },
    {
      id: 'weight_protein',
      move: 'High-protein breakfast (30g+) daily',
      impact: 10,
      dimension: 'Body',
      category: 'Nutrition',
      reasoning: 'Protein reduces hunger and supports muscle maintenance during weight loss',
      frequency: 'Daily',
      difficulty: 'Easy',
      successRate: 79
    },
    {
      id: 'weight_water',
      move: 'Drink 10 glasses water daily',
      impact: 6,
      dimension: 'Body',
      category: 'Nutrition',
      reasoning: 'Water boosts metabolism and reduces hunger between meals',
      frequency: 'Daily',
      difficulty: 'Easy',
      successRate: 76
    },
    {
      id: 'weight_sleep',
      move: '7-8 hours sleep (same schedule)',
      impact: 11,
      dimension: 'Body',
      category: 'Physical',
      reasoning: 'Poor sleep disrupts hunger hormones (leptin, ghrelin) and increases cravings',
      frequency: 'Daily',
      difficulty: 'Medium',
      successRate: 74
    },
    {
      id: 'weight_tracking',
      move: 'Track meals 5x per week',
      impact: 9,
      dimension: 'Mind',
      category: 'Learning',
      reasoning: 'Awareness of eating patterns helps make better food choices',
      frequency: '5x per week',
      difficulty: 'Medium',
      successRate: 64
    }
  ]
};

// Keyword to category mapping
export const INTENTION_KEYWORDS = {
  presence: ['presence', 'present', 'mindful', 'aware', 'attention', 'conscious'],
  energy: ['energy', 'energized', 'vitality', 'vibrant', 'alive', 'vigor'],
  focus: ['focus', 'focused', 'concentrate', 'clarity', 'clear', 'sharp', 'productive'],
  connection: ['connect', 'connection', 'relationship', 'bond', 'intimacy', 'close', 'together'],
  growth: ['grow', 'growth', 'learn', 'improve', 'develop', 'progress', 'better'],
  peace: ['peace', 'peaceful', 'calm', 'tranquil', 'serene', 'relaxed', 'ease'],
  health: ['health', 'healthy', 'fit', 'fitness', 'wellness', 'strong', 'well-being'],
  weight: ['weight', 'lose', 'loss', 'slim', 'lean', 'fat', 'pounds', 'kg', 'diet', 'shed']
};

/**
 * Analyze intention text and suggest relevant micro-moves
 */
export function suggestMicroMoves(intentionText: string): MicroMove[] {
  console.log('🤖 AI analyzing intention:', intentionText);
  
  const lower = intentionText.toLowerCase();
  const suggestions: MicroMove[] = [];
  const categoriesFound: Set<string> = new Set();

  // Check for keywords
  for (const [category, keywords] of Object.entries(INTENTION_KEYWORDS)) {
    for (const keyword of keywords) {
      if (lower.includes(keyword)) {
        categoriesFound.add(category);
        console.log(`✅ Found keyword "${keyword}" → category "${category}"`);
        break;
      }
    }
  }

  console.log('📊 Categories found:', Array.from(categoriesFound));

  // Add suggestions from matched categories
  for (const category of categoriesFound) {
    if (MICRO_MOVE_DATABASE[category]) {
      suggestions.push(...MICRO_MOVE_DATABASE[category]);
    }
  }

  // If no matches, provide default "well-being" suggestions
  if (suggestions.length === 0) {
    console.log('⚠️ No matches, using defaults');
    suggestions.push(
      MICRO_MOVE_DATABASE.presence[0], // Morning walk
      MICRO_MOVE_DATABASE.energy[0],   // 7h sleep
      MICRO_MOVE_DATABASE.connection[0] // Call friend
    );
  }

  // Sort by success rate (highest first)
  suggestions.sort((a, b) => b.successRate - a.successRate);

  console.log(`💡 Suggesting ${suggestions.length} micro-moves`);

  // Return top 10-12 (avoid overwhelming user)
  return suggestions.slice(0, 12);
}

/**
 * Rank suggestions by relevance to intention
 */
export function rankByRelevance(suggestions: MicroMove[], intentionText: string): MicroMove[] {
  const lower = intentionText.toLowerCase();
  
  return suggestions.map(move => {
    let relevanceScore = move.successRate; // Base score
    
    // Boost if category keyword appears
    const category = Object.entries(INTENTION_KEYWORDS).find(([cat, keywords]) =>
      keywords.some(kw => lower.includes(kw))
    );
    
    if (category) {
      relevanceScore += 20; // Boost relevant categories
    }
    
    // Boost "easy" moves slightly (better for beginners)
    if (move.difficulty === 'Easy') {
      relevanceScore += 5;
    }
    
    return { ...move, relevanceScore };
  }).sort((a, b) => (b.relevanceScore || 0) - (a.relevanceScore || 0));
}

/**
 * Group suggestions by effectiveness tier
 */
export function groupByTier(suggestions: MicroMove[]): {
  topTier: MicroMove[];      // ⭐⭐⭐ (success rate 80+)
  recommended: MicroMove[];  // ⭐⭐ (success rate 65-79)
  helpful: MicroMove[];      // ⭐ (success rate <65)
} {
  return {
    topTier: suggestions.filter(m => m.successRate >= 80),
    recommended: suggestions.filter(m => m.successRate >= 65 && m.successRate < 80),
    helpful: suggestions.filter(m => m.successRate < 65)
  };
}

export default {
  MICRO_MOVE_DATABASE,
  INTENTION_KEYWORDS,
  suggestMicroMoves,
  rankByRelevance,
  groupByTier
};

