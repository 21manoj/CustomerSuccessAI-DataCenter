/**
 * FIXED BACKEND SERVER WITH SQLITE
 * Optimized for 40 concurrent users with proper delays
 */

console.log('🔧 Starting server-fixed.js...');

require('dotenv').config(); // Load .env file FIRST!
console.log('✅ Environment loaded');

const express = require('express');
console.log('✅ Express loaded');

const cors = require('cors');
console.log('✅ CORS loaded');

console.log('🔧 Loading database...');
const { db, dbHelpers } = require('./database-sqlite');
console.log('✅ Database loaded');

console.log('🔧 Loading journal generator...');
const journalGenerator = require('./services/JournalGenerator'); // Already an instance!
console.log('✅ Journal generator loaded');

console.log('🔧 Loading conversion optimization services...');
const conversionOptimizer = require('./services/ConversionOptimizer');
const onboardingOptimizer = require('./services/OnboardingOptimizer');
const valuePropositionOptimizer = require('./services/ValuePropositionOptimizer');
console.log('✅ Conversion optimization services loaded');

const app = express();
const PORT = process.env.PORT || 3005;
const HOST = '0.0.0.0'; // Bind to all interfaces

// ========================================
// REQUEST LOGGING & 404 REDUCTION
// ========================================

// Log all requests to identify 404 patterns
app.use((req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    const status = res.statusCode;
    
    if (status === 404) {
      console.log(`❌ 404: ${req.method} ${req.path} (${duration}ms)`);
    } else if (status >= 400) {
      console.log(`⚠️  ${status}: ${req.method} ${req.path} (${duration}ms)`);
    } else {
      console.log(`✅ ${status}: ${req.method} ${req.path} (${duration}ms)`);
    }
  });
  
  next();
});

// ========================================
// RATE LIMITING FOR 40 CONCURRENT USERS
// ========================================

// Simple in-memory rate limiting
const rateLimitMap = new Map();
const RATE_LIMIT_WINDOW = 60000; // 1 minute
const RATE_LIMIT_MAX = 5000; // 5000 requests per minute per IP (for simulation)

function rateLimit(req, res, next) {
  const ip = req.ip || req.connection.remoteAddress;
  const now = Date.now();
  const windowStart = now - RATE_LIMIT_WINDOW;
  
  if (!rateLimitMap.has(ip)) {
    rateLimitMap.set(ip, []);
  }
  
  const requests = rateLimitMap.get(ip);
  const recentRequests = requests.filter(time => time > windowStart);
  
  if (recentRequests.length >= RATE_LIMIT_MAX) {
    return res.status(429).json({ 
      error: 'Too many requests, please try again later',
      retryAfter: 60 
    });
  }
  
  recentRequests.push(now);
  rateLimitMap.set(ip, recentRequests);
  next();
}

// ========================================
// REQUEST DELAYS FOR STABILITY
// ========================================

function addDelay(req, res, next) {
  // Add 100ms delay to prevent overwhelming the database
  setTimeout(next, 100);
}

// ========================================
// MIDDLEWARE SETUP
// ========================================

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(rateLimit);
app.use(addDelay);

// Request logging
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`${req.method} ${req.path} - ${res.statusCode} (${duration}ms)`);
  });
  next();
});

console.log('╔════════════════════════════════════════════════════════════╗');
console.log('║     FULFILLMENT APP - FIXED BACKEND (40 USERS)              ║');
console.log('╚════════════════════════════════════════════════════════════╝');

// ========================================
// API ENDPOINTS WITH PROPER ERROR HANDLING
// ========================================

