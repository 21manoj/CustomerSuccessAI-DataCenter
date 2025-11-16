/**
 * SIM11 Progress Monitor
 * Monitors the industry-standard simulation progress
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

async function getSimulationStats() {
  try {
    // Get user count
    const usersResponse = await axios.get(`${API_BASE}/api/analytics`);
    const users = usersResponse.data.users || 0;
    
    // Get check-ins count
    const checkInsResponse = await axios.get(`${API_BASE}/api/analytics`);
    const checkIns = checkInsResponse.data.checkIns || 0;
    
    // Get journals count
    const journalsResponse = await axios.get(`${API_BASE}/api/analytics`);
    const journals = journalsResponse.data.journals || 0;
    
    // Get insights count
    const insightsResponse = await axios.get(`${API_BASE}/api/analytics`);
    const insights = insightsResponse.data.insights || 0;
    
    // Get details count
    const detailsResponse = await axios.get(`${API_BASE}/api/analytics`);
    const details = insightsResponse.data.details || 0;
    
    // Calculate metrics
    const activeUsers = users;
    const premiumUsers = Math.floor(users * 0.18); // Estimated 18% conversion
    const mrr = premiumUsers * 19.99;
    const arr = mrr * 12;
    
    console.log('📊 SIM11 PROGRESS SNAPSHOT');
    console.log('=' * 50);
    console.log(`👥 Users: ${users}`);
    console.log(`📝 Check-ins: ${checkIns}`);
    console.log(`📖 Journals: ${journals}`);
    console.log(`💡 Insights: ${insights}`);
    console.log(`📋 Details: ${details}`);
    console.log(`💰 Estimated MRR: $${mrr.toFixed(2)}`);
    console.log(`💰 Estimated ARR: $${arr.toFixed(2)}`);
    console.log(`📈 Progress: ${(users / 1000 * 100).toFixed(1)}% (${users}/1000 users)`);
    console.log(`⏰ Time: ${new Date().toLocaleTimeString()}`);
    console.log('=' * 50);
    
  } catch (error) {
    console.log('❌ Error monitoring simulation:', error.message);
  }
}

// Run once
getSimulationStats();
