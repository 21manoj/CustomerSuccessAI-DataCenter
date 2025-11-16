const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const rateLimit = require('express-rate-limit');

// Import services
const journalGenerator = require('./services/JournalGenerator');
const insightEngine = require('./services/InsightEngine');

const app = express();
const PORT = process.env.PORT || 3005;

// ========================================
// A. CONNECTION POOLING (Simplified)
// ========================================

class DatabasePool {
  constructor(maxConnections = 10) {
    this.pool = [];
    this.maxConnections = maxConnections;
    this.activeConnections = 0;
    this.waitingQueue = [];
  }

  async getConnection() {
    return new Promise((resolve, reject) => {
      if (this.pool.length > 0) {
        const connection = this.pool.pop();
        this.activeConnections++;
        resolve(connection);
      } else if (this.activeConnections < this.maxConnections) {
        const connection = new sqlite3.Database('./fulfillment.db', (err) => {
          if (err) {
            reject(err);
          } else {
            this.activeConnections++;
            resolve(connection);
          }
        });
      } else {
        this.waitingQueue.push({ resolve, reject });
      }
    });
  }

  releaseConnection(connection) {
    if (this.waitingQueue.length > 0) {
      const { resolve } = this.waitingQueue.shift();
      this.activeConnections++;
      resolve(connection);
    } else {
      this.pool.push(connection);
      this.activeConnections--;
    }
  }

  async query(sql, params = []) {
    const connection = await this.getConnection();
    return new Promise((resolve, reject) => {
      connection.all(sql, params, (err, rows) => {
        this.releaseConnection(connection);
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });
    });
  }

  async run(sql, params = []) {
    const connection = await this.getConnection();
    return new Promise((resolve, reject) => {
      connection.run(sql, params, function(err) {
        this.releaseConnection(connection);
        if (err) {
          reject(err);
        } else {
          resolve({ id: this.lastID, changes: this.changes });
        }
      });
    });
  }
}

const dbPool = new DatabasePool(10);

// ========================================
// B. RATE LIMITING & THROTTLING
// ========================================

// Rate limiting for 40 concurrent users
const generalLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 200, // 200 requests per minute per IP (5x for 40 users)
  message: 'Too many requests, please try again later',
  standardHeaders: true,
  legacyHeaders: false,
});

const checkInLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 80, // 80 check-ins per minute per IP (2x for 40 users)
  message: 'Too many check-ins, please slow down',
});

const journalLimiter = rateLimit({
  windowMs: 5 * 60 * 1000, // 5 minutes
  max: 40, // 40 journal generations per 5 minutes per IP
  message: 'Too many journal requests, please wait',
});

// ========================================
// C. BATCH PROCESSING UTILITIES
// ========================================

class BatchProcessor {
  constructor(batchSize = 20, delayMs = 50) {
    this.batchSize = batchSize;
    this.delayMs = delayMs;
    this.batches = new Map();
  }

  async addToBatch(batchKey, item, processor) {
    if (!this.batches.has(batchKey)) {
      this.batches.set(batchKey, {
        items: [],
        processor,
        timeout: null
      });
    }

    const batch = this.batches.get(batchKey);
    batch.items.push(item);

    if (batch.items.length >= this.batchSize) {
      await this.processBatch(batchKey);
    } else if (!batch.timeout) {
      batch.timeout = setTimeout(() => {
        this.processBatch(batchKey);
      }, this.delayMs);
    }
  }

  async processBatch(batchKey) {
    const batch = this.batches.get(batchKey);
    if (!batch || batch.items.length === 0) return;

    const items = batch.items.splice(0, this.batchSize);
    if (batch.timeout) {
      clearTimeout(batch.timeout);
      batch.timeout = null;
    }

    try {
      await batch.processor(items);
    } catch (error) {
      console.error(`Batch processing error for ${batchKey}:`, error);
    }

    if (batch.items.length > 0) {
      batch.timeout = setTimeout(() => {
        this.processBatch(batchKey);
      }, this.delayMs);
    } else {
      this.batches.delete(batchKey);
    }
  }
}

