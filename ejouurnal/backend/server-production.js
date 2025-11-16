const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const rateLimit = require('express-rate-limit');
const Queue = require('bull');
const Redis = require('redis');

// Import services
const journalGenerator = require('./services/JournalGenerator');
const insightEngine = require('./services/InsightEngine');

const app = express();
const PORT = process.env.PORT || 3005;

// ========================================
// A. CONNECTION POOLING & QUEUE SYSTEM
// ========================================

// Redis connection for job queues
const redis = Redis.createClient({
  host: 'localhost',
  port: 6379,
  retryDelayOnFailover: 100,
  maxRetriesPerRequest: 3
});

// Job queues for different operations
const checkInQueue = new Queue('check-ins', {
  redis: { host: 'localhost', port: 6379 },
  defaultJobOptions: {
    removeOnComplete: 100,
    removeOnFail: 50,
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 2000,
    }
  }
});

const journalQueue = new Queue('journals', {
  redis: { host: 'localhost', port: 6379 },
  defaultJobOptions: {
    removeOnComplete: 50,
    removeOnFail: 25,
    attempts: 2,
    backoff: {
      type: 'exponential',
      delay: 3000,
    }
  }
});

const insightQueue = new Queue('insights', {
  redis: { host: 'localhost', port: 6379 },
  defaultJobOptions: {
    removeOnComplete: 25,
    removeOnFail: 10,
    attempts: 2,
    backoff: {
      type: 'exponential',
      delay: 5000,
    }
  }
});

// ========================================
// B. RATE LIMITING & THROTTLING
// ========================================

// Rate limiting for different endpoints
const generalLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 100, // 100 requests per minute per IP
  message: 'Too many requests, please try again later',
  standardHeaders: true,
  legacyHeaders: false,
});

const checkInLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 20, // 20 check-ins per minute per IP
  message: 'Too many check-ins, please slow down',
});

const journalLimiter = rateLimit({
  windowMs: 5 * 60 * 1000, // 5 minutes
  max: 10, // 10 journal generations per 5 minutes per IP
  message: 'Too many journal requests, please wait',
});

// ========================================
// C. DATABASE CONNECTION POOL
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
// D. BATCH PROCESSING UTILITIES
// ========================================