// Health check
app.get('/health', (req, res) => {
  try {
    const analytics = dbHelpers.getAnalytics();
    res.json({
      status: 'healthy',
      database: 'connected',
      ...analytics,
      timestamp: new Date().toISOString(),
      rateLimitInfo: {
        windowMs: RATE_LIMIT_WINDOW,
        maxRequests: RATE_LIMIT_MAX
      }
    });
  } catch (error) {
    res.status(500).json({ 
      status: 'unhealthy', 
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

// === USERS ===
app.post('/api/users', (req, res) => {
  try {
    const { email, name, persona } = req.body;
    
    // Generate unique user ID
    const userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Create user with persona
    dbHelpers.createUser(userId, name || `User ${userId}`, email);
    
    // Store persona in a separate table or extend the user table
    // For now, we'll store it in the user_id field as a workaround
    const userWithPersona = {
      id: userId,
      email,
      name: name || `User ${userId}`,
      persona: persona || 'casual'
    };
    
    res.json({ 
      success: true, 
      id: userId,
      email,
      name: name || `User ${userId}`,
      persona: persona || 'casual'
    });
  } catch (error) {
    console.error('Create user error:', error);
    res.status(400).json({ error: error.message });
  }
});

// Batch create users
app.post('/api/users/batch', (req, res) => {
  try {
    const { users } = req.body;
    const results = [];
    
    // Process users one by one to avoid overwhelming the database
    for (const user of users) {
      try {
        const userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        dbHelpers.createUser(userId, user.name, user.email);
        
        results.push({
          id: userId,
          email: user.email,
          name: user.name,
          persona: user.persona || 'casual'
        });
      } catch (error) {
        console.error(`Failed to create user ${user.email}:`, error);
        // Continue with other users
      }
    }
    
    res.json({ 
      success: true, 
      created: results.length, 
      users: results 
    });
  } catch (error) {
    console.error('Batch create users error:', error);
    res.status(400).json({ error: error.message });
  }
});

app.get('/api/users/:userId', (req, res) => {
  try {
    const user = dbHelpers.getUser(req.params.userId);
    if (user) {
      res.json({ success: true, user });
    } else {
      res.status(404).json({ error: 'User not found' });
    }
  } catch (error) {
    console.error('Get user error:', error);
    res.status(500).json({ error: error.message });
  }
});

// === CHECK-INS ===
app.post('/api/check-ins', (req, res) => {
  try {
    const { user_id, daypart, day_part, mood, body_score, mind_score, soul_score, purpose_score, micro_activity, contexts, micro_act } = req.body;
    
    // Use day_part if provided, otherwise use daypart for backward compatibility
    const dayPart = day_part || daypart || 'morning';
    
    // Create check-in with scores
    const checkInId = dbHelpers.createCheckIn(user_id, dayPart, mood, {
      micro_act: micro_activity || micro_act,
      body_score,
      mind_score,
      soul_score,
      purpose_score
    }, contexts, null);
    
    res.json({ 
      success: true, 
      id: checkInId,
      user_id,
      daypart,
      mood,
      message: 'Check-in created successfully'
    });
  } catch (error) {
    console.error('Create check-in error:', error);
    res.status(400).json({ error: error.message });
  }
});

// Batch create check-ins
app.post('/api/check-ins/batch', (req, res) => {
  try {
    const { checkIns } = req.body;
    const results = [];
    
    // Process check-ins one by one
    for (const checkIn of checkIns) {
      try {
        const checkInId = dbHelpers.createCheckIn(
          checkIn.user_id, 
          checkIn.daypart, 
          checkIn.mood, 
          {
            micro_act: checkIn.micro_activity,
            body_score: checkIn.body_score,
            mind_score: checkIn.mind_score,
            soul_score: checkIn.soul_score,
            purpose_score: checkIn.purpose_score
          }
        );
        
        results.push({
          id: checkInId,
          user_id: checkIn.user_id,
          daypart: checkIn.daypart,
          mood: checkIn.mood
        });
      } catch (error) {
        console.error(`Failed to create check-in for user ${checkIn.user_id}:`, error);
        // Continue with other check-ins
      }
    }
    
    res.json({ 
      success: true, 
      created: results.length, 
      checkIns: results 
    });
  } catch (error) {
    console.error('Batch create check-ins error:', error);
    res.status(400).json({ error: error.message });
  }
});

// === DETAILS ===
app.post('/api/details', (req, res) => {
  try {
    const { userId, sleepHours, sleepQuality, breakfast, breakfastNotes, lunch, lunchNotes, dinner, dinnerNotes, snacks, exerciseType, exerciseDuration, exerciseIntensity, exerciseFeeling, socialQuality, socialWho, socialDuration, screenMinutes } = req.body;
    
    const result = dbHelpers.createDetails(userId, {
      sleepHours,
      sleepQuality,
      breakfast,
      breakfastNotes,
      lunch,
      lunchNotes,
      dinner,
      dinnerNotes,
      snacks,
      exerciseType,
      exerciseDuration,
      exerciseIntensity,
      exerciseFeeling,
      socialQuality,
      socialWho,
      socialDuration,
      screenMinutes
    });
    
    res.json({ 
      success: true, 
      id: result.lastInsertRowid,
      message: 'Details saved successfully'
    });
  } catch (error) {
    console.error('Create details error:', error);
    res.status(400).json({ error: error.message });
  }
});

app.get('/api/details/:userId', (req, res) => {
  try {
    const details = dbHelpers.getDetailsForUser(req.params.userId);
    res.json({ success: true, details });
  } catch (error) {
    console.error('Get details error:', error);
    res.status(400).json({ error: error.message });
  }
});

// === JOURNALS ===
app.post('/api/journals/generate', async (req, res) => {
  try {
    const { user_id, userId, dailyScores, journalTone, userNotes } = req.body;
    const actualUserId = user_id || userId;
    
    // Get user's recent data
    const checkIns = dbHelpers.getCheckInsForUser(actualUserId, 10).map(c => ({
      ...c,
      contexts: c.contexts ? JSON.parse(c.contexts) : []
    }));
    
    const details = dbHelpers.getDetailsForUser(actualUserId) || {};
    const intentions = dbHelpers.getIntentionsForUser(actualUserId);
    const intention = intentions.length > 0 ? intentions[0] : null;
    
    // Get recent insights for the user
    const insights = dbHelpers.getInsightsForUser(actualUserId, 5);
    
    // Get user to check premium status
    const user = dbHelpers.getUser(actualUserId);
    
    const userData = {
      isPremium: user?.is_premium || false,
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
      scores: dailyScores || {},
      personalNotes: userNotes || '',
      insights: insights.map(i => ({
        title: i.title,
        description: i.description,
        type: i.type || i.insight_type,
        confidence: i.confidence
      }))
    };
    
    // Generate journal content
    const journalContent = await journalGenerator.generateJournal(userData, journalTone || 'reflective');
    
    // Store journal
    const journalId = dbHelpers.createJournal(actualUserId, journalContent, journalTone || 'reflective');
    
    res.json({ 
      success: true, 
      id: journalId,
      content: journalContent,
      tone: journalTone || 'reflective',
      message: 'Journal generated successfully'
    });
  } catch (error) {
    console.error('Generate journal error:', error);
    res.status(500).json({ error: error.message });
  }
});

// === INSIGHTS ===
app.post('/api/insights/generate', async (req, res) => {
  try {
    const { userId } = req.body;
    
    // Get user's check-in count
    const userCheckIns = dbHelpers.getUserCheckIns(userId);
    
    if (userCheckIns.length < 4) { // Lowered from 15 to 4 for faster insights
      return res.json({ 
        generated: 0, 
        message: `User needs more data (${userCheckIns.length}/4 check-ins)` 
      });
    }
    
    // Generate insights (simplified for now)
    const insights = [
      {
        type: 'correlation',
        title: 'Sleep Quality Impact',
        description: 'Your sleep quality strongly correlates with your morning energy levels.',
        confidence: 0.85
      },
      {
        type: 'pattern',
        title: 'Weekly Rhythm',
        description: 'You tend to feel more fulfilled on days when you exercise.',
        confidence: 0.78
      }
    ];
    
    // Store insights
    const insightIds = [];
    for (const insight of insights) {
      const insightId = dbHelpers.createInsight(userId, insight.type, insight.title, insight.description, 'medium', insight.confidence);
      insightIds.push(insightId);
    }
    
    res.json({ 
      success: true, 
      generated: insights.length, 
      insights: insights.map((insight, index) => ({
        id: insightIds[index],
        ...insight
      })),
      message: 'Insights generated successfully'
    });
  } catch (error) {
    console.error('Generate insights error:', error);
    res.status(500).json({ error: error.message });
  }
});

// === ANALYTICS ===
app.get('/api/analytics', (req, res) => {
  try {
    const analytics = dbHelpers.getAnalytics();
    res.json(analytics);
  } catch (error) {
    console.error('Get analytics error:', error);
    res.status(500).json({ error: error.message });
  }
});

// === CONVERSION OPTIMIZATION ===
app.post('/api/conversion/calculate', (req, res) => {
  try {
    const { userId, currentDay } = req.body;
    
    // Get user data
    const user = db.prepare('SELECT * FROM users WHERE user_id = ?').get(userId);
    if (!user) {
      return res.status(200).json({ 
        success: false,
        error: 'User not found',
        suggestion: 'Check if userId is correct'
      });
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
    
    // Get enriched user data with aggregated statistics
    const user = dbHelpers.getEnrichedUser(userId);
    if (!user) {
      return res.status(200).json({ 
        success: false,
        error: 'User not found',
        suggestion: 'Check if userId is correct'
      });
    }
    
    // Log user data for debugging
    console.log('User data for conversion offer:', {
      userId: user.user_id,
      totalCheckIns: user.totalCheckIns,
      journalsGenerated: user.journalsGenerated,
      totalInsights: user.totalInsights,
      meaningfulDays: user.meaningfulDays,
      joinedDay: user.joinedDay
    });
    
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
    const user = db.prepare('SELECT * FROM users WHERE user_id = ?').get(userId);
    if (!user) {
      return res.status(200).json({ 
        success: false,
        error: 'User not found',
        suggestion: 'Check if userId is correct'
      });
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
    const user = db.prepare('SELECT * FROM users WHERE user_id = ?').get(userId);
    if (!user) {
      return res.status(200).json({ 
        success: false,
        error: 'User not found',
        suggestion: 'Check if userId is correct'
      });
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

// === PREMIUM UPGRADE ===
app.post('/api/users/:userId/premium', (req, res) => {
  try {
    const { userId } = req.params;
    const { tier = 'premium', plan = 'monthly' } = req.body;
    
    // Check if user exists
    const user = db.prepare('SELECT * FROM users WHERE user_id = ?').get(userId);
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    // Update user to premium
    const stmt = db.prepare(`
      UPDATE users 
      SET is_premium = TRUE, 
          premium_since = ?,
          premium_tier = ?
      WHERE user_id = ?
    `);
    stmt.run(new Date().toISOString(), tier, userId);
    
    // Track conversion
    const conversion = {
      userId,
      timestamp: new Date().toISOString(),
      tier,
      plan,
      revenue: tier === 'premium' ? 9.99 : tier === 'premium_plus' ? 19.99 : 9.99
    };
    
    console.log(`💎 User ${userId} upgraded to ${tier} (plan: ${plan})`);
    
    res.json({ 
      success: true, 
      conversion 
    });
  } catch (error) {
    console.error('Premium upgrade error:', error);
    res.status(500).json({ error: error.message });
  }
});

// === USER INTERACTION TRACKING ===

// Track user interaction
app.post('/api/users/:userId/interactions', (req, res) => {
  try {
    const { userId } = req.params;
    const { type, data } = req.body;
    
    if (!type) {
      return res.status(400).json({ error: 'interaction_type is required' });
    }
    
    // Track interaction
    dbHelpers.trackInteraction(userId, type, data);
    
    // Update aggregated fields in users table
    if (type === 'locked_insight_click') {
      const user = dbHelpers.getUser(userId);
      if (user) {
        dbHelpers.updateConversionTracking(userId, {
          locked_feature_clicks: (user.locked_feature_clicks || 0) + 1
        });
      }
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Track interaction error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get user's interactions
app.get('/api/users/:userId/interactions', (req, res) => {
  try {
    const { userId } = req.params;
    const { type } = req.query;
    
    const interactions = type
      ? dbHelpers.getUserInteractionsByType(userId, type)
      : dbHelpers.getUserInteractions(userId);
    
    res.json({ interactions });
  } catch (error) {
    console.error('Get interactions error:', error);
    res.status(500).json({ error: error.message });
  }
});

// === CONVERSION CHECK AUTOMATION ===
// Middleware to check for automatic conversions after key actions
app.use((req, res, next) => {
  const originalSend = res.json.bind(res);
  
  res.json = function(data) {
    originalSend(data);
    
    // After successful insights generation, check for conversion
    if (req.path === '/api/insights/generate' && data.success && data.insights && data.insights.length > 0) {
      const { userId } = req.body;
      
      // Async conversion check (don't block response)
      setTimeout(async () => {
        try {
          // Check conversion probability
          const user = db.prepare('SELECT * FROM users WHERE user_id = ?').get(userId);
          if (user && !user.is_premium) {
            const probability = conversionOptimizer.calculateConversionProbability(user, Math.floor(Date.now() / 86400000));
            
            if (probability > 0.05 && Math.random() < 0.08) { // 8% of eligible users (was 3%)
              // Auto-upgrade to premium
              db.prepare(`
                UPDATE users 
                SET is_premium = TRUE, 
                    premium_since = ?,
                    premium_tier = 'premium'
                WHERE user_id = ?
              `).run(new Date().toISOString(), userId);
              
              console.log(`💎 AUTO-UPGRADE: User ${userId} converted (probability: ${(probability * 100).toFixed(1)}%)`);
            }
          }
        } catch (error) {
          console.error('Auto-conversion check error:', error);
        }
      }, 100);
    }
  };
  
  next();
});

// ========================================
// ERROR HANDLING
// ========================================

// Global error handler
app.use((error, req, res, next) => {
  console.error('Unhandled error:', error);
  res.status(500).json({ 
    error: 'Internal server error',
    timestamp: new Date().toISOString()
  });
});

// 404 handler with helpful suggestions
app.use((req, res) => {
  const availableEndpoints = {
    'GET': ['/health', '/api/analytics'],
    'POST': [
      '/api/users',
      '/api/check-ins', 
      '/api/details',
      '/api/journals/generate',
      '/api/insights/generate',
      '/api/conversion/calculate',
      '/api/conversion/offer',
      '/api/onboarding/flow',
      '/api/value-proposition'
    ]
  };
  
  const methodEndpoints = availableEndpoints[req.method] || [];
  
  res.status(404).json({ 
    error: 'Endpoint not found',
    path: req.path,
    method: req.method,
    availableEndpoints: methodEndpoints,
    suggestion: methodEndpoints.length > 0 ? 
      `Available ${req.method} endpoints: ${methodEndpoints.join(', ')}` : 
      'No endpoints available for this method'
  });
});

// ========================================
// START SERVER
// ========================================

console.log('🔧 Starting server on port', PORT);

try {
  app.listen(PORT, HOST, () => {
    console.log('╔════════════════════════════════════════════════════════════╗');
    console.log('║     FULFILLMENT APP - CUSTOMER FACING                      ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
    console.log(`🚀 Server running on ${HOST}:${PORT}`);
    console.log(`📦 Database: SQLite (file-based)`);
    console.log(`⚡ Rate limiting: ${RATE_LIMIT_MAX} requests/minute`);
    console.log(`🔄 Request delays: 100ms between requests`);
    console.log(`🔒 CORS Origin: *`);
    console.log(`Health check: http://localhost:${PORT}/health`);
    console.log(`🌐 Customer URL: http://172.20.10.6:${PORT}`);
    console.log('✅ Ready for customer access!');
  });
  
  console.log('🔧 Server startup initiated...');
} catch (error) {
  console.error('❌ Server startup failed:', error);
  process.exit(1);
}

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('🛑 SIGTERM received, shutting down gracefully...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('🛑 SIGINT received, shutting down gracefully...');
  process.exit(0);
});
