/**
 * BACKEND SERVER WITH SQLITE
 * Simplified version for simulation - no PostgreSQL needed!
 */

require('dotenv').config(); // Load .env file FIRST!

const express = require('express');
const cors = require('cors');
const { db, dbHelpers } = require('./database-sqlite');
const journalGenerator = require('./services/JournalGenerator'); // Already an instance!
const conversionOptimizer = require('./services/ConversionOptimizer');
const onboardingOptimizer = require('./services/OnboardingOptimizer');
const valuePropositionOptimizer = require('./services/ValuePropositionOptimizer');

const app = express();
const PORT = process.env.PORT || 3005;

// Middleware
app.use(cors());
app.use(express.json());

console.log('╔════════════════════════════════════════════════════════════╗');
console.log('║     FULFILLMENT APP - BACKEND API (SQLite)                 ║');
console.log('╚════════════════════════════════════════════════════════════╝');

// Health check
app.get('/health', (req, res) => {
  const analytics = dbHelpers.getAnalytics();
  res.json({
    status: 'healthy',
    database: 'connected',
    ...analytics
  });
});

// === USERS ===
app.post('/api/users', (req, res) => {
  try {
    const { userId, name, email } = req.body;
    dbHelpers.createUser(userId, name, email);
    res.json({ success: true, userId });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.get('/api/users/:userId', (req, res) => {
  const user = dbHelpers.getUser(req.params.userId);
  if (user) {
    res.json({ success: true, user });
  } else {
    res.status(404).json({ error: 'User not found' });
  }
});

// === INTENTIONS ===
app.post('/api/intentions', (req, res) => {
  try {
    const { userId, intention, microMoves, antiGlitter } = req.body;
    const result = dbHelpers.createIntention(userId, intention, microMoves, antiGlitter);
    res.json({ success: true, intentionId: result.lastInsertRowid });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.get('/api/intentions/:userId', (req, res) => {
  const intentions = dbHelpers.getIntentionsForUser(req.params.userId);
  res.json({ success: true, intentions });
});

// === CHECK-INS ===
app.post('/api/check-ins', (req, res) => {
  try {
    const { userId, dayPart, mood, contexts, microAct, purposeProgress } = req.body;
    const result = dbHelpers.createCheckIn(userId, dayPart, mood, contexts, microAct, purposeProgress);
    res.json({ success: true, checkInId: result.lastInsertRowid });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.get('/api/check-ins/:userId', (req, res) => {
  const checkIns = dbHelpers.getCheckInsForUser(req.params.userId, 20);
  res.json({ success: true, checkIns });
});

// === DETAILS ===
app.post('/api/details', (req, res) => {
  try {
    const { userId, ...details } = req.body;
    const result = dbHelpers.createDetails(userId, details);
    res.json({ success: true, detailsId: result.lastInsertRowid });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// === JOURNALS ===
app.post('/api/journals/generate', async (req, res) => {
  try {
    const { userId, tone = 'reflective' } = req.body;
    
    // Get user's recent data
    const checkIns = dbHelpers.getCheckInsForUser(userId, 10).map(c => ({
      ...c,
      contexts: c.contexts ? JSON.parse(c.contexts) : []
    }));
    
    const details = dbHelpers.getDetailsForUser(userId) || {};
    const intentions = dbHelpers.getIntentionsForUser(userId);
    const intention = intentions.length > 0 ? intentions[0] : null;
    
    const userData = {
      checkIns: checkIns.map(c => ({
        mood: c.mood,
        contexts: c.contexts,
        microAct: c.micro_act,
        purposeProgress: c.purpose_progress
      })),
      details: {
        sleepHours: details.sleep_hours,
        sleepQuality: details.sleep_quality,
        exerciseType: details.exercise_type,
        exerciseDuration: details.exercise_duration,
        exerciseIntensity: details.exercise_intensity,
        exerciseFeeling: details.exercise_feeling,
        breakfastNotes: details.breakfast_notes,
        lunchNotes: details.lunch_notes,
        dinnerNotes: details.dinner_notes,
        hydration: details.hydration,
        foodQuality: details.food_quality,
        socialMinutes: details.social_minutes,
        screenMinutes: details.screen_minutes,
      },
      weeklyIntention: intention ? intention.intention : '',
      microMoves: intention ? JSON.parse(intention.micro_moves || '[]').map(m => ({ description: m })) : [],
      scores: {},
    };
    
    // Generate journal using AI with enhanced engagement
    const content = await journalGenerator.generateEngagingJournal(userData, tone);
    
    // Save to database
    const result = dbHelpers.createJournal(userId, content, tone);
    
    res.json({
      success: true,
      journal: {
        id: result.lastInsertRowid,
        content,
        tone,
      }
    });
  } catch (error) {
    console.error('Error generating journal:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/journals/user/:userId', (req, res) => {
  const limit = parseInt(req.query.limit) || 10;
  const journals = dbHelpers.getJournalsForUser(req.params.userId, limit);
  res.json({ success: true, journals });
});

// === INSIGHTS ===
app.post('/api/insights/generate/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    
    // Get user's data for insight generation
    const checkIns = dbHelpers.getCheckInsForUser(userId, 30);
    const details = dbHelpers.getDetailsForUser(userId);
    
    // Simple insight generation (basic version for simulation)
    const insights = [];
    
    // Same-day correlation
    const walkCheckIns = checkIns.filter(c => c.micro_act === 'walk');
    if (walkCheckIns.length >= 3) {
      dbHelpers.createInsight(
        userId,
        'same-day',
        'Morning walks boost your Mind',
        'Walking in the morning correlates with +15 Mind score boost',
        15,
        'high'
      );
      insights.push({ type: 'same-day', title: 'Morning walks boost your Mind' });
    }
    
    // Sleep correlation
    if (details && details.sleep_hours >= 7) {
      dbHelpers.createInsight(
        userId,
        'same-day',
        'Quality sleep supports Body & Mind',
        '7+ hours sleep correlates with higher Body and Mind scores',
        12,
        'high'
      );
      insights.push({ type: 'same-day', title: 'Quality sleep supports Body & Mind' });
    }
    
    res.json({ success: true, insights });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/insights/:userId', (req, res) => {
  const limit = parseInt(req.query.limit) || 5;
  const insights = dbHelpers.getInsightsForUser(req.params.userId, limit);
  res.json({ success: true, insights });
});

// === SCORES ===
app.post('/api/scores', (req, res) => {
  try {
    const { userId, date, bodyScore, mindScore, soulScore, purposeScore, fulfillmentScore, isMeaningfulDay } = req.body;
    const result = dbHelpers.createScore(userId, date, bodyScore, mindScore, soulScore, purposeScore, fulfillmentScore, isMeaningfulDay);
    res.json({ success: true, scoreId: result.lastInsertRowid });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// === ANALYTICS ===
app.get('/api/analytics', (req, res) => {
  const analytics = dbHelpers.getAnalytics();
  res.json({ success: true, ...analytics });
});

// === CONVERSION OPTIMIZATION ===
app.post('/api/conversion/calculate', (req, res) => {
  try {
    const { userId, currentDay } = req.body;
    
    // Get user data
    const user = db.prepare('SELECT * FROM users WHERE id = ?').get(userId);
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    // Calculate conversion probability
    const probability = conversionOptimizer.calculateConversionProbability(user, currentDay);
    
    res.json({
      success: true,
      conversionProbability: probability,
      isReadyForConversion: probability >= 0.1
    });
  } catch (error) {
    console.error('Conversion calculation error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/conversion/offer', (req, res) => {
  try {
    const { userId, currentDay } = req.body;
    
    // Get user data
    const user = db.prepare('SELECT * FROM users WHERE id = ?').get(userId);
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    // Generate conversion offer
    const offer = conversionOptimizer.generateConversionOffer(user, currentDay);
    
    if (!offer) {
      return res.json({
        success: false,
        message: 'User not ready for conversion'
      });
    }
    
    res.json({
      success: true,
      offer: offer
    });
  } catch (error) {
    console.error('Conversion offer error:', error);
    res.status(500).json({ error: error.message });
  }
});

// === ONBOARDING OPTIMIZATION ===
app.post('/api/onboarding/flow', (req, res) => {
  try {
    const { userId } = req.body;
    
    // Get user data
    const user = db.prepare('SELECT * FROM users WHERE id = ?').get(userId);
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    // Generate onboarding flow
    const flow = onboardingOptimizer.generateOnboardingFlow(user);
    
    res.json({
      success: true,
      flow: flow
    });
  } catch (error) {
    console.error('Onboarding flow error:', error);
    res.status(500).json({ error: error.message });
  }
});

// === VALUE PROPOSITION OPTIMIZATION ===
app.post('/api/value-proposition', (req, res) => {
  try {
    const { userId, context } = req.body;
    
    // Get user data
    const user = db.prepare('SELECT * FROM users WHERE id = ?').get(userId);
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    // Generate value proposition
    const valueProp = valuePropositionOptimizer.generateValueProposition(user, context);
    
    res.json({
      success: true,
      valueProposition: valueProp
    });
  } catch (error) {
    console.error('Value proposition error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📦 Database: SQLite (file-based)`);
  console.log(`🔒 CORS Origin: *`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log('');
  console.log('✅ Ready for Sim4 simulation!');
});

module.exports = app;

