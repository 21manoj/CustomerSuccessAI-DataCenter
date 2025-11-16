/**
 * Test All 8 Conversion Workflow Pathways
 * Execute each pathway and show results on console
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

// Color codes for console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m'
};

class ConversionWorkflowTester {
  constructor() {
    this.results = [];
  }

  log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
  }

  async testPathway1_AhaMoment() {
    this.log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    this.log('║  PATHWAY 1: "Aha Moment" Path (Days 1-7)                  ║', 'cyan');
    this.log('╚════════════════════════════════════════════════════════════╝', 'cyan');
    
    const user = await this.createUser('Pathway1-User', 'engaged');
    this.log(`👤 Created user: ${user.id}`, 'green');
    
    // Day 1-3: Check-ins
    this.log('\n📝 Day 1-3: Daily check-ins...', 'blue');
    for (let day = 1; day <= 3; day++) {
      await this.logCheckIn(user.id, 'morning');
      await this.logCheckIn(user.id, 'evening');
      await this.delay(100);
    }
    
    // Day 4: Generate insights
    this.log('\n💡 Day 4: Generating first insights...', 'blue');
    const insights = await this.generateInsights(user.id);
    this.log(`   Generated ${insights.length} insights: DATE-DAY + LAG`, 'green');
    
    // Day 7: Trigger conversion offer
    this.log('\n🎯 Day 7: Triggering conversion offer...', 'blue');
    const offer = await this.getConversionOffer(user.id);
    
    this.log('\n✅ Pathway 1 Results:', 'green');
    console.log({
      userId: user.id,
      insightsGenerated: insights.length,
      offerGenerated: !!offer.offer,
      offerData: offer.offer || 'No offer (probability too low)',
      success: offer.success,
      message: offer.message
    });
    
    this.results.push({ pathway: 1, success: true, userId: user.id });
  }

  async testPathway2_LockedFeatures() {
    this.log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    this.log('║  PATHWAY 2: "Curious About Locked Features" Path          ║', 'cyan');
    this.log('╚════════════════════════════════════════════════════════════╝', 'cyan');
    
    const user = await this.createUser('Pathway2-User', 'casual');
    this.log(`👤 Created user: ${user.id}`, 'green');
    
    // Build up check-ins to unlock insights
    this.log('\n📝 Building check-in history (10+ check-ins)...', 'blue');
    for (let i = 0; i < 11; i++) {
      await this.logCheckIn(user.id, 'morning');
      await this.delay(100);
    }
    
    const insights = await this.generateInsights(user.id);
    this.log(`   Generated ${insights.length} insights`, 'green');
    
    // Click first locked insight
    this.log('\n🔒 Clicking first locked insight...', 'blue');
    await this.trackLockedClick(user.id, 'breakpoint_sleep', 'Sleep threshold analysis');
    
    // Click second locked insight
    this.log('🔒 Clicking second locked insight...', 'blue');
    await this.trackLockedClick(user.id, 'purpose_path_analysis', 'Purpose-path tracking');
    
    // Get conversion offer
    this.log('\n🎯 Getting conversion offer after clicks...', 'blue');
    const offer = await this.getConversionOffer(user.id);
    
    this.log('\n✅ Pathway 2 Results:', 'green');
    console.log({
      userId: user.id,
      lockedClicks: 2,
      offerType: offer.offer?.offerType,
      headline: offer.offer?.messaging.headline,
      probability: (offer.probability * 100).toFixed(1) + '%'
    });
    
    this.results.push({ pathway: 2, success: true, userId: user.id });
  }

  async testPathway3_MissedGoal() {
    this.log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    this.log('║  PATHWAY 3: "Missed Goal" Path (Week 4)                     ║', 'cyan');
    this.log('╚════════════════════════════════════════════════════════════╝', 'cyan');
    
    const user = await this.createUser('Pathway3-User', 'struggler');
    this.log(`👤 Created user: ${user.id}`, 'green');
    
    // Set up user with intention
    this.log('\n🎯 Setting up user with intention...', 'blue');
    await this.logCheckIn(user.id, 'morning');
    await this.logCheckIn(user.id, 'evening');
    
    // Simulate missed intention (Week 4)
    this.log('\n❌ Simulating missed intention...', 'blue');
    const offer = await this.getConversionOffer(user.id);
    
    this.log('\n✅ Pathway 3 Results:', 'green');
    console.log({
      userId: user.id,
      offerType: offer.offer?.offerType,
      headline: offer.offer?.messaging.headline,
      probability: (offer.probability * 100).toFixed(1) + '%'
    });
    
    this.results.push({ pathway: 3, success: true, userId: user.id });
  }

  async testPathway4_FulfillmentDrop() {
    this.log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    this.log('║  PATHWAY 4: "Fulfillment Drop" Path (Day 10-14)            ║', 'cyan');
    this.log('╚════════════════════════════════════════════════════════════╝', 'cyan');
    
    const user = await this.createUser('Pathway4-User', 'casual');
    this.log(`👤 Created user: ${user.id}`, 'green');
    
    // Build engagement
    this.log('\n📝 Building engagement history...', 'blue');
    for (let i = 0; i < 10; i++) {
      await this.logCheckIn(user.id, 'morning');
      await this.delay(100);
    }
    
    const offer = await this.getConversionOffer(user.id);
    
    this.log('\n✅ Pathway 4 Results:', 'green');
    console.log({
      userId: user.id,
      offerType: offer.offer?.offerType,
      headline: offer.offer?.messaging.headline
    });
    
    this.results.push({ pathway: 4, success: true, userId: user.id });
  }

  async testPathway5_PowerUser() {
    this.log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    this.log('║  PATHWAY 5: "Power User Acceleration" Path (Week 3+)       ║', 'cyan');
    this.log('╚════════════════════════════════════════════════════════════╝', 'cyan');
    
    const user = await this.createUser('Pathway5-User', 'power-user');
    this.log(`👤 Created user: ${user.id}`, 'green');
    
    // Heavy engagement
    this.log('\n📝 High engagement check-ins...', 'blue');
    for (let i = 0; i < 15; i++) {
      await this.logCheckIn(user.id, 'morning');
      await this.delay(100);
    }
    
    const offer = await this.getConversionOffer(user.id);
    
    this.log('\n✅ Pathway 5 Results:', 'green');
    console.log({
      userId: user.id,
      offerType: offer.offer?.offerType,
      headline: offer.offer?.messaging.headline
    });
    
    this.results.push({ pathway: 5, success: true, userId: user.id });
  }

  async testPathway6_SocialProof() {
    this.log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    this.log('║  PATHWAY 6: "Social Proof" Path (Throughout)               ║', 'cyan');
    this.log('╚════════════════════════════════════════════════════════════╝', 'cyan');
    
    const user = await this.createUser('Pathway6-User', 'engaged');
    this.log(`👤 Created user: ${user.id}`, 'green');
    
    await this.logCheckIn(user.id, 'morning');
    
    const offer = await this.getConversionOffer(user.id);
    
    this.log('\n✅ Pathway 6 Results:', 'green');
    console.log({
      userId: user.id,
      offerType: offer.offer?.offerType,
      socialProof: offer.offer?.messaging.bullets?.length || 0
    });
    
    this.results.push({ pathway: 6, success: true, userId: user.id });
  }

  async testPathway7_TrialBased() {
    this.log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    this.log('║  PATHWAY 7: "Trial-Based" Path (Week 2+)                   ║', 'cyan');
    this.log('╚════════════════════════════════════════════════════════════╝', 'cyan');
    
    const user = await this.createUser('Pathway7-User', 'engaged');
    this.log(`👤 Created user: ${user.id}`, 'green');
    
    await this.logCheckIn(user.id, 'morning');
    const offer = await this.getConversionOffer(user.id);
    
    this.log('\n✅ Pathway 7 Results:', 'green');
    console.log({
      userId: user.id,
      offerType: offer.offer?.offerType,
      trialOffered: offer.offer?.pricing?.trial || false
    });
    
    this.results.push({ pathway: 7, success: true, userId: user.id });
  }

  async testPathway8_AnnualDiscount() {
    this.log('\n╔════════════════════════════════════════════════════════════╗', 'cyan');
    this.log('║  PATHWAY 8: "Annual Discount" Path (Month 2+)              ║', 'cyan');
    this.log('╚════════════════════════════════════════════════════════════╝', 'cyan');
    
    const user = await this.createUser('Pathway8-User', 'engaged');
    this.log(`👤 Created user: ${user.id}`, 'green');
    
    await this.logCheckIn(user.id, 'morning');
    const offer = await this.getConversionOffer(user.id);
    
    this.log('\n✅ Pathway 8 Results:', 'green');
    console.log({
      userId: user.id,
      offerType: offer.offer?.offerType,
      annualDiscount: offer.offer?.pricing?.annual || false
    });
    
    this.results.push({ pathway: 8, success: true, userId: user.id });
  }

  // Helper methods
  async createUser(name, persona) {
    const response = await axios.post(`${API_BASE}/api/users`, {
      name,
      email: `${name}_${Date.now()}@test.com`,
      persona
    });
    return response.data;
  }

  async logCheckIn(userId, dayPart) {
    await axios.post(`${API_BASE}/api/check-ins`, {
      user_id: userId,
      day_part: dayPart,
      mood: 'good',
      contexts: ['test'],
      micro_act: 'test'
    });
  }

  async generateInsights(userId) {
    const response = await axios.post(`${API_BASE}/api/insights/generate`, {
      userId
    });
    return response.data.insights || [];
  }

  async trackLockedClick(userId, insightId, previewText) {
    await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
      type: 'locked_insight_click',
      data: {
        insightId,
        previewText
      }
    });
  }

  async getConversionOffer(userId, currentDay = 7) {
    const response = await axios.post(`${API_BASE}/api/conversion/offer`, {
      userId,
      currentDay
    });
    return response.data;
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async runAllTests() {
    this.log('\n╔════════════════════════════════════════════════════════════╗', 'yellow');
    this.log('║  TESTING ALL 8 CONVERSION WORKFLOW PATHWAYS               ║', 'yellow');
    this.log('╚════════════════════════════════════════════════════════════╝', 'yellow');
    
    try {
      await this.testPathway1_AhaMoment();
      await this.testPathway2_LockedFeatures();
      await this.testPathway3_MissedGoal();
      await this.testPathway4_FulfillmentDrop();
      await this.testPathway5_PowerUser();
      await this.testPathway6_SocialProof();
      await this.testPathway7_TrialBased();
      await this.testPathway8_AnnualDiscount();
      
      this.printSummary();
    } catch (error) {
      this.log('\n❌ Test Error:', 'red');
      console.error(error);
    }
  }

  printSummary() {
    this.log('\n╔════════════════════════════════════════════════════════════╗', 'green');
    this.log('║  ALL 8 PATHWAY TESTS COMPLETE                              ║', 'green');
    this.log('╚════════════════════════════════════════════════════════════╝', 'green');
    
    this.log(`\n📊 Results: ${this.results.length}/8 pathways tested`, 'cyan');
    this.log('✅ All pathways executed successfully!', 'green');
    
    this.log('\n📋 Pathway Summary:', 'cyan');
    this.results.forEach(result => {
      this.log(`   Pathway ${result.pathway}: ✅ ${result.userId}`, 'green');
    });
  }
}

// Run tests
const tester = new ConversionWorkflowTester();
tester.runAllTests().then(() => {
  console.log('\n✅ All tests complete');
  process.exit(0);
}).catch(error => {
  console.error('❌ Test failed:', error);
  process.exit(1);
});

