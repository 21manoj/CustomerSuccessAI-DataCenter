/**
 * SIM11 - Industry Standard 15-Day Simulation
 * 1000 users over 15 days with realistic distribution and 20% churn
 * 
 * Industry Standard Distribution:
 * - Strugglers (40%): High churn, low conversion
 * - Casual (30%): Medium engagement, moderate conversion  
 * - Engaged (20%): High engagement, high conversion
 * - Premium (10%): Already converted, highest retention
 */

const axios = require('axios');

// Configuration
const TOTAL_USERS = 1000;
const SIMULATION_DAYS = 15;
const MINUTES_PER_DAY = 2; // 2 minutes per day
const TOTAL_MINUTES = SIMULATION_DAYS * MINUTES_PER_DAY;
const CHURN_RATE = 0.20; // 20% churn

// Industry Standard User Distribution
const USER_DISTRIBUTION = {
  strugglers: { percentage: 0.40, churnRate: 0.35, conversionRate: 0.05, engagement: 0.3 },
  casual: { percentage: 0.30, churnRate: 0.15, conversionRate: 0.15, engagement: 0.6 },
  engaged: { percentage: 0.20, churnRate: 0.05, conversionRate: 0.45, engagement: 0.9 },
  premium: { percentage: 0.10, churnRate: 0.02, conversionRate: 0.95, engagement: 0.95 }
};

// Pricing tiers
const PRICING = {
  basic: 9.99,
  premium: 19.99,
  pro: 29.99
};

// API Configuration
const API_BASE = 'http://localhost:3005';
const RATE_LIMIT_DELAY = 200; // 200ms between requests (5 requests per second)

// Statistics tracking
let stats = {
  users: [],
  totalUsers: 0,
  activeUsers: 0,
  churnedUsers: 0,
  premiumUsers: 0,
  totalCheckIns: 0,
  totalJournals: 0,
  totalInsights: 0,
  totalDetails: 0,
  apiCalls: 0,
  errors: 0,
  startTime: null,
  endTime: null,
  dailyStats: [],
  conversionFunnel: {
    registered: 0,
    activated: 0,
    engaged: 0,
    converted: 0
  },
  revenue: {
    mrr: 0,
    arr: 0,
    totalRevenue: 0
  }
};

// Utility functions
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const getRandomElement = (array) => array[Math.floor(Math.random() * array.length)];

const getRandomBetween = (min, max) => Math.random() * (max - min) + min;

const generateUserId = () => `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

const generateEmail = (name) => `${name.toLowerCase().replace(/\s+/g, '.')}@example.com`;

// User persona data
const PERSONA_DATA = {
  strugglers: {
    names: ['Alex', 'Jordan', 'Casey', 'Taylor', 'Morgan', 'Riley', 'Avery', 'Quinn'],
    moods: ['very-low', 'low', 'neutral'],
    activities: ['none', 'music', 'walk'],
    engagement: 0.3,
    checkInFrequency: 0.4
  },
  casual: {
    names: ['Sam', 'Chris', 'Jamie', 'Drew', 'Blake', 'Sage', 'River', 'Phoenix'],
    moods: ['low', 'neutral', 'good'],
    activities: ['walk', 'music', 'reading', 'meditation'],
    engagement: 0.6,
    checkInFrequency: 0.7
  },
  engaged: {
    names: ['Max', 'Zoe', 'Kai', 'Luna', 'Nova', 'Atlas', 'Sage', 'Indigo'],
    moods: ['neutral', 'good', 'great'],
    activities: ['meditation', 'journaling', 'exercise', 'gratitude', 'reading'],
    engagement: 0.9,
    checkInFrequency: 0.9
  },
  premium: {
    names: ['Aria', 'Phoenix', 'Sage', 'River', 'Luna', 'Nova', 'Atlas', 'Indigo'],
    moods: ['good', 'great'],
    activities: ['meditation', 'journaling', 'exercise', 'gratitude', 'reading', 'breathing'],
    engagement: 0.95,
    checkInFrequency: 0.95
  }
};

// API call wrapper with error handling
async function apiCall(endpoint, method = 'GET', data = null, userContext = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    method,
    url,
    headers: { 'Content-Type': 'application/json' },
    timeout: 10000
  };
  
  if (data) {
    config.data = data;
  }

  try {
    stats.apiCalls++;
    const response = await axios(config);
    
    // Log API call details
    console.log(`🔗 [${new Date().toLocaleTimeString()}] API Call #${stats.apiCalls}`);
    console.log(`   📡 ${method} ${endpoint}`);
    if (userContext.userId) {
      console.log(`   👤 User: ${userContext.userId} (${userContext.persona || 'Unknown'})`);
    }
    if (data) {
      console.log(`   📦 Body: ${JSON.stringify(data).substring(0, 100)}${JSON.stringify(data).length > 100 ? '...' : ''}`);
    }
    console.log(`   ✅ Success: ${response.status} ${response.statusText}`);
    console.log(`   📊 Response: ${JSON.stringify(response.data).substring(0, 100)}${JSON.stringify(response.data).length > 100 ? '...' : ''}`);
    
    return response.data;
  } catch (error) {
    stats.errors++;
    console.log(`   ❌ Error: ${error.response?.status || 'Network'} - ${error.message}`);
    return null;
  }
}

