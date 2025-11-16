#!/usr/bin/env node
/**
 * SIM2 - ADVANCED 1000-USER SIMULATION
 * 
 * Features:
 * - 1000 users total (500 start, 500 join over 24 days)
 * - 24 simulated days (4 hours real time, 10 min = 1 day)
 * - 20% churn rate (random across 24 days)
 * - Realistic user acquisition curve
 * - Advanced retention modeling
 */

const fs = require('fs');
const path = require('path');

// CONFIG
const TOTAL_USERS = 1000;
const INITIAL_USERS = 500;
const NEW_USERS = 500;
const MINUTES_PER_DAY = 10;
const TOTAL_DAYS = 24;
const CHURN_RATE = 0.20; // 20% total churn
const MS_PER_DAY = MINUTES_PER_DAY * 60 * 1000;

// DATA STORES
const users = [];
const checkIns = [];
const details = [];
const analytics = [];
let currentDay = 0;
const startTime = new Date();

// User acquisition curve (how many new users join each day)
function getUserAcquisitionCurve() {
  // More users join early (viral growth), then slows down
  const curve = [];
  let remaining = NEW_USERS;
  
  for (let day = 0; day < TOTAL_DAYS; day++) {
    if (remaining <= 0) {
      curve.push(0);
      continue;
    }
    
    // Exponential decay curve
    const dayFactor = Math.exp(-0.15 * day);
    const newUsersToday = Math.floor(remaining * 0.15 * dayFactor);
    const actual = Math.min(newUsersToday, remaining);
    
    curve.push(Math.max(actual, day < 20 ? 1 : 0)); // At least 1/day for first 20 days
    remaining -= actual;
  }
  
  // Distribute any remaining
  if (remaining > 0) {
    for (let i = 0; i < remaining && i < curve.length; i++) {
      curve[i]++;
    }
  }
  
  return curve;
}

// Initialize starting users
function initializeUsers() {
  console.log('🎭 Initializing users...\n');
  
  const personas = [
    ...Array(300).fill('engaged'),      // 30%
    ...Array(450).fill('casual'),       // 45%
    ...Array(200).fill('struggler'),    // 20%
    ...Array(50).fill('power-user'),    // 5%
  ];
  
  // Shuffle personas
  for (let i = personas.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [personas[i], personas[j]] = [personas[j], personas[i]];
  }
  
  // Create initial 500 users
  for (let i = 0; i < INITIAL_USERS; i++) {
    users.push(createUser(i, 0, personas[i]));
  }
  
  console.log(`✅ Created ${INITIAL_USERS} initial users`);
  console.log(`📅 ${NEW_USERS} more users will join over 24 days\n`);
}

