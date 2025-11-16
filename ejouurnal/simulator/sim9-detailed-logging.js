/**
 * SIM9: DETAILED LOGGING SIMULATION
 * 10 users with comprehensive API logging and user progress tracking
 */

const axios = require('axios');

// Configuration
const BASE_URL = 'http://localhost:3005';
const TOTAL_USERS = 10;
const SIMULATION_DAYS = 3;

// User personas for realistic behavior
const personas = [
  { name: 'Engaged', checkInRate: 0.85, detailsRate: 0.70, engagement: 'high' },
  { name: 'Casual', checkInRate: 0.60, detailsRate: 0.40, engagement: 'medium' },
  { name: 'Struggler', checkInRate: 0.35, detailsRate: 0.20, engagement: 'low' }
];

// API call counter and logger
let apiCallCount = 0;
const apiStats = {
  users: 0,
  checkIns: 0,
  details: 0,
  journals: 0,
  insights: 0,
  errors: 0
};

// Enhanced API call function with detailed logging
async function apiCall(endpoint, method = 'GET', body = null, userContext = null) {
  apiCallCount++;
  const timestamp = new Date().toISOString().substr(11, 8);
  
  try {
    console.log(`\n🔗 [${timestamp}] API Call #${apiCallCount}`);
    console.log(`   📡 ${method} ${endpoint}`);
    if (userContext) {
      console.log(`   👤 User: ${userContext.userId} (${userContext.persona})`);
    }
    if (body) {
      console.log(`   📦 Body: ${JSON.stringify(body).substring(0, 100)}${JSON.stringify(body).length > 100 ? '...' : ''}`);
    }

    const response = await axios({
      method,
      url: `${BASE_URL}${endpoint}`,
      data: body,
      timeout: 10000,
      headers: { 'Content-Type': 'application/json' }
    });

    console.log(`   ✅ Success: ${response.status} ${response.statusText}`);
    if (response.data && typeof response.data === 'object') {
      console.log(`   📊 Response: ${JSON.stringify(response.data).substring(0, 150)}${JSON.stringify(response.data).length > 150 ? '...' : ''}`);
    }

    return response.data;
  } catch (error) {
    apiStats.errors++;
    console.log(`   ❌ Error: ${error.response?.status || 'Network'} - ${error.message}`);
    if (error.response?.data) {
      console.log(`   📄 Error Details: ${JSON.stringify(error.response.data)}`);
    }
    return null;
  }
}

// Create realistic user profiles
function createUserProfile(userId, persona) {
  const baseScores = {
    body: 60 + Math.random() * 30,
    mind: 55 + Math.random() * 35,
    soul: 50 + Math.random() * 40,
    purpose: 45 + Math.random() * 45
  };

  return {
    userId,
    name: `User_${userId.split('_')[1].substring(0, 8)}`,
    email: `user${userId.split('_')[1].substring(0, 8)}@example.com`,
    persona: persona.name,
    engagement: persona.engagement,
    checkInRate: persona.checkInRate,
    detailsRate: persona.detailsRate,
    scores: baseScores,
    checkInCount: 0,
    detailsCount: 0,
    journalCount: 0,
    lastActiveDay: 0,
    intentionText: generateIntention(),
    microMoves: generateMicroMoves()
  };
}

// Generate realistic weekly intentions
function generateIntention() {
  const intentions = [
    "Focus on better sleep habits",
    "Practice daily gratitude",
    "Increase physical activity",
    "Reduce screen time",
    "Connect more with friends",
    "Learn something new each day",
    "Practice mindfulness",
    "Improve work-life balance"
  ];
  return intentions[Math.floor(Math.random() * intentions.length)];
}

// Generate micro-moves for intentions
function generateMicroMoves() {
  const moves = [
    "Take 3 deep breaths when stressed",
    "Write down one thing you're grateful for",
    "Take a 5-minute walk outside",
    "Put phone away during meals",
    "Send a text to a friend",
    "Read for 10 minutes",
    "Do 5 minutes of meditation",
    "Set one small goal for tomorrow"
  ];
  return moves.slice(0, 3).sort(() => Math.random() - 0.5);
}

