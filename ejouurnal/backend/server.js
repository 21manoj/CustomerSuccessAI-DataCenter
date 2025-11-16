/**
 * FULFILLMENT APP - BACKEND API SERVER
 * Production-ready Express.js server
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { Pool } = require('pg');
require('dotenv').config();

const journalGenerator = require('./services/JournalGenerator');
const insightEngine = require('./services/InsightEngine');
const InsightScheduler = require('./services/InsightScheduler');

const app = express();
const PORT = process.env.PORT || 3005;

// ============================================================================
// DATABASE CONNECTION
// ============================================================================

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'fulfillment',
  user: process.env.DB_USER || 'fulfillment_user',
  password: process.env.DB_PASSWORD || 'fulfillment_secure_password_123',
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Test database connection
pool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.error('❌ Database connection failed:', err);
  } else {
    console.log('✅ Database connected:', res.rows[0].now);
  }
});

// ============================================================================
// MIDDLEWARE
// ============================================================================

// Security
app.use(helmet());
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',
  credentials: true,
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.',
});
app.use('/api/', limiter);

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Compression
app.use(compression());

// Logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`${req.method} ${req.path} ${res.statusCode} - ${duration}ms`);
  });
  next();
});

// ============================================================================
// HEALTH CHECK
// ============================================================================

app.get('/health', async (req, res) => {
  try {
    await pool.query('SELECT 1');
    res.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      database: 'connected',
    });
  } catch (error) {
    res.status(503).json({
      status: 'unhealthy',
      database: 'disconnected',
      error: error.message,
    });
  }
});

// ============================================================================
// API ROUTES
// ============================================================================

// -----------------------------
// USERS
// -----------------------------

// Create user
app.post('/api/users', async (req, res) => {
  try {
    const { userId, name, email } = req.body;
    
    const result = await pool.query(
      `INSERT INTO users (user_id, name, email, created_at) 
       VALUES ($1, $2, $3, NOW()) 
       ON CONFLICT (user_id) DO UPDATE 
       SET name = EXCLUDED.name, email = EXCLUDED.email
       RETURNING *`,
      [userId, name, email]
    );
    
    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error creating user:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get user
app.get('/api/users/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    
    const result = await pool.query(
      'SELECT * FROM users WHERE user_id = $1',
      [userId]
    );
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error getting user:', error);
    res.status(500).json({ error: error.message });
  }
});

// -----------------------------
// CHECK-INS
// -----------------------------

// Create check-in
app.post('/api/check-ins', async (req, res) => {
  try {
    const { userId, dayPart, mood, arousal, contexts, microAct } = req.body;
    
    const result = await pool.query(
      `INSERT INTO check_ins (user_id, day_part, mood, arousal, contexts, micro_act, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, NOW())
       RETURNING *`,
      [userId, dayPart, mood, arousal, JSON.stringify(contexts), microAct]
    );
    
    // Check if user has enough data for insights (trigger after 6+ check-ins)
    const checkInCount = await pool.query(
      'SELECT COUNT(*) as count FROM check_ins WHERE user_id = $1',
      [userId]
    );
    
    const totalCheckIns = parseInt(checkInCount.rows[0].count);
    
    // Trigger insight generation at key milestones
    if (totalCheckIns === 6 || totalCheckIns === 12 || totalCheckIns === 24 || totalCheckIns % 30 === 0) {
      // Don't await - run in background
      generateInsightsInBackground(userId);
    }
    
    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error creating check-in:', error);
    res.status(500).json({ error: error.message });
  }
});

// Helper function to generate insights in background
async function generateInsightsInBackground(userId) {
  try {
    const userResult = await pool.query('SELECT * FROM users WHERE user_id = $1', [userId]);
    if (userResult.rows.length === 0) return;
    
    const user = userResult.rows[0];
    
    const checkInsResult = await pool.query(
      `SELECT * FROM check_ins WHERE user_id = $1 ORDER BY created_at DESC LIMIT 120`,
      [userId]
    );
    
    const detailsResult = await pool.query(
      `SELECT * FROM details WHERE user_id = $1 ORDER BY created_at DESC LIMIT 30`,
      [userId]
    );
    
    const scoresResult = await pool.query(
      `SELECT * FROM daily_scores WHERE user_id = $1 ORDER BY created_at DESC LIMIT 30`,
      [userId]
    );
    
    const userData = {
      checkIns: checkInsResult.rows,
      details: detailsResult.rows,
      scores: scoresResult.rows,
      isPremium: user.is_premium || false,
    };
    
    const insights = await insightEngine.generateInsights(userData);
    
    // Save new insights
    for (const insight of insights) {
      const existing = await pool.query(
        `SELECT id FROM insights 
         WHERE user_id = $1 AND insight_type = $2 AND title = $3
         AND created_at > NOW() - INTERVAL '7 days'`,
        [userId, insight.type, insight.title]
      );
      
      if (existing.rows.length === 0) {
        await pool.query(
          `INSERT INTO insights 
           (user_id, insight_type, title, description, confidence, source_metric, target_metric, impact, metadata)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
          [
            userId,
            insight.type,
            insight.title,
            insight.description,
            insight.confidence,
            insight.sourceMetric,
            insight.targetMetric,
            insight.impact,
            JSON.stringify({ 
              isPremiumGate: insight.isPremiumGate || false,
              lagDays: insight.lagDays,
              threshold: insight.threshold
            })
          ]
        );
        console.log(`💡 New insight generated for user ${userId}: ${insight.title}`);
      }
    }
  } catch (error) {
    console.error('Background insight generation error:', error);
  }
}

// Get user check-ins
app.get('/api/users/:userId/check-ins', async (req, res) => {
  try {
    const { userId } = req.params;
    const { limit = 50, offset = 0 } = req.query;
    
    const result = await pool.query(
      `SELECT * FROM check_ins 
       WHERE user_id = $1 
       ORDER BY created_at DESC 
       LIMIT $2 OFFSET $3`,
      [userId, limit, offset]
    );
    
    res.json(result.rows);
  } catch (error) {
    console.error('Error getting check-ins:', error);
    res.status(500).json({ error: error.message });
  }
});

// -----------------------------
// DETAILS (Sleep, Food, Exercise, etc.)
// -----------------------------

// Save details
app.post('/api/details', async (req, res) => {
  try {
    const {
      userId,
      sleepHours,
      sleepQuality,
      steps,
      exerciseType,
      exerciseDuration,
      exerciseIntensity,
      breakfast,
      lunch,
      dinner,
      snacks,
      screenTimeMinutes,
    } = req.body;
    
    const result = await pool.query(
      `INSERT INTO details (
        user_id, sleep_hours, sleep_quality, steps,
        exercise_type, exercise_duration, exercise_intensity,
        breakfast, lunch, dinner, snacks, screen_time_minutes,
        created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
      RETURNING *`,
      [
        userId, sleepHours, sleepQuality, steps,
        exerciseType, exerciseDuration, exerciseIntensity,
        breakfast, lunch, dinner, snacks, screenTimeMinutes,
      ]
    );
    
    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error saving details:', error);
    res.status(500).json({ error: error.message });
  }
});

// -----------------------------
// JOURNALS
// -----------------------------

// Create journal
app.post('/api/journals', async (req, res) => {
  try {
    const { userId, content, tone, personalNotes } = req.body;
    
    const result = await pool.query(
      `INSERT INTO journals (user_id, content, tone, personal_notes, created_at)
       VALUES ($1, $2, $3, $4, NOW())
       RETURNING *`,
      [userId, content, tone, personalNotes]
    );
    
    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error creating journal:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get user journals
app.get('/api/users/:userId/journals', async (req, res) => {
  try {
    const { userId } = req.params;
    const { limit = 30 } = req.query;
    
    const result = await pool.query(
      `SELECT * FROM journals 
       WHERE user_id = $1 
       ORDER BY created_at DESC 
       LIMIT $2`,
      [userId, limit]
    );
    
    res.json(result.rows);
  } catch (error) {
    console.error('Error getting journals:', error);
    res.status(500).json({ error: error.message });
  }
});

// Generate AI journal
app.post('/api/journals/generate', async (req, res) => {
  try {
    const { userId, tone = 'reflective', checkIns = [], details = null, scores = {}, intention = null, userNotes = '' } = req.body;
    
    // Use enriched data from request if provided, otherwise query database
    let userData;
    
    if (checkIns.length > 0 || details || Object.keys(scores).length > 0) {
      // Frontend sent enriched context - use it directly
      console.log('✅ Using enriched context from frontend');
      userData = {
        checkIns: checkIns,
        details: details || {},
        scores: scores || {},
        weeklyIntention: intention ? intention.text : '',
        microMoves: intention ? intention.microMoves.map((m, i) => ({ description: m, completed: false })) : [],
        personalNotes: userNotes,
      };
    } else {
      // Fallback: Query database for data
      console.log('⚠️ No enriched context provided, querying database...');
      const checkInsResult = await pool.query(
        `SELECT * FROM check_ins 
         WHERE user_id = $1 
         AND created_at >= CURRENT_DATE 
         ORDER BY created_at DESC`,
        [userId]
      );
      
      const detailsResult = await pool.query(
        `SELECT * FROM details 
         WHERE user_id = $1 
         AND created_at >= CURRENT_DATE 
         ORDER BY created_at DESC 
         LIMIT 1`,
        [userId]
      );
      
      const scoresResult = await pool.query(
        `SELECT * FROM scores 
         WHERE user_id = $1 
         AND date = CURRENT_DATE 
         LIMIT 1`,
        [userId]
      );
      
      userData = {
        checkIns: checkInsResult.rows,
        details: detailsResult.rows[0] || {},
        scores: scoresResult.rows[0] || {},
        personalNotes: userNotes,
      };
    }
    
    // Generate journal using AI
    const content = await journalGenerator.generateJournal(userData, tone);
    
    // Save to database
    const saveResult = await pool.query(
      `INSERT INTO journals (user_id, content, tone, personal_notes, created_at)
       VALUES ($1, $2, $3, $4, NOW())
       RETURNING *`,
      [userId, content, tone, req.body.personalNotes || '']
    );
    
    res.json({
      success: true,
      journal: saveResult.rows[0],
    });
  } catch (error) {
    console.error('Error generating journal:', error);
    res.status(500).json({ error: error.message });
  }
});

// Regenerate journal with new tone
app.post('/api/journals/:journalId/regenerate', async (req, res) => {
  try {
    const { journalId } = req.params;
    const { tone, personalNotes } = req.body;
    
    // Get existing journal
    const existingResult = await pool.query(
      'SELECT * FROM journals WHERE id = $1',
      [journalId]
    );
    
    if (existingResult.rows.length === 0) {
      return res.status(404).json({ error: 'Journal not found' });
    }
    
    const existing = existingResult.rows[0];
    
    // Get user data (same day)
    const checkInsResult = await pool.query(
      `SELECT * FROM check_ins 
       WHERE user_id = $1 
       AND DATE(created_at) = DATE($2)`,
      [existing.user_id, existing.created_at]
    );
    
    const userData = {
      checkIns: checkInsResult.rows,
      personalNotes: personalNotes || existing.personal_notes || '',
    };
    
    // Regenerate with new tone
    const content = await journalGenerator.generateJournal(userData, tone);
    
    // Update journal
    const updateResult = await pool.query(
      `UPDATE journals 
       SET content = $1, tone = $2, personal_notes = $3, updated_at = NOW()
       WHERE id = $4
       RETURNING *`,
      [content, tone, personalNotes || existing.personal_notes, journalId]
    );
    
    res.json({
      success: true,
      journal: updateResult.rows[0],
    });
  } catch (error) {
    console.error('Error regenerating journal:', error);
    res.status(500).json({ error: error.message });
  }
});

// -----------------------------
// INSIGHTS
// -----------------------------

// Generate insights for user
app.post('/api/insights/generate', async (req, res) => {
  try {
    const { userId } = req.body;
    
    // Fetch user data from database
    const userResult = await pool.query('SELECT * FROM users WHERE user_id = $1', [userId]);
    if (userResult.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    const user = userResult.rows[0];
    
    // Get check-ins (last 30 days)
    const checkInsResult = await pool.query(
      `SELECT * FROM check_ins 
       WHERE user_id = $1 
       ORDER BY created_at DESC 
       LIMIT 120`,
      [userId]
    );
    
    // Get details (last 30 days)
    const detailsResult = await pool.query(
      `SELECT * FROM details 
       WHERE user_id = $1 
       ORDER BY created_at DESC 
       LIMIT 30`,
      [userId]
    );
    
    // Get scores (last 30 days)
    const scoresResult = await pool.query(
      `SELECT * FROM daily_scores 
       WHERE user_id = $1 
       ORDER BY created_at DESC 
       LIMIT 30`,
      [userId]
    );
    
    // Generate insights
    const userData = {
      checkIns: checkInsResult.rows,
      details: detailsResult.rows,
      scores: scoresResult.rows,
      isPremium: user.is_premium || false,
    };
    
    const insights = await insightEngine.generateInsights(userData);
    
    // Save insights to database
    for (const insight of insights) {
      // Check if insight already exists (avoid duplicates)
      const existing = await pool.query(
        `SELECT id FROM insights 
         WHERE user_id = $1 AND insight_type = $2 AND title = $3
         AND created_at > NOW() - INTERVAL '7 days'`,
        [userId, insight.type, insight.title]
      );
      
      if (existing.rows.length === 0) {
        await pool.query(
          `INSERT INTO insights 
           (user_id, insight_type, title, description, confidence, source_metric, target_metric, impact, metadata)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
          [
            userId,
            insight.type,
            insight.title,
            insight.description,
            insight.confidence,
            insight.sourceMetric,
            insight.targetMetric,
            insight.impact,
            JSON.stringify({ 
              isPremiumGate: insight.isPremiumGate || false,
              lagDays: insight.lagDays,
              threshold: insight.threshold
            })
          ]
        );
      }
    }
    
    res.json({
      success: true,
      insights,
      count: insights.length
    });
  } catch (error) {
    console.error('Error generating insights:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get user's insights
app.get('/api/insights/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    const { limit = 10 } = req.query;
    
    const result = await pool.query(
      `SELECT * FROM insights 
       WHERE user_id = $1 
       ORDER BY created_at DESC 
       LIMIT $2`,
      [userId, limit]
    );
    
    res.json({
      success: true,
      insights: result.rows,
      count: result.rows.length
    });
  } catch (error) {
    console.error('Error fetching insights:', error);
    res.status(500).json({ error: error.message });
  }
});

// Mark insight as viewed
app.post('/api/insights/:insightId/view', async (req, res) => {
  try {
    const { insightId } = req.params;
    
    await pool.query(
      `UPDATE insights 
       SET viewed_at = NOW() 
       WHERE id = $1`,
      [insightId]
    );
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error marking insight as viewed:', error);
    res.status(500).json({ error: error.message });
  }
});

// -----------------------------
// ANALYTICS
// -----------------------------

// Get user stats
app.get('/api/users/:userId/stats', async (req, res) => {
  try {
    const { userId } = req.params;
    
    const checkInsResult = await pool.query(
      'SELECT COUNT(*) as total_check_ins FROM check_ins WHERE user_id = $1',
      [userId]
    );
    
    const detailsResult = await pool.query(
      'SELECT COUNT(*) as total_details FROM details WHERE user_id = $1',
      [userId]
    );
    
    const journalsResult = await pool.query(
      'SELECT COUNT(*) as total_journals FROM journals WHERE user_id = $1',
      [userId]
    );
    
    const recentCheckIns = await pool.query(
      `SELECT * FROM check_ins 
       WHERE user_id = $1 
       ORDER BY created_at DESC 
       LIMIT 10`,
      [userId]
    );
    
    res.json({
      userId,
      totalCheckIns: parseInt(checkInsResult.rows[0].total_check_ins),
      totalDetails: parseInt(detailsResult.rows[0].total_details),
      totalJournals: parseInt(journalsResult.rows[0].total_journals),
      recentCheckIns: recentCheckIns.rows,
    });
  } catch (error) {
    console.error('Error getting stats:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get global analytics
app.get('/api/analytics', async (req, res) => {
  try {
    const usersResult = await pool.query('SELECT COUNT(*) as total_users FROM users');
    const checkInsResult = await pool.query('SELECT COUNT(*) as total_check_ins FROM check_ins');
    const journalsResult = await pool.query('SELECT COUNT(*) as total_journals FROM journals');
    
    const avgCheckInsResult = await pool.query(`
      SELECT AVG(check_in_count) as avg_check_ins_per_user
      FROM (
        SELECT COUNT(*) as check_in_count 
        FROM check_ins 
        GROUP BY user_id
      ) as counts
    `);
    
    res.json({
      totalUsers: parseInt(usersResult.rows[0].total_users),
      totalCheckIns: parseInt(checkInsResult.rows[0].total_check_ins),
      totalJournals: parseInt(journalsResult.rows[0].total_journals),
      avgCheckInsPerUser: parseFloat(avgCheckInsResult.rows[0].avg_check_ins_per_user || 0).toFixed(1),
    });
  } catch (error) {
    console.error('Error getting analytics:', error);
    res.status(500).json({ error: error.message });
  }
});

// ============================================================================
// ERROR HANDLING
// ============================================================================

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({
    error: process.env.NODE_ENV === 'production' 
      ? 'Internal server error' 
      : err.message,
  });
});

// ============================================================================
// START SERVER
// ============================================================================

const server = app.listen(PORT, () => {
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║          FULFILLMENT APP - BACKEND API                     ║');
  console.log('╚════════════════════════════════════════════════════════════╝');
  console.log('');
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🗄️  Database: ${process.env.DB_NAME || 'fulfillment'}`);
  console.log(`🔒 CORS Origin: ${process.env.CORS_ORIGIN || '*'}`);
  console.log('');
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log('');
  
  // Start insight scheduler
  const scheduler = new InsightScheduler(pool);
  scheduler.start();
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM signal received: closing HTTP server');
  server.close(() => {
    console.log('HTTP server closed');
    pool.end(() => {
      console.log('Database pool closed');
      process.exit(0);
    });
  });
});

module.exports = app;

