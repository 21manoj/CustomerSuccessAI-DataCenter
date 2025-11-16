#!/usr/bin/env node
/**
 * QUICK DEMO - Runs in ~12 seconds
 * Shows how the simulator works without waiting 2 hours
 */

const fs = require('fs');
const path = require('path');

// QUICK CONFIG - 1 second per day!
const TOTAL_USERS = 100;
const MS_PER_DAY = 1000; // 1 second = 1 day
const TOTAL_DAYS = 12;

const users = [];
const checkIns = [];
const details = [];
const analytics = [];

function initializeUsers() {
  const personas = [
    ...Array(30).fill('engaged'),
    ...Array(45).fill('casual'),
    ...Array(20).fill('struggler'),
    ...Array(5).fill('power-user'),
  ];
  
  for (let i = 0; i < TOTAL_USERS; i++) {
    users.push({
      userId: `user_${String(i + 1).padStart(3, '0')}`,
      name: `User ${i + 1}`,
      persona: personas[i],
      isPremium: Math.random() < 0.15,
      totalCheckIns: 0,
      meaningfulDays: 0,
      currentStreak: 0,
      longestStreak: 0,
      bodyScore: 50 + Math.random() * 20,
      mindScore: 50 + Math.random() * 20,
      soulScore: 50 + Math.random() * 20,
      purposeScore: 50 + Math.random() * 20,
      fulfillmentScore: 60 + Math.random() * 15,
    });
  }
}

function simulateDay(day) {
  console.log(`📅 DAY ${day + 1} - ${new Date().toLocaleTimeString()}`);
  
  const dayParts = ['morning', 'day', 'evening', 'night'];
  const baseRates = { 'engaged': 0.85, 'casual': 0.55, 'struggler': 0.30, 'power-user': 0.95 };
  
  for (const user of users) {
    for (const dayPart of dayParts) {
      let probability = baseRates[user.persona];
      probability *= (0.7 + 0.3 * Math.exp(-0.05 * day));
      if (user.isPremium) probability *= 1.25;
      
      if (Math.random() < probability) {
        const mood = Math.floor(1 + Math.random() * 5);
        checkIns.push({ userId: user.userId, day, dayPart, mood });
        user.totalCheckIns++;
        
        analytics.push({
          userId: user.userId,
          eventType: 'check_in_complete',
          day,
          metadata: { dayPart, mood },
        });
      }
    }
  }
  
  // Update scores
  for (const user of users) {
    const todayCheckIns = checkIns.filter(c => c.userId === user.userId && c.day === day);
    
    if (todayCheckIns.length > 0) {
      const avgMood = todayCheckIns.reduce((sum, c) => sum + c.mood, 0) / todayCheckIns.length;
      user.mindScore += (avgMood - 3) * 2;
      user.soulScore += todayCheckIns.length * 1.5;
      user.purposeScore += todayCheckIns.length * 2;
      user.bodyScore += (Math.random() - 0.3) * 3;
      
      // Clamp
      user.bodyScore = Math.max(0, Math.min(100, user.bodyScore));
      user.mindScore = Math.max(0, Math.min(100, user.mindScore));
      user.soulScore = Math.max(0, Math.min(100, user.soulScore));
      user.purposeScore = Math.max(0, Math.min(100, user.purposeScore));
      user.fulfillmentScore = (user.bodyScore + user.mindScore + user.soulScore + user.purposeScore) / 4;
      
      // Meaningful day?
      if (user.bodyScore >= 70 && user.mindScore >= 65 && user.soulScore >= 80 && user.purposeScore >= 55) {
        user.meaningfulDays++;
        user.currentStreak++;
        user.longestStreak = Math.max(user.longestStreak, user.currentStreak);
        
        analytics.push({
          userId: user.userId,
          eventType: 'meaningful_day',
          day,
          metadata: { streak: user.currentStreak },
        });
      }
    }
  }
  
  // Premium conversions
  for (const user of users) {
    if (!user.isPremium && user.meaningfulDays >= 3 && Math.random() < 0.3) {
      user.isPremium = true;
      analytics.push({
        userId: user.userId,
        eventType: 'premium_conversion',
        day,
        metadata: { trigger: 'mdw' },
      });
    }
  }
  
  // Print summary
  const todayCheckIns = checkIns.filter(c => c.day === day);
  const activeUsers = new Set(todayCheckIns.map(c => c.userId)).size;
  const meaningfulDaysToday = analytics.filter(e => e.eventType === 'meaningful_day' && e.day === day).length;
  const conversionsToday = analytics.filter(e => e.eventType === 'premium_conversion' && e.day === day).length;
  
  console.log(`   ✅ Active: ${activeUsers}/100 | Check-ins: ${todayCheckIns.length} | MDW: ${meaningfulDaysToday} | Conversions: ${conversionsToday}`);
}

