/**
 * SIM5: REALISTIC TEST with Skeptics & Randomness
 * 
 * Key Features:
 * - 100 users, 12 days, 2 min/day (~24 min runtime)
 * - 40% SKEPTICS (low engagement, doubtful)
 * - 40% MEDIUM (inconsistent, hopeful)
 * - 20% HIGH (true believers)
 * - Random behavior based on consistency scores
 * - Realistic conversion rates (5-7% overall)
 * - Real API calls to backend
 */

const fetch = require('node-fetch');
const fs = require('fs');

// Configuration
const CONFIG = {
  API_BASE_URL: 'http://localhost:3005/api',
  TOTAL_USERS: 100,
  SIM_DAYS: 12,
  MINUTES_PER_DAY: 2,
  CHURN_RATE: 0.25, // 25% churn over 12 days
  OUTPUT_DIR: './simulator/output',
  START_TIME: Date.now(),
};

// Realistic User Personas with LOTS of Skeptics
const PERSONAS = [
  // HIGH ENGAGERS (20% - True Believers)
  {
    name: 'Committed Seeker',
    weight: 0.12,
    intentions: [
      'I want to lose weight and feel healthier',
      'Show up with more presence for my family',
      'Improve my focus and concentration'
    ],
    engagementLevel: 'high',
    conversionProbability: 0.15,  // 15% → 45% with insights
    checkInRate: 0.85,            // 85% chance per daypart
    journalRate: 0.75,
    detailsRate: 0.65,
    churnMultiplier: 0.5,         // Half the base churn
  },
  {
    name: 'Purpose-Driven',
    weight: 0.08,
    intentions: [
      'Build sustainable fitness habits',
      'Have more energy throughout the day',
      'Build deeper connections with loved ones'
    ],
    engagementLevel: 'high',
    conversionProbability: 0.12,  // 12% → 36% with insights
    checkInRate: 0.80,
    journalRate: 0.70,
    detailsRate: 0.60,
    churnMultiplier: 0.6,
  },
  
  // MEDIUM ENGAGERS (40% - Hopeful but Inconsistent)
  {
    name: 'Busy Parent',
    weight: 0.15,
    intentions: [
      'Just want to feel less overwhelmed',
      'Try to be more present with kids',
      'Maybe get more sleep'
    ],
    engagementLevel: 'medium',
    conversionProbability: 0.07,  // 7% → 21% with insights
    checkInRate: 0.60,
    journalRate: 0.45,
    detailsRate: 0.30,
    churnMultiplier: 1.0,
  },
  {
    name: 'Curious Explorer',
    weight: 0.15,
    intentions: [
      'Just want to try this out',
      'See if this helps me feel better',
      'Looking for something new'
    ],
    engagementLevel: 'medium',
    conversionProbability: 0.05,  // 5% → 15% with insights
    checkInRate: 0.55,
    journalRate: 0.40,
    detailsRate: 0.25,
    churnMultiplier: 1.1,
  },
  {
    name: 'Inconsistent Optimist',
    weight: 0.10,
    intentions: [
      'Want to make a change',
      'Get in better shape this month',
      'Reduce distractions'
    ],
    engagementLevel: 'medium',
    conversionProbability: 0.06,  // 6% → 18% with insights
    checkInRate: 0.50,
    journalRate: 0.35,
    detailsRate: 0.20,
    churnMultiplier: 1.2,
  },
  
  // LOW ENGAGERS - SKEPTICS (40% - Don't Really Believe)
  {
    name: 'Skeptic - Downloaded But Doubtful',
    weight: 0.15,
    intentions: [
      'My friend told me to try this',
      'I guess I should track something',
      'Not sure this will help'
    ],
    engagementLevel: 'low',
    conversionProbability: 0.02,  // 2% → 6% with insights
    checkInRate: 0.35,
    journalRate: 0.20,
    detailsRate: 0.10,
    churnMultiplier: 1.8,
  },
  {
    name: 'Overwhelmed Struggler',
    weight: 0.15,
    intentions: [
      'Life feels overwhelming lately',
      'Need help but not sure where to start',
      'Everything seems too hard'
    ],
    engagementLevel: 'low',
    conversionProbability: 0.01,  // 1% → 3% with insights
    checkInRate: 0.30,
    journalRate: 0.15,
    detailsRate: 0.08,
    churnMultiplier: 2.0,
  },
  {
    name: 'App Collector',
    weight: 0.10,
    intentions: [
      'Downloaded a bunch of apps',
      'Maybe this one will work',
      'Probably will forget about it'
    ],
    engagementLevel: 'low',
    conversionProbability: 0.01,  // 1% → 3% with insights
    checkInRate: 0.25,
    journalRate: 0.12,
    detailsRate: 0.05,
    churnMultiplier: 2.2,
  },
];

