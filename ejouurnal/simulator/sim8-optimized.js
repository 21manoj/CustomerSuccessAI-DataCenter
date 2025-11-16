const axios = require('axios');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// ========================================
// SIM8: OPTIMIZED FOR 40 CONCURRENT USERS
// ========================================

const API_BASE = 'http://localhost:3005';
const API_TIMEOUT = 10000; // 10 seconds
const TOTAL_USERS = 1000;
const INITIAL_USERS = 40; // Start with 40 users
const NEW_USERS_PER_DAY = 40; // Add 40 users per day
const TOTAL_DAYS = 12;
const MINUTES_PER_DAY = 2; // 2 minutes = 1 day

// Demographics (Sim3 + Sim6 fixes)
const personas = [
  ...Array(300).fill('engaged'),      // 30%
  ...Array(450).fill('casual'),       // 45%
  ...Array(200).fill('struggler'),    // 20%
  ...Array(50).fill('power-user'),    // 5%
];

// Conversion rates (Sim6 fixes)
const conversionRates = {
  'power-user': 0.15,    // 15% (was 40%)
  'engaged': 0.12,       // 12% (was 25%)
  'casual': 0.04,        // 4% (was 8%)
  'struggler': 0.01,     // 1% (was 2%)
};

// Churn rates
const churnRates = {
  'power-user': 0.02,    // 2%
  'engaged': 0.05,       // 5%
  'casual': 0.15,        // 15%
  'struggler': 0.25,     // 25%
};

// ========================================
// HELPER FUNCTIONS
// ========================================

