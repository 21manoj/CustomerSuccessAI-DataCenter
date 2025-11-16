/**
 * Realistic Full Cycle Conversion Simulation
 * With proper engagement tracking and conversion logic
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

const DEMOGRAPHICS = [
  { persona: 'engaged', count: 25, expectedConversion: 0.35 },
  { persona: 'casual', count: 40, expectedConversion: 0.15 },
  { persona: 'struggler', count: 20, expectedConversion: 0.05 },
  { persona: 'power-user', count: 15, expectedConversion: 0.60 }
];

const CHECKIN_RATES = {
  'engaged': 0.80,
  'casual': 0.50,
  'struggler': 0.25,
  'power-user': 0.90
};

class RealisticSimulation {
  constructor() {
    this.users = [];
    this.results = {
      conversions: 0,
      conversionsByPersona: {},
      conversionsByPathway: {},
      insightsGenerated: 0,
      lockedClicks: 0,
      conversionDetails: []
    };
  }

  log(message, color = 'white') {
    const colors = {
      reset: '\x1b[0m',
      bright: '\x1b[1m',
      red: '\x1b[31m',
      green: '\x1b[32m',
      yellow: '\x1b[33m',
      blue: '\x1b[34m',
      cyan: '\x1b[36m',
      magenta: '\x1b[35m'
    };
    console.log(`${colors[color]}${message}${colors.reset}`);
  }

  async createUser(id, persona) {
    try {
      const ts = Date.now() + Math.random();
      const response = await axios.post(`${API_BASE}/api/users`, {
        name: `User_${id}`,
        email: `user${id}_${ts}@test.com`,
        persona
      });
      return response.data;
    } catch (error) {
      return null;
    }
  }

  async createCheckIn(userId, mood = 'good') {
    try {
      await axios.post(`${API_BASE}/api/check-ins`, {
        user_id: userId,
        day_part: 'morning',
        mood,
        contexts: ['wellness'],
        micro_act: 'gratitude'
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  async generateInsights(userId) {
    try {
      const response = await axios.post(`${API_BASE}/api/insights/generate`, { userId });
      return response.data.insights?.length || 0;
    } catch (e) {
      return 0;
    }
  }

  async clickLockedInsight(userId) {
    try {
      await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
        type: 'locked_insight_click',
        data: { insightId: 'breakpoint_sleep', previewText: 'Sleep threshold' }
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  async getConversionOffer(userId, day) {
    try {
      const response = await axios.post(`${API_BASE}/api/conversion/offer`, {
        userId,
        currentDay: day
      });
      return response.data;
    } catch (e) {
      return { success: false };
    }
  }

  shouldCheckIn(persona) {
    return Math.random() < CHECKIN_RATES[persona];
  }

  async simulateDay(day) {
    let activeUsers = 0;
    let conversions = 0;
    const dailyConversions = [];

    for (const user of this.users) {
      if (this.shouldCheckIn(user.persona)) {
        activeUsers++;
        
        // Day 1: Set intention
        if (day === 1) {
          user.intention = 'Exercise 3x/week';
          user.checkIns = 0;
          user.freeInsights = 0;
          user.lockedClicks = 0;
        }

        // Create check-ins
        const numCheckIns = Math.floor(Math.random() * 2) + 2;
        for (let i = 0; i < numCheckIns; i++) {
          await this.createCheckIn(user.id);
        }
        user.checkIns += numCheckIns;

        // Day 3-7: Generate insights (when user has enough check-ins)
        if (day >= 3 && day <= 7 && user.checkIns >= (day * 2)) {
          const insightCount = await this.generateInsights(user.id);
          if (insightCount > 0) {
            this.results.insightsGenerated += insightCount;
            user.freeInsights += insightCount;
          }
        }

        // Day 7: Show locked insights and track clicks
        if (day === 7 && !user.converted) {
          console.log(`   Checking user ${user.id.substring(0,10)}... (${user.persona}): ${user.checkIns} check-ins`);
          
          // Simulate some users clicking locked insights
          if (Math.random() < 0.4) { // 40% click locked features
            await this.clickLockedInsight(user.id);
            user.lockedClicks++;
            this.results.lockedClicks++;
            console.log(`      Locked click: ${user.lockedClicks}`);
            
            // Some click multiple times
            if (Math.random() < 0.5) {
              await this.clickLockedInsight(user.id);
              user.lockedClicks++;
              this.results.lockedClicks++;
              console.log(`      Second locked click: ${user.lockedClicks}`);
            }
          }

          // Try to convert if conditions are met
          const offer = await this.getConversionOffer(user.id, 7);
          
          if (offer.success && offer.offer) {
            // Conversion logic based on engagement and persona
            const engagement = user.checkIns / day; // check-ins per day
            
            let shouldConvert = false;
            const conversionRate = DEMOGRAPHICS.find(d => d.persona === user.persona).expectedConversion;
            console.log(`      Offer received. Engagement: ${engagement.toFixed(2)}, Rate: ${(conversionRate*100).toFixed(0)}%`);
            
            // High engagement with locked clicks (strongest signal)
            if (engagement >= 2.0 && user.lockedClicks >= 2) {
              const rolled = Math.random();
              shouldConvert = rolled < conversionRate;
              console.log(`      High engagement + locked clicks. Roll: ${rolled.toFixed(3)} < ${conversionRate.toFixed(3)} = ${shouldConvert ? 'CONVERT!' : 'no'}`);
            }
            // Medium engagement with insights
            else if (engagement >= 1.5 && user.freeInsights >= 1) {
              const rolled = Math.random();
              const adjustedRate = conversionRate * 0.6;
              shouldConvert = rolled < adjustedRate;
              console.log(`      Medium engagement + insights. Roll: ${rolled.toFixed(3)} < ${adjustedRate.toFixed(3)} = ${shouldConvert ? 'CONVERT!' : 'no'}`);
            }
            // Even low engagement should have some conversions
            else if (engagement >= 1.0) {
              const rolled = Math.random();
              const adjustedRate = conversionRate * 0.3;
              shouldConvert = rolled < adjustedRate;
              console.log(`      Low engagement. Roll: ${rolled.toFixed(3)} < ${adjustedRate.toFixed(3)} = ${shouldConvert ? 'CONVERT!' : 'no'}`);
            } else {
              console.log(`      Too low engagement: ${engagement.toFixed(2)}`);
            }
            
            if (shouldConvert) {
              user.converted = true;
              user.conversionDay = 7;
              user.conversionPathway = 'Day 7 - Locked Features';
              conversions++;
              
              const detail = {
                userId: user.id,
                persona: user.persona,
                day: 7,
                checkIns: user.checkIns,
                lockedClicks: user.lockedClicks,
                pathway: user.conversionPathway
              };
              
              dailyConversions.push(detail);
              this.results.conversionDetails.push(detail);
              this.results.conversionsByPersona[user.persona] = (this.results.conversionsByPersona[user.persona] || 0) + 1;
              this.results.conversionsByPathway[user.conversionPathway] = (this.results.conversionsByPathway[user.conversionPathway] || 0) + 1;
            }
          }
        }

        user.daysActive++;
        await this.delay(3);
      }
    }

    this.results.conversions += conversions;

    // Print daily activity
    const totalCheckIns = this.users.reduce((sum, u) => sum + (u.checkIns || 0), 0);
    console.log(`   Active: ${activeUsers}/${this.users.length} (${(activeUsers/this.users.length*100).toFixed(0)}%) | Total Check-ins: ${totalCheckIns}`);

    // Print daily summary with detailed conversion info
    if (conversions > 0) {
      this.log(`\n💰💰💰 ** DAY ${day} CONVERSIONS: ${conversions} ** 💰💰💰`, 'bright');
      dailyConversions.forEach((c, idx) => {
        this.log(`   ${idx+1}. User ${c.userId.substring(0,15)}... (${c.persona})`, 'green');
        this.log(`      • Check-ins: ${c.checkIns}`, 'white');
        this.log(`      • Locked Clicks: ${c.lockedClicks}`, 'white');
        this.log(`      • Pathway: ${c.pathway}`, 'white');
      });
      this.log('');
    }
    
    // Weekly summary
    if (day % 7 === 0) {
      const week = day / 7;
      this.log(`\n📊 Week ${week} Summary:`, 'cyan');
      this.log(`   Active Users: ${activeUsers}/${this.users.length} (${(activeUsers/this.users.length*100).toFixed(1)}%)`);
      this.log(`   Total Conversions: ${this.results.conversions} (${(this.results.conversions/this.users.length*100).toFixed(1)}%)`);
      this.log(`   Insights Generated: ${this.results.insightsGenerated}`);
      this.log(`   Locked Feature Clicks: ${this.results.lockedClicks}`);
    }
    
    return { activeUsers, conversions };
  }

  async run() {
    this.log('\n╔════════════════════════════════════════════════════════╗', 'bright');
    this.log('║   Realistic Conversion Simulation - 100 Users         ║', 'bright');
    this.log('║   With Engagement Tracking & Proper Paywall Logic    ║', 'bright');
    this.log('╚════════════════════════════════════════════════════════╝\n', 'bright');
    
    this.log('👥 Creating 100 users with demographics...', 'blue');
    let id = 1;
    for (const demo of DEMOGRAPHICS) {
      this.log(`   Creating ${demo.count} ${demo.persona} users...`, 'blue');
      for (let i = 0; i < demo.count; i++) {
        const user = await this.createUser(id++, demo.persona);
        if (user) {
          this.users.push({
            ...user,
            persona: demo.persona,
            converted: false,
            checkIns: 0,
            daysActive: 0
          });
        }
        await this.delay(15);
      }
    }
    this.log(`✅ Created ${this.users.length} users\n`, 'green');
    
    this.log('📅 Simulating 30 days with full engagement tracking...\n', 'blue');
    
    for (let day = 1; day <= 30; day++) {
      const week = Math.floor((day-1)/7) + 1;
      this.log(`\n📅 Day ${day} (Week ${week})`, 'cyan');
      await this.simulateDay(day);
      
      // Progress every 10 days
      if (day % 10 === 0 && day < 30) {
        this.log(`\n📈 Progress (Day ${day}): ${this.results.conversions} conversions so far\n`, 'yellow');
      }
    }
    
    this.printResults();
  }

  printResults() {
    this.log('\n╔════════════════════════════════════════════════════════╗', 'bright');
    this.log('║                    FINAL RESULTS                       ║', 'bright');
    this.log('╚════════════════════════════════════════════════════════╝\n', 'bright');
    
    this.log('📊 Overall Conversion Metrics:', 'cyan');
    this.log(`   Total Users: ${this.users.length}`);
    this.log(`   Total Conversions: ${this.results.conversions}`);
    this.log(`   Conversion Rate: ${(this.results.conversions/this.users.length*100).toFixed(2)}%\n`, 'green');
    
    this.log('👥 Conversions by Persona:', 'cyan');
    DEMOGRAPHICS.forEach(demo => {
      const converted = this.results.conversionsByPersona[demo.persona] || 0;
      const rate = (converted / demo.count * 100).toFixed(1);
      this.log(`   ${demo.persona.padEnd(12)}: ${converted}/${demo.count} (${rate}%)`, 
        rate > 0 ? 'green' : 'white');
    });
    
    this.log('\n🎯 Conversions by Pathway:', 'cyan');
    Object.entries(this.results.conversionsByPathway).forEach(([pathway, count]) => {
      this.log(`   ${pathway}: ${count}`, 'green');
    });
    
    this.log('\n📈 Engagement Metrics:', 'cyan');
    this.log(`   Insights Generated: ${this.results.insightsGenerated}`);
    this.log(`   Locked Feature Clicks: ${this.results.lockedClicks}`);
    
    const avgCheckIns = this.results.conversionDetails.reduce((sum, c) => sum + c.checkIns, 0) / 
                       Math.max(this.results.conversions, 1);
    this.log(`   Avg Check-ins per Converted User: ${avgCheckIns.toFixed(1)}`);
    
    this.log('\n✅ Simulation Complete!\n', 'green');
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

const sim = new RealisticSimulation();
sim.run().then(() => process.exit(0)).catch(err => {
  console.error('Error:', err);
  process.exit(1);
});

