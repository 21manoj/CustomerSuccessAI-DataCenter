#!/usr/bin/env node
/**
 * FINAL RESULTS ANALYZER
 * Comprehensive analytics from 2-hour simulation
 */

const fs = require('fs');
const path = require('path');

const resultsFile = './output/simulation-2025-10-17T03-54-16-166Z.json';
const data = JSON.parse(fs.readFileSync(resultsFile, 'utf8'));

console.clear();
console.log('╔════════════════════════════════════════════════════════════╗');
console.log('║   FULFILLMENT APP - FINAL SIMULATION RESULTS (2 HOURS)    ║');
console.log('╚════════════════════════════════════════════════════════════╝\n');

const { users, checkIns, details, analytics, report } = data;

console.log('═'.repeat(60));
console.log('📊 EXECUTIVE SUMMARY');
console.log('═'.repeat(60) + '\n');

console.log('👥 USER METRICS:');
console.log(`   Total Users: ${report.overview.totalUsers}`);
console.log(`   Active Users: ${report.overview.activeUsers}`);
console.log(`   Premium Users: ${report.overview.premiumUsers} (${report.overview.conversionRate})`);
console.log(`   Avg MDW: ${report.overview.avgMDW}`);
console.log(`   Avg Fulfillment: ${report.overview.avgFulfillment}/100`);
console.log('');

console.log('💰 REVENUE:');
console.log(`   MRR: ${report.revenue.mrr}`);
console.log(`   ARR: ${report.revenue.arr}`);
console.log('');

// Daily retention
console.log('═'.repeat(60));
console.log('📅 DAILY COHORT ANALYSIS');
console.log('═'.repeat(60) + '\n');

const checkInsByDay = {};
checkIns.forEach(c => {
  if (!checkInsByDay[c.day]) {
    checkInsByDay[c.day] = { count: 0, users: new Set(), mdw: 0 };
  }
  checkInsByDay[c.day].count++;
  checkInsByDay[c.day].users.add(c.userId);
});

// Add MDW counts
analytics.forEach(e => {
  if (e.eventType === 'meaningful_day') {
    if (!checkInsByDay[e.day]) checkInsByDay[e.day] = { count: 0, users: new Set(), mdw: 0 };
    checkInsByDay[e.day].mdw++;
  }
});

console.log('Day | Active Users | Check-ins | Retention | MDW  | Conversions');
console.log('----|--------------|-----------|-----------|------|-------------');

const d1Active = checkInsByDay[0]?.users.size || 0;

for (let day = 0; day < 12; day++) {
  const dayData = checkInsByDay[day] || { count: 0, users: new Set(), mdw: 0 };
  const activeUsers = dayData.users.size;
  const retention = d1Active > 0 ? ((activeUsers / d1Active) * 100).toFixed(1) : '0.0';
  const conversions = analytics.filter(e => e.eventType === 'premium_conversion' && e.day === day).length;
  
  console.log(` ${String(day + 1).padStart(2)} | ${String(activeUsers).padStart(12)} | ${String(dayData.count).padStart(9)} | ${String(retention).padStart(8)}% | ${String(dayData.mdw).padStart(4)} | ${conversions || '-'}`);
}

// D7 Retention
const d7Active = checkInsByDay[6]?.users.size || 0;
const d7Retention = ((d7Active / d1Active) * 100).toFixed(1);

console.log('\n📈 KEY RETENTION METRIC:');
console.log(`   D7 Retention: ${d7Retention}% (${d7Active} out of ${d1Active} Day-1 users still active on Day 7)`);
console.log('');

// Persona breakdown
console.log('═'.repeat(60));
console.log('🎭 PERSONA DEEP DIVE');
console.log('═'.repeat(60) + '\n');

const personas = ['engaged', 'casual', 'struggler', 'power-user'];
personas.forEach(persona => {
  const personaUsers = users.filter(u => u.persona === persona);
  const count = personaUsers.length;
  
  const totalCheckIns = checkIns.filter(c => 
    personaUsers.some(u => u.userId === c.userId)
  ).length;
  
  const premiumCount = personaUsers.filter(u => u.isPremium).length;
  const avgMDW = personaUsers.reduce((sum, u) => sum + u.meaningfulDays, 0) / count;
  const avgFulfillment = personaUsers.reduce((sum, u) => sum + u.fulfillmentScore, 0) / count;
  const avgStreak = personaUsers.reduce((sum, u) => sum + u.longestStreak, 0) / count;
  
  console.log(`${persona.toUpperCase()}:`);
  console.log(`   Count: ${count} users (${(count/100*100).toFixed(0)}%)`);
  console.log(`   Avg Check-ins: ${(totalCheckIns / count).toFixed(1)}`);
  console.log(`   Avg MDW: ${avgMDW.toFixed(2)}`);
  console.log(`   Avg Fulfillment: ${avgFulfillment.toFixed(1)}/100`);
  console.log(`   Premium Rate: ${(premiumCount / count * 100).toFixed(0)}%`);
  console.log(`   Avg Longest Streak: ${avgStreak.toFixed(1)} days`);
  console.log('');
});

