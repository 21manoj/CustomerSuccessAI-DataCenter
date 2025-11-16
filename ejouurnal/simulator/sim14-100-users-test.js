const axios = require('axios');

// Configuration
const API_BASE = 'http://localhost:3005';
const MAX_USERS = 100;
const SIMULATION_DAYS = 7; // Shorter test period
const RATE_LIMIT_DELAY = 100; // 100ms between requests

// User personas distribution (industry standard)
const PERSONA_DISTRIBUTION = {
  strugglers: 0.35,  // 35% - users who need help
  casual: 0.40,      // 40% - curious users
  engaged: 0.20,     // 20% - active users
  premium: 0.05      // 5% - already premium
};

// Mood distribution
const MOODS = ['very-low', 'low', 'neutral', 'good', 'great'];
const MOOD_WEIGHTS = [0.1, 0.2, 0.3, 0.3, 0.1]; // More positive moods

// Micro activities
const MICRO_ACTIVITIES = [
  'gratitude', 'meditation', 'walk', 'exercise', 'reading', 
  'journaling', 'breathing', 'music', 'none'
];

// Day parts
const DAY_PARTS = ['morning', 'day', 'evening', 'night'];

// API call counter
let apiCallCount = 0;
let apiStats = {
  users: 0,
  checkIns: 0,
  journals: 0,
  insights: 0,
  conversions: 0,
  churns: 0,
  errors: 0
};

// Helper function to make API calls with rate limiting
async function makeApiCall(method, endpoint, data = null) {
  apiCallCount++;
  
  try {
    await new Promise(resolve => setTimeout(resolve, RATE_LIMIT_DELAY));
    
    const config = {
      method,
      url: `${API_BASE}${endpoint}`,
      headers: { 'Content-Type': 'application/json' }
    };
    
    if (data) {
      config.data = data;
    }
    
    const response = await axios(config);
    return response.data;
  } catch (error) {
    apiStats.errors++;
    console.error(`❌ Error: ${error.response?.status} - ${error.message}`);
    return null;
  }
}

// Generate random user data
function generateUserData() {
  const personas = Object.keys(PERSONA_DISTRIBUTION);
  const weights = Object.values(PERSONA_DISTRIBUTION);
  
  const persona = personas[Math.floor(Math.random() * personas.length)];
  const name = generateRandomName();
  const email = `${name.toLowerCase().replace(' ', '.')}.${Math.floor(Math.random() * 1000)}@example.com`;
  
  return {
    name,
    email,
    persona
  };
}

// Generate random name
function generateRandomName() {
  const firstNames = ['Alex', 'Jordan', 'Taylor', 'Casey', 'Morgan', 'Riley', 'Avery', 'Quinn', 'Sage', 'River', 'Phoenix', 'Blake', 'Drew', 'Kai', 'Nova', 'Indigo', 'Ocean', 'Wren', 'Gray', 'Harper', 'Finley', 'Lane', 'Vale', 'Emery', 'Zoe', 'Max', 'Chris', 'Jamie', 'Jordan', 'Blake'];
  return firstNames[Math.floor(Math.random() * firstNames.length)] + ' ' + Math.floor(Math.random() * 300);
}

// Generate check-in data
function generateCheckInData(user, dayPart) {
  const mood = MOODS[Math.floor(Math.random() * MOODS.length)];
  const microActivity = Math.random() < 0.7 ? MICRO_ACTIVITIES[Math.floor(Math.random() * MICRO_ACTIVITIES.length)] : null;
  
  // Generate body/mind/soul scores
  const bodyScore = Math.floor(Math.random() * 5) + 1;
  const mindScore = Math.floor(Math.random() * 5) + 1;
  const soulScore = Math.floor(Math.random() * 5) + 1;
  
  return {
    user_id: user.id,
    daypart: dayPart,
    mood: mood,
    micro_activity: microActivity,
    body_score: bodyScore,
    mind_score: mindScore,
    soul_score: soulScore
  };
}

// Generate details data
function generateDetailsData(user) {
  return {
    userId: user.id,
    sleepHours: 6 + Math.random() * 3, // 6-9 hours
    sleepQuality: Math.floor(Math.random() * 5) + 1,
    breakfast: ['good', 'okay', 'skipped'][Math.floor(Math.random() * 3)],
    lunch: ['good', 'okay', 'skipped'][Math.floor(Math.random() * 3)],
    dinner: ['good', 'okay', 'skipped'][Math.floor(Math.random() * 3)],
    exercise: Math.random() < 0.6 ? 'yes' : 'no',
    exerciseType: ['walk', 'run', 'gym', 'yoga', 'none'][Math.floor(Math.random() * 5)],
    exerciseDuration: Math.floor(Math.random() * 60) + 10
  };
}

