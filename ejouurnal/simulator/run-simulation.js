#!/usr/bin/env node
/**
 * SIMPLIFIED 100-USER SIMULATOR (JavaScript)
 * Runs immediately without compilation
 * 
 * Usage: node run-simulation.js
 */

const fs = require('fs');
const path = require('path');

// CONFIG
const TOTAL_USERS = 100;
const MINUTES_PER_DAY = 10; // 10 real minutes = 1 simulated day
const TOTAL_DAYS = 12; // 2 hours = 12 days
const MS_PER_DAY = MINUTES_PER_DAY * 60 * 1000;

// DATA STORES
const users = [];
const checkIns = [];
const details = [];
const analytics = [];

let currentDay = 0;
const startTime = new Date();

// INITIALIZE
function initializeUsers() {
  console.log('🎭 Initializing 100 users...\n');
  
  const personas = [
    ...Array(30).fill('engaged'),
    ...Array(45).fill('casual'),
    ...Array(20).fill('struggler'),
    ...Array(5).fill('power-user'),
  ];
  
  const firstNames = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Avery', 'Quinn', 'Sage', 'Rowan'];
  const lastNames = ['Chen', 'Smith', 'Garcia', 'Johnson', 'Brown', 'Lee', 'Kim', 'Davis', 'Wilson', 'Martinez'];
  
  for (let i = 0; i < TOTAL_USERS; i++) {
    const persona = personas[i];
    const first = firstNames[Math.floor(Math.random() * firstNames.length)];
    const last = lastNames[Math.floor(Math.random() * lastNames.length)];
    
    const user = {
      userId: `user_${String(i + 1).padStart(3, '0')}`,
      name: `${first} ${last}`,
      persona,
      isPremium: Math.random() < 0.15,
      joinedDay: 0,
      
      sleepQuality: getTraitForPersona(persona, 'sleep'),
      stressLevel: getTraitForPersona(persona, 'stress'),
      socialMediaMinutes: getTraitForPersona(persona, 'social'),
      motivationLevel: getTraitForPersona(persona, 'motivation'),
      
      totalCheckIns: 0,
      meaningfulDays: 0,
      currentStreak: 0,
      longestStreak: 0,
      lastActive: 0,
      
      bodyScore: 50 + Math.random() * 20,
      mindScore: 50 + Math.random() * 20,
      soulScore: 50 + Math.random() * 20,
      purposeScore: 50 + Math.random() * 20,
      fulfillmentScore: 50 + Math.random() * 20,
    };
    
    users.push(user);
  }
  
  console.log(`✅ Created ${TOTAL_USERS} users:`);
  console.log(`   📈 Engaged: 30 users`);
  console.log(`   😊 Casual: 45 users`);
  console.log(`   😓 Strugglers: 20 users`);
  console.log(`   ⚡ Power Users: 5 users`);
  console.log(`   💎 Premium: ${users.filter(u => u.isPremium).length} users\n`);
}

function getTraitForPersona(persona, trait) {
  const traits = {
    'engaged': { sleep: [0.7, 0.9], stress: [0.3, 0.5], social: [30, 60], motivation: [0.7, 0.9] },
    'casual': { sleep: [0.5, 0.7], stress: [0.4, 0.7], social: [45, 90], motivation: [0.4, 0.6] },
    'struggler': { sleep: [0.3, 0.5], stress: [0.6, 0.9], social: [60, 120], motivation: [0.2, 0.4] },
    'power-user': { sleep: [0.8, 1.0], stress: [0.2, 0.4], social: [15, 45], motivation: [0.85, 1.0] },
  };
  
  const [min, max] = traits[persona][trait];
  return min + Math.random() * (max - min);
}

function getCheckInProbability(user, day, dayPart) {
  const baseRates = {
    'engaged': 0.85,
    'casual': 0.55,
    'struggler': 0.30,
    'power-user': 0.95,
  };
  
  let probability = baseRates[user.persona];
  
  // Decay over time
  const decayFactor = Math.exp(-0.05 * day);
  probability *= (0.7 + 0.3 * decayFactor);
  
  // Daypart adjustments
  if (dayPart === 'morning') probability *= 1.2;
  else if (dayPart === 'night') probability *= 0.85;
  
  // Streak bonus
  if (user.currentStreak >= 3) probability *= 1.15;
  
  // Premium boost
  if (user.isPremium) probability *= 1.25;
  
  return Math.min(probability, 0.98);
}

