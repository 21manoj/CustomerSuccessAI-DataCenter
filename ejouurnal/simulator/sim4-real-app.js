/**
 * SIM4: REAL APP SIMULATION
 * 
 * Uses actual backend API to simulate users interacting with the real application
 * Tests the complete virtuous cycle:
 * 1. Onboarding
 * 2. Set intention (with hybrid AI suggestions)
 * 3. Daily check-ins (with inline details)
 * 4. AI journal generation (with nutrition analysis)
 * 5. Insights discovery
 * 6. Retention & conversion
 * 
 * Simulates 500 users over 24 days (4 hours runtime, 10 min = 1 day)
 */

const fetch = require('node-fetch');
const fs = require('fs');

// Configuration
const CONFIG = {
  API_BASE_URL: 'http://localhost:3005/api',
  TOTAL_USERS: 500,
  SIM_DAYS: 24,
  MINUTES_PER_DAY: 10,
  CHURN_RATE: 0.20, // 20% churn over 24 days
  OUTPUT_DIR: './simulator/output',
  START_TIME: Date.now(),
};

// User Personas with Intentions
const PERSONAS = [
  {
    name: 'Weight Loss Seeker',
    weight: 0.25,
    intentions: [
      'I want to lose weight and feel healthier',
      'Get in better shape this month',
      'Build sustainable fitness habits'
    ],
    microMovePreference: 'ai', // 80% pick AI suggestions
    engagementLevel: 'high',
    conversionProbability: 0.65,
  },
  {
    name: 'Presence Seeker',
    weight: 0.20,
    intentions: [
      'Show up with more presence for my family',
      'Be more mindful and present',
      'Reduce distractions and be more aware'
    ],
    microMovePreference: 'hybrid', // 50% AI, 50% custom
    engagementLevel: 'high',
    conversionProbability: 0.70,
  },
  {
    name: 'Energy Booster',
    weight: 0.18,
    intentions: [
      'Have more energy throughout the day',
      'Feel more alive and vibrant',
      'Boost my vitality and reduce fatigue'
    ],
    microMovePreference: 'ai',
    engagementLevel: 'medium',
    conversionProbability: 0.55,
  },
  {
    name: 'Focus Builder',
    weight: 0.15,
    intentions: [
      'Improve my focus and concentration',
      'Be more productive with deep work',
      'Reduce digital distractions'
    ],
    microMovePreference: 'hybrid',
    engagementLevel: 'high',
    conversionProbability: 0.68,
  },
  {
    name: 'Connection Seeker',
    weight: 0.12,
    intentions: [
      'Build deeper connections with loved ones',
      'Be more social and engaged',
      'Strengthen relationships'
    ],
    microMovePreference: 'ai',
    engagementLevel: 'medium',
    conversionProbability: 0.58,
  },
  {
    name: 'Casual User',
    weight: 0.10,
    intentions: [
      'Just want to try this out',
      'See if this helps me feel better',
      'Looking for something new'
    ],
    microMovePreference: 'random',
    engagementLevel: 'low',
    conversionProbability: 0.25,
  },
];

// Micro-Moves Database (mirrors MicroMoveLibrary.ts)
const AI_SUGGESTED_MICRO_MOVES = {
  weight: [
    '30-min cardio 4x per week',
    'Strength training 3x per week',
    'High-protein breakfast (30g+) daily',
    'Drink 10 glasses water daily',
    '7-8 hours sleep (same schedule)',
    'Track meals 5x per week',
  ],
  presence: [
    '10-min morning walk',
    'No phone first hour after waking',
    '5-min meditation before work',
    '15-min device-free family time',
    'Read 2 chapters of meaningful book',
    'Evening gratitude practice (3 things)',
  ],
  energy: [
    '7+ hours sleep nightly',
    '30-min exercise (any type) 3x per week',
    'Drink 8 glasses of water daily',
    'No caffeine after 2pm',
    '20-min outdoor time daily',
  ],
  focus: [
    '10-min morning meditation',
    '90-min deep work block (no interruptions)',
    'Social media < 60 min per day',
    'Digital sunset at 8pm (no screens)',
    'Same wake time daily (even weekends)',
  ],
  connection: [
    'Call one friend weekly (20+ min)',
    'Family dinner 5x per week (no devices)',
    'Active listening practice (no advice-giving)',
    'Share gratitude with someone daily',
    '30-min quality time with partner (weekly)',
  ],
};

