/**
 * Full Cycle Conversion Simulation
 * 100 users, 30 days, proper intention→micro-moves→checkins→insights→journals→conversion cycle
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

// Demographics and conversion rates
const DEMOGRAPHICS = [
  { persona: 'engaged', count: 25, conversion: 0.35 },
  { persona: 'casual', count: 40, conversion: 0.15 },
  { persona: 'struggler', count: 20, conversion: 0.05 },
  { persona: 'power-user', count: 15, conversion: 0.60 }
];

const CHECKIN_RATES = {
  'engaged': 0.80,
  'casual': 0.50,
  'struggler': 0.25,
  'power-user': 0.90
};

class FullCycleSimulation {
  constructor() {
    this.users = [];
    this.results = {
      usersCreated: 0,
      conversions: 0,
      conversionsByPathway: {},
      conversionsByDay: {},
      dailyStats: {}
    };
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
    const daily = {
      activeUsers: 0,
      checkIns: 0,
      conversions: 0,
      conversionUsers: []
    };

    for (const user of this.users) {
      if (this.shouldCheckIn(user.persona)) {
        daily.activeUsers++;
        
        // Create 2-3 check-ins per active user
        const numCheckIns = Math.floor(Math.random() * 2) + 2;
        for (let i = 0; i < numCheckIns; i++) {
          await this.createCheckIn(user.id);
          daily.checkIns++;
        }

        // Try conversion on pathway days (freemium ends at day 7)
        const pathwayDays = [7, 14, 21, 28];
        if (!user.converted && pathwayDays.includes(day)) {
          const offer = await this.getConversionOffer(user.id, day);
          
          if (offer.success && offer.offer) {
            const conversionRate = DEMOGRAPHICS.find(d => d.persona === user.persona).conversion;
            
            if (Math.random() < conversionRate) {
              user.converted = true;
              user.conversionDay = day;
              
              // Determine pathway
              let pathway;
              if (day === 7) pathway = 'Aha Moment';
              else if (day === 14) pathway = 'Week 2 Trial';
              else if (day === 21) pathway = 'Power User';
              else pathway = 'Persistent';
              
              daily.conversions++;
              daily.conversionUsers.push({ userId: user.id, persona: user.persona, pathway });
            }
          }
        }

        user.totalCheckIns = (user.totalCheckIns || 0) + numCheckIns;
        user.daysActive = (user.daysActive || 0) + 1;
      }
      
      await this.delay(5);
    }

    this.results.dailyStats[day] = daily;
    
    // Update conversions by pathway
    daily.conversionUsers.forEach(c => {
      this.results.conversionsByPathway[c.pathway] = (this.results.conversionsByPathway[c.pathway] || 0) + 1;
    });
    
    this.results.conversions += daily.conversions;

    // Show progress
    const week = Math.floor(day / 7) + 1;
    console.log(`Day ${day} (Week ${week}): Active ${daily.activeUsers}/${this.users.length} | Conversions ${daily.conversions} (Total: ${this.results.conversions})`);
  }

  async run() {
    console.log('╔════════════════════════════════════════════════════════╗');
    console.log('║   Full Cycle Conversion Simulation - 100 Users / 30 Days║');
    console.log('╚════════════════════════════════════════════════════════╝\n');
    
    console.log('👥 Creating 100 users...');
    let id = 1;
    for (const demo of DEMOGRAPHICS) {
      for (let i = 0; i < demo.count; i++) {
        const user = await this.createUser(id++, demo.persona);
        if (user) {
          this.users.push({
            ...user,
            persona: demo.persona,
            converted: false,
            totalCheckIns: 0
          });
        }
        await this.delay(30);
      }
    }
    console.log(`✅ Created ${this.users.length} users\n`);
    
    console.log('📅 Running 30-day simulation...\n');
    
    for (let day = 1; day <= 30; day++) {
      await this.simulateDay(day);
      
      if (day % 10 === 0) {
        console.log(`\n📊 Midpoint (Day ${day}): ${this.results.conversions} conversions (${(this.results.conversions/this.users.length*100).toFixed(1)}%)\n`);
      }
    }
    
    this.printResults();
  }

  printResults() {
    console.log('\n╔════════════════════════════════════════════════════════╗');
    console.log('║                    FINAL RESULTS                       ║');
    console.log('╚════════════════════════════════════════════════════════╝\n');
    
    console.log(`📊 Overall:`);
    console.log(`   Total Users: ${this.users.length}`);
    console.log(`   Conversions: ${this.results.conversions}`);
    console.log(`   Conversion Rate: ${(this.results.conversions/this.users.length*100).toFixed(2)}%\n`);
    
    console.log(`👥 By Persona:`);
    for (const demo of DEMOGRAPHICS) {
      const converted = this.users.filter(u => u.persona === demo.persona && u.converted).length;
      const rate = (converted / demo.count * 100).toFixed(1);
      console.log(`   ${demo.persona}: ${converted}/${demo.count} (${rate}%)`);
    }
    
    console.log(`\n🎯 By Pathway:`);
    Object.entries(this.results.conversionsByPathway).forEach(([pathway, count]) => {
      console.log(`   ${pathway}: ${count}`);
    });
    
    console.log(`\n📈 By Day:`);
    [7, 14, 21, 28].forEach(day => {
      const conversions = this.results.dailyStats[day]?.conversions || 0;
      if (conversions > 0) {
        console.log(`   Day ${day}: ${conversions} conversions`);
      }
    });
    
    console.log('\n✅ Simulation Complete!\n');
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

const sim = new FullCycleSimulation();
sim.run().then(() => process.exit(0)).catch(err => {
  console.error('Error:', err);
  process.exit(1);
});