// Conversion analysis
console.log('═'.repeat(60));
console.log('💰 CONVERSION ANALYSIS');
console.log('═'.repeat(60) + '\n');

const conversions = analytics.filter(e => e.eventType === 'premium_conversion');

console.log(`Total Conversions: ${conversions.length}`);
console.log(`Conversion Rate: ${(conversions.length / 100 * 100).toFixed(1)}%`);

if (conversions.length > 0) {
  const avgDay = conversions.reduce((sum, c) => sum + c.day, 0) / conversions.length;
  console.log(`Avg Days to Convert: ${avgDay.toFixed(1)}`);
  
  // Triggers
  const triggers = {};
  conversions.forEach(c => {
    const trigger = c.metadata?.trigger || 'unknown';
    triggers[trigger] = (triggers[trigger] || 0) + 1;
  });
  
  console.log(`\nConversion Triggers:`);
  Object.keys(triggers).forEach(trigger => {
    console.log(`   ${trigger}: ${triggers[trigger]} users`);
  });
  
  // By day
  console.log(`\nConversions by Day:`);
  for (let day = 0; day < 12; day++) {
    const dayConversions = conversions.filter(c => c.day === day).length;
    if (dayConversions > 0) {
      console.log(`   Day ${day + 1}: ${dayConversions} conversion${dayConversions > 1 ? 's' : ''}`);
    }
  }
}

console.log('');

// Top performers
console.log('═'.repeat(60));
console.log('🏆 TOP 10 USERS (by Total Check-ins)');
console.log('═'.repeat(60) + '\n');

const topByCheckIns = users
  .sort((a, b) => b.totalCheckIns - a.totalCheckIns)
  .slice(0, 10);

topByCheckIns.forEach((u, i) => {
  console.log(`${String(i + 1).padStart(2)}. ${u.name.padEnd(20)} | ${u.persona.padEnd(12)} | ${String(u.totalCheckIns).padStart(3)} check-ins | MDW: ${u.meaningfulDays} | Streak: ${u.longestStreak} | ${u.isPremium ? '💎' : '🆓'}`);
});

console.log('');

// MDW leaders
console.log('═'.repeat(60));
console.log('✨ TOP 10 USERS (by Meaningful Days)');
console.log('═'.repeat(60) + '\n');

const topByMDW = users
  .sort((a, b) => b.meaningfulDays - a.meaningfulDays)
  .slice(0, 10);

topByMDW.forEach((u, i) => {
  console.log(`${String(i + 1).padStart(2)}. ${u.name.padEnd(20)} | ${u.persona.padEnd(12)} | MDW: ${String(u.meaningfulDays).padStart(2)} | Fulfillment: ${u.fulfillmentScore.toFixed(1)} | ${u.isPremium ? '💎 Premium' : '🆓 Free'}`);
});

console.log('');

// Churn analysis
console.log('═'.repeat(60));
console.log('📉 ENGAGEMENT TRENDS');
console.log('═'.repeat(60) + '\n');

const lastThreeDays = [9, 10, 11];
const recentlyActive = new Set();
lastThreeDays.forEach(day => {
  checkIns.filter(c => c.day === day).forEach(c => recentlyActive.add(c.userId));
});

const churnedUsers = users.filter(u => 
  u.totalCheckIns > 0 && !recentlyActive.has(u.userId)
).length;

console.log(`Recently Active (Days 10-12): ${recentlyActive.size} users`);
console.log(`Churned/Inactive: ${churnedUsers} users`);
console.log(`Churn Rate: ${(churnedUsers / 100 * 100).toFixed(1)}%`);
console.log('');

console.log('═'.repeat(60));
console.log('📊 SUMMARY INSIGHTS');
console.log('═'.repeat(60) + '\n');

console.log('✅ STRENGTHS:');
console.log(`   • ${d1Active} users activated on Day 1`);
console.log(`   • ${d7Retention}% D7 retention (benchmark: 60-75%)`);
console.log(`   • ${(conversions.length / 100 * 100).toFixed(0)}% conversion rate (benchmark: 15-20%)`);
console.log(`   • ${report.revenue.mrr} monthly recurring revenue`);
console.log('');

console.log('⚠️  AREAS TO IMPROVE:');
const avgMDW = users.reduce((sum, u) => sum + u.meaningfulDays, 0) / 100;
if (avgMDW < 2) console.log(`   • Low MDW (${avgMDW.toFixed(2)}) - Need to help users hit thresholds`);
if (parseFloat(d7Retention) < 70) console.log(`   • D7 retention below 70% - Improve engagement tactics`);
console.log('');

console.log('═'.repeat(60));
console.log(`\n💾 Full data saved to: ${resultsFile}\n`);
console.log('🎯 Simulation Complete! Review data for product insights.\n');

