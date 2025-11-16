const axios = require('axios');

// SIM12 OPTIMIZED SIMULATION
// 1000 users over 15 days with optimized rate limiting
// Rate limit: 5000 requests/minute
// User cap: 1000 users maximum
// Request delay: 300ms between requests

const API_BASE = 'http://localhost:3005';
const RATE_LIMIT_DELAY = 300; // 300ms between requests (2 requests per second)
const MAX_USERS = 1000; // Cap at 1000 users
const SIMULATION_DAYS = 15;
const MINUTES_PER_DAY = 2; // 2 minutes per day

// Industry-standard persona distribution
const PERSONA_DISTRIBUTION = {
  strugglers: 0.40,  // 40% - Users who need help
  casual: 0.30,      // 30% - Occasional users
  engaged: 0.20,     // 20% - Regular users
  premium: 0.10      // 10% - Power users
};

// Conversion rates by persona
const CONVERSION_RATES = {
  strugglers: 0.05,  // 5% conversion rate
  casual: 0.15,      // 15% conversion rate
  engaged: 0.35,     // 35% conversion rate
  premium: 0.60      // 60% conversion rate
};

// Churn rates by persona
const CHURN_RATES = {
  strugglers: 0.30,  // 30% churn rate
  casual: 0.20,      // 20% churn rate
  engaged: 0.10,     // 10% churn rate
  premium: 0.05      // 5% churn rate
};

let apiStats = {
  users: 0,
  checkIns: 0,
  journals: 0,
  insights: 0,
  details: 0,
  conversions: 0,
  churns: 0,
  errors: 0
};

let users = [];
let conversions = [];
let churns = [];

// Helper function to sleep
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Helper function to make API calls with retry logic
async function apiCall(endpoint, method = 'GET', data = null, userInfo = {}) {
  const maxRetries = 3;
  let attempt = 0;
  
  while (attempt < maxRetries) {
    try {
      const config = {
        method,
        url: `${API_BASE}${endpoint}`,
        headers: { 'Content-Type': 'application/json' },
        timeout: 10000
      };
      
      if (data) config.data = data;
      
      const response = await axios(config);
      return response.data;
    } catch (error) {
      attempt++;
      if (attempt >= maxRetries) {
        console.log(`   ❌ Error: ${error.response?.status || 'Network'} - ${error.message}`);
        apiStats.errors++;
        return null;
      }
      await sleep(1000 * attempt); // Exponential backoff
    }
  }
}