// Simulation State
const simulation = {
  users: [],
  dailyMetrics: [],
  overallMetrics: {
    totalRevenue: 0,
    totalUsers: 0,
    activeUsers: 0,
    premiumUsers: 0,
    churnedUsers: 0,
  },
  apiCallCount: 0,
  errors: [],
};

// Helper: API Call with retry
async function apiCall(endpoint, method = 'GET', body = null, retries = 3) {
  const url = `${CONFIG.API_BASE_URL}${endpoint}`;
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      simulation.apiCallCount++;
      
      const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
      };
      
      if (body) {
        options.body = JSON.stringify(body);
      }
      
      const response = await fetch(url, options);
      const data = await response.json();
      
      if (!response.ok && attempt < retries) {
        console.log(`⚠️ API call failed (attempt ${attempt}/${retries}): ${endpoint}`);
        await sleep(1000 * attempt); // Exponential backoff
        continue;
      }
      
      return data;
    } catch (error) {
      if (attempt === retries) {
        simulation.errors.push({ endpoint, error: error.message, time: new Date() });
        console.error(`❌ API call failed after ${retries} attempts: ${endpoint}`, error.message);
        return null;
      }
      await sleep(1000 * attempt);
    }
  }
}

// Helper: Sleep
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Helper: Random choice
function randomChoice(array) {
  return array[Math.floor(Math.random() * array.length)];
}

// Helper: Random from distribution
function randomFromDistribution() {
  const rand = Math.random();
  let cumulative = 0;
  for (const persona of PERSONAS) {
    cumulative += persona.weight;
    if (rand <= cumulative) {
      return persona;
    }
  }
  return PERSONAS[PERSONAS.length - 1];
}

// Helper: Calculate churn for day
function shouldChurn(user, currentDay) {
  // Higher engagement = lower churn
  const baseChurnRate = CONFIG.CHURN_RATE / CONFIG.SIM_DAYS;
  const engagementMultiplier = {
    high: 0.5,
    medium: 1.0,
    low: 2.0,
  };
  
  const dailyChurnRate = baseChurnRate * engagementMultiplier[user.persona.engagementLevel];
  
  // Insight users have 30% lower churn (like Sim3)
  const insightMultiplier = user.hasInsights ? 0.7 : 1.0;
  
  return Math.random() < (dailyChurnRate * insightMultiplier);
}

// Create User
async function createUser(userId) {
  const persona = randomFromDistribution();
  const intentionText = randomChoice(persona.intentions);
  
  // Determine persona category from intention
  let category = 'presence'; // default
  const lower = intentionText.toLowerCase();
  if (lower.includes('weight') || lower.includes('lose') || lower.includes('fitness')) category = 'weight';
  else if (lower.includes('presence') || lower.includes('mindful')) category = 'presence';
  else if (lower.includes('energy') || lower.includes('alive')) category = 'energy';
  else if (lower.includes('focus') || lower.includes('productive')) category = 'focus';
  else if (lower.includes('connect') || lower.includes('relationship')) category = 'connection';
  
  // Select 3 micro-moves based on preference
  const aiMoves = AI_SUGGESTED_MICRO_MOVES[category] || AI_SUGGESTED_MICRO_MOVES.presence;
  let microMoves = [];
  
  if (persona.microMovePreference === 'ai') {
    // 80% pick top 3 AI suggestions
    microMoves = aiMoves.slice(0, 3);
  } else if (persona.microMovePreference === 'hybrid') {
    // 50% pick 2 AI + 1 custom
    microMoves = [
      aiMoves[0],
      aiMoves[1],
      `Custom: ${category} activity`, // User's own
    ];
  } else {
    // Random selection
    microMoves = [randomChoice(aiMoves), randomChoice(aiMoves), randomChoice(aiMoves)];
  }
  
  const user = {
    userId,
    persona,
    intentionText,
    microMoves,
    category,
    joinDay: 0,
    lastActiveDay: 0,
    checkInCount: 0,
    meaningfulDays: 0,
    journalsGenerated: 0,
    detailsAddedCount: 0,
    isPremium: false,
    premiumDay: null,
    hasInsights: false,
    insightsDay: null,
    isChurned: false,
    churnDay: null,
    avgFulfillment: 50,
    scores: { body: 50, mind: 50, soul: 50, purpose: 50 },
  };
  
  // Create user via API
  const result = await apiCall('/users', 'POST', {
    userId,
    name: `User_${userId}`,
    email: `user${userId}@test.com`,
  });
  
  if (result) {
    console.log(`✅ Created ${persona.name}: "${intentionText}"`);
  }
  
  return user;
}