// Micro-Moves by Category
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
    '20-min sunlight within 2 hours of waking',
    '3 meals, no snacking between',
    '15-min power nap (2-3pm)',
    'Cold shower for 30 seconds (morning)',
    'Desk workout every 90 minutes',
    '8-hour eating window (stop 6pm)',
  ],
  focus: [
    '90-min deep work blocks (no distraction)',
    'Airplane mode 9-11am',
    'Single-tasking (one thing at a time)',
    'Weekly planning Sunday evening',
    'Brain dump before deep work',
    'Turn off all notifications (work hours)',
  ],
  connection: [
    '30-min device-free dinner together',
    'Weekly date night (no agenda)',
    'Ask 3 questions before giving advice',
    'Family dinner 5x per week (no devices)',
    'Active listening practice (no advice-giving)',
    'Share gratitude with someone daily',
  ],
  general: [
    'Morning walk',
    'Meditation',
    'Reading',
    'Journaling',
    'Exercise',
    'Quality sleep',
  ],
};

// Simulation State
const simulation = {
  users: [],
  dailyMetrics: [],
  overallMetrics: { totalRevenue: 0, premiumUsers: 0, churnedUsers: 0 },
  apiCallCount: 0,
  errors: [],
};

// Helper Functions
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function randomChoice(array) {
  return array[Math.floor(Math.random() * array.length)];
}

function randomFromDistribution() {
  const rand = Math.random();
  let cumulative = 0;
  for (const persona of PERSONAS) {
    cumulative += persona.weight;
    if (rand <= cumulative) return persona;
  }
  return PERSONAS[PERSONAS.length - 1];
}

async function apiCall(endpoint, method = 'GET', body = null) {
  try {
    simulation.apiCallCount++;
    const options = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) options.body = JSON.stringify(body);
    
    const response = await fetch(`${CONFIG.API_BASE_URL}${endpoint}`, options);
    return await response.json();
  } catch (error) {
    simulation.errors.push({ endpoint, error: error.message });
    return null;
  }
}

async function createUser(userId) {
  const persona = randomFromDistribution();
  const intentionText = randomChoice(persona.intentions);
  
  // Determine category from intention
  let category = 'general';
  const lower = intentionText.toLowerCase();
  if (lower.includes('weight') || lower.includes('lose') || lower.includes('shape')) category = 'weight';
  else if (lower.includes('presence') || lower.includes('mindful') || lower.includes('present')) category = 'presence';
  else if (lower.includes('energy') || lower.includes('vitality') || lower.includes('alive')) category = 'energy';
  else if (lower.includes('focus') || lower.includes('concentration') || lower.includes('productive')) category = 'focus';
  else if (lower.includes('connect') || lower.includes('family') || lower.includes('relationships')) category = 'connection';
  
  const aiMoves = AI_SUGGESTED_MICRO_MOVES[category] || AI_SUGGESTED_MICRO_MOVES.general;
  const microMoves = aiMoves.slice(0, 3);
  
  await apiCall('/users', 'POST', { userId, name: `User_${userId}`, email: `${userId}@test.com` });
  
  return {
    userId, persona, intentionText, microMoves, category,
    joinDay: 0, lastActiveDay: 0, checkInCount: 0, meaningfulDays: 0,
    journalsGenerated: 0, detailsAddedCount: 0, isPremium: false,
    hasInsights: false, isChurned: false, avgFulfillment: 50,
    scores: { body: 50, mind: 50, soul: 50, purpose: 50 },
  };
}

