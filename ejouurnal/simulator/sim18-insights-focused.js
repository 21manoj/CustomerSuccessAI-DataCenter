const axios = require('axios');

const API_BASE = 'http://localhost:3005';
const TOTAL_DAYS = 15;
const DAY_DURATION_MS = 60 * 1000; // 1 minute per day
const REQUEST_DELAY = 50;
const CHECKIN_PROBABILITY = 0.8; // 80% of users check in daily
const INSIGHTS_START_DAY = 3; // Start generating insights from day 3

const MOODS = ['very-low', 'low', 'neutral', 'good', 'great'];

class InsightsFocusedSim {
    constructor() {
        this.users = [];
        this.stats = {
            totalCheckIns: 0,
            totalJournals: 0,
            totalInsights: 0,
            totalPremium: 0,
            dailyStats: []
        };
    }

    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async makeRequest(method, endpoint, data = null) {
        try {
            const config = {
                method,
                url: `${API_BASE}${endpoint}`,
                headers: { 'Content-Type': 'application/json' }
            };
            if (data) config.data = data;
            
            const response = await axios(config);
            await this.delay(REQUEST_DELAY);
            return response.data;
        } catch (error) {
            return null;
        }
    }

    generateRandomMood() {
        return MOODS[Math.floor(Math.random() * MOODS.length)];
    }

    async createUsers() {
        console.log('👥 Creating 100 users...');
        
        // SIM3 demographics: 30% engaged, 45% casual, 20% struggler, 5% power-user
        const personas = [...Array(30).fill('engaged'), ...Array(45).fill('casual'), ...Array(20).fill('struggler'), ...Array(5).fill('power-user')];
        
        // Shuffle
        for (let i = personas.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [personas[i], personas[j]] = [personas[j], personas[i]];
        }
        
        for (let i = 0; i < 100; i++) {
            const userData = {
                name: `User_${i + 1}`,
                email: `user_${Date.now()}_${i}@example.com`,
                persona: personas[i]
            };
            
            const user = await this.makeRequest('POST', '/api/users', userData);
            if (user && user.id) {
                this.users.push({
                    id: user.id,
                    persona: personas[i],
                    checkins: 0,
                    journals: 0,
                    insights: 0,
                    isPremium: false,
                    conversionDay: null
                });
                if (i < 3) console.log(`   Created user: ${user.id}`);
            } else {
                console.log(`   Failed to create user ${i}:`, user);
            }
        }
        
        console.log(`✅ Created ${this.users.length} users\n`);
    }

    async simulateDay(day) {
        console.log(`\n🌅 DAY ${day}`);
        console.log('='.repeat(60));
        
        let dayCheckIns = 0;
        let dayJournals = 0;
        let dayInsights = 0;
        let activeUsers = 0;
        let conversionsToday = 0;
        
        // Simulate user activities
        for (const user of this.users) {
            if (user.isPremium) continue; // Skip premium users
            let userDidSomething = false;
            
            // Check-in (80% probability)
            if (Math.random() < CHECKIN_PROBABILITY) {
                const checkinResult = await this.makeRequest('POST', '/api/check-ins', {
                    user_id: user.id,
                    day_part: 'morning',
                    mood: this.generateRandomMood(),
                    contexts: ['work', 'health'],
                    micro_act: 'gratitude'
                });
                if (checkinResult && (checkinResult.success || checkinResult.id)) {
                    user.checkins++;
                    dayCheckIns++;
                    this.stats.totalCheckIns++;
                    userDidSomething = true;
                } else if (day === 1 && user === this.users[0]) {
                    console.log(`   Warning: Check-in failed for user ${user.id}:`, checkinResult);
                }
            }
            
            // Journal (after 2 check-ins, 30% probability)
            if (user.checkins >= 2 && Math.random() < 0.3) {
                await this.makeRequest('POST', '/api/journals/generate', {
                    userId: user.id,
                    tone: 'reflective'
                });
                user.journals++;
                dayJournals++;
                this.stats.totalJournals++;
                userDidSomething = true;
            }
            
            // Insights (starting from INSIGHTS_START_DAY, after 4+ check-ins)
            if (day >= INSIGHTS_START_DAY && user.checkins >= 4 && Math.random() < 0.5) {
                const insights = await this.makeRequest('POST', '/api/insights/generate', {
                    userId: user.id
                });
                if (insights && insights.generated > 0) {
                    user.insights += insights.generated;
                    dayInsights += insights.generated;
                    this.stats.totalInsights += insights.generated;
                    userDidSomething = true;
                }
            }
            
            if (userDidSomething) {
                activeUsers++;
            }
        }
        
        // Check for premium conversions
        conversionsToday = await this.checkConversions(day);
        this.stats.totalPremium += conversionsToday;
        
        const dayStats = {
            day,
            activeUsers,
            checkIns: dayCheckIns,
            journals: dayJournals,
            insights: dayInsights,
            conversions: conversionsToday,
            premium: this.stats.totalPremium
        };
        this.stats.dailyStats.push(dayStats);
        
        console.log(`📊 Day ${day} Summary:`);
        console.log(`   Active Users: ${activeUsers}/${this.users.length - this.stats.totalPremium} free users`);
        console.log(`   Check-ins: ${dayCheckIns} (Total: ${this.stats.totalCheckIns})`);
        console.log(`   Journals: ${dayJournals} (Total: ${this.stats.totalJournals})`);
        console.log(`   Insights: ${dayInsights} (Total: ${this.stats.totalInsights})`);
        console.log(`   Conversions: ${conversionsToday} (Total Premium: ${this.stats.totalPremium})`);
        
        return day;
    }