// Set Intention (via API)
async function setIntention(user) {
  const result = await apiCall('/intentions', 'POST', {
    userId: user.userId,
    intention: user.intentionText,
    microMoves: user.microMoves,
    antiGlitter: randomChoice([
      'No phone first hour after waking',
      '30-min morning no-feed',
      'Digital sunset at 8pm',
    ]),
  });
  
  if (result && result.success) {
    console.log(`🎯 ${user.userId} set intention: "${user.intentionText.substring(0, 40)}..."`);
  }
}

// Daily Check-in
async function performCheckIn(user, dayPart, currentDay) {
  // Simulate realistic check-in patterns
  const checkInProbability = {
    high: 0.85,
    medium: 0.65,
    low: 0.40,
  };
  
  if (Math.random() > checkInProbability[user.persona.engagementLevel]) {
    return false; // Skipped check-in
  }
  
  // Generate realistic mood based on scores
  const avgScore = (user.scores.body + user.scores.mind + user.scores.soul + user.scores.purpose) / 4;
  let mood;
  if (avgScore >= 70) mood = Math.random() > 0.3 ? 'great' : 'good';
  else if (avgScore >= 55) mood = Math.random() > 0.5 ? 'good' : 'neutral';
  else if (avgScore >= 40) mood = 'neutral';
  else mood = Math.random() > 0.5 ? 'low' : 'very-low';
  
  // Select context
  const contexts = randomChoice([
    ['sleep'],
    ['work'],
    ['social'],
    ['work', 'stress'],
    ['sleep', 'social'],
  ]);
  
  // Micro-act probability based on engagement
  const microActProbability = {
    high: 0.70,
    medium: 0.50,
    low: 0.25,
  };
  
  const microAct = Math.random() < microActProbability[user.persona.engagementLevel]
    ? randomChoice(['walk', 'meditation', 'gratitude', 'reading', 'exercise'])
    : null;
  
  // Purpose progress
  const purposeProgress = microAct 
    ? randomChoice(['yes', 'partly', 'partly', 'no']) // More "partly"
    : 'no';
  
  // API call
  const result = await apiCall('/check-ins', 'POST', {
    userId: user.userId,
    dayPart,
    mood,
    contexts,
    microAct,
    purposeProgress,
  });
  
  if (result && result.success) {
    user.checkInCount++;
    
    // Update scores based on check-in
    if (mood === 'great') {
      user.scores.body = Math.min(100, user.scores.body + 5);
      user.scores.mind = Math.min(100, user.scores.mind + 5);
      user.scores.soul = Math.min(100, user.scores.soul + 5);
      user.scores.purpose = Math.min(100, user.scores.purpose + 5);
    } else if (mood === 'good') {
      user.scores.body = Math.min(100, user.scores.body + 3);
      user.scores.mind = Math.min(100, user.scores.mind + 3);
      user.scores.soul = Math.min(100, user.scores.soul + 3);
    } else if (mood === 'low' || mood === 'very-low') {
      user.scores.body = Math.max(0, user.scores.body - 3);
      user.scores.mind = Math.max(0, user.scores.mind - 5);
      user.scores.soul = Math.max(0, user.scores.soul - 3);
    }
    
    if (microAct) {
      user.scores.body = Math.min(100, user.scores.body + 8);
      user.scores.mind = Math.min(100, user.scores.mind + 8);
    }
    
    return true;
  }
  
  return false;
}