async function run() {
  console.clear();
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║          ⚡ QUICK DEMO - 12 seconds total                  ║');
  console.log('╚════════════════════════════════════════════════════════════╝\n');
  
  console.log('🎭 Initializing 100 users...\n');
  initializeUsers();
  console.log(`✅ Created: 30 Engaged, 45 Casual, 20 Strugglers, 5 Power Users\n`);
  
  console.log('🚀 Running 12-day simulation (1 second/day)...\n');
  console.log('─'.repeat(60) + '\n');
  
  for (let day = 0; day < TOTAL_DAYS; day++) {
    simulateDay(day);
    if (day < TOTAL_DAYS - 1) {
      await new Promise(resolve => setTimeout(resolve, MS_PER_DAY));
    }
  }
  
  console.log('\n' + '═'.repeat(60));
  console.log('📊 FINAL RESULTS');
  console.log('═'.repeat(60) + '\n');
  
  const activeUsers = new Set(checkIns.map(c => c.userId)).size;
  const premiumUsers = users.filter(u => u.isPremium).length;
  const avgMDW = users.reduce((sum, u) => sum + u.meaningfulDays, 0) / TOTAL_USERS;
  const avgFulfillment = users.reduce((sum, u) => sum + u.fulfillmentScore, 0) / TOTAL_USERS;
  const conversions = analytics.filter(e => e.eventType === 'premium_conversion');
  
  console.log('👥 USER METRICS:');
  console.log(`   Total Users: ${TOTAL_USERS}`);
  console.log(`   Active Users: ${activeUsers} (${(activeUsers/TOTAL_USERS*100).toFixed(1)}%)`);
  console.log(`   Premium Users: ${premiumUsers} (${(premiumUsers/TOTAL_USERS*100).toFixed(1)}%)`);
  console.log('');
  
  console.log('✅ ENGAGEMENT:');
  console.log(`   Total Check-ins: ${checkIns.length.toLocaleString()}`);
  console.log(`   Avg Check-ins/User: ${(checkIns.length / activeUsers).toFixed(1)}`);
  console.log(`   Avg MDW: ${avgMDW.toFixed(2)}`);
  console.log(`   Avg Fulfillment: ${avgFulfillment.toFixed(1)}/100`);
  console.log('');
  
  console.log('💰 REVENUE:');
  console.log(`   MRR: $${(premiumUsers * 7.99).toFixed(2)}`);
  console.log(`   ARR: $${(premiumUsers * 7.99 * 12).toFixed(2)}`);
  console.log(`   Conversions: ${conversions.length} (Day ${(conversions.reduce((sum, c) => sum + c.day, 0) / conversions.length || 0).toFixed(1)} avg)`);
  console.log('');
  
  console.log('🎭 BY PERSONA:');
  const personas = ['engaged', 'casual', 'struggler', 'power-user'];
  for (const persona of personas) {
    const personaUsers = users.filter(u => u.persona === persona);
    const avgCheckIns = personaUsers.reduce((sum, u) => sum + u.totalCheckIns, 0) / personaUsers.length;
    const avgMDWPersona = personaUsers.reduce((sum, u) => sum + u.meaningfulDays, 0) / personaUsers.length;
    const premiumRate = personaUsers.filter(u => u.isPremium).length / personaUsers.length * 100;
    
    console.log(`   ${persona.toUpperCase().padEnd(12)}: ${avgCheckIns.toFixed(1)} check-ins | ${avgMDWPersona.toFixed(2)} MDW | ${premiumRate.toFixed(0)}% premium`);
  }
  
  console.log('\n' + '═'.repeat(60));
  console.log('🎉 DEMO COMPLETE!\n');
  console.log('To run the FULL 2-hour simulation:');
  console.log('   node run-simulation.js\n');
  
  // Save quick results
  const outputDir = path.join(__dirname, 'output');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  fs.writeFileSync(
    path.join(outputDir, 'quick-demo-results.json'),
    JSON.stringify({ users, checkIns, analytics, summary: { activeUsers, premiumUsers, avgMDW, avgFulfillment } }, null, 2)
  );
  
  console.log('💾 Results saved to: simulator/output/quick-demo-results.json\n');
}

run().catch(console.error);

