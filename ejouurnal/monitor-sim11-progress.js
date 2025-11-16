/**
 * SIM11 Progress Monitor
 * Monitors the industry-standard simulation progress
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

async function getSimulationStats() {
  try {
    // Get current stats
    const response = await axios.get(`${API_BASE}/health`);
    const data = response.data;
    
    const users = data.totalUsers || 0;
    const checkIns = data.totalCheckIns || 0;
    const journals = data.totalJournals || 0;
    const insights = data.totalInsights || 0;
    
    // Calculate metrics
    const progress = (users / 1000 * 100).toFixed(1);
    const estimatedPremiumUsers = Math.floor(users * 0.18); // 18% conversion rate
    const mrr = estimatedPremiumUsers * 19.99;
    const arr = mrr * 12;
    
    console.log('📊 SIM11 PROGRESS SNAPSHOT');
    console.log('=' * 50);
    console.log(`👥 Users: ${users} (${progress}% of 1000)`);
    console.log(`📝 Check-ins: ${checkIns}`);
    console.log(`📖 Journals: ${journals}`);
    console.log(`💡 Insights: ${insights}`);
    console.log(`💰 Estimated MRR: $${mrr.toFixed(2)}`);
    console.log(`💰 Estimated ARR: $${arr.toFixed(2)}`);
    console.log(`⚡ Server: ${data.status} (${data.database})`);
    console.log(`🔧 Rate Limit: ${data.rateLimitInfo.maxRequests} requests/minute`);
    console.log(`⏰ Time: ${new Date().toLocaleTimeString()}`);
    console.log('=' * 50);
    
    // Show progress bar
    const barLength = 20;
    const filled = Math.floor((users / 1000) * barLength);
    const bar = '█'.repeat(filled) + '░'.repeat(barLength - filled);
    console.log(`📈 Progress: [${bar}] ${progress}%`);
    
  } catch (error) {
    console.log('❌ Error monitoring simulation:', error.message);
  }
}

// Run once
getSimulationStats();