// Test conversion optimization features
async function testConversionFeatures(user) {
  try {
    // Test conversion probability calculation
    const conversionResponse = await makeApiCall('POST', '/api/conversion/calculate', {
      userId: user.id,
      currentDay: 1
    });
    
    if (conversionResponse && conversionResponse.success) {
      console.log(`   📊 Conversion Probability: ${(conversionResponse.conversionProbability * 100).toFixed(1)}%`);
    }
    
    // Test conversion offer generation
    const offerResponse = await makeApiCall('POST', '/api/conversion/offer', {
      userId: user.id,
      currentDay: 1
    });
    
    if (offerResponse && offerResponse.success && offerResponse.offer) {
      console.log(`   💰 Conversion Offer: ${offerResponse.offer.title}`);
    }
    
    // Test onboarding flow
    const onboardingResponse = await makeApiCall('POST', '/api/onboarding/flow', {
      userId: user.id
    });
    
    if (onboardingResponse && onboardingResponse.success) {
      console.log(`   🚀 Onboarding Steps: ${onboardingResponse.flow.steps.length}`);
    }
    
    // Test value proposition
    const valuePropResponse = await makeApiCall('POST', '/api/value-proposition', {
      userId: user.id,
      context: { trigger: 'high_engagement' }
    });
    
    if (valuePropResponse && valuePropResponse.success) {
      console.log(`   💡 Value Prop: ${valuePropResponse.valueProposition.substring(0, 50)}...`);
    }
    
  } catch (error) {
    console.error(`   ❌ Conversion features test failed: ${error.message}`);
  }
}