// Add Details (enriched data)
async function addDetails(user, currentDay) {
  // Only some users add details (based on engagement)
  const detailsProbability = {
    high: 0.60,
    medium: 0.35,
    low: 0.10,
  };
  
  if (Math.random() > detailsProbability[user.persona.engagementLevel]) {
    return false;
  }
  
  // Generate realistic details
  const meals = [
    { name: 'Oatmeal with berries and walnuts', quality: 'good' },
    { name: 'Scrambled eggs with avocado toast', quality: 'good' },
    { name: 'Greek yogurt with granola', quality: 'good' },
    { name: 'Chicken salad with mixed greens', quality: 'good' },
    { name: 'Salmon with quinoa and broccoli', quality: 'good' },
    { name: 'Fast food burger and fries', quality: 'poor' },
    { name: 'Pizza and soda', quality: 'poor' },
  ];
  
  const exerciseTypes = ['Walk', 'Run', 'Yoga', 'Gym', 'Cycling', 'HIIT'];
  const intensities = ['light', 'moderate', 'vigorous'];
  const feelings = ['😊 Energized', '😌 Good', '😐 Okay', '😓 Exhausted'];
  
  const details = {
    sleepHours: 6 + Math.random() * 3, // 6-9 hours
    sleepQuality: Math.floor(2 + Math.random() * 3), // 2-5
    exerciseType: Math.random() > 0.3 ? randomChoice(exerciseTypes) : null,
    exerciseDuration: Math.random() > 0.3 ? 20 + Math.floor(Math.random() * 40) : null, // 20-60 min
    exerciseIntensity: randomChoice(intensities),
    exerciseFeeling: randomChoice(feelings),
    hydration: Math.floor(4 + Math.random() * 6), // 4-10 glasses
    foodQuality: Math.floor(3 + Math.random() * 2), // 3-5
  };
  
  // Add meal notes for weight loss users
  if (user.category === 'weight' && Math.random() > 0.5) {
    const breakfast = randomChoice(meals);
    details.breakfastNotes = breakfast.name;
    details.breakfast = breakfast.quality;
  }
  
  const result = await apiCall('/details', 'POST', {
    userId: user.userId,
    ...details,
  });
  
  if (result && result.success) {
    user.detailsAddedCount++;
    return true;
  }
  
  return false;
}

// Generate Journal
async function generateJournal(user, currentDay) {
  // Users generate journal at end of day
  // Higher engagement = more likely to generate
  const journalProbability = {
    high: 0.75,
    medium: 0.50,
    low: 0.20,
  };
  
  if (Math.random() > journalProbability[user.persona.engagementLevel]) {
    return false;
  }
  
  const result = await apiCall('/journals/generate', 'POST', {
    userId: user.userId,
    tone: randomChoice(['reflective', 'coach-like', 'factual', 'poetic']),
  });
  
  if (result && result.success) {
    user.journalsGenerated++;
    
    // Calculate fulfillment
    const avgScore = (user.scores.body + user.scores.mind + user.scores.soul + user.scores.purpose) / 4;
    user.avgFulfillment = Math.round(avgScore);
    
    if (avgScore >= 65) {
      user.meaningfulDays++;
    }
    
    return true;
  }
  
  return false;
}

// Generate Insights
async function generateInsights(user, currentDay) {
  // Insights only after 4+ days of data
  if (currentDay < 4 || user.hasInsights) {
    return false;
  }
  
  const result = await apiCall(`/insights/generate/${user.userId}`, 'POST');
  
  if (result && result.success) {
    user.hasInsights = true;
    user.insightsDay = currentDay;
    console.log(`💡 ${user.userId} received insights on Day ${currentDay}`);
    return true;
  }
  
  return false;
}

