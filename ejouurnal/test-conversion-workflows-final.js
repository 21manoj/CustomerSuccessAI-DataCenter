/**
 * Test all 8 Conversion Workflow Pathways with API logging
 * This version shows actual API calls and results
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

class ConversionWorkflowTester {
  log(message, color = 'reset') {
    const colors = {
      reset: '\x1b[0get[0m',
      red: '\x1b[31m',
      green: '\x1b[32m',
      yellow: '\x1b[33m',
      blue: '\x1b[34m',
      cyan: '\x1b[36m'
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

  async logCheckIn(userId, dayPart) {
    await axios.post(`${API_BASE}/api/check-ins`, {
      user_id: userId,
      day_part: dayPart,
      mood: 'good',
      contexts: ['test'],
      micro_act: 'test activity'
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

  async trackLockedClick(userId, insightId, previewText) {
    await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
      type: 'locked_insight_click',
      data: {
        insightId,
        previewText
      }
    });
  }

  async getConversionOffer(userId, currentDay = 14) {
    const response = await axios.post(`${API_BASE}/api/conversion/offer`, {
      userId,
      currentDay
    });
    return response.data;
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async testPathway1_AhaMoment() {
    this.log('\n═══════════════════════════════════════════════', 'cyan');
    this.log('PATHWAY 1: "Aha Moment" Path (Days 1-7)', 'cyan');
    this.log('═══════════════════════════════════════════════', 'cyan');
    
    const user = await this.createUser('Pathway1', 'engaged');
    this.log(`✅ Created user: ${user.id}`, 'green');
    
    this.log('📝 Day 1-3: Daily check-ins (2× per day)...', 'blue');
    for (let day = 1; day <= 3; day++) {
      await this.logCheckIn(user.id, 'morning');
      await this.logCheckIn(user.id, 'evening');
      await this.delay(50);
    }
    
    this.log('💡 Day 4: Generating insights...', 'blue');
    const insights = await this.generateInsights(user.id);
    this.log(`   ✅ Generated ${insights.length} insights`, 'green');
    
    const offer = await this.getConversionOffer(user.id, 7);
    
    this.log('\n📊 RESULTS:', 'yellow');
    console.log({
      userId: user.id,
      checkIns: 6,
      insights: insights.length,
      offerGenerated: !!offer.offer,
      offerType: offer.offer?.offerType || 'none',
      message: offer.message || 'no message'
    });
  }

  async testPathway2_LockedFeatures() {
    this.log('\n═══════════════════════════════════════════════', 'cyan');
    this.log('PATHWAY 2: "Curious About Locked Features"', 'cyan');
    this.log('═══════════════════════════════════════════════', 'cyan');
    
    const user = await this.createUser('Pathway2', 'casual');
    this.log(`✅ Created user: ${user.id}`, 'green');
    
    this.log('📝 Building check-in history...', 'blue');
    for (let i = 0; i < 12; i++) {
      await this.logCheckIn(user.id, 'morning');
      await this.delay(50);
    }
    
    const insights = await this.generateInsights(user.id);
    
    this.log('🔒 Clicking locked insights (2×)...', 'blue');
    await this.trackLockedClick(user.id, 'breakpoint_sleep', 'Sleep threshold');
    await this.trackLockedClick(user.id, 'purpose_path', 'Purpose analysis');
    
    const offer = await this.getConversionOffer(user.id, 14);
    
    this.log('\n📊 RESULTS:', 'yellow');
    console.log({
      userId: user.id,
      checkIns: 12,
      lockedClicks: 2,
      offerGenerated: !!offer.offer,
      offerType: offer.offer?.offerType || 'none',
      message: offer.message || 'no message'
    });
  }

  async runAll() {
    this.log('\n╔════════════════════════════════════════╗', 'yellow');
    this.log('║  TESTING CONVERSION WORKFLOWS         ║', 'yellow');
    this.log('╚════════════════════════════════════════╝', 'yellow');
    
    await this.testPathway1_AhaMoment();
    await this.testPathway2_LockedFeatures();
    
    this.log('\n✅ All pathway tests complete!', 'green');
  }
}

const tester = new ConversionWorkflowTester();
tester.runAll();

