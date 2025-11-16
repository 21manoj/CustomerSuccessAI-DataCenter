#!/usr/bin/env node
/**
 * LIVE ANALYTICS VIEWER
 * Shows progress from the quick demo results
 */

const fs = require('fs');
const path = require('path');

console.clear();
console.log('╔════════════════════════════════════════════════════════════╗');
console.log('║     FULFILLMENT SIMULATOR - CURRENT ANALYTICS              ║');
console.log('╚════════════════════════════════════════════════════════════╝\n');

// Read the quick demo results
const resultsPath = path.join(__dirname, 'output', 'quick-demo-results.json');

if (!fs.existsSync(resultsPath)) {
  console.log('⏳ No results yet. Simulation still running...\n');
  console.log('📊 Current Progress (from terminal):');
  console.log('   Day 1: 95 active users, 242 check-ins');
  console.log('   Day 2: 95 active users, 263 check-ins, 1 MDW');
  console.log('   Day 3: 92 active users, 236 check-ins, 1 MDW');
  console.log('\n⏰ Full simulation completes at ~9:04 PM');
  console.log('   Current time:', new Date().toLocaleTimeString());
  console.log('\n💡 Check back in ~1.5 hours for complete analytics!\n');
  process.exit(0);
}

const data = JSON.parse(fs.readFileSync(resultsPath, 'utf8'));

console.log('📊 SIMULATION ANALYTICS (Quick Demo)\n');
console.log('═'.repeat(60) + '\n');

// Overview
console.log('👥 USER OVERVIEW:');
console.log(`   Total Users: ${data.summary.activeUsers}`);
console.log(`   Premium Users: ${data.summary.premiumUsers} (${(data.summary.premiumUsers/100*100).toFixed(1)}%)`);
console.log(`   Avg Fulfillment: ${data.summary.avgFulfillment}/100`);
console.log(`   Avg MDW: ${data.summary.avgMDW}`);
console.log('');

// Check-ins breakdown
const checkInsByDay = {};
data.checkIns.forEach(c => {
  if (!checkInsByDay[c.day]) {
    checkInsByDay[c.day] = {
      total: 0,
      byDayPart: { morning: 0, day: 0, evening: 0, night: 0 },
      avgMood: 0,
      moods: [],
    };
  }
  checkInsByDay[c.day].total++;
  checkInsByDay[c.day].byDayPart[c.dayPart]++;
  checkInsByDay[c.day].moods.push(c.mood);
});

console.log('📅 DAILY BREAKDOWN:');
Object.keys(checkInsByDay).sort((a, b) => a - b).forEach(day => {
  const dayData = checkInsByDay[day];
  const avgMood = dayData.moods.reduce((sum, m) => sum + m, 0) / dayData.moods.length;
  const activeUsers = new Set(data.checkIns.filter(c => c.day == day).map(c => c.userId)).size;
  
  console.log(`   Day ${parseInt(day) + 1}: ${activeUsers} users, ${dayData.total} check-ins, avg mood ${avgMood.toFixed(1)}/5`);
});
console.log('');

// Persona analysis
console.log('🎭 PERSONA ANALYSIS:');
const personas = ['engaged', 'casual', 'struggler', 'power-user'];
personas.forEach(persona => {
  const users = data.users.filter(u => u.persona === persona);
  const avgCheckIns = users.reduce((sum, u) => sum + u.totalCheckIns, 0) / users.length;
  const avgMDW = users.reduce((sum, u) => sum + u.meaningfulDays, 0) / users.length;
  const premiumCount = users.filter(u => u.isPremium).length;
  const premiumRate = (premiumCount / users.length * 100).toFixed(0);
  
  console.log(`   ${persona.toUpperCase().padEnd(12)}: ${users.length} users | ${avgCheckIns.toFixed(1)} check-ins | ${avgMDW.toFixed(2)} MDW | ${premiumRate}% premium`);
});
console.log('');

// Top performers
console.log('🏆 TOP 5 PERFORMERS (by Fulfillment Score):');
const topUsers = data.users
  .sort((a, b) => b.fulfillmentScore - a.fulfillmentScore)
  .slice(0, 5);

topUsers.forEach((u, i) => {
  console.log(`   ${i + 1}. ${u.name.padEnd(20)} | Score: ${u.fulfillmentScore.toFixed(1)} | ${u.totalCheckIns} check-ins | ${u.meaningfulDays} MDW | ${u.isPremium ? '💎' : '🆓'}`);
});
console.log('');

// Conversion analysis
const conversions = data.analytics.filter(e => e.eventType === 'premium_conversion');
console.log('💰 CONVERSION INSIGHTS:');
console.log(`   Total Conversions: ${conversions.length}`);
if (conversions.length > 0) {
  const avgDay = conversions.reduce((sum, c) => sum + c.day, 0) / conversions.length;
  console.log(`   Avg Day to Convert: ${avgDay.toFixed(1)}`);
  
  const triggers = {};
  conversions.forEach(c => {
    const trigger = c.metadata?.trigger || 'unknown';
    triggers[trigger] = (triggers[trigger] || 0) + 1;
  });
  console.log(`   Triggers: ${JSON.stringify(triggers)}`);
}
console.log('');

// Meaningful Days distribution
console.log('✨ MEANINGFUL DAYS DISTRIBUTION:');
const mdwBuckets = { '0': 0, '1-2': 0, '3-5': 0, '6+': 0 };
data.users.forEach(u => {
  if (u.meaningfulDays === 0) mdwBuckets['0']++;
  else if (u.meaningfulDays <= 2) mdwBuckets['1-2']++;
  else if (u.meaningfulDays <= 5) mdwBuckets['3-5']++;
  else mdwBuckets['6+']++;
});

Object.keys(mdwBuckets).forEach(bucket => {
  const count = mdwBuckets[bucket];
  const pct = (count / 100 * 100).toFixed(0);
  const bar = '█'.repeat(Math.floor(pct / 2));
  console.log(`   ${bucket.padEnd(6)}: ${bar} ${count} users (${pct}%)`);
});
console.log('');

console.log('═'.repeat(60) + '\n');
console.log('💡 This is from the QUICK DEMO (12 seconds)');
console.log('⏳ Full 2-hour simulation still running...');
console.log('   Started: ~7:04 PM');
console.log('   Current time:', new Date().toLocaleTimeString());
console.log('   Will complete at: ~9:04 PM');
console.log('\n🔄 Run this script again after completion for full results!\n');

