/**
 * USER SIMULATOR - 100 User Load Testing Framework
 * 
 * Simulates realistic user behavior patterns:
 * - Check-in completion rates
 * - Details logging
 * - Journal generation
 * - Premium conversion
 * - Retention patterns
 * 
 * Time scale: 10 minutes real = 1 day simulated
 * Total runtime: 2 hours = 12 simulated days
 */

interface UserProfile {
  userId: string;
  name: string;
  persona: 'engaged' | 'casual' | 'struggler' | 'power-user';
  isPremium: boolean;
  joinedDay: number;
  
  // Behavioral traits (affect check-in probability)
  sleepQuality: number; // 0-1
  stressLevel: number; // 0-1
  socialMediaMinutes: number; // avg per day
  motivationLevel: number; // 0-1
  
  // Stats
  totalCheckIns: number;
  meaningfulDays: number;
  currentStreak: number;
  longestStreak: number;
  lastActive: number;
  
  // Scores (track over time)
  bodyScore: number;
  mindScore: number;
  soulScore: number;
  purposeScore: number;
  fulfillmentScore: number;
}

interface CheckInEvent {
  userId: string;
  day: number;
  timestamp: Date;
  dayPart: 'morning' | 'day' | 'evening' | 'night';
  mood: number; // 1-5
  arousal: 'low' | 'medium' | 'high';
  contexts: string[];
  microAct: string | null;
  durationSeconds: number;
}

interface DetailEntry {
  userId: string;
  day: number;
  sleepHours: number;
  sleepQuality: number;
  steps: number;
  exercise: boolean;
  foodQuality: number; // 0-1
  socialInteractions: number;
  screenTimeMinutes: number;
}

interface AnalyticsEvent {
  userId: string;
  eventType: string;
  day: number;
  timestamp: Date;
  metadata: Record<string, any>;
}

export class UserSimulator {
  private users: Map<string, UserProfile> = new Map();
  private checkIns: CheckInEvent[] = [];
  private details: DetailEntry[] = [];
  private analytics: AnalyticsEvent[] = [];
  
  private currentDay: number = 0;
  private startTime: Date = new Date();
  
  // Simulation config
  private readonly TOTAL_USERS = 100;
  private readonly MINUTES_PER_DAY = 10; // 10 real minutes = 1 simulated day
  private readonly TOTAL_DAYS = 12; // 2 hours = 12 days
  private readonly MS_PER_DAY = this.MINUTES_PER_DAY * 60 * 1000;
  
  constructor() {
    this.initializeUsers();
  }
  
  /**
   * Initialize 100 users with realistic persona distribution
   */
  private initializeUsers() {
    console.log('🎭 Initializing 100 users...\n');
    
    const personas: Array<'engaged' | 'casual' | 'struggler' | 'power-user'> = [
      ...Array(30).fill('engaged'),      // 30% highly engaged
      ...Array(45).fill('casual'),       // 45% casual users
      ...Array(20).fill('struggler'),    // 20% struggle with consistency
      ...Array(5).fill('power-user'),    // 5% power users
    ];
    
    const names = this.generateNames(this.TOTAL_USERS);
    
    for (let i = 0; i < this.TOTAL_USERS; i++) {
      const persona = personas[i];
      const user: UserProfile = {
        userId: `user_${String(i + 1).padStart(3, '0')}`,
        name: names[i],
        persona,
        isPremium: Math.random() < 0.15, // 15% start as premium (early adopters)
        joinedDay: 0, // All join on day 0 for this simulation
        
        // Behavioral traits based on persona
        sleepQuality: this.getTraitForPersona(persona, 'sleep'),
        stressLevel: this.getTraitForPersona(persona, 'stress'),
        socialMediaMinutes: this.getTraitForPersona(persona, 'social'),
        motivationLevel: this.getTraitForPersona(persona, 'motivation'),
        
        totalCheckIns: 0,
        meaningfulDays: 0,
        currentStreak: 0,
        longestStreak: 0,
        lastActive: 0,
        
        bodyScore: 50 + Math.random() * 20,
        mindScore: 50 + Math.random() * 20,
        soulScore: 50 + Math.random() * 20,
        purposeScore: 50 + Math.random() * 20,
        fulfillmentScore: 50 + Math.random() * 20,
      };
      
      this.users.set(user.userId, user);
    }
    
    console.log(`✅ Created ${this.TOTAL_USERS} users:`);
    console.log(`   📈 Engaged: 30 users`);
    console.log(`   😊 Casual: 45 users`);
    console.log(`   😓 Strugglers: 20 users`);
    console.log(`   ⚡ Power Users: 5 users`);
    console.log(`   💎 Premium: ${Array.from(this.users.values()).filter(u => u.isPremium).length} users\n`);
  }
  
