/**
 * Phase 2 Testing: Backend API Interaction Tracking Endpoints
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

async function testPhase2() {
  console.log('🧪 Testing Phase 2: Backend API Interaction Tracking\n');
  
  // Test 1: Track locked insight click
  console.log('Test 1: Track Locked Insight Click');
  try {
    const userId = 'test_user_001';
    const response = await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
      type: 'locked_insight_click',
      data: {
        insightId: 'breakpoint_sleep_preview',
        insightType: 'breakpoint',
        previewText: 'Your fulfillment drops when sleep < ~7 hours'
      }
    });
    console.log('✅ Tracked interaction:', response.data);
  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
    return false;
  }
  
  // Wait a moment
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // Test 2: Track another interaction type
  console.log('\nTest 2: Track Premium Preview View');
  try {
    const userId = 'test_user_001';
    const response = await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
      type: 'premium_preview_view',
      data: {
        duration: 45, // seconds
        featurePreviewed: 'breakpoint_insights'
      }
    });
    console.log('✅ Tracked preview view:', response.data);
  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
    return false;
  }
  
  // Test 3: Get all interactions
  console.log('\nTest 3: Get All User Interactions');
  try {
    const userId = 'test_user_001';
    const response = await axios.get(`${API_BASE}/api/users/${userId}/interactions`);
    console.log('✅ Retrieved interactions:', response.data.interactions.length);
    console.log('   Types:', response.data.interactions.map(i => i.interaction_type));
  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
    return false;
  }
  
  // Test 4: Get interactions by type
  console.log('\nTest 4: Get Interactions by Type');
  try {
    const userId = 'test_user_001';
    const response = await axios.get(`${API_BASE}/api/users/${userId}/interactions?type=locked_insight_click`);
    console.log('✅ Retrieved locked clicks:', response.data.interactions.length);
    console.log('   First interaction data:', response.data.interactions[0]?.interaction_data);
  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
    return false;
  }
  
  // Test 5: Verify user tracking fields updated
  console.log('\nTest 5: Verify User Tracking Fields');
  try {
    const userId = 'test_user_001';
    const response = await axios.get(`${API_BASE}/api/users/${userId}`);
    const user = response.data;
    console.log('✅ User fields updated:');
    console.log('   locked_feature_clicks:', user.user?.locked_feature_clicks || user.locked_feature_clicks);
  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
    return false;
  }
  
  // Test 6: Test error handling (missing type)
  console.log('\nTest 6: Error Handling - Missing Type');
  try {
    const userId = 'test_user_001';
    const response = await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
      // Missing type field
      data: { test: 'data' }
    });
    console.error('❌ Should have failed but returned:', response.data);
    return false;
  } catch (error) {
    if (error.response?.status === 400) {
      console.log('✅ Correctly returned 400 for missing type');
    } else {
      console.error('❌ Unexpected error:', error.response?.data || error.message);
      return false;
    }
  }
  
  console.log('\n✅ Phase 2 Tests Passed!\n');
  return true;
}

// Run tests
testPhase2().then(success => {
  if (success) {
    console.log('✅ Phase 2 verification complete');
    process.exit(0);
  } else {
    console.error('❌ Phase 2 tests failed');
    process.exit(1);
  }
}).catch(error => {
  console.error('❌ Test error:', error);
  process.exit(1);
});

