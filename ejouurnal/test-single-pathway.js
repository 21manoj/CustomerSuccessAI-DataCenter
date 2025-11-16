/**
 * Simple test for one pathway to debug the conversion offer
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

async function test() {
  try {
    // Create unique user
    const timestamp = Date.now();
    const user = await axios.post(`${API_BASE}/api/users`, {
      name: `TestUser_${timestamp}`,
      email: `test${timestamp}@example.com`,
      persona: 'engaged'
    });
    console.log('✅ User created:', user.data.id);
    
    // Add check-ins
    console.log('📝 Adding check-ins...');
    for(let i=0; i<12; i++) {
      await axios.post(`${API_BASE}/api/check-ins`, {
        user_id: user.data.id,
        day_part: i < 4 ? 'morning' : 'evening',
        mood: 'good',
        contexts: ['test'],
        micro_act: 'test activity'
      });
    }
    console.log('✅ 12 check-ins added');
    
    // Get offer
    console.log('🎯 Getting conversion offer...');
    const offer = await axios.post(`${API_BASE}/api/conversion/offer`, {
      userId: user.data.id,
      currentDay: 14
    });
    
    console.log('\n📊 Offer Response:');
    console.log(JSON.stringify(offer.data, null, 2));
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    if (error.response) {
      console.error('Response:', error.response.data);
    }
  }
}

test();

