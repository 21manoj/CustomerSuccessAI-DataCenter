const axios = require('axios');

// Monitor SIM13 simulation progress
async function monitorSim13() {
  try {
    console.log('📊 SIM13 SIMULATION MONITORING');
    console.log('==============================');
    
    // Check server health
    const healthResponse = await axios.get('http://localhost:3005/health');
    const health = healthResponse.data;
    
    console.log(`🕐 Timestamp: ${new Date().toLocaleString()}`);
    console.log(`⚡ Server: ${health.status} (${health.database})`);
    console.log(`👥 Total Users: ${health.totalUsers}`);
    console.log(`📝 Total Check-ins: ${health.totalCheckIns}`);
    console.log(`📖 Total Journals: ${health.totalJournals}`);
    console.log(`💡 Total Insights: ${health.totalInsights}`);
    console.log(`🔧 Rate Limit: ${health.rateLimitInfo.maxRequests} requests/minute`);
    
    // Check if SIM13 is running
    const { exec } = require('child_process');
    exec('ps aux | grep sim13 | grep -v grep', (error, stdout, stderr) => {
      if (stdout.trim()) {
        console.log('✅ SIM13 simulation is running');
      } else {
        console.log('❌ SIM13 simulation is not running');
      }
    });
    
    console.log('\n📈 Progress Analysis:');
    const userCount = health.totalUsers;
    const checkInCount = health.totalCheckIns;
    const journalCount = health.totalJournals;
    
    if (userCount > 0) {
      const activityRate = ((checkInCount / userCount) * 100).toFixed(1);
      const journalRate = ((journalCount / userCount) * 100).toFixed(1);
      
      console.log(`   📊 Activity Rate: ${activityRate}% (${checkInCount}/${userCount} users)`);
      console.log(`   📖 Journal Rate: ${journalRate}% (${journalCount}/${userCount} users)`);
      
      // Check if we're approaching the 1000 user cap
      if (userCount >= 1000) {
        console.log(`   ⚠️  User cap reached: ${userCount}/1000 users`);
      } else {
        console.log(`   📈 User progress: ${userCount}/1000 users (${((userCount/1000)*100).toFixed(1)}%)`);
      }
    }
    
    console.log('\n✅ SIM13 monitoring complete!');
    
  } catch (error) {
    console.error('❌ Error monitoring SIM13:', error.message);
  }
}

monitorSim13();