async function makeAPICall(endpoint, data = null, method = 'GET') {
  try {
    const config = {
      method,
      url: `${API_BASE}${endpoint}`,
      timeout: API_TIMEOUT,
      headers: { 'Content-Type': 'application/json' }
    };
    
    if (data) {
      config.data = data;
    }
    
    const response = await axios(config);
    return { success: true, data: response.data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

async function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function getRandomPersona() {
  return personas[Math.floor(Math.random() * personas.length)];
}

function getRandomMood() {
  const moods = ['low', 'rough', 'okay', 'good', 'great'];
  const weights = [0.1, 0.15, 0.3, 0.3, 0.15]; // More realistic distribution
  const random = Math.random();
  let cumulative = 0;
  
  for (let i = 0; i < moods.length; i++) {
    cumulative += weights[i];
    if (random <= cumulative) {
      return moods[i];
    }
  }
  return 'okay';
}

function getRandomDaypart() {
  const dayparts = ['morning', 'afternoon', 'evening', 'night'];
  return dayparts[Math.floor(Math.random() * dayparts.length)];
}

function getRandomMicroActivity() {
  const activities = [
    'gratitude', 'meditation', 'exercise', 'reading', 'walking',
    'cooking', 'socializing', 'learning', 'resting', 'planning'
  ];
  return activities[Math.floor(Math.random() * activities.length)];
}

function calculateScores(mood, persona) {
  const baseScores = {
    'power-user': { body: 75, mind: 80, soul: 85, purpose: 90 },
    'engaged': { body: 70, mind: 75, soul: 80, purpose: 85 },
    'casual': { body: 60, mind: 65, soul: 70, purpose: 75 },
    'struggler': { body: 45, mind: 50, soul: 55, purpose: 60 }
  };
  
  const base = baseScores[persona];
  const moodMultiplier = {
    'low': 0.6,
    'rough': 0.7,
    'okay': 0.85,
    'good': 1.0,
    'great': 1.15
  };
  
  const multiplier = moodMultiplier[mood] || 0.85;
  
  return {
    body: Math.round(base.body * multiplier),
    mind: Math.round(base.mind * multiplier),
    soul: Math.round(base.soul * multiplier),
    purpose: Math.round(base.purpose * multiplier)
  };
}

// ========================================
// SIMULATION FUNCTIONS
// ========================================

async function startBackend() {
  return new Promise((resolve, reject) => {
    console.log('🚀 Starting optimized backend...');
    
    const backend = spawn('node', ['server-optimized.js'], {
      cwd: path.join(__dirname, '../backend'),
      stdio: 'pipe'
    });
    
    let started = false;
    
    backend.stdout.on('data', (data) => {
      const output = data.toString();
      console.log(output.trim());
      
      if (output.includes('Ready for Sim8 simulation!') && !started) {
        started = true;
        resolve(backend);
      }
    });
    
    backend.stderr.on('data', (data) => {
      console.error('Backend error:', data.toString());
    });
    
    backend.on('error', (error) => {
      console.error('Failed to start backend:', error);
      reject(error);
    });
    
    // Timeout after 30 seconds
    setTimeout(() => {
      if (!started) {
        reject(new Error('Backend startup timeout'));
      }
    }, 30000);
  });
}

async function createUsers(count) {
  console.log(`👥 Creating ${count} users...`);
  
  const users = [];
  for (let i = 0; i < count; i++) {
    const persona = getRandomPersona();
    const user = {
      email: `user${Date.now()}_${i}@example.com`,
      name: `User ${i + 1}`,
      persona
    };
    users.push(user);
  }
  
  // Create users in batches of 20
  const results = [];
  for (let i = 0; i < users.length; i += 20) {
    const batch = users.slice(i, i + 20);
    const result = await makeAPICall('/api/users/batch', { users: batch }, 'POST');
    
    if (result.success) {
      results.push(...result.data.users);
    } else {
      console.error(`Failed to create user batch ${i}-${i + 20}:`, result.error);
    }
    
    // Small delay between batches
    await delay(100);
  }
  
  return results;
}

async function processCheckIns(users, day) {
  console.log(`📅 Processing check-ins for day ${day}...`);
  
  const checkIns = [];
  const activeUsers = users.filter(user => !user.churned);
  
  // Limit concurrent check-ins to 40
  const usersToProcess = activeUsers.slice(0, 40);
  
  for (const user of usersToProcess) {
    // 2-4 check-ins per day
    const checkInCount = Math.floor(Math.random() * 3) + 2;
    
    for (let i = 0; i < checkInCount; i++) {
      const mood = getRandomMood();
      const daypart = getRandomDaypart();
      const microActivity = getRandomMicroActivity();
      const scores = calculateScores(mood, user.persona);
      
      checkIns.push({
        user_id: user.id,
        daypart,
        mood,
        body_score: scores.body,
        mind_score: scores.mind,
        soul_score: scores.soul,
        purpose_score: scores.purpose,
        micro_activity: microActivity
      });
    }
  }
  
  // Process check-ins in batches
  const results = [];
  for (let i = 0; i < checkIns.length; i += 20) {
    const batch = checkIns.slice(i, i + 20);
    const result = await makeAPICall('/api/check-ins/batch', { checkIns: batch }, 'POST');
    
    if (result.success) {
      results.push(...result.data.checkIns);
    } else {
      console.error(`Failed to create check-in batch ${i}-${i + 20}:`, result.error);
    }
    
    // Small delay between batches
    await delay(50);
  }
  
  return results;
}

async function processJournals(users, day) {
  console.log(`📝 Processing journals for day ${day}...`);
  
  const activeUsers = users.filter(user => !user.churned);
  const usersToProcess = activeUsers.slice(0, 20); // Limit to 20 users
  
  const results = [];
  for (const user of usersToProcess) {
    // 30% chance to generate journal
    if (Math.random() < 0.3) {
      const dailyScores = {
        body: Math.floor(Math.random() * 40) + 40,
        mind: Math.floor(Math.random() * 40) + 40,
        soul: Math.floor(Math.random() * 40) + 40,
        purpose: Math.floor(Math.random() * 40) + 40
      };
      
      const result = await makeAPICall('/api/journals/generate', {
        user_id: user.id,
        dailyScores,
        journalTone: 'reflective',
        userNotes: `Day ${day} observations`
      }, 'POST');
      
      if (result.success) {
        results.push(result.data);
      } else {
        console.error(`Failed to generate journal for user ${user.id}:`, result.error);
      }
      
      // Small delay between journal generations
      await delay(200);
    }
  }
  
  return results;
}

async function processInsights(users, day) {
  console.log(`🔍 Processing insights for day ${day}...`);
  
  const activeUsers = users.filter(user => !user.churned);
  const usersToProcess = activeUsers.slice(0, 10); // Limit to 10 users
  
  const results = [];
  for (const user of usersToProcess) {
    // Only generate insights for users with enough data
    if (user.total_check_ins >= 15) {
      const result = await makeAPICall('/api/insights/generate', {
        userId: user.id
      }, 'POST');
      
      if (result.success) {
        results.push(...result.data.insights);
      } else {
        console.error(`Failed to generate insights for user ${user.id}:`, result.error);
      }
      
      // Small delay between insight generations
      await delay(500);
    }
  }
  
  return results;
}

async function processConversions(users, day) {
  console.log(`💎 Processing conversions for day ${day}...`);
  
  const activeUsers = users.filter(user => !user.churned && !user.is_premium);
  const usersToProcess = activeUsers.slice(0, 20); // Limit to 20 users
  
  const results = [];
  for (const user of usersToProcess) {
    const baseRate = conversionRates[user.persona] || 0.01;
    let conversionRate = baseRate;
    
    // Apply insights multiplier if user has insights
    if (user.total_insights > 0) {
      conversionRate *= 2.0; // 2.0x multiplier
    }
    
    // Apply time decay (conversions get harder over time)
    const timeDecay = Math.max(0.5, 1 - (day * 0.02));
    conversionRate *= timeDecay;
    
    if (Math.random() < conversionRate) {
      // Convert to premium
      user.is_premium = true;
      user.premium_since = new Date().toISOString();
      results.push(user);
    }
  }
  
  return results;
}

async function processChurn(users, day) {
  console.log(`👋 Processing churn for day ${day}...`);
  
  const activeUsers = users.filter(user => !user.churned);
  const usersToProcess = activeUsers.slice(0, 30); // Limit to 30 users
  
  const results = [];
  for (const user of usersToProcess) {
    const churnRate = churnRates[user.persona] || 0.1;
    
    if (Math.random() < churnRate) {
      user.churned = true;
      user.churned_at = new Date().toISOString();
      results.push(user);
    }
  }
  
  return results;
}

// ========================================
// MAIN SIMULATION LOOP
// ========================================

async function runSimulation() {
  console.log('🚀 SIM8: OPTIMIZED FOR 40 CONCURRENT USERS');
  console.log(`⚙️ ${TOTAL_USERS} users, ${TOTAL_DAYS} days, ${MINUTES_PER_DAY} min/day`);
  console.log('👥 Demographics: 30% Engaged | 45% Casual | 20% Strugglers | 5% Power-Users');
  console.log('🔧 Optimizations: Connection pooling | Rate limiting | Batch processing | Retry logic');
  
  let backend;
  const users = [];
  const stats = {
    totalCheckIns: 0,
    totalJournals: 0,
    totalInsights: 0,
    totalConversions: 0,
    totalChurn: 0,
    apiCalls: 0,
    apiErrors: 0
  };
  
  try {
    // Start backend
    backend = await startBackend();
    console.log('✅ Backend running');
    
    // Create initial users
    const initialUsers = await createUsers(INITIAL_USERS);
    users.push(...initialUsers);
    stats.apiCalls += Math.ceil(INITIAL_USERS / 20);
    
    // Main simulation loop
    for (let day = 1; day <= TOTAL_DAYS; day++) {
      console.log(`\n📅 DAY ${day}`);
      
      // Add new users
      if (day > 1 && users.length < TOTAL_USERS) {
        const newUsers = await createUsers(Math.min(NEW_USERS_PER_DAY, TOTAL_USERS - users.length));
        users.push(...newUsers);
        stats.apiCalls += Math.ceil(newUsers.length / 20);
      }
      
      // Process daily activities
      const checkIns = await processCheckIns(users, day);
      stats.totalCheckIns += checkIns.length;
      stats.apiCalls += Math.ceil(checkIns.length / 20);
      
      const journals = await processJournals(users, day);
      stats.totalJournals += journals.length;
      stats.apiCalls += journals.length;
      
      const insights = await processInsights(users, day);
      stats.totalInsights += insights.length;
      stats.apiCalls += insights.length;
      
      const conversions = await processConversions(users, day);
      stats.totalConversions += conversions.length;
      
      const churned = await processChurn(users, day);
      stats.totalChurn += churned.length;
      
      // Update user stats
      for (const user of users) {
        if (!user.churned) {
          user.total_check_ins = (user.total_check_ins || 0) + 
            checkIns.filter(ci => ci.user_id === user.id).length;
          user.total_journals = (user.total_journals || 0) + 
            journals.filter(j => j.user_id === user.id).length;
          user.total_insights = (user.total_insights || 0) + 
            insights.filter(i => i.user_id === user.id).length;
        }
      }
      
      // Calculate daily stats
      const activeUsers = users.filter(user => !user.churned);
      const premiumUsers = users.filter(user => user.is_premium);
      const usersWithInsights = users.filter(user => user.total_insights > 0);
      
      console.log(`   Active: ${activeUsers.length} | Check-ins: ${checkIns.length} | Journals: ${journals.length} | Premium: ${premiumUsers.length} | Churned: ${churned.length}`);
      
      // Wait for next day
      if (day < TOTAL_DAYS) {
        await delay(MINUTES_PER_DAY * 60 * 1000);
      }
    }
    
    // Calculate final results
    const finalStats = await calculateFinalStats(users, stats);
    
    // Save results
    const results = {
      simulation: 'Sim8-Optimized',
      config: {
        users: TOTAL_USERS,
        days: TOTAL_DAYS,
        demographics: '30% Engaged | 45% Casual | 20% Strugglers | 5% Power-Users',
        optimizations: 'Connection pooling | Rate limiting | Batch processing | Retry logic',
        concurrentUsers: 40
      },
      ...finalStats
    };
    
    // Ensure output directory exists
    const outputDir = path.join(__dirname, 'output');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    
    const outputFile = path.join(outputDir, 'sim8-optimized-results.json');
    fs.writeFileSync(outputFile, JSON.stringify(results, null, 2));
    
    console.log('\n📊 FINAL RESULTS:');
    console.log(JSON.stringify(results, null, 2));
    console.log(`\n✅ Sim8 complete!`);
    console.log(`💾 Results: ${outputFile}`);
    
  } catch (error) {
    console.error('❌ Simulation failed:', error);
    stats.apiErrors++;
  } finally {
    if (backend) {
      backend.kill();
    }
  }
}

async function calculateFinalStats(users, stats) {
  const activeUsers = users.filter(user => !user.churned);
  const premiumUsers = users.filter(user => user.is_premium);
  const usersWithInsights = users.filter(user => user.total_insights > 0);
  
  const retention = {
    d7: activeUsers.length / Math.min(users.length, 280) * 100, // Assuming 40 users per day
    overall: activeUsers.length / users.length * 100
  };
  
  const conversion = {
    overall: premiumUsers.length / users.length * 100,
    withInsights: usersWithInsights.length > 0 ? 
      premiumUsers.filter(user => user.total_insights > 0).length / usersWithInsights.length * 100 : 0,
    withoutInsights: users.filter(user => user.total_insights === 0).length > 0 ?
      premiumUsers.filter(user => user.total_insights === 0).length / users.filter(user => user.total_insights === 0).length * 100 : 0
  };
  
  if (conversion.withoutInsights > 0) {
    conversion.insightsLift = conversion.withInsights / conversion.withoutInsights;
  } else {
    conversion.insightsLift = 0;
  }
  
  const engagement = {
    avgCheckInsPerUser: (stats.totalCheckIns / users.length).toFixed(1),
    avgJournalsPerUser: (stats.totalJournals / users.length).toFixed(1),
    avgDetailsPerUser: (stats.totalCheckIns * 0.4 / users.length).toFixed(1) // Assuming 40% add details
  };
  
  const revenue = {
    mrr: (premiumUsers.length * 9.99).toFixed(2),
    arpu: (premiumUsers.length * 9.99 / users.length).toFixed(2)
  };
  
  const api = {
    totalCalls: stats.apiCalls,
    errors: stats.apiErrors,
    errorRate: stats.apiCalls > 0 ? (stats.apiErrors / stats.apiCalls * 100).toFixed(2) + '%' : '0%'
  };
  
  return {
    users: {
      total: users.length,
      active: activeUsers.length,
      premium: premiumUsers.length,
      churned: stats.totalChurn,
      withInsights: usersWithInsights.length
    },
    retention,
    conversion,
    engagement,
    revenue,
    api
  };
}

// ========================================
// RUN SIMULATION
// ========================================

if (require.main === module) {
  runSimulation().catch(console.error);
}

module.exports = { runSimulation };
