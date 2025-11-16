/**
 * Phase 1 Testing: Database Schema and Helpers
 */

const { dbHelpers } = require('./backend/database-sqlite');

async function testPhase1() {
  console.log('🧪 Testing Phase 1: Database Schema Updates\n');
  
  // Setup: Create test user
  console.log('Setup: Create test user');
  try {
    const userId = 'test_user_001';
    dbHelpers.createUser(userId, 'Test User', 'test@example.com');
    console.log('✅ Test user created');
  } catch (error) {
    console.log('User may already exist, continuing...');
  }
  
  // Test 1: Track Interaction
  console.log('\nTest 1: Track User Interaction');
  try {
    const userId = 'test_user_001';
    const result = dbHelpers.trackInteraction(userId, 'locked_insight_click', {
      insightId: 'breakpoint_sleep',
      insightType: 'breakpoint'
    });
    console.log('✅ Tracked interaction:', result);
  } catch (error) {
    console.error('❌ Error:', error.message);
    return false;
  }
  
  // Test 2: Get Interactions by Type
  console.log('\nTest 2: Get Interactions by Type');
  try {
    const interactions = dbHelpers.getUserInteractionsByType('test_user_001', 'locked_insight_click');
    console.log('✅ Retrieved interactions:', interactions.length);
    console.log('   First interaction:', interactions[0]);
  } catch (error) {
    console.error('❌ Error:', error.message);
    return false;
  }
  
  // Test 3: Update Conversion Tracking
  console.log('\nTest 3: Update Conversion Tracking Fields');
  try {
    dbHelpers.updateConversionTracking('test_user_001', {
      locked_feature_clicks: 1,
      premium_preview_time: 45
    });
    console.log('✅ Updated conversion tracking');
    
    // Verify update
    const user = dbHelpers.getUser('test_user_001');
    if (user) {
      console.log('   locked_feature_clicks:', user.locked_feature_clicks);
      console.log('   premium_preview_time:', user.premium_preview_time);
    }
  } catch (error) {
    console.error('❌ Error:', error.message);
    return false;
  }
  
  // Test 4: Get All Interactions
  console.log('\nTest 4: Get All User Interactions');
  try {
    const allInteractions = dbHelpers.getUserInteractions('test_user_001');
    console.log('✅ Retrieved all interactions:', allInteractions.length);
  } catch (error) {
    console.error('❌ Error:', error.message);
    return false;
  }
  
  console.log('\n✅ Phase 1 Tests Passed!\n');
  return true;
}

// Run tests
testPhase1().then(success => {
  if (success) {
    console.log('✅ Phase 1 verification complete');
    process.exit(0);
  } else {
    console.error('❌ Phase 1 tests failed');
    process.exit(1);
  }
}).catch(error => {
  console.error('❌ Test error:', error);
  process.exit(1);
});

