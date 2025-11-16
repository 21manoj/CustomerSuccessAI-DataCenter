/**
 * SIM4: QUICK TEST (30 minutes runtime)
 * 
 * Faster version of Sim4 for testing:
 * - 100 users (vs 500)
 * - 12 days (vs 24)
 * - 2 min per day (vs 10 min)
 * - Total runtime: ~24 minutes
 */

const fetch = require('node-fetch');
const fs = require('fs');

// Quick Test Configuration
const CONFIG = {
  API_BASE_URL: 'http://localhost:3005/api',
  TOTAL_USERS: 100,
  SIM_DAYS: 12,
  MINUTES_PER_DAY: 2, // Faster for testing
  CHURN_RATE: 0.20,
  OUTPUT_DIR: './simulator/output',
  START_TIME: Date.now(),
};

// Copy all the same code from sim4-real-app.js but with faster CONFIG
// ... (same personas, functions, etc.)

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
    microMovePreference: 'ai',
    engagementLevel: 'high',
    conversionProbability: 0.15,  // 15% → 45% with insights
    checkInConsistency: 0.85,     // 85% of check-ins completed
  },
  {
    name: 'Purpose-Driven',
    weight: 0.08,
    intentions: [
      'Build sustainable fitness habits',
      'Have more energy throughout the day',
      'Build deeper connections with loved ones'
    ],
    microMovePreference: 'hybrid',
    engagementLevel: 'high',
    conversionProbability: 0.12,  // 12% → 36% with insights
    checkInConsistency: 0.80,
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
    microMovePreference: 'random',
    engagementLevel: 'medium',
    conversionProbability: 0.07,  // 7% → 21% with insights
    checkInConsistency: 0.60,
  },
  {
    name: 'Curious Explorer',
    weight: 0.15,
    intentions: [
      'Just want to try this out',
      'See if this helps me feel better',
      'Looking for something new'
    ],
    microMovePreference: 'random',
    engagementLevel: 'medium',
    conversionProbability: 0.05,  // 5% → 15% with insights
    checkInConsistency: 0.55,
  },
  {
    name: 'Inconsistent Optimist',
    weight: 0.10,
    intentions: [
      'Want to make a change',
      'Get in better shape this month',
      'Reduce distractions'
    ],
    microMovePreference: 'ai',
    engagementLevel: 'medium',
    conversionProbability: 0.06,  // 6% → 18% with insights
    checkInConsistency: 0.50,
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
    microMovePreference: 'random',
    engagementLevel: 'low',
    conversionProbability: 0.02,  // 2% → 6% with insights
    checkInConsistency: 0.35,
  },
  {
    name: 'Overwhelmed Struggler',
    weight: 0.15,
    intentions: [
      'Life feels overwhelming lately',
      'Need help but not sure where to start',
      'Everything seems too hard'
    ],
    microMovePreference: 'random',
    engagementLevel: 'low',
    conversionProbability: 0.01,  // 1% → 3% with insights
    checkInConsistency: 0.30,
  },
  {
    name: 'App Collector',
    weight: 0.10,
    intentions: [
      'Downloaded a bunch of apps',
      'Maybe this one will work',
      'Probably will forget about it'
    ],
    microMovePreference: 'random',
    engagementLevel: 'low',
    conversionProbability: 0.01,  // 1% → 3% with insights
    checkInConsistency: 0.25,
  },
];

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

const simulation = {
  users: [],
  dailyMetrics: [],
  overallMetrics: { totalRevenue: 0, premiumUsers: 0, churnedUsers: 0 },
  apiCallCount: 0,
  errors: [],
};

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
  
  let category = 'presence';
  const lower = intentionText.toLowerCase();
  if (lower.includes('weight') || lower.includes('lose')) category = 'weight';
  else if (lower.includes('presence') || lower.includes('mindful')) category = 'presence';
  else if (lower.includes('energy')) category = 'energy';
  else if (lower.includes('focus')) category = 'focus';
  else if (lower.includes('connect')) category = 'connection';
  
  const aiMoves = AI_SUGGESTED_MICRO_MOVES[category] || AI_SUGGESTED_MICRO_MOVES.presence;
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
  const checkInProb = { high: 0.85, medium: 0.65, low: 0.40 };
  if (Math.random() > checkInProb[user.persona.engagementLevel]) return false;
  
  const avgScore = (user.scores.body + user.scores.mind + user.scores.soul + user.scores.purpose) / 4;
  const mood = avgScore >= 70 ? 'great' : avgScore >= 55 ? 'good' : 'neutral';
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
    user.scores.body = Math.min(100, user.scores.body + (mood === 'great' ? 5 : 3));
    user.scores.mind = Math.min(100, user.scores.mind + (mood === 'great' ? 5 : 3));
    return true;
  }
  return false;
}

async function addDetails(user) {
  const detailsProb = { high: 0.60, medium: 0.35, low: 0.10 };
  if (Math.random() > detailsProb[user.persona.engagementLevel]) return false;
  
  const result = await apiCall('/details', 'POST', {
    userId: user.userId,
    sleepHours: 6 + Math.random() * 3,
    sleepQuality: Math.floor(3 + Math.random() * 2),
    exerciseType: Math.random() > 0.5 ? 'Walk' : 'Run',
    exerciseDuration: 30,
    breakfastNotes: user.category === 'weight' ? 'Oatmeal with berries' : null,
  });
  
  if (result) {
    user.detailsAddedCount++;
    return true;
  }
  return false;
}