// Generate user distribution
function generateUserDistribution() {
  const users = [];
  const distribution = USER_DISTRIBUTION;
  
  for (const [persona, config] of Object.entries(distribution)) {
    const count = Math.floor(TOTAL_USERS * config.percentage);
    const personaData = PERSONA_DATA[persona];
    
    for (let i = 0; i < count; i++) {
      const name = getRandomElement(personaData.names);
      const user = {
        userId: generateUserId(),
        name: `${name} ${i + 1}`,
        email: generateEmail(`${name} ${i + 1}`),
        persona: persona,
        churnRate: config.churnRate,
        conversionRate: config.conversionRate,
        engagement: config.engagement,
        checkInFrequency: personaData.checkInFrequency,
        moods: personaData.moods,
        activities: personaData.activities,
        isActive: true,
        isPremium: persona === 'premium',
        joinDay: Math.floor(Math.random() * SIMULATION_DAYS), // Random join day
        churnDay: null,
        conversionDay: null,
        totalCheckIns: 0,
        totalJournals: 0,
        totalInsights: 0,
        totalDetails: 0
      };
      
      users.push(user);
    }
  }
  
  // Shuffle users to randomize join order
  return users.sort(() => Math.random() - 0.5);
}

// Create user in backend
async function createUser(user) {
  const result = await apiCall('/api/users', 'POST', {
    email: user.email,
    name: user.name,
    persona: user.persona
  }, { userId: user.userId, persona: user.persona });

  if (result && result.id) {
    user.backendId = result.id;
    user.isCreated = true;
    stats.totalUsers++;
    console.log(`   ✅ User ${user.name} (${user.persona}) created successfully (ID: ${result.id})`);
    return true;
  } else {
    console.log(`   ❌ Failed to create user ${user.name}`);
    return false;
  }
}

