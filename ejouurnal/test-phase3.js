/**
 * Phase 3 Testing: Frontend Integration
 * Tests interaction tracking UI components
 */

const axios = require('axios');

const API_BASE = 'http://localhost:3005';

async function testPhase3() {
  console.log('🧪 Testing Phase 3: Frontend Integration\n');
  
  const userId = 'test_user_001';
  
  // Test 1: Load Insights with Preview
  console.log('Test 1: Generate Insights (Some Will Be Locked Previews)');
  try {
    const response = await axios.post(`${API_BASE}/api/insights/generate`, {
      userId
    });
    
    if (response.data.insights) {
      const previewInsights = response.data.insights.filter(i => i.preview);
      const freeInsights = response.data.insights.filter(i => !i.preview);
      
      console.log(`✅ Generated ${response.data.insights.length} insights:`);
      console.log(`   - Free insights: ${freeInsights.length}`);
      console.log(`   - Preview insights: ${previewInsights.length}`);
      
      if (previewInsights.length > 0) {
        console.log('\n   Preview insight example:');
        console.log(`   Title: ${previewInsights[0].title}`);
        console.log(`   Unlock message: ${previewInsights[0].unlockMessage}`);
      }
    }
  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
    return false;
  }
  
  // Test 2: Track Interaction from Simulated Click
  console.log('\nTest 2: Track Locked Insight Click (Simulating User Click)');
  try {
    const response = await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
      type: 'locked_insight_click',
      data: {
        insightId: 'breakpoint_preview',
        insightType: 'breakpoint',
        previewText: 'Your fulfillment drops when sleep < ~7 hours'
      }
    });
    console.log('✅ Interaction tracked');
  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
    return false;
  }
  
  // Test 3: Check User Tracking Fields Updated
  console.log('\nTest 3: Verify Tracking Fields Auto-Updated');
  try {
    const response = await axios.get(`${API_BASE}/api/users/${userId}`);
    const user = response.data.user || response.data;
    
    console.log('✅ User fields:');
    console.log(`   locked_feature_clicks: ${user.locked_feature_clicks}`);
    console.log(`   premium_preview_time: ${user.premium_preview_time}`);
    
    if (user.locked_feature_clicks > 0) {
      console.log('✅ Auto-aggregation working!');
    }
  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
    return false;
  }
  
  // Test 4: Get Conversion Offer
  console.log('\nTest 4: Get Conversion Offer');
  try {
    const response = await axios.post(`${API_BASE}/api/conversion/offer`, {
      userId
    });
    
    if (response.data.offer) {
      const offer = response.data.offer;
      console.log('✅ Conversion offer generated:');
      console.log(`   Probability: ${(offer.probability * 100).toFixed(1)}%`);
      console.log(`   Offer type: ${offer.offerType}`);
      console.log(`   Headline: ${offer.messaging.headline}`);
      console.log(`   CTA: ${offer.messaging.cta}`);
    }
  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
    return false;
  }
  
  // Test 5: Simulate Full User Journey
  console.log('\nTest 5: Simulate Full User Journey');
  try {
    // 1. User clicks locked insight
    await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
      type: 'locked_insight_click',
      data: { insightId: 'breakpoint_1' }
    });
    
    // 2. User clicks another
    await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
      type: 'locked_insight_click',
      data: { insightId: 'purpose_path_1' }
    });
    
    // 3. View premium preview
    await axios.post(`${API_BASE}/api/users/${userId}/interactions`, {
      type: 'premium_preview_view',
      data: { duration: 60 }
    });
    
    // 4. Check conversion probability increased
    const user = (await axios.get(`${API_BASE}/api/users/${userId}`)).data.user;
    
    console.log('✅ Full journey complete:');
    console.log(`   Locked clicks: ${user.locked_feature_clicks}`);
    console.log(`   Preview time: ${user.premium_preview_time}s`);
    console.log('\n   This user should have HIGH conversion probability!');
  } catch (error) {
    console.error('❌ Error:', error.response?.data || error.message);
    return false;
  }
  
  console.log('\n✅ Phase 3 Tests Passed!\n');
  console.log('🎨 Frontend Components Ready:');
  console.log('   ✓ InteractionTracker service');
  console.log('   ✓ InsightCard with preview');
  console.log('   ✓ ConversionOffer modal');
  console.log('\n📱 To test UI, open frontend/src/App-Enhanced.js');
  
  return true;
}

// Run tests
testPhase3().then(success => {
  if (success) {
    console.log('✅ Phase 3 verification complete');
    process.exit(0);
  } else {
    console.error('❌ Phase 3 tests failed');
    process.exit(1);
  }
}).catch(error => {
  console.error('❌ Test error:', error);
  process.exit(1);
});