function createUser(index, joinDay, persona) {
  const firstNames = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Avery', 'Quinn', 'Sage', 'Rowan'];
  const lastNames = ['Chen', 'Smith', 'Garcia', 'Johnson', 'Brown', 'Lee', 'Kim', 'Davis', 'Wilson', 'Martinez'];
  
  const first = firstNames[Math.floor(Math.random() * firstNames.length)];
  const last = lastNames[Math.floor(Math.random() * lastNames.length)];
  
  return {
    userId: `user_${String(index + 1).padStart(4, '0')}`,
    name: `${first} ${last}`,
    persona,
    isPremium: Math.random() < 0.10, // 10% start premium
    joinedDay: joinDay,
    churned: false,
    churnedDay: null,
    
    sleepQuality: getTraitForPersona(persona, 'sleep'),
    stressLevel: getTraitForPersona(persona, 'stress'),
    socialMediaMinutes: getTraitForPersona(persona, 'social'),
    motivationLevel: getTraitForPersona(persona, 'motivation'),
    
    totalCheckIns: 0,
    meaningfulDays: 0,
    currentStreak: 0,
    longestStreak: 0,
    lastActive: joinDay,
    
    bodyScore: 50 + Math.random() * 20,
    mindScore: 50 + Math.random() * 20,
    soulScore: 50 + Math.random() * 20,
    purposeScore: 50 + Math.random() * 20,
    fulfillmentScore: 50 + Math.random() * 20,
  };
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

function processChurn(day) {
  // Calculate how many should churn by this day
  const targetChurnByDay = Math.floor(TOTAL_USERS * CHURN_RATE * (day / TOTAL_DAYS));
  const currentlyChurned = users.filter(u => u.churned).length;
  const shouldChurn = targetChurnByDay - currentlyChurned;
  
  if (shouldChurn <= 0) return;
  
  // Select users to churn (prioritize strugglers and low-engagement users)
  const activeUsers = users.filter(u => !u.churned && u.joinedDay < day);
  
  // Sort by churn likelihood (low engagement, high stress, strugglers)
  activeUsers.sort((a, b) => {
    const scoreA = a.totalCheckIns / (day - a.joinedDay + 1) * a.motivationLevel;
    const scoreB = b.totalCheckIns / (day - b.joinedDay + 1) * b.motivationLevel;
    return scoreA - scoreB; // Lower score = more likely to churn
  });
  
  // Churn the lowest-engagement users
  for (let i = 0; i < Math.min(shouldChurn, activeUsers.length); i++) {
    activeUsers[i].churned = true;
    activeUsers[i].churnedDay = day;
    
    analytics.push({
      userId: activeUsers[i].userId,
      eventType: 'user_churned',
      day,
      timestamp: new Date(),
      metadata: {
        totalCheckIns: activeUsers[i].totalCheckIns,
        daysActive: day - activeUsers[i].joinedDay,
        persona: activeUsers[i].persona,
      },
    });
  }
}

function getCheckInProbability(user, day, dayPart) {
  // User hasn't joined yet or has churned
  if (user.joinedDay > day || user.churned) return 0;
  
  const baseRates = {
    'engaged': 0.85,
    'casual': 0.55,
    'struggler': 0.30,
    'power-user': 0.95,
  };
  
  let probability = baseRates[user.persona];
  
  // Decay over time (since user joined)
  const daysActive = day - user.joinedDay;
  const decayFactor = Math.exp(-0.03 * daysActive);
  probability *= (0.65 + 0.35 * decayFactor);
  
  // Daypart adjustments
  if (dayPart === 'morning') probability *= 1.2;
  else if (dayPart === 'night') probability *= 0.85;
  
  // Streak bonus
  if (user.currentStreak >= 3) probability *= 1.15;
  
  // Premium boost
  if (user.isPremium) probability *= 1.25;
  
  // New user boost (first week excitement)
  if (daysActive < 7) probability *= 1.1;
  
  return Math.min(probability, 0.98);
}

function performCheckIn(user, day, dayPart) {
  const mood = Math.floor(1 + Math.random() * 5);
  const arousal = Math.random() < 0.33 ? 'low' : Math.random() < 0.5 ? 'medium' : 'high';
  
  checkIns.push({
    userId: user.userId,
    day,
    dayPart,
    mood,
    arousal,
    microAct: Math.random() < 0.6 ? ['Gratitude', 'Meditation', 'Walk'][Math.floor(Math.random() * 3)] : null,
    durationSeconds: 8 + Math.random() * 20,
  });
  
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
  for (const user of users.filter(u => u.joinedDay <= day && !u.churned)) {
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
  for (const user of users.filter(u => !u.isPremium && !u.churned && u.joinedDay < day)) {
    const hasThreeMDW = user.meaningfulDays >= 3;
    const isDay7Plus = (day - user.joinedDay) >= 6;
    const highEngagement = user.totalCheckIns >= (day - user.joinedDay) * 3;
    
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
          metadata: { 
            trigger: hasThreeMDW ? 'mdw' : 'engagement',
            daysToConvert: day - user.joinedDay,
          },
        });
      }
    }
  }
}

