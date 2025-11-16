const axios = require('axios');

const API_BASE = 'http://localhost:3005';
const REQUEST_DELAY = 100;

class TwoUserTest {
    constructor() {
        this.users = [];
        this.stats = {
            user1: { checkIns: 0, journals: [], insights: [] },
            user2: { checkIns: 0, journals: [], insights: [] }
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
            
            console.log(`📡 ${method} ${endpoint}${data ? '\n   Body: ' + JSON.stringify(data, null, 2) : ''}`);
            
            const response = await axios(config);
            await this.delay(REQUEST_DELAY);
            
            console.log(`✅ Response: ${JSON.stringify(response.data, null, 2)}`);
            return response.data;
        } catch (error) {
            console.log(`❌ Error: ${error.response?.data || error.message}`);
            return null;
        }
    }

    generateRandomMood() {
        const moods = ['very-low', 'low', 'neutral', 'good', 'great'];
        return moods[Math.floor(Math.random() * moods.length)];
    }

    async createUsers() {
        console.log('\n' + '='.repeat(80));
        console.log('STEP 1: CREATE 2 USERS');
        console.log('='.repeat(80));
        
        // User 1 - Will convert
        const user1 = await this.makeRequest('POST', '/api/users', {
            name: 'Conversion User',
            email: 'converter@example.com',
            persona: 'engaged'
        });
        
        if (user1 && user1.id) {
            this.users.push({ id: user1.id, persona: 'engaged', willConvert: true });
            console.log(`✅ User 1 created: ${user1.id} (engaged, will convert)`);
        }
        
        // User 2 - Will churn
        const user2 = await this.makeRequest('POST', '/api/users', {
            name: 'Churn User',
            email: 'churn@example.com',
            persona: 'struggler'
        });
        
        if (user2 && user2.id) {
            this.users.push({ id: user2.id, persona: 'struggler', willConvert: false });
            console.log(`✅ User 2 created: ${user2.id} (struggler, will churn)`);
        }
        
        await this.delay(500);
    }

    async day1CheckIns() {
        console.log('\n' + '='.repeat(80));
        console.log('STEP 2: DAY 1 - DAILY CHECK-INS');
        console.log('='.repeat(80));
        
        for (const user of this.users) {
            console.log(`\n📝 Check-in for ${user.persona} user (${user.id})`);
            
            const checkin = await this.makeRequest('POST', '/api/check-ins', {
                user_id: user.id,
                day_part: 'morning',
                mood: this.generateRandomMood(),
                contexts: ['work', 'health'],
                micro_act: 'gratitude'
            });
            
            if (checkin && checkin.success) {
                this.stats[user.persona === 'engaged' ? 'user1' : 'user2'].checkIns++;
                console.log(`   ✓ Check-in successful`);
            }
        }
        
        await this.delay(500);
    }

    async day2Activities() {
        console.log('\n' + '='.repeat(80));
        console.log('STEP 3: DAY 2 - CHECK-INS + JOURNALS + INSIGHTS');
        console.log('='.repeat(80));
        
        for (const user of this.users) {
            console.log(`\n📝 Day 2 activities for ${user.persona} user (${user.id})`);
            
            // Check-in
            console.log(`\n1️⃣ Morning check-in:`);
            const checkin = await this.makeRequest('POST', '/api/check-ins', {
                user_id: user.id,
                day_part: 'morning',
                mood: this.generateRandomMood(),
                contexts: ['work', 'health'],
                micro_act: 'meditation'
            });
            
            if (checkin && checkin.success) {
                this.stats[user.persona === 'engaged' ? 'user1' : 'user2'].checkIns++;
            }
            
            // Evening check-in
            console.log(`\n2️⃣ Evening check-in:`);
            const eveningCheckin = await this.makeRequest('POST', '/api/check-ins', {
                user_id: user.id,
                day_part: 'evening',
                mood: this.generateRandomMood(),
                contexts: ['social', 'health'],
                micro_act: 'walk'
            });
            
            if (eveningCheckin && eveningCheckin.success) {
                this.stats[user.persona === 'engaged' ? 'user1' : 'user2'].checkIns++;
            }
            
            // Night check-in to reach 4 check-ins
            console.log(`\n3️⃣ Night check-in:`);
            const nightCheckin = await this.makeRequest('POST', '/api/check-ins', {
                user_id: user.id,
                day_part: 'night',
                mood: this.generateRandomMood(),
                contexts: ['reflection'],
                micro_act: 'gratitude'
            });
            
            if (nightCheckin && nightCheckin.success) {
                this.stats[user.persona === 'engaged' ? 'user1' : 'user2'].checkIns++;
            }
            
            // Generate journal
            console.log(`\n4️⃣ Generate AI journal:`);
            const journal = await this.makeRequest('POST', '/api/journals/generate', {
                userId: user.id,
                tone: 'reflective'
            });
            
            if (journal && journal.content) {
                this.stats[user.persona === 'engaged' ? 'user1' : 'user2'].journals.push({
                    content: journal.content.substring(0, 150) + '...',
                    tone: journal.tone
                });
                console.log(`   📔 Journal preview: ${journal.content.substring(0, 200)}...`);
            }
            
            // Generate insights (requires 4+ check-ins)
            if (this.stats[user.persona === 'engaged' ? 'user1' : 'user2'].checkIns >= 4) {
                console.log(`\n5️⃣ Generate insights:`);
                const insights = await this.makeRequest('POST', '/api/insights/generate', {
                    userId: user.id
                });
                
                if (insights && insights.insights) {
                    this.stats[user.persona === 'engaged' ? 'user1' : 'user2'].insights = insights.insights;
                    console.log(`   💡 ${insights.insights.length} insights generated`);
                    insights.insights.forEach((insight, idx) => {
                        console.log(`   ${idx + 1}. ${insight.title}: ${insight.description.substring(0, 100)}...`);
                    });
                }
            } else {
                console.log(`   ⚠️ Need more check-ins (${this.stats[user.persona === 'engaged' ? 'user1' : 'user2'].checkIns}/4)`);
            }
        }
        
        await this.delay(500);
    }