async function generateJournal(user) {
  const journalProb = { high: 0.75, medium: 0.50, low: 0.20 };
  if (Math.random() > journalProb[user.persona.engagementLevel]) return false;
  
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
  if (day < 4 || user.hasInsights) return false;
  
  const result = await apiCall(`/insights/generate/${user.userId}`, 'POST');
  if (result) {
    user.hasInsights = true;
    user.insightsDay = day;
    return true;
  }
  return false;
}

function attemptConversion(user) {
  if (user.isPremium || user.isChurned) return false;
  
  let conversionProb = user.persona.conversionProbability;
  if (user.hasInsights) conversionProb *= 3.0;
  if (user.meaningfulDays >= 3) conversionProb *= 1.5;
  
  if (Math.random() < conversionProb) {
    user.isPremium = true;
    simulation.overallMetrics.totalRevenue += 9.99;
    simulation.overallMetrics.premiumUsers++;
    return true;
  }
  return false;
}

function shouldChurn(user, day) {
  const baseRate = CONFIG.CHURN_RATE / CONFIG.SIM_DAYS;
  const mult = { high: 0.5, medium: 1.0, low: 2.0 };
  const rate = baseRate * mult[user.persona.engagementLevel] * (user.hasInsights ? 0.7 : 1.0);
  return Math.random() < rate;
}

async function simulateDay(day) {
  console.log(`\n📅 DAY ${day}`);
  
  let active = 0, checkIns = 0, journals = 0, details = 0, conversions = 0, churns = 0, insights = 0;
  
  // Add new users (gradual)
  if (day <= 5 && simulation.users.length < CONFIG.TOTAL_USERS) {
    const toAdd = Math.ceil(CONFIG.TOTAL_USERS / 5);
    for (let i = 0; i < toAdd && simulation.users.length < CONFIG.TOTAL_USERS; i++) {
      const userId = `sim4_quick_${String(simulation.users.length + 1).padStart(3, '0')}`;
      const user = await createUser(userId);
      await setIntention(user);
      simulation.users.push(user);
    }
  }
  
  // Simulate each user
  for (const user of simulation.users) {
    if (user.isChurned) continue;
    
    if (day > user.joinDay && shouldChurn(user, day)) {
      user.isChurned = true;
      user.churnDay = day;
      simulation.overallMetrics.churnedUsers++;
      churns++;
      continue;
    }
    
    active++;
    user.lastActiveDay = day;
    
    for (const dayPart of ['morning', 'day', 'evening', 'night']) {
      if (await performCheckIn(user, dayPart)) {
        checkIns++;
        if (Math.random() > 0.6 && await addDetails(user)) details++;
      }
    }
    
    if (await generateJournal(user)) journals++;
    if (await generateInsights(user, day)) insights++;
    if (attemptConversion(user)) conversions++;
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
    premiumUsers: simulation.users.filter(u => u.isPremium).length,
    revenue: simulation.overallMetrics.totalRevenue,
  });
  
  console.log(`   Active: ${active} | Check-ins: ${checkIns} | Journals: ${journals} | Premium: ${simulation.overallMetrics.premiumUsers}`);
}

function calculateAnalytics() {
  const active = simulation.users.filter(u => !u.isChurned);
  const premium = simulation.users.filter(u => u.isPremium);
  const withInsights = simulation.users.filter(u => u.hasInsights);
  const insightPremium = withInsights.filter(u => u.isPremium);
  
  const d7Users = simulation.users.filter(u => u.joinDay <= 7);
  const d7Active = d7Users.filter(u => !u.isChurned && u.lastActiveDay >= 7);
  
  return {
    simulation: 'Sim4-Quick',
    users: {
      total: simulation.users.length,
      active: active.length,
      premium: premium.length,
      withInsights: withInsights.length,
    },
    retention: {
      d7: d7Users.length > 0 ? `${((d7Active.length / d7Users.length) * 100).toFixed(1)}%` : 'N/A',
      overall: `${((active.length / simulation.users.length) * 100).toFixed(1)}%`,
    },
    conversion: {
      overall: `${((premium.length / simulation.users.length) * 100).toFixed(1)}%`,
      withInsights: withInsights.length > 0 ? `${((insightPremium.length / withInsights.length) * 100).toFixed(1)}%` : 'N/A',
    },
    revenue: {
      mrr: `$${simulation.overallMetrics.totalRevenue.toFixed(2)}`,
    },
    api: {
      totalCalls: simulation.apiCallCount,
      errors: simulation.errors.length,
    },
  };
}

async function runSimulation() {
  console.log('🚀 SIM4-QUICK: Real App Test (30 min runtime)');
  console.log(`⚙️ ${CONFIG.TOTAL_USERS} users, ${CONFIG.SIM_DAYS} days, ${CONFIG.MINUTES_PER_DAY} min/day\n`);
  
  // Check backend
  try {
    await fetch(`${CONFIG.API_BASE_URL.replace('/api', '')}/health`);
    console.log('✅ Backend running\n');
  } catch (error) {
    console.error('❌ Start backend first: cd backend && node server.js');
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
  
  fs.writeFileSync(`${CONFIG.OUTPUT_DIR}/sim4-quick-results.json`, JSON.stringify({
    config: CONFIG,
    analytics,
    dailyMetrics: simulation.dailyMetrics,
  }, null, 2));
  
  console.log('\n✅ Quick test complete!');
  console.log(`💾 Results: ${CONFIG.OUTPUT_DIR}/sim4-quick-results.json`);
}

runSimulation().catch(console.error);