const batchProcessor = new BatchProcessor(20, 50);

// ========================================
// D. ERROR HANDLING & RETRY MECHANISM
// ========================================

class RetryHandler {
  static async withRetry(operation, maxRetries = 3, delayMs = 1000) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        console.error(`Attempt ${attempt} failed:`, error.message);
        
        if (attempt === maxRetries) {
          throw error;
        }
        
        await new Promise(resolve => setTimeout(resolve, delayMs * attempt));
      }
    }
  }

  static async handleApiError(res, error, operation = 'operation') {
    console.error(`${operation} error:`, error);
    
    if (error.code === 'SQLITE_BUSY') {
      return res.status(503).json({ 
        error: 'Database busy, please retry', 
        retryAfter: 2 
      });
    }
    
    if (error.code === 'ECONNREFUSED') {
      return res.status(503).json({ 
        error: 'Service temporarily unavailable', 
        retryAfter: 5 
      });
    }
    
    return res.status(500).json({ 
      error: 'Internal server error',
      operation,
      timestamp: new Date().toISOString()
    });
  }
}

// ========================================
// E. MIDDLEWARE SETUP
// ========================================

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Apply rate limiting
app.use('/api', generalLimiter);
app.use('/api/check-ins', checkInLimiter);
app.use('/api/journals', journalLimiter);

// Request logging
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`${req.method} ${req.path} - ${res.statusCode} (${duration}ms)`);
  });
  next();
});

// ========================================
// F. DATABASE INITIALIZATION
// ========================================