// Generate realistic check-in data
function generateCheckInData(user, dayPart) {
  const moods = ['very-low', 'low', 'neutral', 'good', 'great'];
  const contexts = [['work'], ['social'], ['family'], ['work', 'stress'], ['social', 'fun']];
  const microActs = ['meditation', 'gratitude', 'walk', 'reading', 'exercise', 'breathing', 'journaling', 'music'];
  
  // Adjust mood based on user's current scores
  const avgScore = (user.scores.body + user.scores.mind + user.scores.soul + user.scores.purpose) / 4;
  let moodWeights;
  if (avgScore >= 75) moodWeights = [0.05, 0.1, 0.2, 0.35, 0.3];
  else if (avgScore >= 60) moodWeights = [0.1, 0.15, 0.3, 0.3, 0.15];
  else if (avgScore >= 45) moodWeights = [0.2, 0.25, 0.3, 0.2, 0.05];
  else moodWeights = [0.3, 0.3, 0.25, 0.1, 0.05];
  
  const mood = weightedRandom(moods, moodWeights);
  const context = contexts[Math.floor(Math.random() * contexts.length)];
  const microAct = Math.random() < 0.6 ? microActs[Math.floor(Math.random() * microActs.length)] : null;
  
  return {
    user_id: user.userId,
    daypart: dayPart,
    mood,
    micro_activity: microAct,
    body_score: Math.max(20, Math.min(100, user.scores.body + (Math.random() * 20 - 10))),
    mind_score: Math.max(20, Math.min(100, user.scores.mind + (Math.random() * 20 - 10))),
    soul_score: Math.max(20, Math.min(100, user.scores.soul + (Math.random() * 20 - 10))),
    purpose_score: Math.max(20, Math.min(100, user.scores.purpose + (Math.random() * 20 - 10)))
  };
}

// Generate realistic details data
function generateDetailsData(user) {
  const sleepHours = 6 + Math.random() * 4; // 6-10 hours
  const sleepQuality = 2 + Math.random() * 3; // 2-5 stars
  const exerciseTypes = ['walk', 'run', 'gym', 'yoga', 'cycling', 'swimming'];
  const exerciseType = exerciseTypes[Math.floor(Math.random() * exerciseTypes.length)];
  const exerciseDuration = 15 + Math.random() * 75; // 15-90 minutes
  
  return {
    userId: user.userId,
    sleepHours: Math.round(sleepHours * 10) / 10,
    sleepQuality: Math.round(sleepQuality),
    breakfast: ['good', 'ok', 'poor'][Math.floor(Math.random() * 3)],
    breakfastNotes: ['Oatmeal with berries', 'Eggs and toast', 'Smoothie', 'Cereal'][Math.floor(Math.random() * 4)],
    lunch: ['good', 'ok', 'poor'][Math.floor(Math.random() * 3)],
    lunchNotes: ['Salad with chicken', 'Sandwich', 'Soup', 'Leftovers'][Math.floor(Math.random() * 4)],
    dinner: ['good', 'ok', 'poor'][Math.floor(Math.random() * 3)],
    dinnerNotes: ['Home-cooked pasta', 'Grilled fish', 'Stir-fry', 'Pizza'][Math.floor(Math.random() * 4)],
    exerciseType,
    exerciseDuration: Math.round(exerciseDuration),
    exerciseIntensity: ['light', 'moderate', 'vigorous'][Math.floor(Math.random() * 3)],
    exerciseFeeling: ['energized', 'good', 'tired'][Math.floor(Math.random() * 3)],
    socialQuality: ['energized', 'neutral', 'drained'][Math.floor(Math.random() * 3)],
    socialWho: ['friend', 'family', 'colleague'][Math.floor(Math.random() * 3)],
    socialDuration: 15 + Math.random() * 120, // 15-135 minutes
    screenMinutes: 60 + Math.random() * 300 // 1-6 hours
  };
}

// Weighted random selection
function weightedRandom(items, weights) {
  const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
  let random = Math.random() * totalWeight;
  
  for (let i = 0; i < items.length; i++) {
    random -= weights[i];
    if (random <= 0) return items[i];
  }
  return items[items.length - 1];
}