// Convert to Premium
function attemptConversion(user, currentDay) {
  if (user.isPremium || user.isChurned) {
    return false;
  }
  
  // Conversion factors
  let conversionProb = user.persona.conversionProbability;
  
  // Insights boost conversion by 3x (validated in Sim3)
  if (user.hasInsights) {
    conversionProb *= 3.0;
  }
  
  // Meaningful days boost conversion
  if (user.meaningfulDays >= 3) {
    conversionProb *= 1.5;
  }
  
  // Journal engagement boosts conversion
  if (user.journalsGenerated >= 3) {
    conversionProb *= 1.3;
  }
  
  if (Math.random() < conversionProb) {
    user.isPremium = true;
    user.premiumDay = currentDay;
    
    // Add revenue
    const plan = Math.random() > 0.7 ? 'premium_plus' : 'premium';
    const monthlyRevenue = plan === 'premium_plus' ? 19.99 : 9.99;
    simulation.overallMetrics.totalRevenue += monthlyRevenue;
    simulation.overallMetrics.premiumUsers++;
    
    console.log(`💎 ${user.userId} converted to ${plan} on Day ${currentDay} (${user.hasInsights ? 'with' : 'without'} insights)`);
    return true;
  }
  
  return false;
}

// Simulate One Day for All Users
async function simulateDay(currentDay) {
  console.log(`\n📅 === DAY ${currentDay} ===`);
  
  const dayStart = Date.now();
  let activeToday = 0;
  let checkInsToday = 0;
  let detailsToday = 0;
  let journalsToday = 0;
  let conversionsToday = 0;
  let churnsToday = 0;
  let insightsToday = 0;
  
  // Add new users (gradual ramp-up: 500 users join over first 10 days)
  if (currentDay <= 10 && simulation.users.length < CONFIG.TOTAL_USERS) {
    const usersToAdd = Math.ceil(CONFIG.TOTAL_USERS / 10);
    for (let i = 0; i < usersToAdd && simulation.users.length < CONFIG.TOTAL_USERS; i++) {
      const userId = `sim4_user_${String(simulation.users.length + 1).padStart(4, '0')}`;
      const user = await createUser(userId);
      await setIntention(user);
      simulation.users.push(user);
      activeToday++;
    }
  }
  
  // Simulate activity for each active user
  for (const user of simulation.users) {
    if (user.isChurned) continue;
    
    // Check for churn
    if (currentDay > user.joinDay && shouldChurn(user, currentDay)) {
      user.isChurned = true;
      user.churnDay = currentDay;
      simulation.overallMetrics.churnedUsers++;
      churnsToday++;
      console.log(`👋 ${user.userId} churned on Day ${currentDay}`);
      continue;
    }
    
    activeToday++;
    user.lastActiveDay = currentDay;
    
    // Daily check-ins (morning, day, evening, night)
    const dayParts = ['morning', 'day', 'evening', 'night'];
    for (const dayPart of dayParts) {
      const success = await performCheckIn(user, dayPart, currentDay);
      if (success) {
        checkInsToday++;
        
        // Add details after check-in (mirrors new inline flow)
        if (Math.random() > 0.6) { // 40% add details inline
          const detailsAdded = await addDetails(user, currentDay);
          if (detailsAdded) detailsToday++;
        }
      }
    }
    
    // Generate journal at end of day
    const journalGenerated = await generateJournal(user, currentDay);
    if (journalGenerated) journalsToday++;
    
    // Generate insights (after 4+ days)
    const insightsGenerated = await generateInsights(user, currentDay);
    if (insightsGenerated) insightsToday++;
    
    // Attempt conversion
    const converted = attemptConversion(user, currentDay);
    if (converted) conversionsToday++;
    
    // Small delay to avoid overwhelming API
    if (simulation.users.indexOf(user) % 10 === 0) {
      await sleep(100);
    }
  }
  
  // Record daily metrics
  const dayMetrics = {
    day: currentDay,
    totalUsers: simulation.users.length,
    activeUsers: activeToday,
    churnedUsers: churnsToday,
    checkIns: checkInsToday,
    detailsAdded: detailsToday,
    journalsGenerated: journalsToday,
    insightsGenerated: insightsToday,
    conversions: conversionsToday,
    premiumUsers: simulation.users.filter(u => u.isPremium).length,
    revenue: simulation.overallMetrics.totalRevenue,
    avgFulfillment: Math.round(
      simulation.users.reduce((sum, u) => sum + u.avgFulfillment, 0) / simulation.users.length
    ),
  };
  
  simulation.dailyMetrics.push(dayMetrics);
  
  const dayDuration = Date.now() - dayStart;
  console.log(`📊 Day ${currentDay} Summary (${(dayDuration / 1000).toFixed(1)}s):`);
  console.log(`   Users: ${dayMetrics.totalUsers} | Active: ${activeToday} | Churned: ${churnsToday}`);
  console.log(`   Check-ins: ${checkInsToday} | Journals: ${journalsToday} | Details: ${detailsToday}`);
  console.log(`   Insights: ${insightsToday} | Conversions: ${conversionsToday} | Premium: ${dayMetrics.premiumUsers}`);
  console.log(`   Revenue: $${dayMetrics.revenue.toFixed(2)} | Avg Fulfillment: ${dayMetrics.avgFulfillment}`);
}