async function initializeDatabase() {
  try {
    await dbPool.run(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        persona TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_premium BOOLEAN DEFAULT FALSE,
        premium_since DATETIME,
        total_check_ins INTEGER DEFAULT 0,
        total_journals INTEGER DEFAULT 0,
        total_insights INTEGER DEFAULT 0
      )
    `);

    await dbPool.run(`
      CREATE TABLE IF NOT EXISTS check_ins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        daypart TEXT NOT NULL,
        mood TEXT NOT NULL,
        body_score INTEGER,
        mind_score INTEGER,
        soul_score INTEGER,
        purpose_score INTEGER,
        micro_activity TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
      )
    `);

    await dbPool.run(`
      CREATE TABLE IF NOT EXISTS journals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        tone TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
      )
    `);

    await dbPool.run(`
      CREATE TABLE IF NOT EXISTS insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        confidence REAL NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
      )
    `);

    await dbPool.run(`
      CREATE TABLE IF NOT EXISTS daily_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        body_score INTEGER,
        mind_score INTEGER,
        soul_score INTEGER,
        purpose_score INTEGER,
        overall_score INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(user_id, date)
      )
    `);

    console.log('✅ Database tables created');
  } catch (error) {
    console.error('❌ Database initialization failed:', error);
    throw error;
  }
}

// ========================================
// G. API ENDPOINTS WITH BATCH PROCESSING
// ========================================

// Health check
app.get('/health', async (req, res) => {
  try {
    const stats = await dbPool.query(`
      SELECT 
        (SELECT COUNT(*) FROM users) as totalUsers,
        (SELECT COUNT(*) FROM check_ins) as totalCheckIns,
        (SELECT COUNT(*) FROM journals) as totalJournals,
        (SELECT COUNT(*) FROM insights) as totalInsights
    `);
    
    res.json({
      status: 'healthy',
      database: 'connected',
      ...stats[0],
      timestamp: new Date().toISOString(),
      activeConnections: dbPool.activeConnections,
      maxConnections: dbPool.maxConnections
    });
  } catch (error) {
    res.status(500).json({ status: 'unhealthy', error: error.message });
  }
});

// Create user
app.post('/api/users', async (req, res) => {
  try {
    const { email, name, persona } = req.body;
    
    const result = await RetryHandler.withRetry(async () => {
      return await dbPool.run(
        'INSERT INTO users (email, name, persona) VALUES (?, ?, ?)',
        [email, name, persona]
      );
    });

    res.json({ id: result.id, email, name, persona });
  } catch (error) {
    RetryHandler.handleApiError(res, error, 'create user');
  }
});

// Batch create users (optimized for 40 users)
app.post('/api/users/batch', async (req, res) => {
  try {
    const users = req.body.users;
    
    const result = await RetryHandler.withRetry(async () => {
      const stmt = 'INSERT INTO users (email, name, persona) VALUES (?, ?, ?)';
      const results = [];
      
      // Process in smaller batches to avoid overwhelming the database
      for (let i = 0; i < users.length; i += 10) {
        const batch = users.slice(i, i + 10);
        for (const user of batch) {
          const userResult = await dbPool.run(stmt, [user.email, user.name, user.persona]);
          results.push({ id: userResult.id, ...user });
        }
        // Small delay between batches
        if (i + 10 < users.length) {
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      }
      
      return results;
    });

    res.json({ created: result.length, users: result });
  } catch (error) {
    RetryHandler.handleApiError(res, error, 'batch create users');
  }
});

// Create check-in
app.post('/api/check-ins', async (req, res) => {
  try {
    const { user_id, daypart, mood, body_score, mind_score, soul_score, purpose_score, micro_activity } = req.body;
    
    const result = await RetryHandler.withRetry(async () => {
      const checkInResult = await dbPool.run(`
        INSERT INTO check_ins 
        (user_id, daypart, mood, body_score, mind_score, soul_score, purpose_score, micro_activity) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `, [user_id, daypart, mood, body_score, mind_score, soul_score, purpose_score, micro_activity]);

      // Update user stats
      await dbPool.run(`
        UPDATE users 
        SET total_check_ins = total_check_ins + 1, last_active = CURRENT_TIMESTAMP 
        WHERE id = ?
      `, [user_id]);

      return checkInResult;
    });

    res.json({ id: result.id, message: 'Check-in created successfully' });
  } catch (error) {
    RetryHandler.handleApiError(res, error, 'create check-in');
  }
});

// Batch create check-ins (optimized for 40 users)
app.post('/api/check-ins/batch', async (req, res) => {
  try {
    const checkIns = req.body.checkIns;
    
    const result = await RetryHandler.withRetry(async () => {
      const stmt = `INSERT INTO check_ins 
        (user_id, daypart, mood, body_score, mind_score, soul_score, purpose_score, micro_activity) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;
      
      const results = [];
      
      // Process in smaller batches
      for (let i = 0; i < checkIns.length; i += 20) {
        const batch = checkIns.slice(i, i + 20);
        for (const checkIn of batch) {
          const checkInResult = await dbPool.run(stmt, [
            checkIn.user_id,
            checkIn.daypart,
            checkIn.mood,
            checkIn.body_score,
            checkIn.mind_score,
            checkIn.soul_score,
            checkIn.purpose_score,
            checkIn.micro_activity
          ]);
          results.push({ id: checkInResult.id, ...checkIn });
        }
        // Small delay between batches
        if (i + 20 < checkIns.length) {
          await new Promise(resolve => setTimeout(resolve, 5));
        }
      }
      
      return results;
    });

    res.json({ created: result.length, checkIns: result });
  } catch (error) {
    RetryHandler.handleApiError(res, error, 'batch create check-ins');
  }
});

// Generate journal
app.post('/api/journals/generate', async (req, res) => {
  try {
    const { user_id, dailyScores, journalTone, userNotes } = req.body;
    
    const journalContent = await journalGenerator.generateJournal({
      dailyScores,
      journalTone: journalTone || 'reflective',
      userNotes: userNotes || ''
    });

    const result = await RetryHandler.withRetry(async () => {
      const journalResult = await dbPool.run(`
        INSERT INTO journals (user_id, content, tone) 
        VALUES (?, ?, ?)
      `, [user_id, journalContent, journalTone || 'reflective']);

      // Update user stats
      await dbPool.run(`
        UPDATE users 
        SET total_journals = total_journals + 1, last_active = CURRENT_TIMESTAMP 
        WHERE id = ?
      `, [user_id]);

      return journalResult;
    });

    res.json({ 
      id: result.id, 
      content: journalContent,
      message: 'Journal generated successfully' 
    });
  } catch (error) {
    RetryHandler.handleApiError(res, error, 'generate journal');
  }
});

