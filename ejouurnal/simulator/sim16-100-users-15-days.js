const axios = require('axios');

const API_BASE = 'http://localhost:3005';
const MAX_USERS = 100;
const TOTAL_DAYS = 15;
const DAY_DURATION_MS = 2 * 60 * 1000; // 2 minutes per day
const TOTAL_SIMULATION_MS = 30 * 60 * 1000; // 30 minutes total
const REQUEST_DELAY = 100; // 100ms between requests

// User personas with different behaviors
const PERSONAS = {
    'strugglers': { checkin_prob: 0.6, journal_prob: 0.1, insight_prob: 0.05 },
    'casual': { checkin_prob: 0.8, journal_prob: 0.3, insight_prob: 0.15 },
    'engaged': { checkin_prob: 0.95, journal_prob: 0.6, insight_prob: 0.4 },
    'premium': { checkin_prob: 0.98, journal_prob: 0.8, insight_prob: 0.6 }
};

// Mood distribution
const MOODS = ['very-low', 'low', 'neutral', 'good', 'great'];
const MOOD_WEIGHTS = [0.2, 0.2, 0.2, 0.2, 0.2];

// Micro-moves
const MICRO_MOVES = ['gratitude', 'meditation', 'exercise', 'reading', 'journaling', 'breathing'];

