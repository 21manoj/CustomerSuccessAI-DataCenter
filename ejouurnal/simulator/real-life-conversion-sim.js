/**
 * REAL LIFE CONVERSION SIMULATION
 * ==================================
 * Implements full virtuous cycle with:
 * - 28-day conversion window (not just day 7)
 * - Progressive locked feature exposure
 * - User churn and engagement decay
 * - All conversion triggers (missed intentions, score drops, etc.)
 * - Realistic 4x/day check-in patterns
 * - Weekly rituals and insight generation
 * - Time-based conversion windows
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

// More realistic persona distribution
const DEMOGRAPHICS = [
  { persona: 'power-user', count: 10, baseConversion: 0.60 },    // 10% - highly engaged
  { persona: 'engaged', count: 30, baseConversion: 0.35 },       // 30% - good engagement
  { persona: 'casual', count: 40, baseConversion: 0.15 },        // 40% - sporadic use
  { persona: 'struggler', count: 15, baseConversion: 0.05 },     // 15% - low engagement
  { persona: 'churner', count: 5, baseConversion: 0.01 }         // 5% - will abandon
];

// Realistic check-in patterns (4x/day target)
const CHECKIN_PATTERNS = {
  'power-user': {
    week1: { rate: 0.95, avgPerDay: 3.8 },
    week2: { rate: 0.93, avgPerDay: 3.7 },
    week3: { rate: 0.90, avgPerDay: 3.6 },
    week4: { rate: 0.88, avgPerDay: 3.5 }
  },
  'engaged': {
    week1: { rate: 0.85, avgPerDay: 3.0 },
    week2: { rate: 0.80, avgPerDay: 2.8 },
    week3: { rate: 0.75, avgPerDay: 2.5 },
    week4: { rate: 0.70, avgPerDay: 2.2 }
  },
  'casual': {
    week1: { rate: 0.70, avgPerDay: 2.0 },
    week2: { rate: 0.60, avgPerDay: 1.8 },
    week3: { rate: 0.50, avgPerDay: 1.5 },
    week4: { rate: 0.40, avgPerDay: 1.2 }
  },
  'struggler': {
    week1: { rate: 0.50, avgPerDay: 1.5 },
    week2: { rate: 0.35, avgPerDay: 1.2 },
    week3: { rate: 0.25, avgPerDay: 0.8 },
    week4: { rate: 0.15, avgPerDay: 0.5 }
  },
  'churner': {
    week1: { rate: 0.40, avgPerDay: 1.0 },
    week2: { rate: 0.20, avgPerDay: 0.5 },
    week3: { rate: 0.05, avgPerDay: 0.2 },
    week4: { rate: 0.01, avgPerDay: 0.1 }
  }
};

// Progressive locked feature exposure (increases over time)
const LOCKED_FEATURE_EXPOSURE = {
  week1: 0.0,   // No locked features week 1 (hook phase)
  week2: 0.2,   // Start showing locked features
  week3: 0.5,   // More aggressive teasing
  week4: 0.7    // Peak frustration = buying signal
};

// Conversion probability multipliers by week
const CONVERSION_WEEK_MULTIPLIER = {
  week1: 0.3,   // Too early
  week2: 0.7,   // Starting to see value
  week3: 1.0,   // Good conversion window
  week4: 1.3    // Peak conversion (after intention review)
};

class RealLifeSimulation {
  constructor() {
    this.users = [];
    this.results = {
      totalConversions: 0,
      conversionsByPersona: {},
      conversionsByWeek: { week1: 0, week2: 0, week3: 0, week4: 0 },
      conversionsByTrigger: {},
      totalCheckIns: 0,
      totalInsights: 0,
      totalLockedClicks: 0,
      totalJournalReads: 0,
      churnedUsers: 0,
      conversionDetails: []
    };
    this.currentDay = 0;
  }

  log(message, color = 'white') {
    const colors = {
      reset: '\x1b[0m',
      bright: '\x1b[1m',
      dim: '\x1b[2m',
      red: '\x1b[31m',
      green: '\x1b[32m',
      yellow: '\x1b[33m',
      blue: '\x1b[34m',
      magenta: '\x1b[35m',
      cyan: '\x1b[36m',
      white: '\x1b[37m'
    };
    console.log(`${colors[color]}${message}${colors.reset}`);
  }

  // ============= API HELPERS =============
  
  async createUser(id, persona) {
    try {
      const ts = Date.now() + Math.random() * 1000;
      const response = await axios.post(`${API_BASE}/api/users`, {
        name: `User_${persona}_${id}`,
        email: `user${id}_${ts}@simulation.test`,
        persona
      });
      return response.data;
    } catch (error) {
      this.log(`   ⚠️  Failed to create user ${id}: ${error.message}`, 'red');
      return null;
    }
  }

  async createCheckIn(userId, dayPart, mood) {
    try {
      await axios.post(`${API_BASE}/api/check-ins`, {
        user_id: userId,
        day_part: dayPart,
        mood,
        contexts: this.randomContexts(),
        micro_act: this.randomMicroAct()
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  async setIntention(userId, intention) {
    try {
      await axios.post(`${API_BASE}/api/intentions`, {
        user_id: userId,
        intention,
        micro_moves: ['Morning exercise', 'Meal prep', 'Evening walk']
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

  async generateJournal(userId) {
    try {
      await axios.post(`${API_BASE}/api/journals/generate`, { userId });
      return true;
    } catch (e) {
      return false;
    }
  }

  async clickLockedInsight(userId, insightType) {
    try {
      await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
        type: 'locked_insight_click',
        data: { 
          insightType, 
          timestamp: new Date().toISOString(),
          day: this.currentDay
        }
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  async viewPremiumPreview(userId, duration) {
    try {
      await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
        type: 'premium_preview_view',
        data: { 
          duration,
          timestamp: new Date().toISOString(),
          day: this.currentDay
        }
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  async getConversionOffer(userId) {
    try {
      const response = await axios.post(`${API_BASE}/api/conversion/offer`, {
        userId,
        currentDay: this.currentDay
      });
      return response.data;
    } catch (e) {
      return { success: false };
    }
  }

  async convertUser(userId, plan = 'annual') {
    try {
      await axios.post(`${API_BASE}/api/users/${userId}/premium`, {
        plan,
        conversionDay: this.currentDay
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  // ============= HELPER FUNCTIONS =============

  randomContexts() {
    const contexts = ['work', 'family', 'exercise', 'nature', 'social', 'rest', 'creative'];
    const count = Math.floor(Math.random() * 2) + 1;
    return Array.from({ length: count }, () => 
      contexts[Math.floor(Math.random() * contexts.length)]
    );
  }

  randomMicroAct() {
    const acts = ['gratitude', 'meditation', 'movement', 'connection', 'learning', 'rest'];
    return acts[Math.floor(Math.random() * acts.length)];
  }

  randomMood() {
    const moods = ['great', 'good', 'okay', 'low', 'struggling'];
    const weights = [0.2, 0.35, 0.3, 0.1, 0.05]; // Weighted random
    const rand = Math.random();
    let sum = 0;
    for (let i = 0; i < weights.length; i++) {
      sum += weights[i];
      if (rand < sum) return moods[i];
    }
    return 'okay';
  }

  getWeek(day) {
    return Math.ceil(day / 7);
  }

  getWeekKey(week) {
    return `week${week}`;
  }

  getCheckinPattern(user, day) {
    const week = this.getWeek(day);
    const weekKey = this.getWeekKey(week);
    return CHECKIN_PATTERNS[user.persona][weekKey];
  }

  // ============= SIMULATION LOGIC =============

  async simulateDay(day) {
    this.currentDay = day;
    const week = this.getWeek(day);
    const weekKey = this.getWeekKey(week);
    
    const dayActivity = {
      active: 0,
      checkIns: 0,
      insights: 0,
      lockedClicks: 0,
      conversions: 0,
      churned: 0
    };

    this.log(`\n📅 Day ${day} (Week ${week}, ${['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][(day-1) % 7]})`, 'cyan');

    for (const user of this.users) {
      // Skip already converted or churned users
      if (user.converted || user.churned) continue;

      const pattern = this.getCheckinPattern(user, day);
      
      // Determine if user is active today
      const isActiveToday = Math.random() < pattern.rate;
      
      if (!isActiveToday) {
        // Track consecutive inactive days for churn detection
        user.consecutiveInactiveDays = (user.consecutiveInactiveDays || 0) + 1;
        
        // Churn after 7 consecutive inactive days
        if (user.consecutiveInactiveDays >= 7 && !user.churned) {
          user.churned = true;
          user.churnDay = day;
          dayActivity.churned++;
          this.results.churnedUsers++;
          this.log(`   💀 User ${user.id.substring(0, 8)}... (${user.persona}) CHURNED after ${day} days`, 'red');
        }
        continue;
      }

      // User is active!
      user.consecutiveInactiveDays = 0;
      dayActivity.active++;

      // === DAY 1: ONBOARDING & SET INTENTION ===
      if (day === 1) {
        user.stats = {
          totalCheckIns: 0,
          totalInsights: 0,
          freeInsights: 0,
          lockedClicks: 0,
          journalReads: 0,
          premiumPreviewTime: 0,
          streak: 0,
          maxStreak: 0,
          lastCheckInDay: 0,
          fulfillmentHistory: [],
          missedIntentions: 0
        };
        await this.setIntention(user.id, 'Exercise 3x/week and practice gratitude daily');
        user.intentionSet = true;
      }
      
      // Initialize stats if null (safety check)
      if (!user.stats) {
        user.stats = {
          totalCheckIns: 0,
          totalInsights: 0,
          freeInsights: 0,
          lockedClicks: 0,
          journalReads: 0,
          premiumPreviewTime: 0,
          streak: 0,
          maxStreak: 0,
          lastCheckInDay: 0,
          fulfillmentHistory: [],
          missedIntentions: 0
        };
      }

      // === CHECK-INS (4x/day target, but varies by persona) ===
      const targetCheckIns = Math.max(1, Math.round(pattern.avgPerDay + (Math.random() - 0.5)));
      const dayParts = ['morning', 'afternoon', 'evening', 'night'];
      
      for (let i = 0; i < Math.min(targetCheckIns, 4); i++) {
        const mood = this.randomMood();
        await this.createCheckIn(user.id, dayParts[i], mood);
        user.stats.totalCheckIns++;
        dayActivity.checkIns++;
        await this.delay(2); // Small delay
      }

      // Update streak
      if (user.stats.lastCheckInDay === day - 1 || day === 1) {
        user.stats.streak++;
        user.stats.maxStreak = Math.max(user.stats.maxStreak, user.stats.streak);
      } else if (user.stats.lastCheckInDay < day - 1) {
        user.stats.streak = 1; // Streak broken
      }
      user.stats.lastCheckInDay = day;

      // === MOCK FULFILLMENT SCORE ===
      const baseFulfillment = 50 + (user.stats.totalCheckIns / day) * 10;
      const randomVariation = Math.random() * 20 - 10;
      user.currentFulfillment = Math.min(100, Math.max(0, baseFulfillment + randomVariation));
      user.stats.fulfillmentHistory.push(user.currentFulfillment);

      // === WEEKLY INSIGHTS (Days 3, 7, 14, 21, 28) ===
      if ([3, 7, 14, 21, 28].includes(day) && user.stats.totalCheckIns >= 6) {
        const insightCount = await this.generateInsights(user.id);
        if (insightCount > 0) {
          user.stats.totalInsights += insightCount;
          user.stats.freeInsights += Math.min(2, insightCount); // Max 2 free per generation
          dayActivity.insights += insightCount;
          this.results.totalInsights += insightCount;
        }
      }

      // === DAILY JOURNAL (50% of active users read it) ===
      if (day > 1 && Math.random() < 0.5) {
        const journalGenerated = await this.generateJournal(user.id);
        if (journalGenerated) {
          user.stats.journalReads++;
          this.results.totalJournalReads++;
        }
      }

      // === PROGRESSIVE LOCKED FEATURE EXPOSURE ===
      if (day >= 8) { // Start showing locked features week 2+
        const exposureRate = LOCKED_FEATURE_EXPOSURE[weekKey];
        const shouldSeeLockedFeature = Math.random() < exposureRate;
        
        if (shouldSeeLockedFeature) {
          // Multiple locked features for highly engaged users
          const numClicks = user.persona === 'power-user' || user.persona === 'engaged' 
            ? Math.floor(Math.random() * 3) + 1 
            : Math.random() < 0.3 ? 1 : 0;
          
          for (let i = 0; i < numClicks; i++) {
            const insightTypes = ['BREAKPOINT', 'PURPOSE-PATH'];
            const type = insightTypes[Math.floor(Math.random() * insightTypes.length)];
            await this.clickLockedInsight(user.id, type);
            user.stats.lockedClicks++;
            dayActivity.lockedClicks++;
            this.results.totalLockedClicks++;
            await this.delay(5);
          }

          // Some users spend time viewing premium preview
          if (user.stats.lockedClicks >= 2 && Math.random() < 0.4) {
            const previewTime = 30 + Math.random() * 60; // 30-90 seconds
            await this.viewPremiumPreview(user.id, previewTime);
            user.stats.premiumPreviewTime += previewTime;
          }
        }
      }

      // === MISSED INTENTION DETECTION (Week 1 end, 2, 3, 4) ===
      if ([7, 14, 21, 28].includes(day)) {
        // Simulate some users missing their weekly intention
        const missedIntention = Math.random() < 0.4; // 40% miss intention
        if (missedIntention) {
          user.stats.missedIntentions++;
          user.lastMissedIntentionDay = day;
        }
      }

      // === CONVERSION OPPORTUNITY (Days 7, 14, 21, 28) ===
      if ([7, 14, 21, 28].includes(day)) {
        await this.evaluateConversion(user, day, week);
        if (user.converted) {
          dayActivity.conversions++;
        }
      }

      await this.delay(1); // Tiny delay between users
    }

    // === DAY SUMMARY ===
    const activeRate = (dayActivity.active / this.users.filter(u => !u.churned).length * 100).toFixed(1);
    this.log(`   Active: ${dayActivity.active}/${this.users.filter(u => !u.churned).length} (${activeRate}%) | Check-ins: ${dayActivity.checkIns} | Insights: ${dayActivity.insights}`, 'white');
    
    if (dayActivity.lockedClicks > 0) {
      this.log(`   🔒 Locked clicks: ${dayActivity.lockedClicks}`, 'yellow');
    }

    if (dayActivity.conversions > 0) {
      this.log(`   💰 CONVERSIONS: ${dayActivity.conversions}`, 'green');
    }

    if (dayActivity.churned > 0) {
      this.log(`   💀 Churned: ${dayActivity.churned}`, 'red');
    }

    // === WEEKLY SUMMARY ===
    if (day % 7 === 0) {
      this.printWeeklySummary(week);
    }

    this.results.totalCheckIns += dayActivity.checkIns;
  }

  async evaluateConversion(user, day, week) {
    // Get conversion offer from backend
    const offer = await this.getConversionOffer(user.id);
    
    if (!offer.success || !offer.offer) return;

    // === CALCULATE CONVERSION PROBABILITY ===
    
    const demo = DEMOGRAPHICS.find(d => d.persona === user.persona);
    let conversionProb = demo.baseConversion;

    // Apply week multiplier (week 4 is peak)
    const weekKey = this.getWeekKey(week);
    conversionProb *= CONVERSION_WEEK_MULTIPLIER[weekKey];

    // === CONVERSION SIGNALS (Increase probability) ===

    // 1. High engagement (check-ins per day)
    const avgCheckInsPerDay = user.stats.totalCheckIns / day;
    if (avgCheckInsPerDay >= 3.0) {
      conversionProb *= 1.5; // 50% boost
    } else if (avgCheckInsPerDay >= 2.0) {
      conversionProb *= 1.2; // 20% boost
    }

    // 2. Locked feature clicks (strong buying signal)
    if (user.stats.lockedClicks >= 5) {
      conversionProb *= 2.0; // 100% boost
    } else if (user.stats.lockedClicks >= 3) {
      conversionProb *= 1.5;
    } else if (user.stats.lockedClicks >= 1) {
      conversionProb *= 1.2;
    }

    // 3. Premium preview time (very strong signal)
    if (user.stats.premiumPreviewTime >= 60) {
      conversionProb *= 1.8;
    } else if (user.stats.premiumPreviewTime >= 30) {
      conversionProb *= 1.3;
    }

    // 4. Missed intention (emotional trigger)
    if (user.lastMissedIntentionDay === day) {
      conversionProb *= 1.4; // 40% boost when frustrated
    }

    // 5. Fulfillment drop (seeking answers)
    if (user.stats.fulfillmentHistory.length >= 3) {
      const recent = user.stats.fulfillmentHistory.slice(-3);
      const dropped = recent[2] < recent[0] - 10;
      if (dropped) {
        conversionProb *= 1.3;
      }
    }

    // 6. High streak (invested user)
    if (user.stats.streak >= 14) {
      conversionProb *= 1.4;
    } else if (user.stats.streak >= 7) {
      conversionProb *= 1.2;
    }

    // 7. Journal engagement
    if (user.stats.journalReads >= 10) {
      conversionProb *= 1.3;
    } else if (user.stats.journalReads >= 5) {
      conversionProb *= 1.15;
    }

    // 8. Free insights viewed (seeing value)
    if (user.stats.freeInsights >= 5) {
      conversionProb *= 1.2;
    }

    // Cap probability at 95%
    conversionProb = Math.min(0.95, conversionProb);

    // === ROLL FOR CONVERSION ===
    const roll = Math.random();
    const shouldConvert = roll < conversionProb;

    // Debug log for high-probability conversions
    if (conversionProb > 0.3 || shouldConvert) {
      this.log(`   🎲 User ${user.id.substring(0, 8)}... (${user.persona})`, 'dim');
      this.log(`      Prob: ${(conversionProb * 100).toFixed(1)}% | Roll: ${(roll * 100).toFixed(1)}% → ${shouldConvert ? '✅ CONVERT' : '❌ Pass'}`, shouldConvert ? 'green' : 'dim');
      if (shouldConvert) {
        this.log(`      Signals: CheckIns=${avgCheckInsPerDay.toFixed(1)}/day, Locked=${user.stats.lockedClicks}, Streak=${user.stats.streak}, Preview=${user.stats.premiumPreviewTime}s`, 'white');
      }
    }

    if (shouldConvert) {
      // CONVERT!
      user.converted = true;
      user.conversionDay = day;
      user.conversionWeek = week;
      
      // Determine trigger
      let trigger = 'Base conversion';
      if (user.lastMissedIntentionDay === day) trigger = 'Missed Intention';
      else if (user.stats.lockedClicks >= 5) trigger = 'High Locked Clicks';
      else if (user.stats.premiumPreviewTime >= 60) trigger = 'Premium Preview';
      else if (user.stats.streak >= 14) trigger = '14-Day Streak';
      else if (avgCheckInsPerDay >= 3) trigger = 'High Engagement';

      user.conversionTrigger = trigger;

      // Choose plan (70% annual, 30% monthly)
      const plan = Math.random() < 0.7 ? 'annual' : 'monthly';
      await this.convertUser(user.id, plan);

      // Record results
      this.results.totalConversions++;
      this.results.conversionsByPersona[user.persona] = (this.results.conversionsByPersona[user.persona] || 0) + 1;
      this.results.conversionsByWeek[weekKey]++;
      this.results.conversionsByTrigger[trigger] = (this.results.conversionsByTrigger[trigger] || 0) + 1;

      this.results.conversionDetails.push({
        userId: user.id,
        persona: user.persona,
        day,
        week,
        trigger,
        plan,
        stats: { ...user.stats },
        conversionProb: conversionProb.toFixed(3)
      });

      this.log(`   💰💰💰 CONVERSION! User ${user.id.substring(0, 15)}...`, 'bright');
      this.log(`      Persona: ${user.persona} | Day: ${day} | Week: ${week}`, 'green');
      this.log(`      Trigger: ${trigger} | Plan: ${plan}`, 'green');
      this.log(`      Conversion Prob: ${(conversionProb * 100).toFixed(1)}%`, 'yellow');
    }
  }

  printWeeklySummary(week) {
    const weekKey = this.getWeekKey(week);
    const activeUsers = this.users.filter(u => !u.churned && !u.converted).length;
    const convertedThisWeek = this.results.conversionsByWeek[weekKey];
    const totalConverted = this.results.totalConversions;
    const totalChurned = this.results.churnedUsers;

    this.log(`\n${'='.repeat(60)}`, 'cyan');
    this.log(`📊 WEEK ${week} SUMMARY`, 'bright');
    this.log(`${'='.repeat(60)}`, 'cyan');
    this.log(`   Active Users: ${activeUsers}/${this.users.length} (${(activeUsers/this.users.length*100).toFixed(1)}%)`);
    this.log(`   Conversions This Week: ${convertedThisWeek}`, convertedThisWeek > 0 ? 'green' : 'white');
    this.log(`   Total Conversions: ${totalConverted} (${(totalConverted/this.users.length*100).toFixed(1)}%)`);
    this.log(`   Total Churned: ${totalChurned} (${(totalChurned/this.users.length*100).toFixed(1)}%)`);
    this.log(`   Check-ins: ${this.results.totalCheckIns}`);
    this.log(`   Insights: ${this.results.totalInsights}`);
    this.log(`   Locked Clicks: ${this.results.totalLockedClicks}`);
    this.log(`${'='.repeat(60)}\n`, 'cyan');
  }

  async run() {
    this.log('\n╔══════════════════════════════════════════════════════════╗', 'bright');
    this.log('║     REAL LIFE CONVERSION SIMULATION - 100 USERS         ║', 'bright');
    this.log('║     Full Virtuous Cycle with Churn & All Triggers       ║', 'bright');
    this.log('╚══════════════════════════════════════════════════════════╝\n', 'bright');

    // === PHASE 1: CREATE USERS ===
    this.log('👥 Creating 100 users across 5 personas...', 'blue');
    let userId = 1;
    for (const demo of DEMOGRAPHICS) {
      this.log(`   Creating ${demo.count} ${demo.persona} users (base conversion: ${(demo.baseConversion*100).toFixed(0)}%)...`, 'blue');
      for (let i = 0; i < demo.count; i++) {
        const user = await this.createUser(userId++, demo.persona);
        if (user) {
          this.users.push({
            ...user,
            persona: demo.persona,
            converted: false,
            churned: false,
            stats: null
          });
        }
        await this.delay(10);
      }
    }
    this.log(`✅ Created ${this.users.length} users\n`, 'green');

    // === PHASE 2: RUN 28-DAY SIMULATION ===
    this.log('📅 Starting 28-day simulation (4 weeks)...\n', 'blue');
    
    for (let day = 1; day <= 28; day++) {
      await this.simulateDay(day);
    }

    // === PHASE 3: FINAL RESULTS ===
    this.printFinalResults();
  }

  printFinalResults() {
    this.log('\n╔══════════════════════════════════════════════════════════╗', 'bright');
    this.log('║                    FINAL RESULTS                         ║', 'bright');
    this.log('╚══════════════════════════════════════════════════════════╝\n', 'bright');

    const totalActive = this.users.length - this.results.churnedUsers - this.results.totalConversions;
    const conversionRate = (this.results.totalConversions / this.users.length * 100).toFixed(2);

    this.log('📊 OVERALL METRICS', 'cyan');
    this.log('─'.repeat(60));
    this.log(`   Total Users:        ${this.users.length}`);
    this.log(`   Conversions:        ${this.results.totalConversions} (${conversionRate}%)`, 'green');
    this.log(`   Still Active:       ${totalActive}`);
    this.log(`   Churned:            ${this.results.churnedUsers} (${(this.results.churnedUsers/this.users.length*100).toFixed(1)}%)`, 'red');
    this.log('');

    this.log('👥 CONVERSIONS BY PERSONA', 'cyan');
    this.log('─'.repeat(60));
    DEMOGRAPHICS.forEach(demo => {
      const converted = this.results.conversionsByPersona[demo.persona] || 0;
      const rate = (converted / demo.count * 100).toFixed(1);
      const bar = '█'.repeat(Math.floor(converted / 2)) + '░'.repeat(Math.floor((demo.count - converted) / 2));
      this.log(`   ${demo.persona.padEnd(12)} ${converted}/${demo.count} (${rate.padStart(5)}%) ${bar}`, 
        converted > 0 ? 'green' : 'white');
    });
    this.log('');

    this.log('📅 CONVERSIONS BY WEEK', 'cyan');
    this.log('─'.repeat(60));
    for (let w = 1; w <= 4; w++) {
      const weekKey = this.getWeekKey(w);
      const count = this.results.conversionsByWeek[weekKey];
      const bar = '█'.repeat(count);
      this.log(`   Week ${w}: ${count.toString().padStart(2)} conversions ${bar}`, count > 0 ? 'green' : 'white');
    }
    this.log('');

    this.log('🎯 CONVERSIONS BY TRIGGER', 'cyan');
    this.log('─'.repeat(60));
    const sortedTriggers = Object.entries(this.results.conversionsByTrigger)
      .sort((a, b) => b[1] - a[1]);
    sortedTriggers.forEach(([trigger, count]) => {
      const bar = '█'.repeat(count);
      this.log(`   ${trigger.padEnd(25)} ${count.toString().padStart(2)} ${bar}`, 'green');
    });
    this.log('');

    this.log('📈 ENGAGEMENT METRICS', 'cyan');
    this.log('─'.repeat(60));
    this.log(`   Total Check-ins:           ${this.results.totalCheckIns}`);
    this.log(`   Total Insights Generated:  ${this.results.totalInsights}`);
    this.log(`   Total Locked Clicks:       ${this.results.totalLockedClicks}`);
    this.log(`   Total Journal Reads:       ${this.results.totalJournalReads}`);
    
    if (this.results.totalConversions > 0) {
      const avgCheckIns = this.results.conversionDetails
        .reduce((sum, c) => sum + c.stats.totalCheckIns, 0) / this.results.totalConversions;
      const avgLockedClicks = this.results.conversionDetails
        .reduce((sum, c) => sum + c.stats.lockedClicks, 0) / this.results.totalConversions;
      const avgStreak = this.results.conversionDetails
        .reduce((sum, c) => sum + c.stats.maxStreak, 0) / this.results.totalConversions;
      
      this.log('');
      this.log('💎 CONVERTED USER AVERAGES', 'cyan');
      this.log('─'.repeat(60));
      this.log(`   Avg Check-ins:      ${avgCheckIns.toFixed(1)}`);
      this.log(`   Avg Locked Clicks:  ${avgLockedClicks.toFixed(1)}`);
      this.log(`   Avg Max Streak:     ${avgStreak.toFixed(1)} days`);
    }

    this.log('\n✅ Simulation Complete!\n', 'green');
    
    // Export detailed results to JSON
    this.exportResults();
  }

  exportResults() {
    const output = {
      summary: {
        totalUsers: this.users.length,
        conversions: this.results.totalConversions,
        conversionRate: (this.results.totalConversions / this.users.length * 100).toFixed(2) + '%',
        churned: this.results.churnedUsers,
        churnRate: (this.results.churnedUsers / this.users.length * 100).toFixed(2) + '%'
      },
      conversionsByPersona: this.results.conversionsByPersona,
      conversionsByWeek: this.results.conversionsByWeek,
      conversionsByTrigger: this.results.conversionsByTrigger,
      engagementMetrics: {
        totalCheckIns: this.results.totalCheckIns,
        totalInsights: this.results.totalInsights,
        totalLockedClicks: this.results.totalLockedClicks,
        totalJournalReads: this.results.totalJournalReads
      },
      conversionDetails: this.results.conversionDetails
    };

    const fs = require('fs');
    const filename = `simulation-results-${Date.now()}.json`;
    fs.writeFileSync(filename, JSON.stringify(output, null, 2));
    this.log(`📄 Detailed results exported to: ${filename}`, 'blue');
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// === RUN SIMULATION ===
const sim = new RealLifeSimulation();
sim.run()
  .then(() => process.exit(0))
  .catch(err => {
    console.error('❌ Simulation Error:', err.message);
    console.error(err.stack);
    process.exit(1);
  });