function performCheckIn(user, day, dayPart) {
  const mood = Math.floor(1 + Math.random() * 5);
  const arousal = Math.random() < 0.33 ? 'low' : Math.random() < 0.5 ? 'medium' : 'high';
  
  const checkIn = {
    userId: user.userId,
    day,
    timestamp: new Date(),
    dayPart,
    mood,
    arousal,
    microAct: Math.random() < 0.6 ? ['Gratitude', 'Meditation', 'Walk'][Math.floor(Math.random() * 3)] : null,
    durationSeconds: 8 + Math.random() * 20,
  };
  
  checkIns.push(checkIn);
  user.totalCheckIns++;
  user.lastActive = day;
  
  // Log details
  if ((user.isPremium || Math.random() < 0.3) && dayPart === 'morning') {
    details.push({
      userId: user.userId,
      day,
      sleepHours: 5 + user.sleepQuality * 3.5,
      sleepQuality: user.sleepQuality,
      steps: Math.floor(3000 + Math.random() * 12000),
      screenTimeMinutes: Math.floor(user.socialMediaMinutes * (0.7 + Math.random() * 0.6)),
    });
  }
  
  analytics.push({
    userId: user.userId,
    eventType: 'check_in_complete',
    day,
    timestamp: new Date(),
    metadata: { dayPart, mood },
  });
}

function updateDailyStats(day) {
  for (const user of users) {
    const todayCheckIns = checkIns.filter(c => c.userId === user.userId && c.day === day);
    
    if (todayCheckIns.length > 0) {
      const avgMood = todayCheckIns.reduce((sum, c) => sum + c.mood, 0) / todayCheckIns.length;
      
      user.mindScore += (avgMood - 3) * 2 + (Math.random() - 0.5) * 5;
      user.soulScore += todayCheckIns.filter(c => c.microAct).length * 3;
      user.purposeScore += todayCheckIns.length * 2;
      
      const todayDetails = details.find(d => d.userId === user.userId && d.day === day);
      if (todayDetails) {
        user.bodyScore += (todayDetails.sleepHours - 6.5) * 3 + (Math.random() - 0.5) * 5;
      }
      
      // Clamp scores
      user.bodyScore = Math.max(0, Math.min(100, user.bodyScore));
      user.mindScore = Math.max(0, Math.min(100, user.mindScore));
      user.soulScore = Math.max(0, Math.min(100, user.soulScore));
      user.purposeScore = Math.max(0, Math.min(100, user.purposeScore));
      
      user.fulfillmentScore = (user.bodyScore + user.mindScore + user.soulScore + user.purposeScore) / 4;
      
      // Check meaningful day
      if (user.bodyScore >= 70 && user.mindScore >= 65 && user.soulScore >= 80 && user.purposeScore >= 55) {
        user.meaningfulDays++;
        user.currentStreak++;
        user.longestStreak = Math.max(user.longestStreak, user.currentStreak);
        
        analytics.push({
          userId: user.userId,
          eventType: 'meaningful_day',
          day,
          timestamp: new Date(),
          metadata: { streak: user.currentStreak },
        });
      }
    } else {
      user.currentStreak = 0;
    }
  }
}

function processPremiumConversions(day) {
  for (const user of users) {
    if (!user.isPremium) {
      const hasThreeMDW = user.meaningfulDays >= 3;
      const isDay7Plus = day >= 6;
      const highEngagement = user.totalCheckIns >= day * 3;
      
      if (hasThreeMDW || (isDay7Plus && highEngagement)) {
        const conversionRate = user.persona === 'power-user' ? 0.4
          : user.persona === 'engaged' ? 0.25
          : user.persona === 'casual' ? 0.08
          : 0.02;
        
        if (Math.random() < conversionRate) {
          user.isPremium = true;
          analytics.push({
            userId: user.userId,
            eventType: 'premium_conversion',
            day,
            timestamp: new Date(),
            metadata: { trigger: hasThreeMDW ? 'mdw' : 'engagement' },
          });
        }
      }
    }
  }
}