class Simulation16 {
    constructor() {
        this.users = [];
        this.stats = {
            totalCheckIns: 0,
            totalJournals: 0,
            totalInsights: 0,
            dailyStats: []
        };
        this.startTime = null;
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
            console.error(`❌ Request failed: ${method} ${endpoint}`, error.message);
            return null;
        }
    }

    generateRandomMood() {
        const random = Math.random();
        let cumulative = 0;
        for (let i = 0; i < MOODS.length; i++) {
            cumulative += MOOD_WEIGHTS[i];
            if (random <= cumulative) {
                return MOODS[i];
            }
        }
        return 'neutral';
    }

    async createUsers() {
        console.log('👥 Creating 100 users...');
        
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
                    lastCheckinDay: 0
                });
            }
        }
        
        console.log(`✅ Created ${this.users.length} users`);
    }

    async simulateDay(day) {
        const dayStartTime = new Date();
        console.log(`\n🌅 DAY ${day} - ${dayStartTime.toLocaleTimeString()}`);
        console.log('='.repeat(50));
        
        let dayCheckIns = 0;
        let dayJournals = 0;
        let dayInsights = 0;
        
        // Process each user for this day
        for (const user of this.users) {
            const persona = PERSONAS[user.persona];
            
            // Check if user does check-in today
            if (Math.random() < persona.checkin_prob) {
                const mood = this.generateRandomMood();
                const microMove = MICRO_MOVES[Math.floor(Math.random() * MICRO_MOVES.length)];
                const contexts = ['work', 'personal', 'health'][Math.floor(Math.random() * 3)];
                
                const checkinData = {
                    user_id: user.id,
                    day_part: 'morning',
                    mood: mood,
                    contexts: [contexts],
                    micro_act: microMove
                };
                
                const checkin = await this.makeRequest('POST', '/api/check-ins', checkinData);
                if (checkin && checkin.success) {
                    user.checkins++;
                    dayCheckIns++;
                    user.lastCheckinDay = day;
                }
            }
            
            // Generate journal if user has enough check-ins and probability
            if (user.checkins >= 3 && Math.random() < persona.journal_prob) {
                const journalData = {
                    userId: user.id,
                    tone: ['reflective', 'celebratory', 'insightful', 'motivational'][Math.floor(Math.random() * 4)]
                };
                
                const journal = await this.makeRequest('POST', '/api/journals/generate', journalData);
                if (journal && journal.success) {
                    user.journals++;
                    dayJournals++;
                }
            }
            
            // Generate insights starting day 4 if user has enough check-ins
            if (day >= 4 && user.checkins >= 4 && Math.random() < persona.insight_prob) {
                const insightData = {
                    userId: user.id
                };
                
                const insights = await this.makeRequest('POST', '/api/insights/generate', insightData);
                if (insights && insights.success && insights.insights && insights.insights.length > 0) {
                    user.insights += insights.insights.length;
                    dayInsights += insights.insights.length;
                }
            }
        }
        
        // Update totals
        this.stats.totalCheckIns += dayCheckIns;
        this.stats.totalJournals += dayJournals;
        this.stats.totalInsights += dayInsights;
        
        // Store daily stats
        this.stats.dailyStats.push({
            day: day,
            checkIns: dayCheckIns,
            journals: dayJournals,
            insights: dayInsights,
            cumulativeCheckIns: this.stats.totalCheckIns,
            cumulativeJournals: this.stats.totalJournals,
            cumulativeInsights: this.stats.totalInsights
        });
        
        // Print day summary
        console.log(`📊 Day ${day} Summary:`);
        console.log(`   Check-ins: ${dayCheckIns} (Total: ${this.stats.totalCheckIns})`);
        console.log(`   Journals: ${dayJournals} (Total: ${this.stats.totalJournals})`);
        console.log(`   Insights: ${dayInsights} (Total: ${this.stats.totalInsights})`);
        
        // Print user activity by persona
        const personaStats = {};
        this.users.forEach(user => {
            if (!personaStats[user.persona]) {
                personaStats[user.persona] = { checkins: 0, journals: 0, insights: 0, count: 0 };
            }
            personaStats[user.persona].checkins += user.checkins;
            personaStats[user.persona].journals += user.journals;
            personaStats[user.persona].insights += user.insights;
            personaStats[user.persona].count++;
        });
        
        console.log(`\n👥 User Activity by Persona:`);
        Object.keys(personaStats).forEach(persona => {
            const stats = personaStats[persona];
            console.log(`   ${persona}: ${stats.count} users, ${stats.checkins} check-ins, ${stats.journals} journals, ${stats.insights} insights`);
        });
        
        const dayEndTime = new Date();
        const dayDuration = dayEndTime - dayStartTime;
        console.log(`⏱️  Day ${day} completed in ${(dayDuration / 1000).toFixed(1)}s`);
    }

    async runSimulation() {
        console.log('🚀 Starting SIM16 - 100 Users, 15 Days Simulation');
        console.log(`📅 Duration: 30 minutes (2 minutes per day)`);
        console.log(`👥 Users: ${MAX_USERS}`);
        console.log(`📊 Days: ${TOTAL_DAYS}`);
        console.log('='.repeat(60));
        
        this.startTime = new Date();
        console.log(`🕐 Simulation started at: ${this.startTime.toLocaleString()}`);
        
        // Create users
        await this.createUsers();
        
        // Simulate each day
        for (let day = 1; day <= TOTAL_DAYS; day++) {
            await this.simulateDay(day);
            
            // Wait for day duration (2 minutes)
            if (day < TOTAL_DAYS) {
                console.log(`⏳ Waiting 2 minutes before Day ${day + 1}...`);
                await this.delay(DAY_DURATION_MS);
            }
        }
        
        // Final summary
        const endTime = new Date();
        const totalDuration = endTime - this.startTime;
        
        console.log('\n' + '='.repeat(60));
        console.log('🎉 SIMULATION COMPLETE!');
        console.log('='.repeat(60));
        console.log(`🕐 Started: ${this.startTime.toLocaleString()}`);
        console.log(`🕐 Ended: ${endTime.toLocaleString()}`);
        console.log(`⏱️  Total Duration: ${(totalDuration / 1000 / 60).toFixed(1)} minutes`);
        
        console.log('\n📊 FINAL STATISTICS:');
        console.log(`   Total Check-ins: ${this.stats.totalCheckIns}`);
        console.log(`   Total Journals: ${this.stats.totalJournals}`);
        console.log(`   Total Insights: ${this.stats.totalInsights}`);
        console.log(`   Average Check-ins per User: ${(this.stats.totalCheckIns / this.users.length).toFixed(1)}`);
        console.log(`   Average Journals per User: ${(this.stats.totalJournals / this.users.length).toFixed(1)}`);
        console.log(`   Average Insights per User: ${(this.stats.totalInsights / this.users.length).toFixed(1)}`);
        
        console.log('\n📈 DAILY BREAKDOWN:');
        this.stats.dailyStats.forEach(day => {
            console.log(`   Day ${day.day}: ${day.checkIns} check-ins, ${day.journals} journals, ${day.insights} insights`);
        });
        
        // Get final analytics from API
        try {
            const analytics = await this.makeRequest('GET', '/api/analytics');
            if (analytics) {
                console.log('\n🔍 API ANALYTICS:');
                console.log(`   Total Users: ${analytics.totalUsers}`);
                console.log(`   Total Check-ins: ${analytics.totalCheckIns}`);
                console.log(`   Total Journals: ${analytics.totalJournals}`);
                console.log(`   Total Insights: ${analytics.totalInsights}`);
            }
        } catch (error) {
            console.error('Failed to get final analytics:', error.message);
        }
    }
}

// Run simulation
const sim = new Simulation16();
sim.runSimulation().catch(console.error);
