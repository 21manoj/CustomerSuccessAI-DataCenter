#!/usr/bin/env node
/**
 * View Sim3 Progress in Real-Time
 */

const fs = require('fs');
const path = require('path');

console.clear();
console.log('╔════════════════════════════════════════════════════════════╗');
console.log('║           SIM3 LIVE PROGRESS MONITOR 🧠                    ║');
console.log('╚════════════════════════════════════════════════════════════╝\n');

const outputDir = path.join(__dirname, 'output');
const files = fs.readdirSync(outputDir)
  .filter(f => f.startsWith('sim3-insights-driven-'))
  .sort()
  .reverse();

if (files.length === 0) {
  console.log('⏳ Waiting for Sim3 to start generating data...\n');
  console.log('💡 Sim3 should begin outputting results within 5-10 minutes\n');
  console.log('📊 Once started, you\'ll see:');
  console.log('   - Insight delivery events');
  console.log('   - Engagement boost tracking');
  console.log('   - Insight-driven conversions');
  console.log('   - Struggler rescue attempts\n');
  process.exit(0);
}

const latestFile = path.join(outputDir, files[0]);
console.log(`📂 Reading: ${files[0]}\n`);

try {
  const data = JSON.parse(fs.readFileSync(latestFile, 'utf8'));
  
  const { users, insights, analytics, report } = data;
  
  if (!report) {
    console.log('⚠️  Simulation still in progress (no final report yet)\n');
    console.log(`📊 Current Stats:`);
    console.log(`   Users: ${users?.length || 0}`);
    console.log(`   Insights Delivered: ${insights?.length || 0}`);
    console.log(`   Analytics Events: ${analytics?.length || 0}\n`);
    process.exit(0);
  }
  
  // FULL REPORT
  console.log('═'.repeat(60));
  console.log('✅ SIMULATION COMPLETE! FINAL REPORT:');
  console.log('═'.repeat(60) + '\n');
  
  console.log('👥 USER METRICS:');
  console.log(`   Total Users: ${report.overview.totalUsers}`);
  console.log(`   Active: ${report.overview.activeUsers}`);
  console.log(`   Premium: ${report.overview.premiumUsers}`);
  console.log(`   D7 Retention: ${report.retention.d7}%\n`);
  
  console.log('💡 INSIGHT IMPACT:');
  console.log(`   Total Insights Delivered: ${report.insights.totalInsights}`);
  console.log(`   Users w/ Insights: ${report.insights.usersWithInsights}`);
  console.log(`   Avg Insights/User: ${report.insights.avgInsightsPerUser}\n`);
  
  console.log('🔥 INSIGHT vs NON-INSIGHT:');
  console.log(`   Insight Users Churn: ${report.insights.insightUserChurnRate}%`);
  console.log(`   Non-Insight Churn: ${report.insights.nonInsightUserChurnRate}%`);
  console.log(`   Insight Users Premium: ${report.insights.insightUserPremiumRate}%`);
  console.log(`   Non-Insight Premium: ${report.insights.nonInsightUserPremiumRate}%\n`);
  
  console.log('💰 REVENUE:');
  console.log(`   MRR: $${report.revenue.mrr}`);
  console.log(`   ARR: $${report.revenue.arr}`);
  console.log(`   Insight-Driven Conversions: ${report.revenue.insightDrivenConversions}/${report.revenue.totalConversions} (${(report.revenue.insightDrivenConversions/report.revenue.totalConversions*100).toFixed(1)}%)\n`);
  
  console.log('═'.repeat(60) + '\n');
  
} catch (error) {
  console.error('Error reading file:', error.message);
}

