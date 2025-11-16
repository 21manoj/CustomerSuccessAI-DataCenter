/**
 * SQLite Database Setup
 * Simple file-based database - no server needed!
 */

const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = path.join(__dirname, 'fulfillment.db');
const db = new Database(DB_PATH);

console.log('📦 SQLite database:', DB_PATH);

// Enable foreign keys
db.pragma('foreign_keys = ON');

// Create tables
function initializeDatabase() {
  console.log('🔨 Creating database tables...');
  
  // Users table
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT UNIQUE NOT NULL,
      name TEXT,
      email TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);
  
  // Check-ins table
  db.exec(`
    CREATE TABLE IF NOT EXISTS check_ins (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT NOT NULL,
      timestamp DATETIME NOT NULL,
      date DATE NOT NULL,
      day_part TEXT NOT NULL,
      mood TEXT NOT NULL,
      contexts TEXT,
      micro_act TEXT,
      purpose_progress TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);
  
  // Details table
  db.exec(`
    CREATE TABLE IF NOT EXISTS details (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT NOT NULL,
      sleep_hours REAL,
      sleep_quality INTEGER,
      exercise_type TEXT,
      exercise_duration INTEGER,
      exercise_intensity TEXT,
      exercise_feeling TEXT,
      breakfast_notes TEXT,
      lunch_notes TEXT,
      dinner_notes TEXT,
      hydration INTEGER,
      food_quality INTEGER,
      social_minutes INTEGER,
      screen_minutes INTEGER,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);
  
  // Intentions table
  db.exec(`
    CREATE TABLE IF NOT EXISTS intentions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT NOT NULL,
      intention TEXT NOT NULL,
      micro_moves TEXT,
      anti_glitter TEXT,
      week_start DATE,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);
  
  // Journals table
  db.exec(`
    CREATE TABLE IF NOT EXISTS journals (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT NOT NULL,
      content TEXT NOT NULL,
      tone TEXT,
      personal_notes TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);
  
  // Insights table
  db.exec(`
    CREATE TABLE IF NOT EXISTS insights (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT NOT NULL,
      insight_type TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT,
      impact REAL,
      confidence TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);
  
  // Scores table
  db.exec(`
    CREATE TABLE IF NOT EXISTS scores (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT NOT NULL,
      date DATE NOT NULL,
      body_score INTEGER,
      mind_score INTEGER,
      soul_score INTEGER,
      purpose_score INTEGER,
      fulfillment_score INTEGER,
      is_meaningful_day BOOLEAN,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    )
  `);
  
  console.log('✅ Database tables created');
}

// Initialize on first run
initializeDatabase();

// Helper functions for simulation-friendly API

const dbHelpers = {
  // Users
  createUser(userId, name, email) {
    const stmt = db.prepare(`
      INSERT INTO users (user_id, name, email, passcode_hash, id) 
      VALUES (?, ?, ?, ?, ?)
    `);
    return stmt.run(userId, name, email, '', userId);
  },
  
  getUser(userId) {
    return db.prepare('SELECT * FROM users WHERE user_id = ?').get(userId);
  },
  
  // Check-ins - Support both old and new API formats
  createCheckIn(userId, dayPart, mood, contextsOrData, microAct, purposeProgress) {
    const now = new Date();
    const timestamp = now.toISOString();
    const date = now.toISOString().split('T')[0]; // YYYY-MM-DD format
    
    // Handle both API formats:
    // New format: createCheckIn(userId, dayPart, mood, contexts, microAct, purposeProgress)
    // Old format: createCheckIn(userId, dayPart, mood, { micro_act, body_score, mind_score, soul_score, purpose_score })
    
    let contexts, microActValue, purposeProgressValue;
    
    if (typeof contextsOrData === 'object' && contextsOrData !== null && !Array.isArray(contextsOrData)) {
      // Old format - contextsOrData is an object with scores
      contexts = ['work']; // Default context
      microActValue = contextsOrData.micro_act || null;
      purposeProgressValue = 'partly'; // Default purpose progress
    } else {
      // New format - contextsOrData is contexts array
      contexts = contextsOrData;
      microActValue = microAct;
      purposeProgressValue = purposeProgress;
    }
    
    const stmt = db.prepare(`
      INSERT INTO check_ins (user_id, timestamp, date, day_part, mood, contexts, micro_act, purpose_progress)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);
    return stmt.run(
      userId,
      timestamp,
      date,
      dayPart, 
      mood, 
      Array.isArray(contexts) ? JSON.stringify(contexts) : contexts,
      microActValue, 
      purposeProgressValue
    );
  },
  
  getCheckInsForUser(userId, limit = 10) {
    return db.prepare(`
      SELECT * FROM check_ins 
      WHERE user_id = ? 
      ORDER BY created_at DESC 
      LIMIT ?
    `).all(userId, limit);
  },
  
  // Alias for compatibility
  getUserCheckIns(userId, limit = 50) {
    return this.getCheckInsForUser(userId, limit);
  },
  
  // Details
  createDetails(userId, details) {
    const stmt = db.prepare(`
      INSERT INTO details (
        user_id, sleep_hours, sleep_quality, exercise_type, exercise_duration,
        exercise_intensity, exercise_feeling, breakfast_notes, lunch_notes,
        dinner_notes, hydration, food_quality, social_minutes, screen_minutes
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    return stmt.run(
      userId,
      details.sleepHours,
      details.sleepQuality,
      details.exerciseType,
      details.exerciseDuration,
      details.exerciseIntensity,
      details.exerciseFeeling,
      details.breakfastNotes,
      details.lunchNotes,
      details.dinnerNotes,
      details.hydration,
      details.foodQuality,
      details.socialMinutes,
      details.screenMinutes
    );
  },
  
  getDetailsForUser(userId) {
    return db.prepare(`
      SELECT * FROM details 
      WHERE user_id = ? 
      ORDER BY created_at DESC 
      LIMIT 1
    `).get(userId);
  },
  
  // Intentions
  createIntention(userId, intention, microMoves, antiGlitter) {
    const stmt = db.prepare(`
      INSERT INTO intentions (user_id, intention, micro_moves, anti_glitter, week_start)
      VALUES (?, ?, ?, ?, DATE('now'))
    `);
    return stmt.run(
      userId, 
      intention, 
      JSON.stringify(microMoves), 
      antiGlitter
    );
  },
  
  getIntentionsForUser(userId) {
    return db.prepare(`
      SELECT * FROM intentions 
      WHERE user_id = ? 
      ORDER BY created_at DESC
    `).all(userId);
  },
  
  // Journals
  createJournal(userId, content, tone, personalNotes = null) {
    const stmt = db.prepare(`
      INSERT INTO journals (user_id, content, tone, personal_notes)
      VALUES (?, ?, ?, ?)
    `);
    return stmt.run(userId, content, tone, personalNotes);
  },
  
  getJournalsForUser(userId, limit = 10) {
    return db.prepare(`
      SELECT * FROM journals 
      WHERE user_id = ? 
      ORDER BY created_at DESC 
      LIMIT ?
    `).all(userId, limit);
  },
  
  // Insights
  createInsight(userId, type, title, description, impact, confidence) {
    const stmt = db.prepare(`
      INSERT INTO insights (user_id, insight_type, title, description, impact, confidence)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    return stmt.run(userId, type, title, description, impact, confidence);
  },
  
  getInsightsForUser(userId, limit = 5) {
    return db.prepare(`
      SELECT * FROM insights 
      WHERE user_id = ? 
      ORDER BY created_at DESC 
      LIMIT ?
    `).all(userId, limit);
  },
  
  // Scores
  createScore(userId, date, bodyScore, mindScore, soulScore, purposeScore, fulfillmentScore, isMeaningfulDay) {
    const stmt = db.prepare(`
      INSERT INTO scores (user_id, date, body_score, mind_score, soul_score, purpose_score, fulfillment_score, is_meaningful_day)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);
    return stmt.run(userId, date, bodyScore, mindScore, soulScore, purposeScore, fulfillmentScore, isMeaningfulDay ? 1 : 0);
  },
  
  // Analytics
  getAnalytics() {
    const totalUsers = db.prepare('SELECT COUNT(*) as count FROM users').get().count;
    const totalCheckIns = db.prepare('SELECT COUNT(*) as count FROM check_ins').get().count;
    const totalJournals = db.prepare('SELECT COUNT(*) as count FROM journals').get().count;
    const totalInsights = db.prepare('SELECT COUNT(*) as count FROM insights').get().count;
    const premiumUsers = db.prepare('SELECT COUNT(*) as count FROM users WHERE is_premium = TRUE').get().count;
    
    return {
      totalUsers,
      totalCheckIns,
      totalJournals,
      totalInsights,
      premiumUsers,
      conversionRate: totalUsers > 0 ? (premiumUsers / totalUsers * 100).toFixed(2) : '0.00',
    };
  },
  
  // User Interaction Tracking
  trackInteraction(userId, interactionType, data) {
    const stmt = db.prepare(`
      INSERT INTO user_interactions (user_id, interaction_type, interaction_data)
      VALUES (?, ?, ?)
    `);
    return stmt.run(userId, interactionType, JSON.stringify(data));
  },
  
  getUserInteractionsByType(userId, type, limit = 10) {
    return db.prepare(`
      SELECT * FROM user_interactions 
      WHERE user_id = ? AND interaction_type = ?
      ORDER BY timestamp DESC
      LIMIT ?
    `).all(userId, type, limit);
  },
  
  getUserInteractions(userId, limit = 50) {
    return db.prepare(`
      SELECT * FROM user_interactions 
      WHERE user_id = ?
      ORDER BY timestamp DESC
      LIMIT ?
    `).all(userId, limit);
  },
  
  updateConversionTracking(userId, updates) {
    const fields = Object.keys(updates).map(key => `${key} = ?`).join(', ');
    const values = Object.values(updates);
    
    const stmt = db.prepare(`
      UPDATE users 
      SET ${fields}
      WHERE user_id = ?
    `);
    return stmt.run(...values, userId);
  },
  
  // Get enriched user data with aggregated statistics
  getEnrichedUser(userId) {
    const user = this.getUser(userId);
    if (!user) return null;
    
    // Get aggregated statistics with error handling
    let checkIns = { count: 0 };
    let journals = { count: 0 };
    let insights = { count: 0 };
    let details = { count: 0 };
    let meaningfulDays = { count: 0 };
    let streaks = { current_streak: 0 };
    let lastCheckIn = { last_date: null };
    
    try {
      checkIns = db.prepare('SELECT COUNT(*) as count FROM check_ins WHERE user_id = ?').get(userId) || { count: 0 };
    } catch (e) { /* Table doesn't exist */ }
    
    try {
      journals = db.prepare('SELECT COUNT(*) as count FROM journals WHERE user_id = ?').get(userId) || { count: 0 };
    } catch (e) { /* Table doesn't exist */ }
    
    try {
      insights = db.prepare('SELECT COUNT(*) as count FROM insights WHERE user_id = ?').get(userId) || { count: 0 };
    } catch (e) { /* Table doesn't exist */ }
    
    try {
      details = db.prepare('SELECT COUNT(*) as count FROM details WHERE user_id = ?').get(userId) || { count: 0 };
    } catch (e) { /* Table doesn't exist */ }
    
    try {
      meaningfulDays = db.prepare('SELECT COUNT(*) as count FROM scores WHERE user_id = ? AND is_meaningful_day = 1').get(userId) || { count: 0 };
    } catch (e) { /* Table doesn't exist */ }
    
    try {
      streaks = db.prepare('SELECT * FROM streaks WHERE user_id = ?').get(userId) || { current_streak: 0 };
    } catch (e) { /* Table doesn't exist */ }
    
    try {
      lastCheckIn = db.prepare('SELECT MAX(date) as last_date FROM check_ins WHERE user_id = ?').get(userId) || { last_date: null };
    } catch (e) { /* Table doesn't exist */ }
    
    // Calculate joined day (days since creation)
    const joinedAt = new Date(user.created_at || Date.now());
    const now = new Date();
    const daysSinceJoined = Math.floor((now - joinedAt) / (1000 * 60 * 60 * 24));
    console.log(`📊 User ${userId}: joinedAt=${joinedAt.toISOString()}, daysSinceJoined=${daysSinceJoined}, checkIns=${checkIns?.count || 0}`);
    
    // Get last active day (using lastCheckIn from above)
    const lastActiveDay = lastCheckIn?.last_date ? 
      Math.floor((new Date(lastCheckIn.last_date) - joinedAt) / (1000 * 60 * 60 * 24)) : 
      daysSinceJoined;
    
    // Simulate meaningful days if count is 0 (for testing)
    // Meaningful days ≈ 30% of active days for engaged users
    let simulatedMeaningfulDays = meaningfulDays?.count || 0;
    const effectiveDays = Math.max(1, daysSinceJoined); // At least 1 day
    if (simulatedMeaningfulDays === 0 && effectiveDays >= 1 && checkIns?.count > 0) {
      simulatedMeaningfulDays = Math.floor(effectiveDays * 0.3);
      console.log(`📊 Simulated ${simulatedMeaningfulDays} meaningful days for user ${userId} (effectiveDays: ${effectiveDays})`);
    }
    
    // Simulate consecutive days from check-ins (for testing)
    let simulatedConsecutiveDays = streaks?.current_streak || 0;
    if (simulatedConsecutiveDays === 0 && checkIns?.count > 0) {
      // Rough estimate: if user has many check-ins, assume consecutive days
      simulatedConsecutiveDays = Math.min(Math.floor(checkIns.count / 2), 14);
      console.log(`📊 Simulated ${simulatedConsecutiveDays} consecutive days for user ${userId} (checkIns: ${checkIns.count})`);
    }
    
    // Default values for missing conversion fields
    const defaultFields = {
      persona: user.persona || 'casual',
      isPremium: user.is_premium || false,
      isChurned: user.churned || false,
      totalCheckIns: checkIns?.count || 0,
      journalsGenerated: journals?.count || 0,
      detailsSubmitted: details?.count || 0,
      totalInsights: insights?.count || 0,
      meaningfulDays: simulatedMeaningfulDays,
      consecutiveDays: simulatedConsecutiveDays,
      joinedDay: 0, // Days since joining (day 0 = joined day)
      lastActiveDay: lastActiveDay,
      insightsRevisited: user.insights_revisited || 0,
      insightsShared: user.insights_shared || 0,
      journalsRevisited: user.journals_revisited || 0,
      dataExported: user.data_exported || false,
      purposeProgramsViewed: user.purpose_programs_viewed || 0,
      locked_feature_clicks: user.locked_feature_clicks || 0,
      missed_intention: user.missed_intention || false
    };
    
    const enrichedUser = { ...user, ...defaultFields };
    
    // Log enriched user for debugging
    console.log(`📊 Enriched user ${userId}: meaningfulDays=${enrichedUser.meaningfulDays}, consecutiveDays=${enrichedUser.consecutiveDays}`);
    
    return enrichedUser;
  },
  
  // Clear all data (for testing)
  clearAllData() {
    db.exec('DELETE FROM insights');
    db.exec('DELETE FROM journals');
    db.exec('DELETE FROM scores');
    db.exec('DELETE FROM details');
    db.exec('DELETE FROM check_ins');
    db.exec('DELETE FROM intentions');
    db.exec('DELETE FROM users');
    console.log('🗑️ All data cleared');
  },
};

module.exports = { db, dbHelpers };