// Simulate user activity for a day
async function simulateUserDay(user, day) {
  if (!user.isActive || user.churnDay !== null) return;
  
  // Check for churn
  if (Math.random() < user.churnRate / SIMULATION_DAYS) {
    user.isActive = false;
    user.churnDay = day;
    stats.churnedUsers++;
    stats.activeUsers--;
    console.log(`   💔 User ${user.name} (${user.persona}) churned on day ${day}`);
    return;
  }
  
  // Check for conversion (if not already premium)
  if (!user.isPremium && Math.random() < user.conversionRate / SIMULATION_DAYS) {
    user.isPremium = true;
    user.conversionDay = day;
    stats.premiumUsers++;
    console.log(`   💰 User ${user.name} (${user.persona}) converted to premium on day ${day}`);
  }
  
  // Simulate check-ins (2-4 per day based on engagement)
  const checkInsPerDay = Math.floor(getRandomBetween(1, 3) * user.checkInFrequency);
  const dayParts = ['morning', 'day', 'evening', 'night'];
  
  for (let i = 0; i < checkInsPerDay; i++) {
    const dayPart = getRandomElement(dayParts);
    const mood = getRandomElement(user.moods);
    const activity = getRandomElement(user.activities);
    
    const checkInData = {
      user_id: user.backendId,
      daypart: dayPart,
      mood: mood,
      micro_activity: activity,
      body_score: Math.floor(Math.random() * 5) + 1,
      mind_score: Math.floor(Math.random() * 5) + 1,
      soul_score: Math.floor(Math.random() * 5) + 1,
      purpose_score: Math.floor(Math.random() * 5) + 1
    };
    
    const result = await apiCall('/api/check-ins', 'POST', checkInData, { userId: user.userId, persona: user.persona });
    if (result) {
      user.totalCheckIns++;
      stats.totalCheckIns++;
    }
    
    await sleep(RATE_LIMIT_DELAY);
  }
  
  // Simulate details (30% chance per day)
  if (Math.random() < 0.3) {
    const detailsData = {
      userId: user.backendId,
      sleepHours: getRandomBetween(6, 9),
      sleepQuality: Math.floor(Math.random() * 5) + 1,
      breakfast: getRandomElement(['good', 'okay', 'skipped']),
      breakfastNotes: `Breakfast notes for ${user.name}`,
      lunch: getRandomElement(['healthy', 'okay', 'heavy']),
      lunchNotes: `Lunch notes for ${user.name}`,
      dinner: getRandomElement(['light', 'balanced', 'heavy']),
      dinnerNotes: `Dinner notes for ${user.name}`,
      snacks: Math.floor(Math.random() * 3),
      exerciseType: getRandomElement(['walking', 'running', 'yoga', 'gym', 'none']),
      exerciseDuration: Math.floor(Math.random() * 60),
      exerciseIntensity: Math.floor(Math.random() * 5) + 1,
      exerciseFeeling: getRandomElement(['energized', 'tired', 'good', 'great']),
      socialQuality: Math.floor(Math.random() * 5) + 1,
      socialWho: getRandomElement(['friends', 'family', 'colleagues', 'alone']),
      socialDuration: Math.floor(Math.random() * 120),
      screenMinutes: Math.floor(Math.random() * 300)
    };
    
    const result = await apiCall('/api/details', 'POST', detailsData, { userId: user.userId, persona: user.persona });
    if (result) {
      user.totalDetails++;
      stats.totalDetails++;
    }
    
    await sleep(RATE_LIMIT_DELAY);
  }
  
  // Simulate journal generation (20% chance per day for engaged users)
  if (user.persona === 'engaged' || user.persona === 'premium') {
    if (Math.random() < 0.2) {
      const journalData = {
        user_id: user.backendId,
        journalTone: getRandomElement(['reflective', 'analytical', 'poetic']),
        userNotes: `Daily notes from ${user.name}`
      };
      
      const result = await apiCall('/api/journals/generate', 'POST', journalData, { userId: user.userId, persona: user.persona });
      if (result) {
        user.totalJournals++;
        stats.totalJournals++;
      }
      
      await sleep(RATE_LIMIT_DELAY);
    }
  }
}