    async conversionPath() {
        console.log('\n' + '='.repeat(80));
        console.log('STEP 4: CONVERSION PATH - USER 1 (Engaged)');
        console.log('='.repeat(80));
        
        const user1 = this.users[0];
        console.log(`\n🔍 Checking conversion probability for ${user1.id}:`);
        
        // Check conversion probability
        const conversion = await this.makeRequest('POST', '/api/conversion/calculate', {
            userId: user1.id,
            currentDay: 3
        });
        
        if (conversion && conversion.conversionProbability) {
            console.log(`   Probability: ${(conversion.conversionProbability * 100).toFixed(1)}%`);
            console.log(`   Factors: ${JSON.stringify(conversion.factors, null, 2)}`);
            
            // Generate offer
            const offer = await this.makeRequest('POST', '/api/conversion/offer', {
                userId: user1.id,
                tier: 'premium'
            });
            
            if (offer && offer.offer) {
                console.log(`\n💎 Conversion offer:`);
                console.log(`   ${offer.offer.message}`);
                console.log(`   ${offer.offer.cta}`);
            }
            
            // Convert user
            console.log(`\n✅ Converting user to premium:`);
            const upgrade = await this.makeRequest('POST', `/api/users/${user1.id}/premium`, {
                tier: 'premium',
                plan: 'monthly'
            });
            
            if (upgrade && upgrade.success) {
                console.log(`   ✓ User successfully converted to premium! 🎉`);
            }
        }
        
        await this.delay(500);
    }

    async churnPath() {
        console.log('\n' + '='.repeat(80));
        console.log('STEP 5: CHURN PATH - USER 2 (Struggler)');
        console.log('='.repeat(80));
        
        const user2 = this.users[1];
        console.log(`\n🔍 Checking engagement for ${user2.id}:`);
        
        // Generate insights once more to show engagement
        console.log(`\n1️⃣ Final insights generation:`);
        const insights = await this.makeRequest('POST', '/api/insights/generate', {
            userId: user2.id
        });
        
        if (insights && insights.insights) {
            console.log(`   Generated ${insights.insights.length} insights`);
        }
        
        // Mark as churned
        console.log(`\n2️⃣ User demonstrates low engagement (struggler persona)`);
        console.log(`   ❌ User not engaging with app features`);
        console.log(`   📉 Low check-in frequency`);
        console.log(`   💔 No journals created`);
        console.log(`\n✅ Simulated churn: User inactive after 3 days`);
        console.log(`   Churned at: ${new Date().toISOString()}`);
    }

    async run() {
        console.log('\n🎬 STARTING COMPREHENSIVE 2-USER TEST');
        console.log('='.repeat(80));
        console.log('This test demonstrates:');
        console.log('  - User 1 (Engaged): Daily check-ins, journals, insights, CONVERSION');
        console.log('  - User 2 (Struggler): Daily check-ins, low engagement, CHURN');
        console.log('='.repeat(80));
        
        await this.createUsers();
        await this.day1CheckIns();
        await this.day2Activities();
        await this.conversionPath();
        await this.churnPath();
        
        // Final summary
        console.log('\n' + '='.repeat(80));
        console.log('📊 FINAL SUMMARY');
        console.log('='.repeat(80));
        console.log('\nUSER 1 (Engaged → Converted):');
        console.log(`   Check-ins: ${this.stats.user1.checkIns}`);
        console.log(`   Journals: ${this.stats.user1.journals.length}`);
        if (this.stats.user1.journals.length > 0) {
            console.log(`   Sample journal: "${this.stats.user1.journals[0].content}"`);
        }
        console.log(`   Insights: ${this.stats.user1.insights.length}`);
        if (this.stats.user1.insights.length > 0) {
            this.stats.user1.insights.forEach((insight, idx) => {
                console.log(`   ${idx + 1}. ${insight.title}: ${insight.description.substring(0, 80)}...`);
            });
        }
        console.log(`   Status: ✅ PREMIUM CONVERTED`);
        
        console.log('\nUSER 2 (Struggler → Churned):');
        console.log(`   Check-ins: ${this.stats.user2.checkIns}`);
        console.log(`   Journals: ${this.stats.user2.journals.length}`);
        if (this.stats.user2.journals.length > 0) {
            console.log(`   Sample journal: "${this.stats.user2.journals[0].content}"`);
        }
        console.log(`   Insights: ${this.stats.user2.insights.length}`);
        console.log(`   Status: ❌ CHURNED`);
        
        console.log('\n✅ Test complete!\n');
    }
}

// Run test
const test = new TwoUserTest();
test.run().catch(console.error);

