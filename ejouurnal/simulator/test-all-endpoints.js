const axios = require('axios');

const API_BASE = 'http://localhost:3005';

async function testAllEndpoints() {
  console.log('🧪 Testing All Endpoints for 404s');
  console.log('==================================');
  
  const tests = [
    // GET endpoints
    { method: 'GET', path: '/health', expectedStatus: 200 },
    { method: 'GET', path: '/api/analytics', expectedStatus: 200 },
    
    // POST endpoints with valid data
    { method: 'POST', path: '/api/users', data: { name: 'Test User', email: 'test@example.com', persona: 'engaged' }, expectedStatus: 200 },
    { method: 'POST', path: '/api/check-ins', data: { user_id: 'test', daypart: 'morning', mood: 'good' }, expectedStatus: 200 },
    { method: 'POST', path: '/api/details', data: { userId: 'test', sleepHours: 8, sleepQuality: 4 }, expectedStatus: 200 },
    { method: 'POST', path: '/api/journals/generate', data: { user_id: 'test', journalTone: 'reflective' }, expectedStatus: 200 },
    { method: 'POST', path: '/api/insights/generate', data: { user_id: 'test' }, expectedStatus: 200 },
    { method: 'POST', path: '/api/conversion/calculate', data: { userId: 'test', currentDay: 1 }, expectedStatus: 200 },
    { method: 'POST', path: '/api/conversion/offer', data: { userId: 'test', currentDay: 1 }, expectedStatus: 200 },
    { method: 'POST', path: '/api/onboarding/flow', data: { userId: 'test' }, expectedStatus: 200 },
    { method: 'POST', path: '/api/value-proposition', data: { userId: 'test', context: {} }, expectedStatus: 200 },
    
    // Test invalid endpoints (should return 404)
    { method: 'GET', path: '/api/invalid', expectedStatus: 404 },
    { method: 'POST', path: '/api/invalid', data: {}, expectedStatus: 404 },
  ];
  
  let passed = 0;
  let failed = 0;
  let unexpected404s = 0;
  
  for (const test of tests) {
    try {
      const config = {
        method: test.method,
        url: `${API_BASE}${test.path}`,
        headers: { 'Content-Type': 'application/json' }
      };
      
      if (test.data) {
        config.data = test.data;
      }
      
      const response = await axios(config);
      const status = response.status;
      
      if (status === test.expectedStatus) {
        console.log(`✅ ${test.method} ${test.path} - ${status} (expected)`);
        passed++;
      } else {
        console.log(`❌ ${test.method} ${test.path} - ${status} (expected ${test.expectedStatus})`);
        failed++;
      }
      
      // Check for unexpected 404s
      if (status === 404 && test.expectedStatus !== 404) {
        unexpected404s++;
        console.log(`   🚨 UNEXPECTED 404: ${test.method} ${test.path}`);
      }
      
    } catch (error) {
      const status = error.response?.status || 'ERROR';
      
      if (status === test.expectedStatus) {
        console.log(`✅ ${test.method} ${test.path} - ${status} (expected)`);
        passed++;
      } else {
        console.log(`❌ ${test.method} ${test.path} - ${status} (expected ${test.expectedStatus})`);
        failed++;
      }
      
      // Check for unexpected 404s
      if (status === 404 && test.expectedStatus !== 404) {
        unexpected404s++;
        console.log(`   🚨 UNEXPECTED 404: ${test.method} ${test.path}`);
      }
    }
    
    // Small delay to avoid overwhelming the server
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  console.log('\n📊 Test Results:');
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`🚨 Unexpected 404s: ${unexpected404s}`);
  
  if (unexpected404s === 0) {
    console.log('\n🎉 No unexpected 404s found! All endpoints working correctly.');
  } else {
    console.log('\n⚠️  Found unexpected 404s that need fixing.');
  }
}

testAllEndpoints().catch(console.error);
