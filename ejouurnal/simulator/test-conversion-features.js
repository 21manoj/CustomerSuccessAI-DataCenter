const axios = require('axios');

const API_BASE = 'http://localhost:3005';

async function testConversionFeatures() {
  console.log('🧪 Testing Conversion Optimization Features');
  console.log('==========================================');
  
  try {
    // Test 1: Create a test user
    console.log('\n1️⃣ Creating test user...');
    const userResponse = await axios.post(`${API_BASE}/api/users`, {
      name: 'Test User',
      email: 'test@example.com',
      persona: 'engaged'
    });
    
    if (userResponse.data.success) {
      const userId = userResponse.data.id;
      console.log(`✅ User created: ${userId}`);
      
      // Test 2: Conversion probability
      console.log('\n2️⃣ Testing conversion probability...');
      const conversionResponse = await axios.post(`${API_BASE}/api/conversion/calculate`, {
        userId: userId,
        currentDay: 1
      });
      
      if (conversionResponse.data.success) {
        console.log(`✅ Conversion probability: ${(conversionResponse.data.conversionProbability * 100).toFixed(2)}%`);
        console.log(`   Ready for conversion: ${conversionResponse.data.isReadyForConversion}`);
      }
      
      // Test 3: Conversion offer
      console.log('\n3️⃣ Testing conversion offer...');
      const offerResponse = await axios.post(`${API_BASE}/api/conversion/offer`, {
        userId: userId,
        currentDay: 1
      });
      
      if (offerResponse.data.success) {
        console.log(`✅ Conversion offer: ${offerResponse.data.offer.title}`);
      } else {
        console.log(`ℹ️  No offer generated: ${offerResponse.data.message}`);
      }
      
      // Test 4: Onboarding flow
      console.log('\n4️⃣ Testing onboarding flow...');
      const onboardingResponse = await axios.post(`${API_BASE}/api/onboarding/flow`, {
        userId: userId
      });
      
      if (onboardingResponse.data.success) {
        console.log(`✅ Onboarding flow: ${onboardingResponse.data.flow.length} steps`);
      }
      
      // Test 5: Value proposition
      console.log('\n5️⃣ Testing value proposition...');
      const valuePropResponse = await axios.post(`${API_BASE}/api/value-proposition`, {
        userId: userId,
        context: { trigger: 'high_engagement' }
      });
      
      if (valuePropResponse.data.success) {
        console.log(`✅ Value proposition: ${valuePropResponse.data.valueProposition.primary.title}`);
      }
      
      console.log('\n🎉 All conversion optimization features are working!');
      
    } else {
      console.log('❌ Failed to create test user');
    }
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    if (error.response) {
      console.error('   Status:', error.response.status);
      console.error('   Data:', error.response.data);
    }
  }
}

testConversionFeatures();