    async checkConversions(day) {
        let conversions = 0;
        
        for (const user of this.users) {
            if (user.isPremium) continue; // Already converted
            
            // Only check conversions after day 3
            if (day >= 3 && user.checkins >= 4) {
                try {
                    const convData = await this.makeRequest('POST', '/api/conversion/calculate', {
                        userId: user.id,
                        currentDay: day
                    });
                    
                    if (convData && convData.conversionProbability) {
                        const prob = convData.conversionProbability;
                        
                        // 5% of eligible users convert
                        if (prob >= 0.05 && Math.random() < 0.05) {
                            const upgrade = await this.makeRequest('POST', `/api/users/${user.id}/premium`, {
                                tier: 'premium',
                                plan: 'monthly'
                            });
                            
                            if (upgrade && upgrade.success) {
                                user.isPremium = true;
                                user.conversionDay = day;
                                conversions++;
                                console.log(`   💎 User converted (${user.checkins} check-ins, ${user.insights} insights, day ${day})`);
                            }
                        }
                    }
                } catch (error) {
                    // Ignore conversion errors
                }
            }
        }
        
        return conversions;
    }

    async run() {
        console.log('🚀 Starting Insights-Focused Simulation');
        console.log(`📅 Duration: ${TOTAL_DAYS} days`);
        console.log(`📊 Daily Check-in Rate: ${CHECKIN_PROBABILITY * 100}%`);
        console.log(`📊 Insights Start: Day ${INSIGHTS_START_DAY}`);
        console.log('='.repeat(60));
        
        await this.createUsers();
        
        for (let day = 1; day <= TOTAL_DAYS; day++) {
            await this.simulateDay(day);
            
            if (day < TOTAL_DAYS) {
                await this.delay(DAY_DURATION_MS);
            }
        }
        
        // Final stats
        console.log('\n' + '='.repeat(60));
        console.log('🎉 SIMULATION COMPLETE!');
        console.log('='.repeat(60));
        console.log(`📊 FINAL STATISTICS:`);
        console.log(`   Total Users: ${this.users.length}`);
        console.log(`   Total Check-ins: ${this.stats.totalCheckIns}`);
        console.log(`   Total Journals: ${this.stats.totalJournals}`);
        console.log(`   Total Insights: ${this.stats.totalInsights}`);
        console.log(`   ** Premium Users: ${this.stats.totalPremium} **`);
        console.log(`   ** Conversion Rate: ${((this.stats.totalPremium / this.users.length) * 100).toFixed(2)}% **`);
        
        // Daily breakdown
        console.log('\n📈 DAILY BREAKDOWN:');
        this.stats.dailyStats.forEach(stat => {
            console.log(`   Day ${stat.day}: ${stat.activeUsers} active, ${stat.checkIns} check-ins, ${stat.journals} journals, ${stat.insights} insights, ${stat.conversions} conversions`);
        });
    }
}

// Run simulation
const sim = new InsightsFocusedSim();
sim.run().catch(console.error);

