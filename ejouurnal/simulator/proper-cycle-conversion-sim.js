/**
 * Proper Full Cycle Conversion Simulation
 * Intention → Micro-moves → Check-ins → Insights (Day 3+) → Journals → Conversion Pathways
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

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

class ProperCycleSimulation {
  constructor() {
    this.users = [];
    this.results = {
      conversions: 0,
      conversionsByPathway: {},
      conversionsByPersona: {},
      insightsGenerated: 0,
      journalsGenerated: 0
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

  async generateInsights(userId) {
    try {
      await axios.post(`${API_BASE}/api/insights/generate`, { userId });
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

    for (const user of this.users) {
      if (this.shouldCheckIn(user.persona)) {
        activeUsers++;
        
        // Day 1: Set intention (simulate)
        if (day === 1) {
          user.intention = 'Exercise 3x/week';
          user.intentionDays = 7;
          user.microMovesCompleted = 0;
        }

        // Create check-ins (2-3 per day)
        const numCheckIns = Math.floor(Math.random() * 2) + 2;
        for (let i = 0; i < numCheckIns; i++) {
          await this.createCheckIn(user.id);
        }
        
        user.totalCheckIns = (user.totalCheckIns || 0) + numCheckIns;
        user.daysActive = (user.daysActive || 0) + 1;

        // Day 3+: Generate insights (after sufficient check-ins)
        if (day >= 3 && day <= 7 && user.totalCheckIns >= 6 && Math.random() < 0.5) {
          const generated = await this.generateInsights(user.id);
          if (generated) {
            this.results.insightsGenerated++;
            user.hasInsights = true;
          }
        }

        // Day 7: Conversion attempt (freemium ends)
        if (day === 7 && !user.converted) {
          const offer = await this.getConversionOffer(user.id, 7);
          
          if (offer.success && offer.offer) {
            const rate = DEMOGRAPHICS.find(d => d.persona === user.persona).conversion;
            
            if (Math.random() < rate) {
              user.converted = true;
              user.conversionDay = 7;
              user.conversionPathway = 'Day 7 Aha Moment';
              conversions++;
              this.results.conversionsByPersona[user.persona] = (this.results.conversionsByPersona[user.persona] || 0) + 1;
            }
          }
        }

        // Day 14: Second wave (journals locked behind paywall)
        if (day === 14 && !user.converted) {
          const offer = await this.getConversionOffer(user.id, 14);
          if (offer.success && offer.offer && Math.random() < 0.2) {
            user.converted = true;
            user.conversionDay = 14;
            user.conversionPathway = 'Week 2 Persistent';
            conversions++;
          }
        }
        
        await this.delay(5);
      }
    }

    this.results.conversions += conversions;
    
    // Weekly summary
    if (day % 7 === 0) {
      console.log(`\n📊 Week ${day/7} Summary:`);
      console.log(`   Active Users: ${activeUsers}/${this.users.length}`);
      console.log(`   New Conversions: ${conversions}`);
      console.log(`   Total Conversions: ${this.results.conversions} (${(this.results.conversions/this.users.length*100).toFixed(1)}%)`);
      console.log(`   Insights Generated: ${this.results.insightsGenerated}`);
    }
    
    return { activeUsers, conversions };
  }

  async run() {
    console.log('╔════════════════════════════════════════════════════════╗');
    console.log('║   Proper Cycle Conversion Simulation                   ║');
    console.log('║   100 Users, 30 Days, Full Virtuous Cycle             ║');
    console.log('╚════════════════════════════════════════════════════════╝\n');
    
    console.log('👥 Creating users...');
    let id = 1;
    for (const demo of DEMOGRAPHICS) {
      for (let i = 0; i < demo.count; i++) {
        const user = await this.createUser(id++, demo.persona);
        if (user) {
          this.users.push({
            ...user,
            persona: demo.persona,
            converted: false,
            totalCheckIns: 0,
            daysActive: 0
          });
        }
        await this.delay(20);
      }
    }
    console.log(`✅ Created ${this.users.length} users\n`);
    
    console.log('📅 Simulating 30 days...\n');
    
    for (let day = 1; day <= 30; day++) {
      await this.simulateDay(day);
    }
    
    this.printResults();
  }

  printResults() {
    console.log('\n╔════════════════════════════════════════════════════════╗');
    console.log('║                    FINAL RESULTS                       ║');
    console.log('╚════════════════════════════════════════════════════════╝\n');
    
    console.log(`📊 Conversion Metrics:`);
    console.log(`   Total Users: ${this.users.length}`);
    console.log(`   Conversions: ${this.results.conversions}`);
    console.log(`   Conversion Rate: ${(this.results.conversions/this.users.length*100).toFixed(2)}%\n`);
    console.log(`\n👥 Conversions by Persona:`);
    DEMOGRAPHICS.forEach(demo => {
      const converted = this.results.conversionsByPersona[demo.persona] || 0;
      const rate = (converted / demo.count * 100).toFixed(1);
      console.log(`   ${demo.persona}: ${converted}/${demo.count} (${rate}%)`);
    });
    
    console.log(`\n📈 Content Generated:`);
    console.log(`   Insights: ${this.results.insightsGenerated}`);
    console.log(`   Journals: ${this.results.journalsGenerated}`);
    
    console.log('\n✅ Simulation Complete!\n');
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

const sim = new ProperCycleSimulation();
sim.run().then(() => process.exit(0)).catch(err => {
  console.error('Error:', err);
  process.exit(1);
});