// Main simulation function
async function runSimulation() {
  console.log('🚀 Starting SIM14 - 100 Users Test');
  console.log('=====================================');
  console.log(`📊 Target: ${MAX_USERS} users over ${SIMULATION_DAYS} days`);
  console.log(`⏱️  Rate limit: ${RATE_LIMIT_DELAY}ms between requests`);
  console.log('');
  
  const startTime = Date.now();
  const users = [];
  
  // Phase 1: Create users
  console.log('👥 PHASE 1: Creating Users');
  console.log('-------------------------');
  
  for (let i = 0; i < MAX_USERS; i++) {
    const userData = generateUserData();
    const response = await makeApiCall('POST', '/api/users', userData);
    
    if (response && response.success) {
      const user = {
        id: response.id,
        name: userData.name,
        email: userData.email,
        persona: userData.persona,
        created_at: new Date(),
        checkIns: 0,
        journals: 0,
        insights: 0,
        converted: false,
        churned: false
      };
      
      users.push(user);
      apiStats.users++;
      
      console.log(`✅ User ${user.name} (${user.persona}) created successfully (ID: ${user.id})`);
      
      // Test conversion features for first 10 users
      if (i < 10) {
        console.log(`   🧪 Testing conversion features for ${user.name}...`);
        await testConversionFeatures(user);
      }
    } else {
      console.log(`❌ Failed to create user ${i + 1}`);
    }
  }
  
  console.log(`\n📊 User Creation Complete: ${users.length}/${MAX_USERS} users created`);
  console.log(`⏱️  Time elapsed: ${((Date.now() - startTime) / 1000).toFixed(1)}s`);
  console.log(`🔗 API calls made: ${apiCallCount}`);
  console.log(`❌ Errors: ${apiStats.errors}`);
  
  if (users.length === 0) {
    console.log('❌ No users created. Exiting simulation.');
    return;
  }
  
  // Phase 2: Daily activities
  console.log('\n📅 PHASE 2: Daily Activities');
  console.log('-----------------------------');
  
  for (let day = 1; day <= SIMULATION_DAYS; day++) {
    console.log(`\n📅 Day ${day}`);
    console.log('---');
    
    const activeUsers = users.filter(u => !u.churned);
    console.log(`👥 Active users: ${activeUsers.length}`);
    
    // Check-ins for each active user
    for (const user of activeUsers) {
      const checkInsToday = Math.floor(Math.random() * 3) + 1; // 1-3 check-ins per day
      
      for (let i = 0; i < checkInsToday; i++) {
        const dayPart = DAY_PARTS[Math.floor(Math.random() * DAY_PARTS.length)];
        const checkInData = generateCheckInData(user, dayPart);
        
        const response = await makeApiCall('POST', '/api/check-ins', checkInData);
        
        if (response && response.success) {
          user.checkIns++;
          apiStats.checkIns++;
        }
      }
      
      // Add details (50% chance)
      if (Math.random() < 0.5) {
        const detailsData = generateDetailsData(user);
        const detailsResponse = await makeApiCall('POST', '/api/details', detailsData);
        
        if (detailsResponse && detailsResponse.success) {
          // Details saved successfully
        }
      }
      
      // Generate journal (30% chance)
      if (Math.random() < 0.3 && user.checkIns >= 2) {
        const journalResponse = await makeApiCall('POST', '/api/journals/generate', {
          user_id: user.id,
          journalTone: 'reflective',
          userNotes: 'Feeling good today'
        });
        
        if (journalResponse && journalResponse.success) {
          user.journals++;
          apiStats.journals++;
        }
      }
      
      // Generate insights (20% chance)
      if (Math.random() < 0.2 && user.checkIns >= 5) {
        const insightsResponse = await makeApiCall('POST', '/api/insights/generate', {
          user_id: user.id
        });
        
        if (insightsResponse && insightsResponse.success) {
          user.insights++;
          apiStats.insights++;
        }
      }
      
      // Test conversion features for random users
      if (Math.random() < 0.1) {
        await testConversionFeatures(user);
      }
    }
    
    // Simulate some conversions
    const potentialConverters = activeUsers.filter(u => !u.converted && u.checkIns >= 3);
    for (const user of potentialConverters) {
      if (Math.random() < 0.05) { // 5% conversion chance per day
        user.converted = true;
        apiStats.conversions++;
        console.log(`💰 User ${user.name} (${user.persona}) converted to premium on day ${day}`);
      }
    }
    
    // Simulate some churn
    const potentialChurners = activeUsers.filter(u => !u.converted && u.checkIns < 2);
    for (const user of potentialChurners) {
      if (Math.random() < 0.1) { // 10% churn chance per day
        user.churned = true;
        apiStats.churns++;
        console.log(`💔 User ${user.name} (${user.persona}) churned on day ${day}`);
      }
    }
  }
  
  // Final analytics
  console.log('\n📊 FINAL ANALYTICS');
  console.log('==================');
  
  const totalUsers = users.length;
  const activeUsers = users.filter(u => !u.churned).length;
  const convertedUsers = users.filter(u => u.converted).length;
  const churnedUsers = users.filter(u => u.churned).length;
  
  const conversionRate = totalUsers > 0 ? ((convertedUsers / totalUsers) * 100).toFixed(1) : 0;
  const churnRate = totalUsers > 0 ? ((churnedUsers / totalUsers) * 100).toFixed(1) : 0;
  const activityRate = totalUsers > 0 ? ((activeUsers / totalUsers) * 100).toFixed(1) : 0;
  
  console.log(`👥 Total Users: ${totalUsers}`);
  console.log(`✅ Active Users: ${activeUsers} (${activityRate}%)`);
  console.log(`💰 Converted Users: ${convertedUsers} (${conversionRate}%)`);
  console.log(`💔 Churned Users: ${churnedUsers} (${churnRate}%)`);
  console.log(`📝 Total Check-ins: ${apiStats.checkIns}`);
  console.log(`📖 Total Journals: ${apiStats.journals}`);
  console.log(`💡 Total Insights: ${apiStats.insights}`);
  console.log(`🔗 Total API Calls: ${apiCallCount}`);
  console.log(`❌ Total Errors: ${apiStats.errors}`);
  
  // Test final analytics endpoint
  console.log('\n🔍 Testing Analytics Endpoint');
  console.log('-----------------------------');
  
  try {
    const analyticsResponse = await makeApiCall('GET', '/api/analytics');
    if (analyticsResponse) {
      console.log('✅ Analytics endpoint working');
      console.log(`   📊 Server reports: ${analyticsResponse.totalUsers} users, ${analyticsResponse.totalCheckIns} check-ins`);
    }
  } catch (error) {
    console.log('❌ Analytics endpoint failed');
  }
  
  const endTime = Date.now();
  const totalTime = (endTime - startTime) / 1000;
  
  console.log(`\n⏱️  Total simulation time: ${totalTime.toFixed(1)}s`);
  console.log(`📈 API calls per second: ${(apiCallCount / totalTime).toFixed(1)}`);
  console.log(`✅ SIM14 simulation complete!`);
}

// Run the simulation
runSimulation().catch(console.error);