// Sleep function for realistic timing
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Main simulation function
async function runSimulation() {
  console.log('\n🚀 SIM9: DETAILED LOGGING SIMULATION STARTING');
  console.log('=' * 60);
  console.log(`👥 Users: ${TOTAL_USERS}`);
  console.log(`📅 Days: ${SIMULATION_DAYS}`);
  console.log(`🌐 Backend: ${BASE_URL}`);
  console.log('=' * 60);

  // Create users
  const users = [];
  for (let i = 0; i < TOTAL_USERS; i++) {
    const persona = personas[i % personas.length];
    const userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`;
    const user = createUserProfile(userId, persona);
    users.push(user);
    
    console.log(`\n👤 Created User: ${user.name} (${user.persona})`);
    console.log(`   📧 Email: ${user.email}`);
    console.log(`   🎯 Intention: ${user.intentionText}`);
    console.log(`   📊 Initial Scores: Body:${user.scores.body.toFixed(1)} Mind:${user.scores.mind.toFixed(1)} Soul:${user.scores.soul.toFixed(1)} Purpose:${user.scores.purpose.toFixed(1)}`);
  }

  // Create users in backend
  console.log('\n📝 CREATING USERS IN BACKEND...');
  for (const user of users) {
    const result = await apiCall('/api/users', 'POST', {
      email: user.email,
      name: user.name,
      persona: user.persona
    }, { userId: user.userId, persona: user.persona });
    
    if (result && result.id) {
      // Update user with actual backend ID
      user.userId = result.id;
      apiStats.users++;
      console.log(`   ✅ User ${user.name} created successfully (ID: ${result.id})`);
    } else {
      console.log(`   ❌ Failed to create user ${user.name}`);
    }
    await sleep(100); // Rate limiting
  }

  // Run simulation for each day
  for (let day = 1; day <= SIMULATION_DAYS; day++) {
    console.log(`\n📅 DAY ${day} SIMULATION`);
    console.log('-' * 40);
    
    const dayParts = ['morning', 'day', 'evening', 'night'];
    
    for (const user of users) {
      console.log(`\n👤 ${user.name} (${user.persona}) - Day ${day}`);
      
      // Check-in simulation
      for (const dayPart of dayParts) {
        if (Math.random() < user.checkInRate) {
          const checkInData = generateCheckInData(user, dayPart);
          
          const result = await apiCall('/api/check-ins', 'POST', checkInData, {
            userId: user.userId,
            persona: user.persona,
            action: `check-in-${dayPart}`
          });
          
          if (result) {
            user.checkInCount++;
            apiStats.checkIns++;
            console.log(`   ✅ ${dayPart} check-in completed`);
            
            // Update user scores based on check-in
            user.scores.body = Math.max(20, Math.min(100, user.scores.body + (Math.random() * 4 - 2)));
            user.scores.mind = Math.max(20, Math.min(100, user.scores.mind + (Math.random() * 4 - 2)));
            user.scores.soul = Math.max(20, Math.min(100, user.scores.soul + (Math.random() * 4 - 2)));
            user.scores.purpose = Math.max(20, Math.min(100, user.scores.purpose + (Math.random() * 4 - 2)));
          } else {
            console.log(`   ❌ ${dayPart} check-in failed`);
          }
          
          await sleep(200); // Rate limiting
        } else {
          console.log(`   ⏭️  ${dayPart} check-in skipped`);
        }
      }
      
      // Details simulation (once per day)
      if (Math.random() < user.detailsRate) {
        const detailsData = generateDetailsData(user);
        
        const result = await apiCall('/api/details', 'POST', detailsData, {
          userId: user.userId,
          persona: user.persona,
          action: 'details'
        });
        
        if (result) {
          user.detailsCount++;
          apiStats.details++;
          console.log(`   ✅ Details logged: Sleep:${detailsData.sleepHours}h Exercise:${detailsData.exerciseType} Food:${detailsData.breakfast}`);
        } else {
          console.log(`   ❌ Details logging failed`);
        }
        
        await sleep(200); // Rate limiting
      }
      
      // Journal generation (if enough check-ins)
      if (user.checkInCount >= 4 && Math.random() < 0.7) {
        const result = await apiCall('/api/journals/generate', 'POST', {
          user_id: user.userId,
          journalTone: 'reflective',
          userNotes: `Day ${day} - Feeling ${user.scores.body > 70 ? 'energized' : user.scores.body > 50 ? 'balanced' : 'tired'}`
        }, {
          userId: user.userId,
          persona: user.persona,
          action: 'journal'
        });
        
        if (result) {
          user.journalCount++;
          apiStats.journals++;
          console.log(`   ✅ Journal generated (${result.content?.length || 0} chars)`);
        } else {
          console.log(`   ❌ Journal generation failed`);
        }
        
        await sleep(500); // Rate limiting for AI calls
      }
      
      // Insights generation (if enough data)
      if (user.checkInCount >= 15 && Math.random() < 0.3) {
        const result = await apiCall('/api/insights/generate', 'POST', {
          userId: user.userId
        }, {
          userId: user.userId,
          persona: user.persona,
          action: 'insights'
        });
        
        if (result) {
          apiStats.insights++;
          console.log(`   ✅ Insights generated: ${result.generated || 0} insights`);
        } else {
          console.log(`   ❌ Insights generation failed`);
        }
        
        await sleep(500); // Rate limiting for AI calls
      }
      
      user.lastActiveDay = day;
    }
    
    // Daily summary
    console.log(`\n📊 DAY ${day} SUMMARY`);
    const activeUsers = users.filter(u => u.lastActiveDay === day).length;
    const totalCheckIns = users.reduce((sum, u) => sum + u.checkInCount, 0);
    const totalDetails = users.reduce((sum, u) => sum + u.detailsCount, 0);
    const totalJournals = users.reduce((sum, u) => sum + u.journalCount, 0);
    
    console.log(`   👥 Active Users: ${activeUsers}/${TOTAL_USERS}`);
    console.log(`   📝 Total Check-ins: ${totalCheckIns}`);
    console.log(`   📊 Total Details: ${totalDetails}`);
    console.log(`   📖 Total Journals: ${totalJournals}`);
    console.log(`   🔗 Total API Calls: ${apiCallCount}`);
  }
  
  // Final simulation summary
  console.log('\n🎉 SIMULATION COMPLETE!');
  console.log('=' * 60);
  console.log('📊 FINAL STATISTICS');
  console.log('=' * 60);
  
  console.log(`\n👥 USER BREAKDOWN:`);
  users.forEach((user, index) => {
    const avgScore = (user.scores.body + user.scores.mind + user.scores.soul + user.scores.purpose) / 4;
    console.log(`   ${index + 1}. ${user.name} (${user.persona})`);
    console.log(`      📝 Check-ins: ${user.checkInCount}`);
    console.log(`      📊 Details: ${user.detailsCount}`);
    console.log(`      📖 Journals: ${user.journalCount}`);
    console.log(`      📈 Avg Score: ${avgScore.toFixed(1)}/100`);
    console.log(`      🎯 Intention: ${user.intentionText}`);
  });
  
  console.log(`\n🔗 API STATISTICS:`);
  console.log(`   📡 Total API Calls: ${apiCallCount}`);
  console.log(`   ✅ Successful: ${apiCallCount - apiStats.errors}`);
  console.log(`   ❌ Errors: ${apiStats.errors}`);
  console.log(`   👥 Users Created: ${apiStats.users}`);
  console.log(`   📝 Check-ins: ${apiStats.checkIns}`);
  console.log(`   📊 Details: ${apiStats.details}`);
  console.log(`   📖 Journals: ${apiStats.journals}`);
  console.log(`   💡 Insights: ${apiStats.insights}`);
  
  console.log(`\n📈 ENGAGEMENT METRICS:`);
  const avgCheckIns = users.reduce((sum, u) => sum + u.checkInCount, 0) / users.length;
  const avgDetails = users.reduce((sum, u) => sum + u.detailsCount, 0) / users.length;
  const avgJournals = users.reduce((sum, u) => sum + u.journalCount, 0) / users.length;
  const avgScore = users.reduce((sum, u) => sum + (u.scores.body + u.scores.mind + u.scores.soul + u.scores.purpose) / 4, 0) / users.length;
  
  console.log(`   📝 Avg Check-ins per User: ${avgCheckIns.toFixed(1)}`);
  console.log(`   📊 Avg Details per User: ${avgDetails.toFixed(1)}`);
  console.log(`   📖 Avg Journals per User: ${avgJournals.toFixed(1)}`);
  console.log(`   📈 Avg Fulfillment Score: ${avgScore.toFixed(1)}/100`);
  
  console.log(`\n🎯 PERSONA PERFORMANCE:`);
  personas.forEach(persona => {
    const personaUsers = users.filter(u => u.persona === persona.name);
    if (personaUsers.length > 0) {
      const personaAvgCheckIns = personaUsers.reduce((sum, u) => sum + u.checkInCount, 0) / personaUsers.length;
      const personaAvgDetails = personaUsers.reduce((sum, u) => sum + u.detailsCount, 0) / personaUsers.length;
      const personaAvgScore = personaUsers.reduce((sum, u) => sum + (u.scores.body + u.scores.mind + u.scores.soul + u.scores.purpose) / 4, 0) / personaUsers.length;
      
      console.log(`   ${persona.name}: ${personaUsers.length} users`);
      console.log(`      📝 Avg Check-ins: ${personaAvgCheckIns.toFixed(1)}`);
      console.log(`      📊 Avg Details: ${personaAvgDetails.toFixed(1)}`);
      console.log(`      📈 Avg Score: ${personaAvgScore.toFixed(1)}/100`);
    }
  });
  
  console.log('\n🏆 SIMULATION COMPLETE!');
  console.log('All users have been processed with detailed API logging.');
}

// Run the simulation
if (require.main === module) {
  runSimulation().catch(console.error);
}

module.exports = { runSimulation };