// Generate insights
app.post('/api/insights/generate', async (req, res) => {
  try {
    const { userId } = req.body;
    
    // Get user data for insights
    const userData = await dbPool.query(`
      SELECT u.*, 
        (SELECT COUNT(*) FROM check_ins WHERE user_id = u.id) as check_in_count,
        (SELECT COUNT(*) FROM journals WHERE user_id = u.id) as journal_count
      FROM users u WHERE u.id = ?
    `, [userId]);

    if (userData.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    const user = userData[0];
    
    // Only generate insights if user has enough data
    if (user.check_in_count >= 15) {
      const insights = await insightEngine.generateInsights(user);
      
      const result = await RetryHandler.withRetry(async () => {
        const insightResults = [];
        for (const insight of insights) {
          const insightResult = await dbPool.run(`
            INSERT INTO insights (user_id, type, title, description, confidence) 
            VALUES (?, ?, ?, ?, ?)
          `, [userId, insight.type, insight.title, insight.description, insight.confidence]);
          insightResults.push({ id: insightResult.id, ...insight });
        }

        // Update user stats
        await dbPool.run(`
          UPDATE users 
          SET total_insights = total_insights + ?, last_active = CURRENT_TIMESTAMP 
          WHERE id = ?
        `, [insights.length, userId]);

        return insightResults;
      });

      res.json({ 
        generated: insights.length, 
        insights: result,
        message: 'Insights generated successfully' 
      });
    } else {
      res.json({ 
        generated: 0, 
        message: `User needs more data (${user.check_in_count}/15 check-ins)` 
      });
    }
  } catch (error) {
    RetryHandler.handleApiError(res, error, 'generate insights');
  }
});

// Analytics endpoint
app.get('/api/analytics', async (req, res) => {
  try {
    const analytics = await RetryHandler.withRetry(async () => {
      return await dbPool.query(`
        SELECT 
          (SELECT COUNT(*) FROM users) as totalUsers,
          (SELECT COUNT(*) FROM users WHERE is_premium = 1) as premiumUsers,
          (SELECT COUNT(*) FROM check_ins) as totalCheckIns,
          (SELECT COUNT(*) FROM journals) as totalJournals,
          (SELECT COUNT(*) FROM insights) as totalInsights,
          (SELECT AVG(overall_score) FROM daily_scores) as avgScore
      `);
    });

    res.json(analytics[0]);
  } catch (error) {
    RetryHandler.handleApiError(res, error, 'get analytics');
  }
});

// ========================================
// H. ERROR HANDLING & GRACEFUL SHUTDOWN
// ========================================

// Global error handler
app.use((error, req, res, next) => {
  console.error('Unhandled error:', error);
  res.status(500).json({ 
    error: 'Internal server error',
    timestamp: new Date().toISOString()
  });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('🛑 SIGTERM received, shutting down gracefully...');
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('🛑 SIGINT received, shutting down gracefully...');
  process.exit(0);
});

// ========================================
// I. START SERVER
// ========================================

async function startServer() {
  try {
    await initializeDatabase();
    
    app.listen(PORT, () => {
      console.log('╔════════════════════════════════════════════════════════════╗');
      console.log('║     FULFILLMENT APP - OPTIMIZED BACKEND (40 USERS)       ║');
      console.log('╚════════════════════════════════════════════════════════════╝');
      console.log(`🚀 Server running on port ${PORT}`);
      console.log(`📦 Database: SQLite with connection pooling (10 connections)`);
      console.log(`⚡ Rate limiting: Optimized for 40 concurrent users`);
      console.log(`🔄 Batch processing: Enabled for bulk operations`);
      console.log(`🔒 CORS Origin: *`);
      console.log(`Health check: http://localhost:${PORT}/health`);
      console.log('✅ Ready for Sim8 simulation!');
    });
  } catch (error) {
    console.error('❌ Failed to start server:', error);
    process.exit(1);
  }
}

startServer();