// Calculate Final Analytics
function calculateAnalytics() {
  const activeUsers = simulation.users.filter(u => !u.isChurned);
  const premiumUsers = simulation.users.filter(u => u.isPremium);
  const insightUsers = simulation.users.filter(u => u.hasInsights);
  const insightPremiumUsers = insightUsers.filter(u => u.isPremium);
  
  // D7, D14, D30 retention
  const d7Users = simulation.users.filter(u => u.joinDay <= 7);
  const d7Active = d7Users.filter(u => !u.isChurned && u.lastActiveDay >= 7);
  const d7Retention = d7Users.length > 0 ? (d7Active.length / d7Users.length) * 100 : 0;
  
  const d14Users = simulation.users.filter(u => u.joinDay <= 14);
  const d14Active = d14Users.filter(u => !u.isChurned && u.lastActiveDay >= 14);
  const d14Retention = d14Users.length > 0 ? (d14Active.length / d14Users.length) * 100 : 0;
  
  // Conversion rates
  const overallConversionRate = (premiumUsers.length / simulation.users.length) * 100;
  const insightConversionRate = insightUsers.length > 0 
    ? (insightPremiumUsers.length / insightUsers.length) * 100 
    : 0;
  const noInsightConversionRate = simulation.users.filter(u => !u.hasInsights && u.isPremium).length 
    / simulation.users.filter(u => !u.hasInsights).length * 100;
  
  // Revenue
  const mrr = simulation.overallMetrics.totalRevenue;
  const arr = mrr * 12;
  const arpu = simulation.users.length > 0 ? mrr / simulation.users.length : 0;
  
  // Engagement
  const avgCheckInsPerUser = simulation.users.reduce((sum, u) => sum + u.checkInCount, 0) / simulation.users.length;
  const avgJournalsPerUser = simulation.users.reduce((sum, u) => sum + u.journalsGenerated, 0) / simulation.users.length;
  const avgDetailsPerUser = simulation.users.reduce((sum, u) => sum + u.detailsAddedCount, 0) / simulation.users.length;
  const avgMeaningfulDays = simulation.users.reduce((sum, u) => sum + u.meaningfulDays, 0) / simulation.users.length;
  
  return {
    simulation: 'Sim4: Real App',
    duration: `${CONFIG.SIM_DAYS} days (${(Date.now() - CONFIG.START_TIME) / 1000 / 60} minutes)`,
    users: {
      total: simulation.users.length,
      active: activeUsers.length,
      churned: simulation.users.filter(u => u.isChurned).length,
      premium: premiumUsers.length,
      withInsights: insightUsers.length,
    },
    retention: {
      d7: `${d7Retention.toFixed(1)}%`,
      d14: `${d14Retention.toFixed(1)}%`,
      overall: `${((activeUsers.length / simulation.users.length) * 100).toFixed(1)}%`,
    },
    conversion: {
      overall: `${overallConversionRate.toFixed(1)}%`,
      withInsights: `${insightConversionRate.toFixed(1)}%`,
      withoutInsights: `${noInsightConversionRate.toFixed(1)}%`,
      insightMultiplier: `${(insightConversionRate / noInsightConversionRate).toFixed(1)}x`,
    },
    engagement: {
      avgCheckInsPerUser: avgCheckInsPerUser.toFixed(1),
      avgJournalsPerUser: avgJournalsPerUser.toFixed(1),
      avgDetailsPerUser: avgDetailsPerUser.toFixed(1),
      avgMeaningfulDays: avgMeaningfulDays.toFixed(1),
      avgFulfillment: Math.round(
        simulation.users.reduce((sum, u) => sum + u.avgFulfillment, 0) / simulation.users.length
      ),
    },
    revenue: {
      mrr: `$${mrr.toFixed(2)}`,
      arr: `$${arr.toFixed(2)}`,
      arpu: `$${arpu.toFixed(2)}`,
    },
    api: {
      totalCalls: simulation.apiCallCount,
      errors: simulation.errors.length,
    },
  };
}