async function setIntention(user) {
  await apiCall('/intentions', 'POST', {
    userId: user.userId,
    intention: user.intentionText,
    microMoves: user.microMoves,
  });
}

async function performCheckIn(user, dayPart) {
  // Random check-in based on persona's rate
  if (Math.random() > user.persona.checkInRate) return false;
  
  const avgScore = (user.scores.body + user.scores.mind + user.scores.soul + user.scores.purpose) / 4;
  const mood = avgScore >= 70 ? 'great' : avgScore >= 55 ? 'good' : avgScore >= 40 ? 'neutral' : 'low';
  const microAct = Math.random() > 0.5 ? randomChoice(['walk', 'meditation', 'reading']) : null;
  
  const result = await apiCall('/check-ins', 'POST', {
    userId: user.userId,
    dayPart,
    mood,
    contexts: [randomChoice(['sleep', 'work', 'social'])],
    microAct,
    purposeProgress: microAct ? 'partly' : 'no',
  });
  
  if (result) {
    user.checkInCount++;
    // Update scores with randomness
    const impact = mood === 'great' ? 5 : mood === 'good' ? 3 : mood === 'neutral' ? 0 : -3;
    user.scores.body = Math.max(20, Math.min(100, user.scores.body + impact + (Math.random() * 4 - 2)));
    user.scores.mind = Math.max(20, Math.min(100, user.scores.mind + impact + (Math.random() * 4 - 2)));
    user.scores.soul = Math.max(20, Math.min(100, user.scores.soul + impact + (Math.random() * 4 - 2)));
    user.scores.purpose = Math.max(20, Math.min(100, user.scores.purpose + impact + (Math.random() * 4 - 2)));
    return true;
  }
  return false;
}

async function addDetails(user) {
  // Random details based on persona's rate
  if (Math.random() > user.persona.detailsRate) return false;
  
  const result = await apiCall('/details', 'POST', {
    userId: user.userId,
    sleepHours: 5 + Math.random() * 4,
    sleepQuality: Math.floor(2 + Math.random() * 3),
    exerciseType: Math.random() > 0.5 ? 'Walk' : 'Run',
    exerciseDuration: 15 + Math.floor(Math.random() * 45),
    breakfastNotes: user.category === 'weight' && Math.random() > 0.5 ? randomChoice([
      'Oatmeal with berries',
      'Greek yogurt with nuts',
      'Scrambled eggs with spinach',
      'Protein smoothie',
    ]) : null,
  });
  
  if (result) {
    user.detailsAddedCount++;
    return true;
  }
  return false;
}

async function generateJournal(user) {
  // Random journal generation based on persona's rate
  if (Math.random() > user.persona.journalRate) return false;
  
  const result = await apiCall('/journals/generate', 'POST', {
    userId: user.userId,
    tone: 'reflective',
  });
  
  if (result) {
    user.journalsGenerated++;
    const avgScore = (user.scores.body + user.scores.mind + user.scores.soul + user.scores.purpose) / 4;
    user.avgFulfillment = Math.round(avgScore);
    if (avgScore >= 65) user.meaningfulDays++;
    return true;
  }
  return false;
}

async function generateInsights(user, day) {
  // Insights available after Day 4 if enough data
  if (day < 4 || user.hasInsights || user.checkInCount < 8) return false;
  
  const result = await apiCall(`/insights/generate/${user.userId}`, 'POST');
  if (result) {
    user.hasInsights = true;
    user.insightsDay = day;
    return true;
  }
  return false;
}