// Generate user data
function generateUsers(count) {
  const userList = [];
  const names = ['Alex', 'Blake', 'Casey', 'Drew', 'Emery', 'Finley', 'Gray', 'Harper', 'Indigo', 'Jamie', 'Kai', 'Lane', 'Max', 'Nova', 'Ocean', 'Phoenix', 'Quinn', 'River', 'Sage', 'Taylor', 'Vale', 'Wren', 'Zoe'];
  
  for (let i = 0; i < count; i++) {
    const persona = Math.random();
    let userPersona;
    
    if (persona < PERSONA_DISTRIBUTION.strugglers) {
      userPersona = 'strugglers';
    } else if (persona < PERSONA_DISTRIBUTION.strugglers + PERSONA_DISTRIBUTION.casual) {
      userPersona = 'casual';
    } else if (persona < PERSONA_DISTRIBUTION.strugglers + PERSONA_DISTRIBUTION.casual + PERSONA_DISTRIBUTION.engaged) {
      userPersona = 'engaged';
    } else {
      userPersona = 'premium';
    }
    
    const name = names[Math.floor(Math.random() * names.length)];
    const number = Math.floor(Math.random() * 300) + 1;
    
    userList.push({
      userId: `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      email: `${name.toLowerCase()}.${number}@example.com`,
      name: `${name} ${number}`,
      persona: userPersona,
      converted: false,
      churned: false,
      activities: 0,
      checkIns: 0,
      journals: 0
    });
  }
  
  return userList;
}

// Simulate user activities
async function simulateUserActivities(user, day) {
  const activities = [];
  
  // Check-in activities based on persona
  const checkInCount = user.persona === 'premium' ? 4 : 
                      user.persona === 'engaged' ? 3 : 
                      user.persona === 'casual' ? 2 : 1;
  
  const dayParts = ['morning', 'day', 'evening', 'night'];
  const moods = ['very-low', 'low', 'neutral', 'good', 'great'];
  const microActivities = ['meditation', 'gratitude', 'walk', 'reading', 'music', 'journaling', 'breathing', 'exercise', 'none'];
  
  for (let i = 0; i < checkInCount; i++) {
    const dayPart = dayParts[i];
    const mood = moods[Math.floor(Math.random() * moods.length)];
    const microActivity = microActivities[Math.floor(Math.random() * microActivities.length)];
    
    const checkInData = {
      user_id: user.userId,
      daypart: dayPart,
      mood: mood,
      micro_activity: microActivity,
      body_score: Math.floor(Math.random() * 5) + 1,
      mind_score: Math.floor(Math.random() * 5) + 1,
      soul_score: Math.floor(Math.random() * 5) + 1,
      purpose_score: Math.floor(Math.random() * 5) + 1
    };
    
    const result = await apiCall('/api/check-ins', 'POST', checkInData, { userId: user.userId, persona: user.persona });
    if (result) {
      user.checkIns++;
      apiStats.checkIns++;
      activities.push('check-in');
    }
    
    await sleep(RATE_LIMIT_DELAY);
  }
  
  // Details submission (30% chance)
  if (Math.random() < 0.3) {
    const detailsData = {
      userId: user.userId,
      sleepHours: 6 + Math.random() * 3,
      sleepQuality: Math.floor(Math.random() * 5) + 1,
      breakfast: Math.random() < 0.7 ? 'good' : 'poor',
      breakfastNotes: 'Quick breakfast',
      lunch: Math.random() < 0.8 ? 'good' : 'poor',
      lunchNotes: 'Healthy salad',
      dinner: Math.random() < 0.6 ? 'good' : 'poor',
      dinnerNotes: 'Home cooked meal',
      snacks: Math.random() < 0.4 ? 'healthy' : 'unhealthy',
      exerciseType: Math.random() < 0.5 ? 'cardio' : 'strength',
      exerciseDuration: Math.floor(Math.random() * 60) + 15,
      exerciseIntensity: Math.floor(Math.random() * 5) + 1,
      exerciseFeeling: Math.random() < 0.7 ? 'good' : 'tired',
      socialQuality: Math.floor(Math.random() * 5) + 1,
      socialWho: 'friends',
      socialDuration: Math.floor(Math.random() * 120) + 30,
      screenMinutes: Math.floor(Math.random() * 300) + 60
    };
    
    const result = await apiCall('/api/details', 'POST', detailsData, { userId: user.userId, persona: user.persona });
    if (result) {
      apiStats.details++;
      activities.push('details');
    }
    
    await sleep(RATE_LIMIT_DELAY);
  }
  
  // Journal generation (20% chance for engaged/premium, 10% for others)
  const journalChance = user.persona === 'premium' || user.persona === 'engaged' ? 0.2 : 0.1;
  if (Math.random() < journalChance) {
    const journalData = {
      user_id: user.userId,
      journalTone: ['reflective', 'analytical', 'poetic'][Math.floor(Math.random() * 3)],
      userNotes: `Daily notes from ${user.name}`
    };
    
    const result = await apiCall('/api/journals/generate', 'POST', journalData, { userId: user.userId, persona: user.persona });
    if (result) {
      user.journals++;
      apiStats.journals++;
      activities.push('journal');
    }
    
    await sleep(RATE_LIMIT_DELAY);
  }
  
  user.activities += activities.length;
  return activities;
}

// Check for conversion
function checkConversion(user, day) {
  if (user.converted || user.churned) return false;
  
  const conversionRate = CONVERSION_RATES[user.persona];
  const activityBonus = Math.min(user.activities * 0.05, 0.2); // Up to 20% bonus for activity
  const finalRate = Math.min(conversionRate + activityBonus, 0.8); // Cap at 80%
  
  if (Math.random() < finalRate) {
    user.converted = true;
    conversions.push({ user, day });
    apiStats.conversions++;
    console.log(`   💰 User ${user.name} (${user.persona}) converted to premium on day ${day}`);
    return true;
  }
  
  return false;
}

// Check for churn
function checkChurn(user, day) {
  if (user.converted || user.churned) return false;
  
  const churnRate = CHURN_RATES[user.persona];
  const activityPenalty = Math.max(user.activities * -0.02, -0.1); // Up to 10% penalty for low activity
  const finalRate = Math.max(churnRate + activityPenalty, 0.01); // Minimum 1% churn
  
  if (Math.random() < finalRate) {
    user.churned = true;
    churns.push({ user, day });
    apiStats.churns++;
    console.log(`   💔 User ${user.name} (${user.persona}) churned on day ${day}`);
    return true;
  }
  
  return false;
}

// Main simulation function
async function runSimulation() {
  console.log('🚀 Starting SIM12 Optimized Simulation');
  console.log('=====================================');
  console.log(`📊 Configuration:`);
  console.log(`   👥 Max Users: ${MAX_USERS}`);
  console.log(`   ⚡ Rate Limit: 5000 requests/minute`);
  console.log(`   ⏱️  Request Delay: ${RATE_LIMIT_DELAY}ms`);
  console.log(`   📅 Days: ${SIMULATION_DAYS} (${MINUTES_PER_DAY} minutes per day)`);
  console.log(`   🎯 Persona Distribution: ${JSON.stringify(PERSONA_DISTRIBUTION)}`);
  console.log('');
  
  const startTime = Date.now();
  
  // Phase 1: Create users (capped at 1000)
  console.log('👥 Phase 1: Creating users...');
  const userCount = MAX_USERS; // Use MAX_USERS directly
  users = generateUsers(userCount);
  
  for (const user of users) {
    const result = await apiCall('/api/users', 'POST', {
      email: user.email,
      name: user.name,
      persona: user.persona
    }, { userId: user.userId, persona: user.persona });
    
    if (result && result.id) {
      user.userId = result.id;
      apiStats.users++;
      console.log(`   ✅ User ${user.name} (${user.persona}) created successfully (ID: ${result.id})`);
    } else {
      console.log(`   ❌ Failed to create user ${user.name}`);
    }
    
    await sleep(RATE_LIMIT_DELAY);
  }
  
  console.log(`\n📊 User Creation Complete: ${apiStats.users} users created`);
  
  // Enforce strict user cap
  if (apiStats.users > MAX_USERS) {
    console.log(`⚠️  WARNING: Created ${apiStats.users} users, but cap is ${MAX_USERS}. Stopping simulation.`);
    return;
  }
  
  console.log('');
  
  // Phase 2: Simulate daily activities
  console.log('📅 Phase 2: Simulating daily activities...');
  
  for (let day = 1; day <= SIMULATION_DAYS; day++) {
    console.log(`\n📅 Day ${day}/${SIMULATION_DAYS}`);
    
    const activeUsers = users.filter(u => !u.churned);
    console.log(`   👥 Active Users: ${activeUsers.length}`);
    
    // Enforce user cap during daily activities
    if (activeUsers.length > MAX_USERS) {
      console.log(`⚠️  WARNING: ${activeUsers.length} active users exceeds cap of ${MAX_USERS}. Stopping simulation.`);
      break;
    }
    
    // Simulate activities for each active user
    for (const user of activeUsers) {
      if (user.churned) continue;
      
      const activities = await simulateUserActivities(user, day);
      
      // Check for conversion
      checkConversion(user, day);
      
      // Check for churn
      checkChurn(user, day);
      
      if (activities.length > 0) {
        console.log(`   📝 ${user.name} (${user.persona}): ${activities.join(', ')}`);
      }
    }
    
    // Day summary
    const dayConversions = conversions.filter(c => c.day === day).length;
    const dayChurns = churns.filter(c => c.day === day).length;
    
    console.log(`   💰 Conversions: ${dayConversions}`);
    console.log(`   💔 Churns: ${dayChurns}`);
    
    // Wait for next day (2 minutes = 120 seconds)
    if (day < SIMULATION_DAYS) {
      console.log(`   ⏳ Waiting for next day... (${MINUTES_PER_DAY} minutes)`);
      await sleep(MINUTES_PER_DAY * 60 * 1000);
    }
  }
  
  // Final results
  const endTime = Date.now();
  const duration = Math.round((endTime - startTime) / 1000 / 60);
  
  console.log('\n🎉 SIM12 SIMULATION COMPLETE');
  console.log('============================');
  console.log(`⏱️  Duration: ${duration} minutes`);
  console.log(`👥 Total Users: ${apiStats.users}`);
  console.log(`📝 Check-ins: ${apiStats.checkIns}`);
  console.log(`📖 Journals: ${apiStats.journals}`);
  console.log(`📋 Details: ${apiStats.details}`);
  console.log(`💰 Conversions: ${apiStats.conversions}`);
  console.log(`💔 Churns: ${apiStats.churns}`);
  console.log(`❌ Errors: ${apiStats.errors}`);
  
  // Conversion analysis
  const conversionRate = (apiStats.conversions / apiStats.users * 100).toFixed(2);
  const churnRate = (apiStats.churns / apiStats.users * 100).toFixed(2);
  
  console.log(`\n📊 Performance Metrics:`);
  console.log(`   🎯 Conversion Rate: ${conversionRate}%`);
  console.log(`   💔 Churn Rate: ${churnRate}%`);
  console.log(`   📈 Net Growth: ${apiStats.conversions - apiStats.churns} users`);
  
  // Revenue projection
  const monthlyRevenue = apiStats.conversions * 19.99;
  const annualRevenue = monthlyRevenue * 12;
  
  console.log(`\n💰 Revenue Projections:`);
  console.log(`   💵 Monthly Revenue: $${monthlyRevenue.toFixed(2)}`);
  console.log(`   💰 Annual Revenue: $${annualRevenue.toFixed(2)}`);
  
  // Persona breakdown
  console.log(`\n👥 Persona Breakdown:`);
  const personaStats = {};
  users.forEach(user => {
    if (!personaStats[user.persona]) {
      personaStats[user.persona] = { total: 0, converted: 0, churned: 0 };
    }
    personaStats[user.persona].total++;
    if (user.converted) personaStats[user.persona].converted++;
    if (user.churned) personaStats[user.persona].churned++;
  });
  
  Object.entries(personaStats).forEach(([persona, stats]) => {
    const convRate = (stats.converted / stats.total * 100).toFixed(1);
    const churnRate = (stats.churned / stats.total * 100).toFixed(1);
    console.log(`   ${persona}: ${stats.total} users, ${stats.converted} converted (${convRate}%), ${stats.churned} churned (${churnRate}%)`);
  });
  
  console.log('\n✅ Simulation completed successfully!');
}

// Start simulation
runSimulation().catch(console.error);