// Calculate daily statistics
function calculateDailyStats(day) {
  const activeUsers = stats.users.filter(u => u.isActive && u.churnDay === null).length;
  const premiumUsers = stats.users.filter(u => u.isPremium).length;
  const totalCheckIns = stats.users.reduce((sum, u) => sum + u.totalCheckIns, 0);
  const totalJournals = stats.users.reduce((sum, u) => sum + u.totalJournals, 0);
  const totalInsights = stats.users.reduce((sum, u) => sum + u.totalInsights, 0);
  
  // Calculate MRR
  const mrr = premiumUsers * PRICING.premium; // Assuming all premium users pay $19.99
  
  const dailyStat = {
    day,
    activeUsers,
    premiumUsers,
    totalCheckIns,
    totalJournals,
    totalInsights,
    mrr,
    arr: mrr * 12,
    conversionRate: premiumUsers / Math.max(activeUsers, 1),
    churnRate: stats.churnedUsers / Math.max(stats.totalUsers, 1)
  };
  
  stats.dailyStats.push(dailyStat);
  
  console.log(`\n📊 Day ${day} Summary:`);
  console.log(`   👥 Active Users: ${activeUsers}`);
  console.log(`   💰 Premium Users: ${premiumUsers}`);
  console.log(`   📝 Total Check-ins: ${totalCheckIns}`);
  console.log(`   📖 Total Journals: ${totalJournals}`);
  console.log(`   💡 Total Insights: ${totalInsights}`);
  console.log(`   💵 MRR: $${mrr.toFixed(2)}`);
  console.log(`   📈 Conversion Rate: ${(dailyStat.conversionRate * 100).toFixed(1)}%`);
  console.log(`   💔 Churn Rate: ${(dailyStat.churnRate * 100).toFixed(1)}%`);
}