  private getTraitForPersona(persona: string, trait: string): number {
    const traits: Record<string, Record<string, [number, number]>> = {
      'engaged': {
        sleep: [0.7, 0.9],
        stress: [0.3, 0.5],
        social: [30, 60],
        motivation: [0.7, 0.9],
      },
      'casual': {
        sleep: [0.5, 0.7],
        stress: [0.4, 0.7],
        social: [45, 90],
        motivation: [0.4, 0.6],
      },
      'struggler': {
        sleep: [0.3, 0.5],
        stress: [0.6, 0.9],
        social: [60, 120],
        motivation: [0.2, 0.4],
      },
      'power-user': {
        sleep: [0.8, 1.0],
        stress: [0.2, 0.4],
        social: [15, 45],
        motivation: [0.85, 1.0],
      },
    };
    
    const [min, max] = traits[persona][trait];
    return min + Math.random() * (max - min);
  }
  
  private generateNames(count: number): string[] {
    const firstNames = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Avery', 'Quinn', 'Sage', 'Rowan',
                        'Skylar', 'Phoenix', 'River', 'Dakota', 'Ember', 'Kai', 'Indigo', 'Aspen', 'Blake', 'Cameron',
                        'Drew', 'Eden', 'Finley', 'Gray', 'Harper', 'Iris', 'Jesse', 'Kelly', 'Logan', 'Marley'];
    const lastNames = ['Chen', 'Smith', 'Garcia', 'Johnson', 'Brown', 'Lee', 'Kim', 'Davis', 'Wilson', 'Martinez',
                       'Anderson', 'Taylor', 'Thomas', 'Moore', 'Jackson', 'White', 'Harris', 'Martin', 'Thompson', 'Robinson'];
    
