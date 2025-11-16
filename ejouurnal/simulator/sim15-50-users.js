const axios = require('axios');

const API_BASE = 'http://localhost:3005';
const MAX_USERS = 50;
const SIMULATION_DAYS = 7;
const RATE_LIMIT_DELAY = 200; // 200ms between requests

// User personas distribution
const PERSONAS = {
  'struggler': 0.3,    // 30% - Low engagement, high churn risk
  'casual': 0.4,       // 40% - Moderate engagement
  'engaged': 0.25,     // 25% - High engagement
  'premium': 0.05      // 5% - Already premium users
};

// Churn rates by persona
const CHURN_RATES = {
  'struggler': 0.4,    // 40% churn rate
  'casual': 0.2,       // 20% churn rate
  'engaged': 0.1,      // 10% churn rate
  'premium': 0.05      // 5% churn rate
};

class Sim15Runner {
  constructor() {
    this.users = [];
    this.stats = {
      totalUsers: 0,
      activeUsers: 0,
      churnedUsers: 0,
      totalCheckIns: 0,
      totalJournals: 0,
      totalInsights: 0,
      totalDetails: 0,
      conversionOffers: 0,
      premiumConversions: 0,
      errors: 0,
      startTime: Date.now()
    };
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  getRandomPersona() {
    const rand = Math.random();
    let cumulative = 0;
    for (const [persona, probability] of Object.entries(PERSONAS)) {
      cumulative += probability;
      if (rand <= cumulative) {
        return persona;
      }
    }
    return 'casual';
  }

  async createUser(index) {
    try {
      const persona = this.getRandomPersona();
      const userData = {
        name: `User_${index}`,
        email: `user${index}@example.com`,
        persona: persona
      };

      const response = await axios.post(`${API_BASE}/api/users`, userData);
      const user = {
        id: response.data.id,
        name: userData.name,
        email: userData.email,
        persona: persona,
        checkIns: 0,
        journals: 0,
        insights: 0,
        details: 0,
        isChurned: false,
        churnDay: null,
        lastActivity: 0
      };

      this.users.push(user);
      this.stats.totalUsers++;
      this.stats.activeUsers++;

      console.log(`👤 Created user ${index + 1}/${MAX_USERS}: ${user.id} (${persona})`);
      return user;
    } catch (error) {
      console.error(`❌ Failed to create user ${index + 1}:`, error.response?.data || error.message);
      this.stats.errors++;
      return null;
    }
  }

  async createCheckIn(user, day) {
    try {
      const dayParts = ['morning', 'day', 'evening', 'night'];
      const moods = ['very-low', 'low', 'neutral', 'good', 'great'];
      const contexts = [['work'], ['social'], ['family'], ['health']];
      const microActs = ['gratitude', 'meditation', 'walk', 'breathing', 'journaling'];

      const dayPart = dayParts[Math.floor(Math.random() * dayParts.length)];
      const mood = moods[Math.floor(Math.random() * moods.length)];
      const context = contexts[Math.floor(Math.random() * contexts.length)];
      const microAct = Math.random() < 0.7 ? microActs[Math.floor(Math.random() * microActs.length)] : null;

      const checkInData = {
        user_id: user.id,
        daypart: dayPart,
        mood: mood,
        contexts: context,
        micro_act: microAct,
        purpose_progress: dayPart === 'night' ? (Math.random() < 0.6 ? 'yes' : 'partly') : null
      };

      await axios.post(`${API_BASE}/api/check-ins`, checkInData);
      user.checkIns++;
      this.stats.totalCheckIns++;

      console.log(`  ✅ Check-in: ${dayPart} (${mood})`);
      return true;
    } catch (error) {
      console.error(`  ❌ Check-in failed:`, error.response?.data || error.message);
      this.stats.errors++;
      return false;
    }
  }

  async createDetails(user, day) {
    try {
      const detailsData = {
        userId: user.id,
        sleepHours: Math.floor(Math.random() * 4) + 6, // 6-9 hours
        sleepQuality: Math.floor(Math.random() * 5) + 1, // 1-5
        exerciseMinutes: Math.floor(Math.random() * 60) + 15, // 15-75 minutes
        exerciseType: ['cardio', 'strength', 'yoga', 'walking'][Math.floor(Math.random() * 4)],
        meals: Math.floor(Math.random() * 2) + 2, // 2-3 meals
        waterGlasses: Math.floor(Math.random() * 6) + 4, // 4-9 glasses
        stressLevel: Math.floor(Math.random() * 5) + 1, // 1-5
        energyLevel: Math.floor(Math.random() * 5) + 1, // 1-5
        mood: ['very-low', 'low', 'neutral', 'good', 'great'][Math.floor(Math.random() * 5)]
      };

      await axios.post(`${API_BASE}/api/details`, detailsData);
      user.details++;
      this.stats.totalDetails++;

      console.log(`  ✅ Details: ${detailsData.sleepHours}h sleep, ${detailsData.exerciseMinutes}min exercise`);
      return true;
    } catch (error) {
      console.error(`  ❌ Details failed:`, error.response?.data || error.message);
      this.stats.errors++;
      return false;
    }
  }

  async generateJournal(user, day) {
    try {
      const journalData = {
        user_id: user.id,
        journalTone: ['reflective', 'celebratory', 'insightful'][Math.floor(Math.random() * 3)]
      };

      await axios.post(`${API_BASE}/api/journals/generate`, journalData);
      user.journals++;
      this.stats.totalJournals++;

      console.log(`  ✅ Journal: ${journalData.journalTone} tone`);
      return true;
    } catch (error) {
      console.error(`  ❌ Journal failed:`, error.response?.data || error.message);
      this.stats.errors++;
      return false;
    }
  }

  async generateInsights(user, day) {
    try {
      const insightsData = {
        user_id: user.id
      };

      await axios.post(`${API_BASE}/api/insights/generate`, insightsData);
      user.insights++;
      this.stats.totalInsights++;

      console.log(`  ✅ Insights generated`);
      return true;
    } catch (error) {
      console.error(`  ❌ Insights failed:`, error.response?.data || error.message);
      this.stats.errors++;
      return false;
    }
  }

  async testConversionFeatures(user, day) {
    try {
      // Test conversion calculation
      const conversionResponse = await axios.post(`${API_BASE}/api/conversion/calculate`, {
        userId: user.id,
        currentDay: day
      });

      if (conversionResponse.data.isReadyForConversion) {
        // Test conversion offer
        const offerResponse = await axios.post(`${API_BASE}/api/conversion/offer`, {
          userId: user.id,
          currentDay: day
        });

        this.stats.conversionOffers++;
        console.log(`  🎯 Conversion offer: ${offerResponse.data.offerType}`);
      }

      // Test onboarding flow
      const onboardingResponse = await axios.post(`${API_BASE}/api/onboarding/flow`, {
        userId: user.id
      });

      // Test value proposition
      const valuePropResponse = await axios.post(`${API_BASE}/api/value-proposition`, {
        userId: user.id,
        context: { day: day, persona: user.persona }
      });

      return true;
    } catch (error) {
      console.error(`  ❌ Conversion features failed:`, error.response?.data || error.message);
      this.stats.errors++;
      return false;
    }
  }

  shouldChurn(user, day) {
    if (user.isChurned) return false;
    
    const churnRate = CHURN_RATES[user.persona];
    const daysSinceLastActivity = day - user.lastActivity;
    
    // Higher churn probability if inactive for multiple days
    const adjustedChurnRate = churnRate + (daysSinceLastActivity * 0.05);
    
    return Math.random() < adjustedChurnRate;
  }

  async runSimulation() {
    console.log('🚀 Starting SIM15 - 50 Users Simulation');
    console.log('==========================================');
    console.log(`👥 Users: ${MAX_USERS}`);
    console.log(`📅 Days: ${SIMULATION_DAYS}`);
    console.log(`⏱️  Delay: ${RATE_LIMIT_DELAY}ms between requests`);
    console.log('');

    // Create users
    console.log('👤 Creating users...');
    for (let i = 0; i < MAX_USERS; i++) {
      await this.createUser(i);
      await this.delay(RATE_LIMIT_DELAY);
    }

    console.log(`\n✅ Created ${this.stats.totalUsers} users`);
    console.log('');

    // Run daily activities
    for (let day = 1; day <= SIMULATION_DAYS; day++) {
      console.log(`📅 Day ${day}/${SIMULATION_DAYS}`);
      console.log('==================');

      const activeUsers = this.users.filter(u => !u.isChurned);
      console.log(`👥 Active users: ${activeUsers.length}`);

      for (const user of activeUsers) {
        console.log(`\n👤 ${user.name} (${user.persona})`);

        // Check for churn
        if (this.shouldChurn(user, day)) {
          user.isChurned = true;
          user.churnDay = day;
          this.stats.churnedUsers++;
          this.stats.activeUsers--;
          console.log(`  💔 User churned (Day ${day})`);
          continue;
        }

        // Daily activities based on persona
        const activityProbability = {
          'struggler': 0.3,
          'casual': 0.6,
          'engaged': 0.8,
          'premium': 0.9
        };

        const shouldBeActive = Math.random() < activityProbability[user.persona];
        
        if (shouldBeActive) {
          user.lastActivity = day;

          // Check-in (always if active)
          await this.createCheckIn(user, day);
          await this.delay(RATE_LIMIT_DELAY);

          // Details (70% chance)
          if (Math.random() < 0.7) {
            await this.createDetails(user, day);
            await this.delay(RATE_LIMIT_DELAY);
          }

          // Journal (50% chance for engaged/premium, 30% for others)
          const journalChance = user.persona === 'engaged' || user.persona === 'premium' ? 0.5 : 0.3;
          if (Math.random() < journalChance) {
            await this.generateJournal(user, day);
            await this.delay(RATE_LIMIT_DELAY);
          }

          // Insights (30% chance for engaged/premium)
          const insightsChance = user.persona === 'engaged' || user.persona === 'premium' ? 0.3 : 0.1;
          if (Math.random() < insightsChance) {
            await this.generateInsights(user, day);
            await this.delay(RATE_LIMIT_DELAY);
          }

          // Test conversion features (every 3 days)
          if (day % 3 === 0) {
            await this.testConversionFeatures(user, day);
            await this.delay(RATE_LIMIT_DELAY);
          }
        } else {
          console.log(`  😴 User inactive today`);
        }
      }

      console.log(`\n📊 Day ${day} Summary:`);
      console.log(`  👥 Active: ${this.stats.activeUsers}`);
      console.log(`  💔 Churned: ${this.stats.churnedUsers}`);
      console.log(`  📝 Check-ins: ${this.stats.totalCheckIns}`);
      console.log(`  📖 Journals: ${this.stats.totalJournals}`);
      console.log(`  💡 Insights: ${this.stats.totalInsights}`);
      console.log(`  📋 Details: ${this.stats.totalDetails}`);
      console.log(`  🎯 Conversion offers: ${this.stats.conversionOffers}`);
      console.log(`  ❌ Errors: ${this.stats.errors}`);
      console.log('');
    }

    // Final analytics
    await this.showFinalAnalytics();
  }

  async showFinalAnalytics() {
    console.log('📊 SIM15 Final Analytics');
    console.log('========================');

    const duration = (Date.now() - this.stats.startTime) / 1000;
    const churnedUsers = this.users.filter(u => u.isChurned);
    const activeUsers = this.users.filter(u => !u.isChurned);

    console.log(`⏱️  Duration: ${duration.toFixed(1)}s`);
    console.log(`👥 Total Users: ${this.stats.totalUsers}`);
    console.log(`✅ Active Users: ${this.stats.activeUsers}`);
    console.log(`💔 Churned Users: ${this.stats.churnedUsers}`);
    console.log(`📈 Churn Rate: ${((this.stats.churnedUsers / this.stats.totalUsers) * 100).toFixed(1)}%`);
    console.log('');

    console.log(`📝 Total Check-ins: ${this.stats.totalCheckIns}`);
    console.log(`📖 Total Journals: ${this.stats.totalJournals}`);
    console.log(`💡 Total Insights: ${this.stats.totalInsights}`);
    console.log(`📋 Total Details: ${this.stats.totalDetails}`);
    console.log(`🎯 Conversion Offers: ${this.stats.conversionOffers}`);
    console.log(`❌ Total Errors: ${this.stats.errors}`);
    console.log('');

    // Persona breakdown
    const personaStats = {};
    this.users.forEach(user => {
      if (!personaStats[user.persona]) {
        personaStats[user.persona] = { total: 0, active: 0, churned: 0 };
      }
      personaStats[user.persona].total++;
      if (user.isChurned) {
        personaStats[user.persona].churned++;
      } else {
        personaStats[user.persona].active++;
      }
    });

    console.log('👥 Persona Breakdown:');
    Object.entries(personaStats).forEach(([persona, stats]) => {
      const churnRate = ((stats.churned / stats.total) * 100).toFixed(1);
      console.log(`  ${persona}: ${stats.total} total, ${stats.active} active, ${stats.churned} churned (${churnRate}% churn)`);
    });
    console.log('');

    // Activity rates
    const avgCheckInsPerUser = (this.stats.totalCheckIns / this.stats.totalUsers).toFixed(1);
    const avgJournalsPerUser = (this.stats.totalJournals / this.stats.totalUsers).toFixed(1);
    const avgInsightsPerUser = (this.stats.totalInsights / this.stats.totalUsers).toFixed(1);

    console.log('📊 Activity Rates:');
    console.log(`  📝 Avg Check-ins per user: ${avgCheckInsPerUser}`);
    console.log(`  📖 Avg Journals per user: ${avgJournalsPerUser}`);
    console.log(`  💡 Avg Insights per user: ${avgInsightsPerUser}`);
    console.log(`  🎯 Conversion offer rate: ${((this.stats.conversionOffers / this.stats.totalUsers) * 100).toFixed(1)}%`);
    console.log('');

    // Error rate
    const errorRate = ((this.stats.errors / (this.stats.totalCheckIns + this.stats.totalJournals + this.stats.totalInsights + this.stats.totalDetails)) * 100).toFixed(2);
    console.log(`❌ Error Rate: ${errorRate}%`);
    console.log('');

    console.log('🎉 SIM15 Simulation Complete!');
  }
}

// Run simulation
const sim = new Sim15Runner();
sim.runSimulation().catch(console.error);
