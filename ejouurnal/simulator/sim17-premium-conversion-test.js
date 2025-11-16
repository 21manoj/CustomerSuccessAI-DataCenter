const axios = require('axios');

const API_BASE = 'http://localhost:3005';
const MAX_USERS = 50;
const TOTAL_DAYS = 10;
const DAY_DURATION_MS = 60 * 1000; // 1 minute per day
const REQUEST_DELAY = 50;

const PERSONAS = {
    'strugglers': { checkin_prob: 0.5 },
    'casual': { checkin_prob: 0.7 },
    'engaged': { checkin_prob: 0.9 },
    'premium': { checkin_prob: 0.95 }
};

const MOODS = ['very-low', 'low', 'neutral', 'good', 'great'];

class PremiumConversionTest {
    constructor() {
        this.users = [];
        this.stats = {
            totalCheckIns: 0,
            totalJournals: 0,
            totalInsights: 0,
            totalPremium: 0,
            conversionEvents: []
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
            if (error.message.includes('ECONNREFUSED')) {
                console.error('❌ Server not running!');
                process.exit(1);
            }
            return null;
        }
    }

    generateRandomMood() {
        return MOODS[Math.floor(Math.random() * MOODS.length)];
    }

    async createUsers() {
        console.log(`👥 Creating ${MAX_USERS} users...`);
        
        for (let i = 0; i < MAX_USERS; i++) {
            const personaKeys = Object.keys(PERSONAS);
            const persona = personaKeys[Math.floor(Math.random() * personaKeys.length)];
            
            const userData = {
                name: `User_${i + 1}`,
                email: `user_${i + 1}_${Date.now()}@example.com`,
                persona: persona
            };

            const user = await this.makeRequest('POST', '/api/users', userData);
            if (user && user.id) {
                this.users.push({
                    id: user.id,
                    persona: persona,
                    checkins: 0,
                    journals: 0,
                    insights: 0,
                    isPremium: false,
                    conversionDay: null
                });
            }
        }
        
        console.log(`✅ Created ${this.users.length} users\n`);
    }

    async simulateDay(day) {
        console.log(`\n🌅 DAY ${day}`);
        console.log('='.repeat(50));
        
        let dayCheckIns = 0;
        let dayJournals = 0;
        let dayInsights = 0;
        let activeUsers = 0;
        
        // Simulate user activities
        for (const user of this.users) {
            let userDidSomething = false;
            const persona = PERSONAS[user.persona];
            
            // Check-in
            if (Math.random() < persona.checkin_prob) {
                await this.makeRequest('POST', '/api/check-ins', {
                    user_id: user.id,
                    day_part: 'morning',
                    mood: this.generateRandomMood(),
                    contexts: ['work', 'health'],
                    micro_act: 'gratitude'
                });
                user.checkins++;
                dayCheckIns++;
                this.stats.totalCheckIns++;
                userDidSomething = true;
            }
            
            // Journal (after some check-ins)
            if (user.checkins >= 3 && Math.random() < 0.3) {
                await this.makeRequest('POST', '/api/journals/generate', {
                    userId: user.id,
                    tone: 'reflective'
                });
                user.journals++;
                dayJournals++;
                this.stats.totalJournals++;
                userDidSomething = true;
            }
            
            // Insights (after 4 check-ins)
            if (user.checkins >= 4 && Math.random() < 0.4) {
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
        await this.checkConversions(day);
        
        console.log(`📊 Day ${day} Summary:`);
        console.log(`   Active Users: ${activeUsers}/${this.users.length}`);
        console.log(`   Check-ins: ${dayCheckIns} (Total: ${this.stats.totalCheckIns})`);
        console.log(`   Journals: ${dayJournals} (Total: ${this.stats.totalJournals})`);
        console.log(`   Insights: ${dayInsights} (Total: ${this.stats.totalInsights})`);
        console.log(`   Premium: ${this.stats.totalPremium} users`);
        
        return day;
    }

    async checkConversions(day) {
        for (const user of this.users) {
            if (user.isPremium) continue; // Already converted
            
            // Check conversion probability
            try {
                const convData = await this.makeRequest('POST', '/api/conversion/calculate', {
                    userId: user.id,
                    currentDay: day
                });
                
                if (convData && convData.conversionProbability) {
                    const prob = convData.conversionProbability;
                    
                    // Attempt conversion based on probability
                    if (prob >= 0.05 && Math.random() < 0.02) { // 2% of eligible users
                        const upgrade = await this.makeRequest('POST', `/api/users/${user.id}/premium`, {
                            tier: 'premium',
                            plan: 'monthly'
                        });
                        
                        if (upgrade && upgrade.success) {
                            user.isPremium = true;
                            user.conversionDay = day;
                            this.stats.totalPremium++;
                            this.stats.conversionEvents.push({
                                userId: user.id,
                                day,
                                probability: prob,
                                persona: user.persona,
                                checkins: user.checkins,
                                insights: user.insights
                            });
                            console.log(`💎 User ${user.id.substring(0, 8)}... converted on day ${day} (${(prob * 100).toFixed(1)}% prob)`);
                        }
                    }
                }
            } catch (error) {
                // Ignore conversion errors
            }
        }
    }

    async run() {
        console.log('🚀 Starting Premium Conversion Test');
        console.log(`📅 Duration: ${TOTAL_DAYS} days`);
        console.log(`👥 Users: ${MAX_USERS}`);
        console.log('='.repeat(50));
        
        await this.createUsers();
        
        for (let day = 1; day <= TOTAL_DAYS; day++) {
            await this.simulateDay(day);
            
            if (day < TOTAL_DAYS) {
                await this.delay(DAY_DURATION_MS);
            }
        }
        
        // Final stats
        console.log('\n' + '='.repeat(50));
        console.log('🎉 SIMULATION COMPLETE!');
        console.log('='.repeat(50));
        console.log(`📊 FINAL STATISTICS:`);
        console.log(`   Total Users: ${this.users.length}`);
        console.log(`   Total Check-ins: ${this.stats.totalCheckIns}`);
        console.log(`   Total Journals: ${this.stats.totalJournals}`);
        console.log(`   Total Insights: ${this.stats.totalInsights}`);
        console.log(`   ** Premium Users: ${this.stats.totalPremium} **`);
        console.log(`   ** Conversion Rate: ${((this.stats.totalPremium / this.users.length) * 100).toFixed(2)}% **`);
        
        if (this.stats.conversionEvents.length > 0) {
            console.log(`\n💎 Conversion Events:`);
            this.stats.conversionEvents.forEach(conv => {
                console.log(`   Day ${conv.day}: User converted with ${conv.checkins} check-ins, ${conv.insights} insights`);
            });
        }
    }
}

// Run simulation
const sim = new PremiumConversionTest();
sim.run().catch(console.error);