    const names: string[] = [];
    for (let i = 0; i < count; i++) {
      const first = firstNames[Math.floor(Math.random() * firstNames.length)];
      const last = lastNames[Math.floor(Math.random() * lastNames.length)];
      names.push(`${first} ${last}`);
    }
    return names;
  }
  
  /**
   * Main simulation loop - runs for 2 hours (12 simulated days)
   */
  async runSimulation() {
    console.log('\n🚀 STARTING 2-HOUR SIMULATION (12 simulated days)\n');
    console.log(`⏰ Time scale: 10 minutes real = 1 day simulated`);
    console.log(`📅 Total: ${this.TOTAL_DAYS} days\n`);
    console.log('─'.repeat(60) + '\n');
    
    this.startTime = new Date();
    
    for (let day = 0; day < this.TOTAL_DAYS; day++) {
      this.currentDay = day;
      await this.simulateDay(day);
      
      // Wait for 10 minutes (1 simulated day)
      if (day < this.TOTAL_DAYS - 1) {
        await this.sleep(this.MS_PER_DAY);
      }
    }
    
    console.log('\n✅ SIMULATION COMPLETE!\n');
    this.generateFinalReport();
  }
  
  /**
   * Simulate a single day for all users
   */
  private async simulateDay(day: number) {
    const dayStart = new Date();
    console.log(`📅 DAY ${day + 1} - ${dayStart.toLocaleTimeString()}`);
    console.log('─'.repeat(60));
    
    // Morning check-ins (0-2.5 minutes into the day)
    await this.simulateDayPart(day, 'morning', 0, 0.25);
    
    // Day check-ins (2.5-5 minutes)
    await this.simulateDayPart(day, 'day', 0.25, 0.5);
    
    // Evening check-ins (5-7.5 minutes)
    await this.simulateDayPart(day, 'evening', 0.5, 0.75);
    
    // Night check-ins (7.5-10 minutes)
    await this.simulateDayPart(day, 'night', 0.75, 1.0);
    
    // Update daily stats
    this.updateDailyStats(day);
    
    // Premium conversions (after 3 MDW or day 7+)
    this.processPremiumConversions(day);
    
    // Print daily summary
    this.printDailySummary(day);
    
    console.log('');
  }
  
  /**
   * Simulate check-ins for a specific daypart
   */
  private async simulateDayPart(
    day: number,
    dayPart: 'morning' | 'day' | 'evening' | 'night',
    startRatio: number,
    endRatio: number
  ) {
    const startDelay = startRatio * this.MS_PER_DAY;
    const endDelay = endRatio * this.MS_PER_DAY;
    
    // Wait until daypart starts
    if (startDelay > 0) {
      await this.sleep(startDelay);
    }
    
    const checkInWindow = endDelay - startDelay;
    
    for (const user of this.users.values()) {
      // Check-in probability based on persona and day
      const probability = this.getCheckInProbability(user, day, dayPart);
      
      if (Math.random() < probability) {
        // Random delay within the daypart window
        const delay = Math.random() * checkInWindow;
        
        setTimeout(() => {
          this.performCheckIn(user, day, dayPart);
        }, delay);
      }
    }
  }
  
  private getCheckInProbability(user: UserProfile, day: number, dayPart: string): number {
    const baseRates: Record<string, number> = {
      'engaged': 0.85,
      'casual': 0.55,
      'struggler': 0.30,
      'power-user': 0.95,
    };
    
    let probability = baseRates[user.persona];
    
    // Decay over time (novelty wears off)
    const decayFactor = Math.exp(-0.05 * day);
    probability *= (0.7 + 0.3 * decayFactor);
    
    // Morning has higher completion rate
    if (dayPart === 'morning') {
      probability *= 1.2;
    } else if (dayPart === 'night') {
      probability *= 0.85; // Night has slightly lower rate
    }
    
    // Streak bonus (momentum)
    if (user.currentStreak >= 3) {
      probability *= 1.15;
    }
    
    // Premium users are more engaged
    if (user.isPremium) {
      probability *= 1.25;
    }
    
    return Math.min(probability, 0.98); // Cap at 98%
  }
  
  private performCheckIn(user: UserProfile, day: number, dayPart: string) {
    const moods = [1, 2, 3, 4, 5];
    const moodWeights = user.persona === 'struggler' 
      ? [0.2, 0.3, 0.3, 0.15, 0.05] // More negative
      : user.persona === 'power-user'
      ? [0.05, 0.1, 0.25, 0.35, 0.25] // More positive
      : [0.1, 0.2, 0.4, 0.2, 0.1]; // Balanced
    
    const mood = this.weightedRandom(moods, moodWeights);
    
    const checkIn: CheckInEvent = {
      userId: user.userId,
      day,
      timestamp: new Date(),
      dayPart: dayPart as any,
      mood,
      arousal: Math.random() < 0.33 ? 'low' : Math.random() < 0.5 ? 'medium' : 'high',
      contexts: this.selectContexts(),
      microAct: Math.random() < 0.6 ? this.selectMicroAct() : null,
      durationSeconds: 8 + Math.random() * 20, // 8-28 seconds
    };
    
    this.checkIns.push(checkIn);
    user.totalCheckIns++;
    user.lastActive = day;
    
    // Log details (premium users or engaged users)
    if ((user.isPremium || Math.random() < 0.3) && dayPart === 'morning') {
      this.logDetails(user, day);
    }
    
    // Analytics event
    this.trackEvent(user.userId, 'check_in_complete', day, {
      dayPart,
      mood,
      duration: checkIn.durationSeconds,
    });
  }
  
  private logDetails(user: UserProfile, day: number) {
    const details: DetailEntry = {
      userId: user.userId,
      day,
      sleepHours: 5 + user.sleepQuality * 3.5, // 5-8.5 hours
      sleepQuality: user.sleepQuality,
      steps: Math.floor(3000 + Math.random() * 12000),
      exercise: Math.random() < 0.4,
      foodQuality: 0.4 + Math.random() * 0.5,
      socialInteractions: Math.floor(Math.random() * 6),
      screenTimeMinutes: Math.floor(user.socialMediaMinutes * (0.7 + Math.random() * 0.6)),
    };
    
    this.details.push(details);
    
    this.trackEvent(user.userId, 'details_logged', day, {
      sleepHours: details.sleepHours,
      steps: details.steps,
    });
  }
  
  private selectContexts(): string[] {
    const allContexts = ['Work', 'Social', 'Family', 'Exercise', 'Rest'];
    const count = Math.random() < 0.5 ? 1 : 2;
    return this.shuffleArray(allContexts).slice(0, count);
  }
  
  private selectMicroAct(): string {
    const acts = ['Gratitude', 'Meditation', 'Walk', 'Learning', 'Kindness', 'Nature'];
    return acts[Math.floor(Math.random() * acts.length)];
  }
  
  private updateDailyStats(day: number) {
    for (const user of this.users.values()) {
      const todayCheckIns = this.checkIns.filter(c => c.userId === user.userId && c.day === day);
      const completedDayParts = new Set(todayCheckIns.map(c => c.dayPart));
      
      // Update scores based on check-ins
      if (todayCheckIns.length > 0) {
        const avgMood = todayCheckIns.reduce((sum, c) => sum + c.mood, 0) / todayCheckIns.length;
        
        // Scores improve with engagement
        user.mindScore += (avgMood - 3) * 2 + (Math.random() - 0.5) * 5;
        user.soulScore += todayCheckIns.filter(c => c.microAct).length * 3;
        user.purposeScore += completedDayParts.size * 2;
        
        // Get details for body score
        const todayDetails = this.details.find(d => d.userId === user.userId && d.day === day);
        if (todayDetails) {
          user.bodyScore += (todayDetails.sleepHours - 6.5) * 3 + (Math.random() - 0.5) * 5;
        } else {
          user.bodyScore += (Math.random() - 0.5) * 3;
        }
        
        // Clamp scores
        user.bodyScore = Math.max(0, Math.min(100, user.bodyScore));
        user.mindScore = Math.max(0, Math.min(100, user.mindScore));
        user.soulScore = Math.max(0, Math.min(100, user.soulScore));
        user.purposeScore = Math.max(0, Math.min(100, user.purposeScore));
        
        user.fulfillmentScore = 
          0.25 * user.bodyScore + 
          0.25 * user.mindScore + 
          0.25 * user.soulScore + 
          0.25 * user.purposeScore;
        
        // Check if meaningful day
        if (
          user.bodyScore >= 70 &&
          user.mindScore >= 65 &&
          user.soulScore >= 80 &&
          user.purposeScore >= 55
        ) {
          user.meaningfulDays++;
          user.currentStreak++;
          user.longestStreak = Math.max(user.longestStreak, user.currentStreak);
          
          this.trackEvent(user.userId, 'meaningful_day', day, {
            streak: user.currentStreak,
          });
        } else if (completedDayParts.size > 0) {
          user.currentStreak++;
        }
      } else {
        // Missed day - break streak
        user.currentStreak = 0;
        user.bodyScore -= 5;
        user.mindScore -= 3;
      }
    }
  }
  
  private processPremiumConversions(day: number) {
    for (const user of this.users.values()) {
      if (!user.isPremium) {
        // Conversion triggers
        const hasThreeMDW = user.meaningfulDays >= 3;
        const isDay7Plus = day >= 6;
        const highEngagement = user.totalCheckIns >= day * 3;
        
        if (hasThreeMDW || (isDay7Plus && highEngagement)) {
          // Conversion probability
          const conversionRate = user.persona === 'power-user' ? 0.4 
            : user.persona === 'engaged' ? 0.25
            : user.persona === 'casual' ? 0.08
            : 0.02;
          
          if (Math.random() < conversionRate) {
            user.isPremium = true;
            this.trackEvent(user.userId, 'premium_conversion', day, {
              trigger: hasThreeMDW ? 'mdw' : 'engagement',
              meaningfulDays: user.meaningfulDays,
              totalCheckIns: user.totalCheckIns,
            });
          }
        }
      }
    }
  }
  
  private trackEvent(userId: string, eventType: string, day: number, metadata: Record<string, any>) {
    this.analytics.push({
      userId,
      eventType,
      day,
      timestamp: new Date(),
      metadata,
    });
  }
  
  private printDailySummary(day: number) {
    const todayCheckIns = this.checkIns.filter(c => c.day === day);
    const activeUsers = new Set(todayCheckIns.map(c => c.userId)).size;
    const avgCheckInsPerUser = todayCheckIns.length / activeUsers || 0;
    const meaningfulDaysToday = this.analytics.filter(
      e => e.eventType === 'meaningful_day' && e.day === day
    ).length;
    const conversionsToday = this.analytics.filter(
      e => e.eventType === 'premium_conversion' && e.day === day
    ).length;
    
    console.log(`   Active Users: ${activeUsers}/${this.TOTAL_USERS}`);
    console.log(`   Check-ins: ${todayCheckIns.length} (avg ${avgCheckInsPerUser.toFixed(1)}/user)`);
    console.log(`   Meaningful Days: ${meaningfulDaysToday}`);
    if (conversionsToday > 0) {
      console.log(`   💰 Premium Conversions: ${conversionsToday}`);
    }
  }
  
  /**
   * Generate final analytics report
   */
  private generateFinalReport() {
    const totalCheckIns = this.checkIns.length;
    const totalUsers = this.users.size;
    const activeUsers = new Set(this.checkIns.map(c => c.userId)).size;
    const premiumUsers = Array.from(this.users.values()).filter(u => u.isPremium).length;
    
    const d1Active = new Set(this.checkIns.filter(c => c.day === 0).map(c => c.userId)).size;
    const d7Active = new Set(this.checkIns.filter(c => c.day === 6).map(c => c.userId)).size;
    const d7Retention = (d7Active / d1Active) * 100;
    
    const avgMDW = Array.from(this.users.values()).reduce((sum, u) => sum + u.meaningfulDays, 0) / totalUsers;
    const avgCheckInsPerUser = totalCheckIns / activeUsers;
    
    const avgFulfillment = Array.from(this.users.values()).reduce((sum, u) => sum + u.fulfillmentScore, 0) / totalUsers;
    
    console.log('\n' + '='.repeat(60));
    console.log('📊 FINAL ANALYTICS REPORT');
    console.log('='.repeat(60) + '\n');
    
    console.log('👥 USER METRICS:');
    console.log(`   Total Users: ${totalUsers}`);
    console.log(`   Active Users (made ≥1 check-in): ${activeUsers} (${(activeUsers/totalUsers*100).toFixed(1)}%)`);
    console.log(`   Premium Users: ${premiumUsers} (${(premiumUsers/totalUsers*100).toFixed(1)}%)`);
    console.log(`   D7 Retention: ${d7Retention.toFixed(1)}%`);
    console.log('');
    
    console.log('✅ ENGAGEMENT:');
    console.log(`   Total Check-ins: ${totalCheckIns.toLocaleString()}`);
    console.log(`   Avg Check-ins/User: ${avgCheckInsPerUser.toFixed(1)}`);
    console.log(`   Details Logged: ${this.details.length}`);
    console.log(`   Avg Check-in Duration: ${(this.checkIns.reduce((sum, c) => sum + c.durationSeconds, 0) / totalCheckIns).toFixed(1)}s`);
    console.log('');
    
    console.log('🎯 NORTH STAR (MDW):');
    console.log(`   Avg Meaningful Days/Week: ${avgMDW.toFixed(2)}`);
    console.log(`   Users with MDW ≥3: ${Array.from(this.users.values()).filter(u => u.meaningfulDays >= 3).length}`);
    console.log('');
    
    console.log('📈 SCORES:');
    console.log(`   Avg Fulfillment Score: ${avgFulfillment.toFixed(1)}/100`);
    console.log('');
    
    console.log('💰 CONVERSION:');
    const conversions = this.analytics.filter(e => e.eventType === 'premium_conversion');
    console.log(`   Total Conversions: ${conversions.length}`);
    console.log(`   Conversion Rate: ${(conversions.length / totalUsers * 100).toFixed(1)}%`);
    console.log(`   Avg Days to Convert: ${(conversions.reduce((sum, c) => sum + c.day, 0) / conversions.length || 0).toFixed(1)}`);
    console.log('');
    
    // Persona breakdown
    console.log('🎭 PERSONA BREAKDOWN:');
    const personas = ['engaged', 'casual', 'struggler', 'power-user'];
    for (const persona of personas) {
      const personaUsers = Array.from(this.users.values()).filter(u => u.persona === persona);
      const avgCheckIns = personaUsers.reduce((sum, u) => sum + u.totalCheckIns, 0) / personaUsers.length;
      const avgMDWPersona = personaUsers.reduce((sum, u) => sum + u.meaningfulDays, 0) / personaUsers.length;
      const premiumRate = personaUsers.filter(u => u.isPremium).length / personaUsers.length * 100;
      
      console.log(`   ${persona.toUpperCase()}:`);
      console.log(`      Avg Check-ins: ${avgCheckIns.toFixed(1)}`);
      console.log(`      Avg MDW: ${avgMDWPersona.toFixed(2)}`);
      console.log(`      Premium Rate: ${premiumRate.toFixed(1)}%`);
    }
    
    console.log('\n' + '='.repeat(60) + '\n');
  }
  
  // Utility functions
  private weightedRandom<T>(items: T[], weights: number[]): T {
    const total = weights.reduce((sum, w) => sum + w, 0);
    let random = Math.random() * total;
    
    for (let i = 0; i < items.length; i++) {
      random -= weights[i];
      if (random <= 0) return items[i];
    }
    
    return items[items.length - 1];
  }
  
  private shuffleArray<T>(array: T[]): T[] {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  }
  
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  /**
   * Export data for backend analytics
   */
  exportData() {
    return {
      users: Array.from(this.users.values()),
      checkIns: this.checkIns,
      details: this.details,
      analytics: this.analytics,
      metadata: {
        totalDays: this.TOTAL_DAYS,
        startTime: this.startTime,
        endTime: new Date(),
        totalUsers: this.TOTAL_USERS,
      },
    };
  }
}