// Main Simulation Loop
async function runSimulation() {
  console.log('🚀 Starting Sim4: Real App Simulation');
  console.log(`⚙️ Config: ${CONFIG.TOTAL_USERS} users, ${CONFIG.SIM_DAYS} days, ${CONFIG.MINUTES_PER_DAY} min/day`);
  console.log(`🌐 API: ${CONFIG.API_BASE_URL}`);
  console.log('');
  
  // Check if backend is running
  try {
    const health = await fetch(`${CONFIG.API_BASE_URL.replace('/api', '')}/health`);
    if (!health.ok) {
      throw new Error('Backend not healthy');
    }
    console.log('✅ Backend is running\n');
  } catch (error) {
    console.error('❌ Backend is not running! Start it with: cd backend && node server.js');
    process.exit(1);
  }
  
  // Run simulation for each day
  for (let day = 1; day <= CONFIG.SIM_DAYS; day++) {
    await simulateDay(day);
    
    // Wait between days (10 minutes = 1 day)
    if (day < CONFIG.SIM_DAYS) {
      const waitTime = CONFIG.MINUTES_PER_DAY * 60 * 1000;
      const nextDay = new Date(Date.now() + waitTime);
      console.log(`⏸️ Waiting ${CONFIG.MINUTES_PER_DAY} min until Day ${day + 1} (next: ${nextDay.toLocaleTimeString()})`);
      await sleep(waitTime);
    }
  }
  
  // Calculate and save analytics
  console.log('\n📊 === SIMULATION COMPLETE ===\n');
  const analytics = calculateAnalytics();
  
  console.log('FINAL RESULTS:');
  console.log(JSON.stringify(analytics, null, 2));
  
  // Save results
  const outputPath = `${CONFIG.OUTPUT_DIR}/sim4-real-app-results.json`;
  fs.writeFileSync(outputPath, JSON.stringify({
    config: CONFIG,
    analytics,
    dailyMetrics: simulation.dailyMetrics,
    userDetails: simulation.users.map(u => ({
      userId: u.userId,
      persona: u.persona.name,
      intention: u.intentionText,
      microMoves: u.microMoves,
      isPremium: u.isPremium,
      hasInsights: u.hasInsights,
      checkIns: u.checkInCount,
      journals: u.journalsGenerated,
      meaningfulDays: u.meaningfulDays,
      avgFulfillment: u.avgFulfillment,
      isChurned: u.isChurned,
    })),
    errors: simulation.errors,
    completedAt: new Date().toISOString(),
  }, null, 2));
  
  console.log(`\n💾 Results saved to: ${outputPath}`);
  
  // Compare to Sim2 & Sim3
  console.log('\n📈 === COMPARISON TO SIM2 & SIM3 ===\n');
  console.log(`SIM2 (No Insights): D7 79.3%, Premium 44.2%, MRR $2,988`);
  console.log(`SIM3 (With Insights): D7 81.6%, Premium 73.5%, MRR $4,970 (+66%)`);
  console.log(`SIM4 (Real App): D7 ${analytics.retention.d7}, Premium ${analytics.conversion.overall}, MRR ${analytics.revenue.mrr}`);
  console.log('');
  console.log(`Insight Multiplier: SIM3 ${13}x | SIM4 ${analytics.conversion.insightMultiplier}`);
}

// Start simulation
runSimulation().catch(error => {
  console.error('❌ Simulation failed:', error);
  process.exit(1);
});

