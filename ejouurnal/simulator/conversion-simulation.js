/**
 * Conversion Workflow Simulation
 * Simulates 100 users over 30 days with industry-standard demographics
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

// Industry-standard demographics for wellness apps
const USER_DEMOGRAPHICS = [
  { persona: 'engaged', percentage: 25, conversion: 0.35 },      // Early adopters
  { persona: 'casual', percentage: 40, conversion: 0.15 },       // Mainstream users
  { persona: 'struggler', percentage: 20, conversion: 0.05 },    // Strugglers
  { persona: 'power-user', percentage: 15, conversion: 0.60 }    // Power users
];

// Check-in rates by persona
const CHECKIN_RATES = {
  'engaged': 0.80,    // 80% daily check-ins
  'casual': 0.50,     // 50% daily check-ins
  'struggler': 0.25,  // 25% daily check-ins
  'power-user': 0.90  // 90% daily check-ins
};

// Check-ins per day by persona
const CHECKINS_PER_DAY = {
  'engaged': 2.5,     // 2-3 check-ins per day
  'casual': 1.8,      // 1-2 check-ins per day
  'struggler': 0.8,   // Less than 1 per day
  'power-user': 3.0   // 3-4 check-ins per day
};

class ConversionSimulator {
  constructor() {
    this.users = [];
    this.results = {
      totalUsers: 100,
      conversions: 0,
      conversionsByPathway: {},
      conversionsByDay: {},
      dailyActiveUsers: {},
      engagement: {}
    };
  }

  async createUser(userId, persona) {
    try {
      const timestamp = Date.now();
      const response = await axios.post(`${API_BASE}/api/users`, {
        name: `User_${userId}`,
        email: `user${userId}_${timestamp}@test.com`,
        persona
      });
      return response.data;
    } catch (error) {
      console.error(`Failed to create user ${userId}:`, error.message);
      return null;
    }
  }

  async createCheckIn(userId) {
    try {
      await axios.post(`${API_BASE}/api/check-ins`, {
        user_id: userId,
        day_part: 'morning',
        mood: 'good',
        contexts: ['wellness'],
        micro_act: 'gratitude'
      });
      return true;
    } catch (error) {
      return false;
    }
  }

  async generateInsights(userId) {
    try {
      await axios.post(`${API_BASE}/api/insights/generate`, {
        userId
      });
      return true;
    } catch (error) {
      return false;
    }
  }

  async generateJournal(userId) {
    try {
      await axios.post(`${API_BASE}/api/journals/generate`, {
        userId,
        dailyScores: {
          overallScore: 70,
          bodyScore: 75,
          mindScore: 70,
          soulScore: 72,
          purposeScore: 68
        }
      });
      return true;
    } catch (error) {
      return false;
    }
  }

  async getConversionOffer(userId, currentDay) {
    try {
      const response = await axios.post(`${API_BASE}/api/conversion/offer`, {
        userId,
        currentDay
      });
      return response.data;
    } catch (error) {
      return { success: false };
    }
  }

  shouldCheckInToday(persona) {
    return Math.random() < CHECKIN_RATES[persona];
  }

  async simulateDay(day) {
    console.log(`\n📅 Day ${day} (${Math.floor((day-1)/7)+1} weeks completed)`);
    
    let activeUsers = 0;
    let conversions = 0;
    const dailyConversions = [];

    for (const user of this.users) {
      // Determine if user checks in today
      if (this.shouldCheckInToday(user.persona)) {
        activeUsers++;
        
        // Create check-ins
        const numCheckIns = Math.ceil(CHECKINS_PER_DAY[user.persona] * (Math.random() * 0.5 + 0.75));
        for (let i = 0; i < numCheckIns; i++) {
          await this.createCheckIn(user.id);
        }
        
        // Generate insights every few days (skip for speed)
        // if (day % 3 === 0 && Math.random() < 0.3) {
        //   await this.generateInsights(user.id);
        // }
        
        // Generate journals weekly (skip for speed - takes 6-8 seconds each)
        // if (day % 7 === 0) {
        //   await this.generateJournal(user.id);
        // }

        // Try to convert on specific days (simulating pathways)
        if (!user.converted && (day === 7 || day === 14 || day === 21 || day === 28)) {
          const offer = await this.getConversionOffer(user.id, day);
          
          if (offer.success && offer.offer) {
            // Simulate conversion based on persona conversion rate
            const conversionChance = USER_DEMOGRAPHICS.find(d => d.persona === user.persona).conversion;
            
            if (Math.random() < conversionChance) {
              user.converted = true;
              user.conversionDay = day;
              conversions++;
              dailyConversions.push({
                userId: user.id,
                persona: user.persona,
                day: day,
                pathway: day === 7 ? 'Aha Moment' : 
                        day === 14 ? 'Week 2' : 
                        day === 21 ? 'Power User' : 'Persistent'
              });
            }
          }
        }

        // Update user stats
        user.daysActive = (user.daysActive || 0) + 1;
      }
      
      // Minimal delay for speed
      await this.delay(10);
    }

    this.results.dailyActiveUsers[day] = activeUsers;
    if (conversions > 0) {
      this.results.conversionsByDay[day] = conversions;
      dailyConversions.forEach(c => {
        this.results.conversionsByPathway[c.pathway] = (this.results.conversionsByPathway[c.pathway] || 0) + 1;
      });
    }

    console.log(`   👥 Active: ${activeUsers}/${this.users.length} (${(activeUsers/this.users.length*100).toFixed(1)}%)`);
    console.log(`   💳 Conversions: ${conversions} (Total: ${this.results.conversions})`);
    
    return { activeUsers, conversions };
  }

  async runSimulation() {
    console.log('╔════════════════════════════════════════════════════════╗');
    console.log('║  Conversion Workflow Simulation - 100 Users / 30 Days ║');
    console.log('╚════════════════════════════════════════════════════════╝');
    
    console.log('\n👥 Creating 100 users with demographics...');
    
    // Create users based on demographics
    let userIdx = 1;
    for (const demo of USER_DEMOGRAPHICS) {
      const numUsers = Math.floor(100 * demo.percentage / 100);
      console.log(`   Creating ${numUsers} ${demo.persona} users...`);
      
      for (let i = 0; i < numUsers; i++) {
        const user = await this.createUser(userIdx++, demo.persona);
        if (user) {
          this.users.push({
            ...user,
            persona: demo.persona,
            converted: false,
            daysActive: 0
          });
        }
        await this.delay(50);
      }
    }
    
    console.log(`✅ Created ${this.users.length} users`);
    
    // Simulate 30 days
    for (let day = 1; day <= 30; day++) {
      const stats = await this.simulateDay(day);
      this.results.conversions += stats.conversions;
      
      // Progress update every 10 days
      if (day % 10 === 0) {
        console.log(`\n📊 Progress Update (Day ${day}):`);
        console.log(`   Total Conversions: ${this.results.conversions}`);
        console.log(`   Conversion Rate: ${(this.results.conversions/this.users.length*100).toFixed(2)}%`);
      }
    }
    
    this.printResults();
  }

  printResults() {
    console.log('\n╔════════════════════════════════════════════════════════╗');
    console.log('║              SIMULATION RESULTS                        ║');
    console.log('╚════════════════════════════════════════════════════════╝');
    
    console.log(`\n📊 Overall Metrics:`);
    console.log(`   Total Users: ${this.users.length}`);
    console.log(`   Total Conversions: ${this.results.conversions}`);
    console.log(`   Overall Conversion Rate: ${(this.results.conversions/this.users.length*100).toFixed(2)}%`);
    
    console.log(`\n👥 Conversions by Persona:`);
    const personaConversions = {};
    this.users.forEach(user => {
      if (user.converted) {
        personaConversions[user.persona] = (personaConversions[user.persona] || 0) + 1;
      }
    });
    
    USER_DEMOGRAPHICS.forEach(demo => {
      const converted = personaConversions[demo.persona] || 0;
      const total = this.users.filter(u => u.persona === demo.persona).length;
      const rate = total > 0 ? (converted/total*100).toFixed(1) : 0;
      console.log(`   ${demo.persona}: ${converted}/${total} (${rate}%)`);
    });
    
    console.log(`\n📈 Conversions by Day:`);
    Object.keys(this.results.conversionsByDay).forEach(day => {
      console.log(`   Day ${day}: ${this.results.conversionsByDay[day]} conversions`);
    });
    
    console.log(`\n🎯 Conversions by Pathway:`);
    Object.keys(this.results.conversionsByPathway).forEach(pathway => {
      console.log(`   ${pathway}: ${this.results.conversionsByPathway[pathway]}`);
    });
    
    console.log(`\n🔥 Average Daily Active Users:`);
    const avgDAU = Object.values(this.results.dailyActiveUsers).reduce((a,b) => a+b, 0) / Object.keys(this.results.dailyActiveUsers).length;
    console.log(`   ${avgDAU.toFixed(1)} users per day`);
    
    console.log(`\n✅ Simulation Complete!\n`);
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Run simulation
const simulator = new ConversionSimulator();
simulator.runSimulation().then(() => {
  process.exit(0);
}).catch(error => {
  console.error('Simulation failed:', error);
  process.exit(1);
});

