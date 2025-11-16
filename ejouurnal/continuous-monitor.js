/**
 * CONTINUOUS SIMULATION MONITOR
 * Monitor the large-scale simulation progress every 30 seconds
 */

const axios = require('axios');

let startTime = Date.now();
let lastUsers = 0;
let lastCheckIns = 0;
let lastJournals = 0;

async function monitorSimulation() {
  try {
    const response = await axios.get('http://localhost:3005/health');
    const data = response.data;
    
    const now = Date.now();
    const elapsed = Math.floor((now - startTime) / 1000);
    const elapsedMinutes = Math.floor(elapsed / 60);
    const elapsedSeconds = elapsed % 60;
    
    // Calculate rates
    const userRate = data.totalUsers - lastUsers;
    const checkInRate = data.totalCheckIns - lastCheckIns;
    const journalRate = data.totalJournals - lastJournals;
    
    console.log(`\n📊 [${elapsedMinutes}:${elapsedSeconds.toString().padStart(2, '0')}] SIMULATION PROGRESS`);
    console.log(`   👥 Users: ${data.totalUsers} (+${userRate})`);
    console.log(`   📝 Check-ins: ${data.totalCheckIns} (+${checkInRate})`);
    console.log(`   📖 Journals: ${data.totalJournals} (+${journalRate})`);
    console.log(`   💡 Insights: ${data.totalInsights}`);
    console.log(`   🔗 Total API Calls: ${data.totalUsers + data.totalCheckIns + data.totalJournals + data.totalInsights}`);
    console.log(`   ⚡ Server: ${data.status} (${data.database})`);
    
    // Update last values
    lastUsers = data.totalUsers;
    lastCheckIns = data.totalCheckIns;
    lastJournals = data.totalJournals;
    
    // Show completion percentage
    const completionPercent = Math.min(100, (data.totalUsers / 1000) * 100);
    console.log(`   📈 Progress: ${completionPercent.toFixed(1)}% (${data.totalUsers}/1000 users)`);
    
  } catch (error) {
    console.log(`❌ Error monitoring simulation: ${error.message}`);
  }
}

// Run monitoring every 30 seconds
console.log('🔍 Starting continuous simulation monitoring...');
console.log('⏱️  Monitoring every 30 seconds for 30 minutes');
console.log('🛑 Press Ctrl+C to stop monitoring');

setInterval(monitorSimulation, 30000);

// Initial check
monitorSimulation();