async function simulateDay(day) {
  currentDay = day;
  console.log(`📅 DAY ${day + 1} - ${new Date().toLocaleTimeString()}`);
  
  // Add new users (based on acquisition curve)
  const acquisitionCurve = getUserAcquisitionCurve();
  const newUsersToday = acquisitionCurve[day] || 0;
  
  if (newUsersToday > 0) {
    const startIndex = users.length;
    const personas = ['engaged', 'casual', 'struggler', 'power-user'];
    const personaWeights = [0.3, 0.45, 0.2, 0.05];
    
    for (let i = 0; i < newUsersToday; i++) {
      const persona = weightedRandom(personas, personaWeights);
      users.push(createUser(startIndex + i, day, persona));
      
      analytics.push({
        userId: users[users.length - 1].userId,
        eventType: 'user_joined',
        day,
        timestamp: new Date(),
        metadata: { persona },
      });
    }
  }
  
  // Process churn
  processChurn(day);
  
  // Simulate check-ins for all active users
  const dayParts = ['morning', 'day', 'evening', 'night'];
  const activeUsers = users.filter(u => u.joinedDay <= day && !u.churned);
  
  for (const user of activeUsers) {
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
  const activeUsersToday = new Set(todayCheckIns.map(c => c.userId)).size;
  const totalActiveUsers = users.filter(u => u.joinedDay <= day && !u.churned).length;
  const meaningfulDaysToday = analytics.filter(e => e.eventType === 'meaningful_day' && e.day === day).length;
  const conversionsToday = analytics.filter(e => e.eventType === 'premium_conversion' && e.day === day).length;
  const churnedToday = analytics.filter(e => e.eventType === 'user_churned' && e.day === day).length;
  
  console.log(`   👥 Total Users: ${users.length} | Active: ${totalActiveUsers} | Check-ins: ${activeUsersToday}`);
  console.log(`   📊 Check-ins: ${todayCheckIns.length} | MDW: ${meaningfulDaysToday} | Conversions: ${conversionsToday}`);
  if (newUsersToday > 0) console.log(`   ➕ New Users: ${newUsersToday}`);
  if (churnedToday > 0) console.log(`   ➖ Churned: ${churnedToday}`);
  console.log('');
}

function weightedRandom(items, weights) {
  const total = weights.reduce((sum, w) => sum + w, 0);
  let random = Math.random() * total;
  
  for (let i = 0; i < items.length; i++) {
    random -= weights[i];
    if (random <= 0) return items[i];
  }
  
  return items[items.length - 1];
}

async function runSimulation() {
  console.clear();
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║        SIM2 - ADVANCED 1000-USER SIMULATION                ║');
  console.log('║        24 Days • 4 Hours • Realistic Growth & Churn        ║');
  console.log('╚════════════════════════════════════════════════════════════╝\n');
  
  initializeUsers();
  
  console.log('🚀 STARTING 4-HOUR SIMULATION (24 simulated days)\n');
  console.log(`⏰ Time scale: ${MINUTES_PER_DAY} minutes real = 1 day simulated`);
  console.log(`📅 Total: ${TOTAL_DAYS} days`);
  console.log(`👥 Users: 500 start + 500 join gradually`);
  console.log(`📉 Churn: ${CHURN_RATE * 100}% total (random across 24 days)\n`);
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
  const activeUsers = users.filter(u => !u.churned).length;
  const premiumUsers = users.filter(u => u.isPremium).length;
  const churnedUsers = users.filter(u => u.churned).length;
  const avgMDW = users.reduce((sum, u) => sum + u.meaningfulDays, 0) / users.length;
  const avgFulfillment = users.reduce((sum, u) => sum + u.fulfillmentScore, 0) / users.length;
  const conversions = analytics.filter(e => e.eventType === 'premium_conversion');
  
  // D7 Retention (users who joined Day 0, still active Day 7)
  const d0Users = users.filter(u => u.joinedDay === 0);
  const d7Active = d0Users.filter(u => {
    const hasCheckInsAfterD7 = checkIns.some(c => c.userId === u.userId && c.day >= 7);
    return hasCheckInsAfterD7 && !u.churned;
  }).length;
  const d7Retention = (d7Active / d0Users.length * 100);
  
  console.log('═'.repeat(60));
  console.log('📊 FINAL ANALYTICS REPORT - SIM2');
  console.log('═'.repeat(60) + '\n');
  
  console.log('👥 USER METRICS:');
  console.log(`   Total Users Created: ${users.length}`);
  console.log(`   Active Users: ${activeUsers} (${(activeUsers/users.length*100).toFixed(1)}%)`);
  console.log(`   Churned Users: ${churnedUsers} (${(churnedUsers/users.length*100).toFixed(1)}%)`);
  console.log(`   Premium Users: ${premiumUsers} (${(premiumUsers/users.length*100).toFixed(1)}%)`);
  console.log(`   D7 Retention: ${d7Retention.toFixed(1)}% (Day 0 cohort)`);
  console.log('');
  
  console.log('✅ ENGAGEMENT:');
  console.log(`   Total Check-ins: ${totalCheckIns.toLocaleString()}`);
  console.log(`   Avg Check-ins/User: ${(totalCheckIns / activeUsers).toFixed(1)}`);
  console.log(`   Avg MDW: ${avgMDW.toFixed(2)}`);
  console.log(`   Avg Fulfillment: ${avgFulfillment.toFixed(1)}/100`);
  console.log('');
  
  console.log('💰 REVENUE:');
  const mrr = premiumUsers * 7.99;
  const arr = mrr * 12;
  console.log(`   MRR: $${mrr.toFixed(2)}`);
  console.log(`   ARR: $${arr.toLocaleString()}`);
  console.log(`   Conversions: ${conversions.length} users`);
  if (conversions.length > 0) {
    const avgDaysToConvert = conversions.reduce((sum, c) => sum + c.metadata.daysToConvert, 0) / conversions.length;
    console.log(`   Avg Days to Convert: ${avgDaysToConvert.toFixed(1)}`);
  }
  console.log('');
  
  console.log('🎭 BY PERSONA:');
  const personas = ['engaged', 'casual', 'struggler', 'power-user'];
  for (const persona of personas) {
    const personaUsers = users.filter(u => u.persona === persona);
    const activePersona = personaUsers.filter(u => !u.churned);
    const avgCheckIns = activePersona.reduce((sum, u) => sum + u.totalCheckIns, 0) / activePersona.length || 0;
    const avgMDWPersona = activePersona.reduce((sum, u) => sum + u.meaningfulDays, 0) / activePersona.length || 0;
    const premiumRate = personaUsers.filter(u => u.isPremium).length / personaUsers.length * 100;
    const churnRate = personaUsers.filter(u => u.churned).length / personaUsers.length * 100;
    
    console.log(`   ${persona.toUpperCase().padEnd(12)}: ${personaUsers.length} users | ${avgCheckIns.toFixed(1)} check-ins | ${avgMDWPersona.toFixed(2)} MDW | ${premiumRate.toFixed(0)}% premium | ${churnRate.toFixed(0)}% churn`);
  }
  console.log('');
  
  console.log('📈 COHORT INSIGHTS:');
  console.log(`   Initial Cohort (Day 0): ${d0Users.length} users`);
  console.log(`   D7 Retention: ${d7Retention.toFixed(1)}%`);
  console.log(`   D14 Active: ${d0Users.filter(u => checkIns.some(c => c.userId === u.userId && c.day >= 14) && !u.churned).length}`);
  console.log(`   D21 Active: ${d0Users.filter(u => checkIns.some(c => c.userId === u.userId && c.day >= 21) && !u.churned).length}`);
  console.log('');
  
  // Save data
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const outputDir = path.join(__dirname, 'output');
  
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  fs.writeFileSync(
    path.join(outputDir, `sim2-advanced-${timestamp}.json`),
    JSON.stringify({ 
      users, 
      checkIns, 
      details, 
      analytics, 
      report: {
        overview: {
          totalUsers: users.length,
          activeUsers,
          churnedUsers,
          premiumUsers,
          avgMDW: avgMDW.toFixed(2),
          avgFulfillment: avgFulfillment.toFixed(1),
        },
        revenue: { mrr: mrr.toFixed(2), arr: arr.toFixed(2) },
        retention: { d7: d7Retention.toFixed(1) },
      }
    }, null, 2)
  );
  
  console.log(`💾 Data saved to: output/sim2-advanced-${timestamp}.json\n`);
  console.log('═'.repeat(60) + '\n');
}

runSimulation().catch(console.error);