function attemptConversion(user, day) {
  if (user.isPremium || user.isChurned) return false;
  
  let conversionProb = user.persona.conversionProbability;
  
  // Insights boost (3x multiplier)
  if (user.hasInsights) conversionProb *= 3.0;
  
  // Meaningful days boost
  if (user.meaningfulDays >= 3) conversionProb *= 1.3;
  
  // Time decay (lower chance early on)
  if (day < 5) conversionProb *= 0.5;
  
  // Add randomness
  const roll = Math.random();
  if (roll < conversionProb) {
    user.isPremium = true;
    simulation.overallMetrics.totalRevenue += 9.99;
    simulation.overallMetrics.premiumUsers++;
    return true;
  }
  return false;
}

function shouldChurn(user, day) {
  const baseRate = CONFIG.CHURN_RATE / CONFIG.SIM_DAYS;
  const rate = baseRate * user.persona.churnMultiplier * (user.hasInsights ? 0.7 : 1.0);
  return Math.random() < rate;
}

async function simulateDay(day) {
  console.log(`\n📅 DAY ${day}`);
  
  let active = 0, checkIns = 0, journals = 0, details = 0, conversions = 0, churns = 0, insights = 0;
  
  // Add new users gradually (Day 1-3)
  if (day <= 3 && simulation.users.length < CONFIG.TOTAL_USERS) {
    const toAdd = Math.ceil(CONFIG.TOTAL_USERS / 3);
    for (let i = 0; i < toAdd && simulation.users.length < CONFIG.TOTAL_USERS; i++) {
      const userId = `sim5_${String(simulation.users.length + 1).padStart(3, '0')}`;
      const user = await createUser(userId);
      await setIntention(user);
      simulation.users.push(user);
    }
  }
  
  // Simulate each user
  for (const user of simulation.users) {
    if (user.isChurned) continue;
    
    // Churn check
    if (day > user.joinDay && shouldChurn(user, day)) {
      user.isChurned = true;
      user.churnDay = day;
      simulation.overallMetrics.churnedUsers++;
      churns++;
      continue;
    }
    
    active++;
    user.lastActiveDay = day;
    
    // Check-ins (random per daypart)
    for (const dayPart of ['morning', 'day', 'evening', 'night']) {
      if (await performCheckIn(user, dayPart)) {
        checkIns++;
        // Maybe add details after check-in
        if (await addDetails(user)) details++;
      }
    }
    
    // Maybe generate journal
    if (await generateJournal(user)) journals++;
    
    // Maybe generate insights
    if (await generateInsights(user, day)) insights++;
    
    // Maybe convert to premium
    if (attemptConversion(user, day)) conversions++;
  }
  
  simulation.dailyMetrics.push({
    day,
    totalUsers: simulation.users.length,
    activeUsers: active,
    checkIns,
    journals,
    details,
    insights,
    conversions,
    churns,
    premiumUsers: simulation.users.filter(u => u.isPremium).length,
    revenue: simulation.overallMetrics.totalRevenue,
  });
  
  console.log(`   Active: ${active} | Check-ins: ${checkIns} | Journals: ${journals} | Premium: ${simulation.overallMetrics.premiumUsers} | Churned: ${churns}`);
}