class BatchProcessor {
  constructor(batchSize = 10, delayMs = 100) {
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

const batchProcessor = new BatchProcessor(10, 100);

// ========================================
// E. ERROR HANDLING & RETRY MECHANISM
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
// F. MIDDLEWARE SETUP
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
// G. DATABASE INITIALIZATION
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
// H. API ENDPOINTS WITH BATCH PROCESSING
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
      queuedJobs: {
        checkIns: await checkInQueue.getWaiting(),
        journals: await journalQueue.getWaiting(),
        insights: await insightQueue.getWaiting()
      }
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

// Batch create users
app.post('/api/users/batch', async (req, res) => {
  try {
    const users = req.body.users;
    
    const result = await RetryHandler.withRetry(async () => {
      const stmt = 'INSERT INTO users (email, name, persona) VALUES (?, ?, ?)';
      const results = [];
      
      for (const user of users) {
        const userResult = await dbPool.run(stmt, [user.email, user.name, user.persona]);
        results.push({ id: userResult.id, ...user });
      }
      
      return results;
    });

    res.json({ created: result.length, users: result });
  } catch (error) {
    RetryHandler.handleApiError(res, error, 'batch create users');
  }
});

// Create check-in (with queuing)
app.post('/api/check-ins', async (req, res) => {
  try {
    const checkInData = req.body;
    
    // Add to queue for processing
    const job = await checkInQueue.add('process-check-in', checkInData, {
      priority: 1,
      delay: 0
    });

    res.json({ 
      message: 'Check-in queued for processing',
      jobId: job.id,
      status: 'queued'
    });
  } catch (error) {
    RetryHandler.handleApiError(res, error, 'create check-in');
  }
});

// Batch create check-ins
app.post('/api/check-ins/batch', async (req, res) => {
  try {
    const checkIns = req.body.checkIns;
    
    const result = await RetryHandler.withRetry(async () => {
      const stmt = `INSERT INTO check_ins 
        (user_id, daypart, mood, body_score, mind_score, soul_score, purpose_score, micro_activity) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;
      
      const results = [];
      for (const checkIn of checkIns) {
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
      
      return results;
    });

    res.json({ created: result.length, checkIns: result });
  } catch (error) {
    RetryHandler.handleApiError(res, error, 'batch create check-ins');
  }
});

// Generate journal (with queuing)
app.post('/api/journals/generate', async (req, res) => {
  try {
    const journalData = req.body;
    
    // Add to queue for processing
    const job = await journalQueue.add('generate-journal', journalData, {
      priority: 2,
      delay: 0
    });

    res.json({ 
      message: 'Journal generation queued',
      jobId: job.id,
      status: 'queued'
    });
  } catch (error) {
    RetryHandler.handleApiError(res, error, 'generate journal');
  }
});

// Generate insights (with queuing)
app.post('/api/insights/generate', async (req, res) => {
  try {
    const { userId } = req.body;
    
    // Add to queue for processing
    const job = await insightQueue.add('generate-insights', { userId }, {
      priority: 3,
      delay: 0
    });

    res.json({ 
      message: 'Insight generation queued',
      jobId: job.id,
      status: 'queued'
    });
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
// I. QUEUE PROCESSORS
// ========================================

// Check-in processor
checkInQueue.process('process-check-in', 5, async (job) => {
  const { user_id, daypart, mood, body_score, mind_score, soul_score, purpose_score, micro_activity } = job.data;
  
  try {
    await RetryHandler.withRetry(async () => {
      await dbPool.run(`
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
    });

    console.log(`✅ Processed check-in for user ${user_id}`);
  } catch (error) {
    console.error(`❌ Check-in processing failed:`, error);
    throw error;
  }
});

// Journal processor
journalQueue.process('generate-journal', 3, async (job) => {
  const { user_id, dailyScores, journalTone, userNotes } = job.data;
  
  try {
    const journalContent = await journalGenerator.generateJournal({
      dailyScores,
      journalTone: journalTone || 'reflective',
      userNotes: userNotes || ''
    });

    await RetryHandler.withRetry(async () => {
      await dbPool.run(`
        INSERT INTO journals (user_id, content, tone) 
        VALUES (?, ?, ?)
      `, [user_id, journalContent, journalTone || 'reflective']);

      // Update user stats
      await dbPool.run(`
        UPDATE users 
        SET total_journals = total_journals + 1, last_active = CURRENT_TIMESTAMP 
        WHERE id = ?
      `, [user_id]);
    });

    console.log(`✅ Generated journal for user ${user_id}`);
  } catch (error) {
    console.error(`❌ Journal generation failed:`, error);
    throw error;
  }
});

// Insight processor
insightQueue.process('generate-insights', 2, async (job) => {
  const { userId } = job.data;
  
  try {
    // Get user data for insights
    const userData = await dbPool.query(`
      SELECT u.*, 
        (SELECT COUNT(*) FROM check_ins WHERE user_id = u.id) as check_in_count,
        (SELECT COUNT(*) FROM journals WHERE user_id = u.id) as journal_count
      FROM users u WHERE u.id = ?
    `, [userId]);

    if (userData.length === 0) {
      throw new Error(`User ${userId} not found`);
    }

    const user = userData[0];
    
    // Only generate insights if user has enough data
    if (user.check_in_count >= 15) {
      const insights = await insightEngine.generateInsights(user);
      
      for (const insight of insights) {
        await RetryHandler.withRetry(async () => {
          await dbPool.run(`
            INSERT INTO insights (user_id, type, title, description, confidence) 
            VALUES (?, ?, ?, ?, ?)
          `, [userId, insight.type, insight.title, insight.description, insight.confidence]);
        });
      }

      // Update user stats
      await dbPool.run(`
        UPDATE users 
        SET total_insights = total_insights + ?, last_active = CURRENT_TIMESTAMP 
        WHERE id = ?
      `, [insights.length, userId]);

      console.log(`✅ Generated ${insights.length} insights for user ${userId}`);
    } else {
      console.log(`⏳ User ${userId} needs more data (${user.check_in_count}/15 check-ins)`);
    }
  } catch (error) {
    console.error(`❌ Insight generation failed:`, error);
    throw error;
  }
});

// ========================================
// J. ERROR HANDLING & GRACEFUL SHUTDOWN
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
  
  // Close queues
  await checkInQueue.close();
  await journalQueue.close();
  await insightQueue.close();
  
  // Close Redis
  await redis.quit();
  
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('🛑 SIGINT received, shutting down gracefully...');
  
  // Close queues
  await checkInQueue.close();
  await journalQueue.close();
  await insightQueue.close();
  
  // Close Redis
  await redis.quit();
  
  process.exit(0);
});

// ========================================
// K. START SERVER
// ========================================

async function startServer() {
  try {
    await initializeDatabase();
    
    app.listen(PORT, () => {
      console.log('╔════════════════════════════════════════════════════════════╗');
      console.log('║     FULFILLMENT APP - PRODUCTION BACKEND (40 USERS)      ║');
      console.log('╚════════════════════════════════════════════════════════════╝');
      console.log(`🚀 Server running on port ${PORT}`);
      console.log(`📦 Database: SQLite with connection pooling (10 connections)`);
      console.log(`🔄 Queues: Redis-based job processing`);
      console.log(`⚡ Rate limiting: Enabled for 40 concurrent users`);
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
