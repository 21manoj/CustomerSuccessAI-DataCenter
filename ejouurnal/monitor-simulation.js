/**
 * SIMULATION MONITOR
 * Monitor the large-scale simulation progress
 */

const axios = require('axios');

async function monitorSimulation() {
  console.log('\n🔍 SIMULATION MONITOR');
  console.log('=' * 50);
  
  try {
    const response = await axios.get('http://localhost:3005/health');
    const data = response.data;
    
    console.log(`📊 Server Status: ${data.status}`);
    console.log(`🗄️  Database: ${data.database}`);
    console.log(`👥 Total Users: ${data.totalUsers}`);
    console.log(`📝 Total Check-ins: ${data.totalCheckIns}`);
    console.log(`📖 Total Journals: ${data.totalJournals}`);
    console.log(`💡 Total Insights: ${data.totalInsights}`);
    console.log(`⏰ Timestamp: ${data.timestamp}`);
    
    if (data.rateLimitInfo) {
      console.log(`🚦 Rate Limit: ${data.rateLimitInfo.maxRequests} requests per ${data.rateLimitInfo.windowMs/1000}s`);
    }
    
    // Calculate rates
    const now = new Date();
    const serverTime = new Date(data.timestamp);
    const timeDiff = (now - serverTime) / 1000; // seconds
    
    if (timeDiff < 60) {
      console.log(`⚡ Server is very responsive (${Math.round(timeDiff)}s ago)`);
    } else if (timeDiff < 300) {
      console.log(`✅ Server is responsive (${Math.round(timeDiff/60)}m ago)`);
    } else {
      console.log(`⚠️  Server may be under load (${Math.round(timeDiff/60)}m ago)`);
    }
    
  } catch (error) {
    console.log(`❌ Error monitoring simulation: ${error.message}`);
  }
}

// Run monitoring
monitorSimulation();
