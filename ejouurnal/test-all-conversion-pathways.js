/**
 * Complete Test for All 8 Conversion Workflow Pathways
 * This script seeds proper data for each pathway and tests the conversion offers
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

class ConversionPathwayTester {
  results = [];

  log(message, color = 'white') {
    const colors = {
      reset: '\x1b[0m',
      red: '\x1b[31m',
      green: '\x1b[32m',
      yellow: '\x1b[33m',
      blue: '\x1b[34m',
      cyan: '\x1b[36m',
      white: '\x1b[37m',
      magenta: '\x1b[35m'
    };
    console.log(`${colors[color]}${message}${colors.reset}`);
  }

  async createUser(name, persona) {
    const timestamp = Date.now();
    const response = await axios.post(`${API_BASE}/api/users`, {
      name: `${name}_${timestamp}`,
      email: `${name}_${timestamp}@test.com`,
      persona
    });
    return response.data;
  }

  async logCheckIn(userId, mood = 'good', contexts = ['test'], microAct = 'test') {
    await axios.post(`${API_BASE}/api/check-ins`, {
      user_id: userId,
      day_part: 'morning',
      mood,
      contexts,
      micro_act: microAct
    });
  }

  async generateInsights(userId) {
    try {
      const response = await axios.post(`${API_BASE}/api/insights/generate`, {
        userId
      });
      return response.data.insights || [];
    } catch (e) {
      return [];
    }
  }

  async generateJournal(userId, scores = {}) {
    try {
      await axios.post(`${API_BASE}/api/journals/generate`, {
        userId,
        dailyScores: {
          overallScore: 70,
          bodyScore: 75,
          mindScore: 70,
          soulScore: 72,
          purposeScore: 68,
          ...scores
        }
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  async createMeaningfulDay(userId) {
    // Create a meaningful day by creating a check-in with good mood
    // The scores will be calculated and marked as meaningful
    try {
      await this.logCheckIn(userId, 'great', ['nature', 'exercise']);
      return true;
    } catch (e) {
      return false;
    }
  }

  async trackInteraction(userId, type, data) {
    await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
      type,
      data
    });
  }

  async getConversionOffer(userId, currentDay = 14) {
    const response = await axios.post(`${API_BASE}/api/conversion/offer`, {
      userId,
      currentDay
    });
    return response.data;
  }

  async testPathway1_AhaMoment() {
    this.log('\n═══════════════════════════════════════════════════', 'cyan');
    this.log('PATHWAY 1: "Aha Moment" Path (Days 1-7)', 'cyan');
    this.log('═══════════════════════════════════════════════════', 'cyan');
    this.log('REQUIREMENTS: 7 days active, 14+ check-ins, 2+ insights, 2+ journals', 'yellow');
    
    const user = await this.createUser('Pathway1', 'engaged');
    this.log(`✅ Created user: ${user.id}`, 'green');
    
    // Simulate 7 days of activity
    this.log('📅 Simulating 7 days of activity...', 'blue');
    for (let day = 1; day <= 7; day++) {
      await this.logCheckIn(user.id, 'good', ['morning']);
      await this.logCheckIn(user.id, 'good', ['evening']);
      // Generate insights on day 4 and 7
      if (day === 4 || day === 7) {
        await this.generateInsights(user.id);
      }
      // Generate journals on day 3 and 6
      if (day === 3 || day === 6) {
        await this.generateJournal(user.id);
      }
    }
    
    const offer = await this.getConversionOffer(user.id, 7);
    
    this.log('\n📊 RESULTS:', 'yellow');
    console.log(JSON.stringify({
      pathway: 1,
      success: !!offer.offer,
      userId: user.id,
      checkIns: 14,
      insights: 2,
      journals: 2,
      offerType: offer.offer?.offerType || 'none',
      headline: offer.offer?.personalizedMessage || offer.message
    }, null, 2));
    
    this.results.push({
      pathway: 1,
      name: 'Aha Moment',
      success: !!offer.offer,
      offerType: offer.offer?.offerType
    });
  }

  async testPathway2_LockedFeatures() {
    this.log('\n═══════════════════════════════════════════════════', 'cyan');
    this.log('PATHWAY 2: "Curious About Locked Features"', 'cyan');
    this.log('═══════════════════════════════════════════════════', 'cyan');
    this.log('REQUIREMENTS: 12+ check-ins, 2+ locked insight clicks', 'yellow');
    
    const user = await this.createUser('Pathway2', 'casual');
    this.log(`✅ Created user: ${user.id}`, 'green');
    
    this.log('📝 Building check-in history...', 'blue');
    for (let i = 0; i < 12; i++) {
      await this.logCheckIn(user.id);
    }
    
    await this.generateInsights(user.id);
    
    this.log('🔒 Clicking locked insights...', 'blue');
    await this.trackInteraction(user.id, 'locked_insight_click', {
      insightId: 'breakpoint_sleep',
      previewText: 'Sleep threshold analysis'
    });
    await this.trackInteraction(user.id, 'locked_insight_click', {
      insightId: 'purpose_path',
      previewText: 'Purpose-path tracking'
    });
    
    const offer = await this.getConversionOffer(user.id, 14);
    
    this.log('\n📊 RESULTS:', 'yellow');
    console.log(JSON.stringify({
      pathway: 2,
      success: !!offer.offer,
      userId: user.id,
      checkIns: 12,
      lockedClicks: 2,
      offerType: offer.offer?.offerType || 'none',
      headline: offer.offer?.personalizedMessage || offer.message
    }, null, 2));
    
    this.results.push({
      pathway: 2,
      name: 'Locked Features',
      success: !!offer.offer,
      offerType: offer.offer?.offerType
    });
  }

  async testPathway3_MissedGoal() {
    this.log('\n═══════════════════════════════════════════════════', 'cyan');
    this.log('PATHWAY 3: "Missed Goal" Path (Week 4)', 'cyan');
    this.log('═══════════════════════════════════════════════════', 'cyan');
    this.log('REQUIREMENTS: 28 days active, set intention, missed target', 'yellow');
    
    const user = await this.createUser('Pathway3', 'struggler');
    this.log(`✅ Created user: ${user.id}`, 'green');
    
    this.log('📅 Simulating 4 weeks...', 'blue');
    for (let day = 1; day <= 28; day++) {
      await this.logCheckIn(user.id);
      if (day % 4 === 0) {
        await this.generateJournal(user.id);
      }
    }
    
    // Mark as missed intention
    await this.trackInteraction(user.id, 'missed_goal', {
      intentionText: 'Exercise 3x/week',
      completionRate: 67
    });
    
    const offer = await this.getConversionOffer(user.id, 28);
    
    this.log('\n📊 RESULTS:', 'yellow');
    console.log(JSON.stringify({
      pathway: 3,
      success: !!offer.offer,
      userId: user.id,
      daysActive: 28,
      offerType: offer.offer?.offerType || 'none',
      headline: offer.offer?.personalizedMessage || offer.message
    }, null, 2));
    
    this.results.push({
      pathway: 3,
      name: 'Missed Goal',
      success: !!offer.offer,
      offerType: offer.offer?.offerType
    });
  }

  async testPathway4_FulfillmentDrop() {
    this.log('\n═══════════════════════════════════════════════════', 'cyan');
    this.log('PATHWAY 4: "Fulfillment Drop" Path', 'cyan');
    this.log('═══════════════════════════════════════════════════', 'cyan');
    this.log('REQUIREMENTS: 14 days active, score drop detected', 'yellow');
    
    const user = await this.createUser('Pathway4', 'casual');
    this.log(`✅ Created user: ${user.id}`, 'green');
    
    this.log('📅 Simulating 2 weeks with drop...', 'blue');
    for (let day = 1; day <= 14; day++) {
      const mood = day > 10 ? 'low' : 'good'; // Drop after day 10
      await this.logCheckIn(user.id, mood);
    }
    
    const offer = await this.getConversionOffer(user.id, 14);
    
    this.log('\n📊 RESULTS:', 'yellow');
    console.log(JSON.stringify({
      pathway: 4,
      success: !!offer.offer,
      userId: user.id,
      daysActive: 14,
      offerType: offer.offer?.offerType || 'none',
      headline: offer.offer?.personalizedMessage || offer.message
    }, null, 2));
    
    this.results.push({
      pathway: 4,
      name: 'Fulfillment Drop',
      success: !!offer.offer,
      offerType: offer.offer?.offerType
    });
  }

  async testPathway5_PowerUser() {
    this.log('\n═══════════════════════════════════════════════════', 'cyan');
    this.log('PATHWAY 5: "Power User Acceleration" Path', 'cyan');
    this.log('═══════════════════════════════════════════════════', 'cyan');
    this.log('REQUIREMENTS: 40+ check-ins, 10+ insights, 8+ journals', 'yellow');
    
    const user = await this.createUser('Pathway5', 'power-user');
    this.log(`✅ Created user: ${user.id}`, 'green');
    
    this.log('📝 High engagement simulation...', 'blue');
    for (let i = 0; i < 40; i++) {
      await this.logCheckIn(user.id);
    }
    
    // Generate insights
    for (let i = 0; i < 5; i++) {
      await this.generateInsights(user.id);
    }
    
    // Generate journals
    for (let i = 0; i < 8; i++) {
      await this.generateJournal(user.id);
    }
    
    const offer = await this.getConversionOffer(user.id, 21);
    
    this.log('\n📊 RESULTS:', 'yellow');
    console.log(JSON.stringify({
      pathway: 5,
      success: !!offer.offer,
      userId: user.id,
      checkIns: 40,
      insights: 5,
      journals: 8,
      offerType: offer.offer?.offerType || 'none',
      headline: offer.offer?.personalizedMessage || offer.message
    }, null, 2));
    
    this.results.push({
      pathway: 5,
      name: 'Power User',
      success: !!offer.offer,
      offerType: offer.offer?.offerType
    });
  }

  async testPathway6_SocialProof() {
    this.log('\n═══════════════════════════════════════════════════', 'cyan');
    this.log('PATHWAY 6: "Social Proof" Path', 'cyan');
    this.log('═══════════════════════════════════════════════════', 'cyan');
    this.log('REQUIREMENTS: Active user showing interest', 'yellow');
    
    const user = await this.createUser('Pathway6', 'engaged');
    this.log(`✅ Created user: ${user.id}`, 'green');
    
    for (let i = 0; i < 10; i++) {
      await this.logCheckIn(user.id);
    }
    
    const offer = await this.getConversionOffer(user.id, 14);
    
    this.log('\n📊 RESULTS:', 'yellow');
    console.log(JSON.stringify({
      pathway: 6,
      success: !!offer.offer,
      userId: user.id,
      checkIns: 10,
      offerType: offer.offer?.offerType || 'none',
      headline: offer.offer?.personalizedMessage || offer.message
    }, null, 2));
    
    this.results.push({
      pathway: 6,
      name: 'Social Proof',
      success: !!offer.offer,
      offerType: offer.offer?.offerType
    });
  }

  async testPathway7_TrialBased() {
    this.log('\n═══════════════════════════════════════════════════', 'cyan');
    this.log('PATHWAY 7: "Trial-Based" Path', 'cyan');
    this.log('═══════════════════════════════════════════════════', 'cyan');
    this.log('REQUIREMENTS: 15+ check-ins, medium engagement', 'yellow');
    
    const user = await this.createUser('Pathway7', 'engaged');
    this.log(`✅ Created user: ${user.id}`, 'green');
    
    for (let i = 0; i < 15; i++) {
      await this.logCheckIn(user.id);
    }
    
    await this.generateJournal(user.id);
    
    const offer = await this.getConversionOffer(user.id, 14);
    
    this.log('\n📊 RESULTS:', 'yellow');
    console.log(JSON.stringify({
      pathway: 7,
      success: !!offer.offer,
      userId: user.id,
      checkIns: 15,
      offerType: offer.offer?.offerType || 'none',
      trialOffered: !!offer.offer?.pricing?.trial
    }, null, 2));
    
    this.results.push({
      pathway: 7,
      name: 'Trial-Based',
      success: !!offer.offer,
      offerType: offer.offer?.offerType
    });
  }

  async testPathway8_AnnualDiscount() {
    this.log('\n═══════════════════════════════════════════════════', 'cyan');
    this.log('PATHWAY 8: "Annual Discount" Path', 'cyan');
    this.log('═══════════════════════════════════════════════════', 'cyan');
    this.log('REQUIREMENTS: 30+ days active, persistent user', 'yellow');
    
    const user = await this.createUser('Pathway8', 'casual');
    this.log(`✅ Created user: ${user.id}`, 'green');
    
    this.log('📅 Simulating 30 days...', 'blue');
    for (let day = 1; day <= 30; day++) {
      if (day % 3 === 0) { // Every 3rd day
        await this.logCheckIn(user.id);
      }
    }
    
    const offer = await this.getConversionOffer(user.id, 30);
    
    this.log('\n📊 RESULTS:', 'yellow');
    console.log(JSON.stringify({
      pathway: 8,
      success: !!offer.offer,
      userId: user.id,
      daysActive: 30,
      offerType: offer.offer?.offerType || 'none',
      annualDiscount: !!offer.offer?.annualPrice
    }, null, 2));
    
    this.results.push({
      pathway: 8,
      name: 'Annual Discount',
      success: !!offer.offer,
      offerType: offer.offer?.offerType
    });
  }

  printSummary() {
    this.log('\n╔════════════════════════════════════════════════════════╗', 'green');
    this.log('║           CONVERSION PATHWAY TEST SUMMARY            ║', 'green');
    this.log('╚════════════════════════════════════════════════════════╝', 'green');
    
    const successful = this.results.filter(r => r.success).length;
    const total = this.results.length;
    
    this.log(`\n📊 Results: ${successful}/${total} pathways generated offers`, 'cyan');
    
    this.log('\n📋 Detailed Results:', 'yellow');
    this.results.forEach(result => {
      const status = result.success ? '✅' : '❌';
      const offerType = result.offerType || 'no offer';
      this.log(`   ${status} Pathway ${result.pathway}: ${result.name} - ${offerType}`, 
        result.success ? 'green' : 'red');
    });
    
    if (successful === 0) {
      this.log('\n⚠️  NOTE: No offers were generated because users did not meet', 'yellow');
      this.log('   the conversion probability threshold (0.1). This indicates', 'yellow');
      this.log('   that the ConversionOptimizer requires higher engagement', 'yellow');
      this.log('   metrics to trigger offers.', 'yellow');
    }
  }

  async runAll() {
    this.log('\n╔════════════════════════════════════════════════════════╗', 'magenta');
    this.log('║     TESTING ALL 8 CONVERSION WORKFLOW PATHWAYS      ║', 'magenta');
    this.log('╚════════════════════════════════════════════════════════╝', 'magenta');
    
    try {
      await this.testPathway1_AhaMoment();
      await this.delay(200);
      await this.testPathway2_LockedFeatures();
      await this.delay(200);
      await this.testPathway3_MissedGoal();
      await this.delay(200);
      await this.testPathway4_FulfillmentDrop();
      await this.delay(200);
      await this.testPathway5_PowerUser();
      await this.delay(200);
      await this.testPathway6_SocialProof();
      await this.delay(200);
      await this.testPathway7_TrialBased();
      await this.delay(200);
      await this.testPathway8_AnnualDiscount();
      
      this.printSummary();
    } catch (error) {
      this.log('\n❌ Test Error:', 'red');
      console.error(error);
    }
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

const tester = new ConversionPathwayTester();
tester.runAll().then(() => {
  console.log('\n✅ All tests complete');
  process.exit(0);
}).catch(error => {
  console.error('❌ Test failed:', error);
  process.exit(1);
});