// Main simulation function
async function runSimulation() {
  console.log('🚀 Starting SIM11 - Industry Standard 15-Day Simulation');
  console.log(`📊 ${TOTAL_USERS} users over ${SIMULATION_DAYS} days (${TOTAL_MINUTES} minutes total)`);
  console.log(`⏱️  ${MINUTES_PER_DAY} minutes per day`);
  console.log(`💔 ${(CHURN_RATE * 100)}% churn rate`);
  console.log('=' * 60);
  
  stats.startTime = new Date();
  
  // Generate users
  console.log('\n👥 Generating user distribution...');
  stats.users = generateUserDistribution();
  
  // Log distribution
  const distribution = {};
  stats.users.forEach(user => {
    distribution[user.persona] = (distribution[user.persona] || 0) + 1;
  });
  
  console.log('📊 User Distribution:');
  Object.entries(distribution).forEach(([persona, count]) => {
    const percentage = (count / TOTAL_USERS * 100).toFixed(1);
    console.log(`   ${persona}: ${count} users (${percentage}%)`);
  });
  
  // Create users in backend
  console.log('\n🔧 Creating users in backend...');
  for (const user of stats.users) {
    await createUser(user);
    await sleep(RATE_LIMIT_DELAY);
  }
  
  stats.activeUsers = stats.users.filter(u => u.isActive).length;
  
  // Run simulation day by day
  console.log('\n🎬 Starting daily simulation...');
  
  for (let day = 1; day <= SIMULATION_DAYS; day++) {
    console.log(`\n📅 Day ${day}/${SIMULATION_DAYS}`);
    
    // Get users who joined on this day
    const todaysUsers = stats.users.filter(u => u.joinDay === day - 1);
    console.log(`   👥 ${todaysUsers.length} users joining today`);
    
    // Simulate activity for all active users
    const activeUsers = stats.users.filter(u => u.isActive && u.churnDay === null);
    console.log(`   🎯 ${activeUsers.length} active users to simulate`);
    
    for (const user of activeUsers) {
      await simulateUserDay(user, day);
      await sleep(RATE_LIMIT_DELAY);
    }
    
    // Calculate and log daily stats
    calculateDailyStats(day);
    
    // Wait for next day (2 minutes)
    if (day < SIMULATION_DAYS) {
      console.log(`   ⏳ Waiting 2 minutes for next day...`);
      await sleep(2 * 60 * 1000); // 2 minutes
    }
  }
  
  stats.endTime = new Date();
  
  // Final results
  console.log('\n🏆 SIMULATION COMPLETE!');
  console.log('=' * 60);
  
  const duration = (stats.endTime - stats.startTime) / 1000 / 60; // minutes
  const finalActiveUsers = stats.users.filter(u => u.isActive && u.churnDay === null).length;
  const finalPremiumUsers = stats.users.filter(u => u.isPremium).length;
  const finalMRR = finalPremiumUsers * PRICING.premium;
  const finalARR = finalMRR * 12;
  
  console.log(`⏱️  Duration: ${duration.toFixed(1)} minutes`);
  console.log(`👥 Total Users: ${stats.totalUsers}`);
  console.log(`✅ Active Users: ${finalActiveUsers}`);
  console.log(`💔 Churned Users: ${stats.churnedUsers}`);
  console.log(`💰 Premium Users: ${finalPremiumUsers}`);
  console.log(`📝 Total Check-ins: ${stats.totalCheckIns}`);
  console.log(`📖 Total Journals: ${stats.totalJournals}`);
  console.log(`💡 Total Insights: ${stats.totalInsights}`);
  console.log(`🔗 Total API Calls: ${stats.apiCalls}`);
  console.log(`❌ Total Errors: ${stats.errors}`);
  console.log(`💵 Final MRR: $${finalMRR.toFixed(2)}`);
  console.log(`💵 Final ARR: $${finalARR.toFixed(2)}`);
  console.log(`📈 Final Conversion Rate: ${(finalPremiumUsers / Math.max(finalActiveUsers, 1) * 100).toFixed(1)}%`);
  console.log(`💔 Final Churn Rate: ${(stats.churnedUsers / Math.max(stats.totalUsers, 1) * 100).toFixed(1)}%`);
  
  // Persona breakdown
  console.log('\n👥 Persona Breakdown:');
  Object.entries(USER_DISTRIBUTION).forEach(([persona, config]) => {
    const personaUsers = stats.users.filter(u => u.persona === persona);
    const activePersonaUsers = personaUsers.filter(u => u.isActive && u.churnDay === null);
    const premiumPersonaUsers = personaUsers.filter(u => u.isPremium);
    const churnedPersonaUsers = personaUsers.filter(u => u.churnDay !== null);
    
    console.log(`\n   ${persona.toUpperCase()}:`);
    console.log(`     Total: ${personaUsers.length}`);
    console.log(`     Active: ${activePersonaUsers.length}`);
    console.log(`     Premium: ${premiumPersonaUsers.length}`);
    console.log(`     Churned: ${churnedPersonaUsers.length}`);
    console.log(`     Conversion Rate: ${(premiumPersonaUsers.length / Math.max(activePersonaUsers.length, 1) * 100).toFixed(1)}%`);
    console.log(`     Churn Rate: ${(churnedPersonaUsers.length / Math.max(personaUsers.length, 1) * 100).toFixed(1)}%`);
  });
  
  // Save results
  const results = {
    simulation: 'SIM11',
    config: {
      totalUsers: TOTAL_USERS,
      simulationDays: SIMULATION_DAYS,
      minutesPerDay: MINUTES_PER_DAY,
      churnRate: CHURN_RATE,
      userDistribution: USER_DISTRIBUTION,
      pricing: PRICING
    },
    stats: {
      ...stats,
      finalActiveUsers,
      finalPremiumUsers,
      finalMRR,
      finalARR,
      duration
    },
    timestamp: new Date().toISOString()
  };
  
  const fs = require('fs');
  const filename = `simulator/output/sim11-results-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
  fs.writeFileSync(filename, JSON.stringify(results, null, 2));
  console.log(`\n💾 Results saved to: ${filename}`);
}

// Run the simulation
if (require.main === module) {
  runSimulation().catch(console.error);
}

module.exports = { runSimulation };