function calculateAnalytics() {
  const active = simulation.users.filter(u => !u.isChurned);
  const premium = simulation.users.filter(u => u.isPremium);
  const withInsights = simulation.users.filter(u => u.hasInsights);
  const insightPremium = withInsights.filter(u => u.isPremium);
  const withoutInsights = simulation.users.filter(u => !u.hasInsights);
  const noInsightPremium = withoutInsights.filter(u => u.isPremium);
  
  const d7Users = simulation.users.filter(u => u.joinDay <= 7);
  const d7Active = d7Users.filter(u => !u.isChurned && u.lastActiveDay >= 7);
  
  // Breakdown by persona
  const personaBreakdown = {};
  for (const persona of PERSONAS) {
    const users = simulation.users.filter(u => u.persona.name === persona.name);
    personaBreakdown[persona.name] = {
      total: users.length,
      active: users.filter(u => !u.isChurned).length,
      premium: users.filter(u => u.isPremium).length,
      withInsights: users.filter(u => u.hasInsights).length,
      avgCheckIns: users.reduce((sum, u) => sum + u.checkInCount, 0) / users.length,
      avgJournals: users.reduce((sum, u) => sum + u.journalsGenerated, 0) / users.length,
      conversionRate: `${((users.filter(u => u.isPremium).length / users.length) * 100).toFixed(1)}%`,
    };
  }
  
  return {
    simulation: 'Sim5-Realistic',
    config: {
      users: CONFIG.TOTAL_USERS,
      days: CONFIG.SIM_DAYS,
      skeptics: '40%',
    },
    users: {
      total: simulation.users.length,
      active: active.length,
      premium: premium.length,
      churned: simulation.overallMetrics.churnedUsers,
      withInsights: withInsights.length,
    },
    retention: {
      d7: d7Users.length > 0 ? `${((d7Active.length / d7Users.length) * 100).toFixed(1)}%` : 'N/A',
      overall: `${((active.length / simulation.users.length) * 100).toFixed(1)}%`,
    },
    conversion: {
      overall: `${((premium.length / simulation.users.length) * 100).toFixed(1)}%`,
      withInsights: withInsights.length > 0 ? `${((insightPremium.length / withInsights.length) * 100).toFixed(1)}%` : 'N/A',
      withoutInsights: withoutInsights.length > 0 ? `${((noInsightPremium.length / withoutInsights.length) * 100).toFixed(1)}%` : 'N/A',
      insightsLift: withInsights.length > 0 && withoutInsights.length > 0 ? 
        `${(((insightPremium.length / withInsights.length) / (noInsightPremium.length / withoutInsights.length))).toFixed(1)}x` : 'N/A',
    },
    engagement: {
      avgCheckInsPerUser: (simulation.users.reduce((sum, u) => sum + u.checkInCount, 0) / simulation.users.length).toFixed(1),
      avgJournalsPerUser: (simulation.users.reduce((sum, u) => sum + u.journalsGenerated, 0) / simulation.users.length).toFixed(1),
      avgDetailsPerUser: (simulation.users.reduce((sum, u) => sum + u.detailsAddedCount, 0) / simulation.users.length).toFixed(1),
    },
    revenue: {
      mrr: `$${simulation.overallMetrics.totalRevenue.toFixed(2)}`,
      arpu: `$${(simulation.overallMetrics.totalRevenue / simulation.users.length).toFixed(2)}`,
    },
    api: {
      totalCalls: simulation.apiCallCount,
      errors: simulation.errors.length,
    },
    personaBreakdown,
  };
}

async function runSimulation() {
  console.log('🚀 SIM5: REALISTIC TEST with 40% Skeptics');
  console.log(`⚙️ ${CONFIG.TOTAL_USERS} users, ${CONFIG.SIM_DAYS} days, ${CONFIG.MINUTES_PER_DAY} min/day`);
  console.log(`👥 Demographics: 20% High | 40% Medium | 40% Skeptics\n`);
  
  // Check backend
  try {
    await fetch(`${CONFIG.API_BASE_URL.replace('/api', '')}/health`);
    console.log('✅ Backend running\n');
  } catch (error) {
    console.error('❌ Start backend first: cd backend && node server-sqlite.js');
    process.exit(1);
  }
  
  for (let day = 1; day <= CONFIG.SIM_DAYS; day++) {
    await simulateDay(day);
    if (day < CONFIG.SIM_DAYS) {
      await sleep(CONFIG.MINUTES_PER_DAY * 60 * 1000);
    }
  }
  
  const analytics = calculateAnalytics();
  console.log('\n📊 FINAL RESULTS:');
  console.log(JSON.stringify(analytics, null, 2));
  
  fs.writeFileSync(`${CONFIG.OUTPUT_DIR}/sim5-realistic-results.json`, JSON.stringify({
    config: CONFIG,
    analytics,
    dailyMetrics: simulation.dailyMetrics,
    userDetails: simulation.users,
  }, null, 2));
  
  console.log('\n✅ Sim5 complete!');
  console.log(`💾 Results: ${CONFIG.OUTPUT_DIR}/sim5-realistic-results.json`);
}

runSimulation().catch(console.error);