async function simulateDay(day) {
  currentDay = day;
  console.log(`📅 DAY ${day + 1} - ${new Date().toLocaleTimeString()}`);
  console.log('─'.repeat(60));
  
  // Simulate check-ins for all dayparts
  const dayParts = ['morning', 'day', 'evening', 'night'];
  
  for (const user of users) {
    for (const dayPart of dayParts) {
      const probability = getCheckInProbability(user, day, dayPart);
      if (Math.random() < probability) {
        performCheckIn(user, day, dayPart);
      }
    }
  }
  
  updateDailyStats(day);
  processPremiumConversions(day);
  
  // Print summary
  const todayCheckIns = checkIns.filter(c => c.day === day);
  const activeUsers = new Set(todayCheckIns.map(c => c.userId)).size;
  const meaningfulDaysToday = analytics.filter(e => e.eventType === 'meaningful_day' && e.day === day).length;
  const conversionsToday = analytics.filter(e => e.eventType === 'premium_conversion' && e.day === day).length;
  
  console.log(`   Active Users: ${activeUsers}/${TOTAL_USERS}`);
  console.log(`   Check-ins: ${todayCheckIns.length}`);
  console.log(`   Meaningful Days: ${meaningfulDaysToday}`);
  if (conversionsToday > 0) {
    console.log(`   💰 Premium Conversions: ${conversionsToday}`);
  }
  console.log('');
}

async function runSimulation() {
  console.clear();
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║          FULFILLMENT APP - 100 USER SIMULATOR              ║');
  console.log('╚════════════════════════════════════════════════════════════╝\n');
  
  initializeUsers();
  
  console.log('\n🚀 STARTING 2-HOUR SIMULATION (12 simulated days)\n');
  console.log(`⏰ Time scale: ${MINUTES_PER_DAY} minutes real = 1 day simulated`);
  console.log(`📅 Total: ${TOTAL_DAYS} days\n`);
  console.log('─'.repeat(60) + '\n');
  
  for (let day = 0; day < TOTAL_DAYS; day++) {
    await simulateDay(day);
    
    if (day < TOTAL_DAYS - 1) {
      await new Promise(resolve => setTimeout(resolve, MS_PER_DAY));
    }
  }
  
  console.log('\n✅ SIMULATION COMPLETE!\n');
  generateReport();
}

function generateReport() {
  const totalCheckIns = checkIns.length;
  const activeUsers = new Set(checkIns.map(c => c.userId)).size;
  const premiumUsers = users.filter(u => u.isPremium).length;
  const avgMDW = users.reduce((sum, u) => sum + u.meaningfulDays, 0) / TOTAL_USERS;
  const avgFulfillment = users.reduce((sum, u) => sum + u.fulfillmentScore, 0) / TOTAL_USERS;
  const conversions = analytics.filter(e => e.eventType === 'premium_conversion');
  
  const report = {
    overview: {
      totalUsers: TOTAL_USERS,
      activeUsers,
      premiumUsers,
      conversionRate: (premiumUsers / TOTAL_USERS * 100).toFixed(1) + '%',
      totalCheckIns,
      avgMDW: avgMDW.toFixed(2),
      avgFulfillment: avgFulfillment.toFixed(1),
    },
    revenue: {
      mrr: '$' + (premiumUsers * 7.99).toFixed(2),
      arr: '$' + (premiumUsers * 7.99 * 12).toFixed(2),
    },
  };
  
  console.log('═'.repeat(60));
  console.log('📊 FINAL ANALYTICS REPORT');
  console.log('═'.repeat(60) + '\n');
  
  console.log('👥 USER METRICS:');
  console.log(`   Total Users: ${report.overview.totalUsers}`);
  console.log(`   Active Users: ${report.overview.activeUsers}`);
  console.log(`   Premium Users: ${report.overview.premiumUsers} (${report.overview.conversionRate})`);
  console.log('');
  
  console.log('✅ ENGAGEMENT:');
  console.log(`   Total Check-ins: ${totalCheckIns.toLocaleString()}`);
  console.log(`   Avg MDW: ${report.overview.avgMDW}`);
  console.log(`   Avg Fulfillment Score: ${report.overview.avgFulfillment}/100`);
  console.log('');
  
  console.log('💰 REVENUE:');
  console.log(`   MRR: ${report.revenue.mrr}`);
  console.log(`   ARR: ${report.revenue.arr}`);
  console.log('');
  
  // Save data
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const outputDir = path.join(__dirname, 'output');
  
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  fs.writeFileSync(
    path.join(outputDir, `simulation-${timestamp}.json`),
    JSON.stringify({ users, checkIns, details, analytics, report }, null, 2)
  );
  
  console.log(`💾 Data saved to: output/simulation-${timestamp}.json\n`);
}

runSimulation().catch(console.error);

