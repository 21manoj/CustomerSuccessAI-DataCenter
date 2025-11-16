-- Database Schema for Fulfillment App
-- Optimized for insight generation queries
-- Uses SQLite with SQLCipher encryption

-- ============================================
-- USER & SETTINGS
-- ============================================

CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  passcode_hash TEXT NOT NULL, -- For encryption key derivation
  biometric_enabled BOOLEAN DEFAULT FALSE,
  premium_status BOOLEAN DEFAULT FALSE,
  premium_expires_at TIMESTAMP
);

CREATE TABLE user_preferences (
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  
  -- Fulfillment weights (personalized over time)
  body_weight REAL DEFAULT 0.25,
  mind_weight REAL DEFAULT 0.25,
  soul_weight REAL DEFAULT 0.25,
  purpose_weight REAL DEFAULT 0.25,
  
  -- Thresholds for "Meaningful Day"
  body_threshold REAL DEFAULT 70,
  mind_threshold REAL DEFAULT 65,
  soul_threshold REAL DEFAULT 75,
  purpose_threshold REAL DEFAULT 60,
  
  -- Baselines (calculated from first 2 weeks)
  social_minutes_baseline REAL DEFAULT 70,
  sleep_hours_baseline REAL DEFAULT 7.5,
  activity_minutes_baseline REAL DEFAULT 30,
  
  -- Journal preferences
  journal_tone TEXT DEFAULT 'reflective', -- reflective, factual, coach-like, poetic
  
  -- Privacy settings
  cloud_sync_enabled BOOLEAN DEFAULT FALSE,
  device_data_sync BOOLEAN DEFAULT TRUE,
  anonymous_aggregation BOOLEAN DEFAULT FALSE,
  
  -- Reminder times (JSON array)
  reminder_times TEXT DEFAULT '{"morning":"8:00","day":"13:00","evening":"18:00","night":"21:00"}',
  
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- CORE DATA (Encrypted)
-- ============================================

CREATE TABLE check_ins (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  timestamp TIMESTAMP NOT NULL,
  date DATE NOT NULL, -- For efficient querying
  day_part TEXT NOT NULL, -- morning, day, evening, night
  
  -- Core check-in data
  mood TEXT NOT NULL, -- very-low, low, neutral, good, great
  arousal TEXT, -- low, medium, high
  contexts TEXT, -- JSON array: ["work", "social"]
  micro_act TEXT, -- gratitude, meditation, walk, etc.
  purpose_progress TEXT, -- yes, partly, no (night check-in only)
  sparkle_tagged BOOLEAN DEFAULT FALSE,
  
  -- Voice note (encrypted file path)
  voice_note_path TEXT,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  synced_to_cloud BOOLEAN DEFAULT FALSE,
  
  -- Indexes for fast queries
  INDEX idx_checkins_user_date (user_id, date),
  INDEX idx_checkins_daypart (user_id, day_part),
  INDEX idx_checkins_microact (user_id, micro_act) WHERE micro_act IS NOT NULL
);

CREATE TABLE body_metrics (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  
  -- Sleep data (from HealthKit/Google Fit or manual)
  sleep_hours REAL,
  sleep_quality INTEGER, -- 1-5 stars
  sleep_start_time TIME,
  sleep_end_time TIME,
  
  -- Activity data
  steps INTEGER,
  active_minutes INTEGER,
  distance_km REAL,
  calories_burned INTEGER,
  hrv INTEGER, -- Heart Rate Variability (optional)
  resting_hr INTEGER, -- Resting Heart Rate (optional)
  
  -- Fuel data
  fuel_quality TEXT, -- good, ok, poor
  
  -- Source tracking
  data_source TEXT DEFAULT 'manual', -- manual, healthkit, googlefit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(user_id, date),
  INDEX idx_body_user_date (user_id, date)
);

CREATE TABLE mind_metrics (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  
  -- Focus data
  focus_minutes INTEGER DEFAULT 0,
  deep_work_sessions INTEGER DEFAULT 0,
  
  -- Screen time (from OS or manual)
  screen_time_minutes INTEGER,
  social_media_minutes INTEGER,
  work_screen_minutes INTEGER,
  entertainment_minutes INTEGER,
  
  -- Stress relief
  stress_relief_used BOOLEAN DEFAULT FALSE,
  stress_relief_type TEXT, -- breathwork, walk, journal
  
  -- Source
  data_source TEXT DEFAULT 'manual',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(user_id, date),
  INDEX idx_mind_user_date (user_id, date)
);

CREATE TABLE soul_metrics (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  
  -- Aggregated micro-acts from check-ins
  micro_acts_count INTEGER DEFAULT 0,
  micro_acts_variety INTEGER DEFAULT 0, -- Unique types
  
  -- Social interactions
  social_energized_count INTEGER DEFAULT 0,
  social_neutral_count INTEGER DEFAULT 0,
  social_drained_count INTEGER DEFAULT 0,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(user_id, date),
  INDEX idx_soul_user_date (user_id, date)
);

-- ============================================
-- DETAIL ENTRIES (Premium Feature)
-- ============================================

CREATE TABLE food_logs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  meal_type TEXT NOT NULL, -- breakfast, lunch, dinner, snack
  quality TEXT NOT NULL, -- good, ok, poor
  notes TEXT, -- Optional: "Oatmeal + fruit"
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_food_user_date (user_id, date)
);

CREATE TABLE exercise_logs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  exercise_type TEXT NOT NULL, -- walk, run, gym, yoga, sport
  duration_minutes INTEGER NOT NULL,
  intensity TEXT NOT NULL, -- light, moderate, vigorous
  feeling_after TEXT, -- energized, good, tired
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_exercise_user_date (user_id, date)
);

CREATE TABLE social_interactions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  quality TEXT NOT NULL, -- energized, neutral, drained
  
  -- Optional details
  who_category TEXT, -- friend, family, colleague, other
  who_name TEXT, -- Optional free text (encrypted)
  duration_minutes INTEGER,
  interaction_type TEXT, -- deep-talk, casual, meeting, group
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_social_user_date (user_id, date)
);

-- ============================================
-- CALCULATED SCORES
-- ============================================

CREATE TABLE daily_scores (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  
  -- Dimension scores (0-100)
  body_score REAL NOT NULL,
  mind_score REAL NOT NULL,
  soul_score REAL NOT NULL,
  purpose_score REAL NOT NULL,
  
  -- Overall
  fulfillment_score REAL NOT NULL,
  is_meaningful_day BOOLEAN DEFAULT FALSE,
  
  -- Calculation metadata
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  recalculated_count INTEGER DEFAULT 0,
  
  UNIQUE(user_id, date),
  INDEX idx_scores_user_date (user_id, date),
  INDEX idx_scores_meaningful (user_id, is_meaningful_day, date)
);

-- ============================================
-- PURPOSE TRACKING
-- ============================================

CREATE TABLE weekly_intentions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,
  
  intention TEXT NOT NULL,
  anti_glitter_experiment TEXT,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(user_id, week_start),
  INDEX idx_intentions_user_week (user_id, week_start)
);

CREATE TABLE micro_moves (
  id TEXT PRIMARY KEY,
  intention_id TEXT NOT NULL REFERENCES weekly_intentions(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  order_index INTEGER NOT NULL, -- 1, 2, or 3
  completed BOOLEAN DEFAULT FALSE,
  completed_date DATE,
  
  INDEX idx_micromoves_intention (intention_id)
);

-- ============================================
-- INSIGHTS (Generated)
-- ============================================

CREATE TABLE insights (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  type TEXT NOT NULL, -- same-day, lag, breakpoint, purpose-path
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  
  confidence TEXT NOT NULL, -- high, medium, low
  source_metric TEXT NOT NULL,
  target_metric TEXT NOT NULL,
  lag_days INTEGER,
  impact REAL NOT NULL,
  
  -- Ranking metadata
  relevance_score REAL, -- Impact × confidence for ranking
  shown_to_user BOOLEAN DEFAULT FALSE,
  user_clicked BOOLEAN DEFAULT FALSE,
  user_acted_on BOOLEAN DEFAULT FALSE, -- Did they follow the suggestion?
  
  -- A/B testing
  variant TEXT, -- control, variant-a, variant-b (for testing presentation)
  
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP, -- Insights can become stale
  
  INDEX idx_insights_user (user_id, generated_at),
  INDEX idx_insights_relevance (user_id, relevance_score DESC)
);

-- ============================================
-- AI JOURNALS (Extra Encryption Layer)
-- ============================================

CREATE TABLE journals (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  
  -- AI-generated content (encrypted with journalKey)
  ai_text_encrypted TEXT NOT NULL,
  
  -- User edits (encrypted)
  user_edited_text_encrypted TEXT,
  user_notes_encrypted TEXT,
  
  -- Metadata
  tone TEXT NOT NULL, -- reflective, factual, coach-like, poetic
  word_count INTEGER,
  generation_time_ms INTEGER,
  regeneration_count INTEGER DEFAULT 0,
  
  -- User engagement
  read_count INTEGER DEFAULT 0,
  time_spent_reading_seconds INTEGER DEFAULT 0,
  edited BOOLEAN DEFAULT FALSE,
  exported BOOLEAN DEFAULT FALSE,
  shared_with_coach BOOLEAN DEFAULT FALSE,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(user_id, date),
  INDEX idx_journals_user_date (user_id, date DESC)
);

-- ============================================
-- ANALYTICS & A/B TESTING
-- ============================================

CREATE TABLE events (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_name TEXT NOT NULL,
  event_properties TEXT, -- JSON
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- A/B test assignment
  ab_test_id TEXT,
  ab_test_variant TEXT,
  
  INDEX idx_events_user (user_id, timestamp),
  INDEX idx_events_name (event_name, timestamp),
  INDEX idx_events_abtest (ab_test_id, ab_test_variant)
);

CREATE TABLE ab_tests (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  start_date DATE NOT NULL,
  end_date DATE,
  
  variants TEXT NOT NULL, -- JSON array: ["control", "variant-a", "variant-b"]
  allocation TEXT NOT NULL, -- JSON: {"control": 0.5, "variant-a": 0.25, "variant-b": 0.25}
  
  success_metric TEXT NOT NULL, -- e.g., "insight_clicked", "user_acted_on", "retention_d7"
  
  active BOOLEAN DEFAULT TRUE,
  
  INDEX idx_abtests_active (active, start_date)
);

-- ============================================
-- QUERY OPTIMIZATION VIEWS
-- ============================================

-- View for quick MDW calculation
CREATE VIEW weekly_mdw AS
SELECT 
  user_id,
  strftime('%Y-%W', date) as week,
  COUNT(*) as meaningful_days_count
FROM daily_scores
WHERE is_meaningful_day = TRUE
GROUP BY user_id, week;

-- View for latest scores (frequently accessed)
CREATE VIEW latest_scores AS
SELECT 
  user_id,
  date,
  body_score,
  mind_score,
  soul_score,
  purpose_score,
  fulfillment_score,
  is_meaningful_day
FROM daily_scores
WHERE (user_id, date) IN (
  SELECT user_id, MAX(date)
  FROM daily_scores
  GROUP BY user_id
);

-- View for insight generation (7-day rolling window)
CREATE VIEW recent_data_for_insights AS
SELECT
  user_id,
  date,
  body_score,
  mind_score,
  soul_score,
  purpose_score
FROM daily_scores
WHERE date >= date('now', '-7 days')
ORDER BY user_id, date;

-- ============================================
-- COMMON QUERIES FOR INSIGHT GENERATION
-- ============================================

-- Query 1: Get all data for last 30 days (for lag correlation analysis)
-- SELECT * FROM check_ins WHERE user_id = ? AND date >= date('now', '-30 days') ORDER BY timestamp;

-- Query 2: Get sleep vs mind score (for breakpoint detection)
-- SELECT b.date, b.sleep_hours, s.mind_score 
-- FROM body_metrics b 
-- JOIN daily_scores s ON b.user_id = s.user_id AND b.date = s.date
-- WHERE b.user_id = ? AND b.date >= date('now', '-30 days');

-- Query 3: Get micro-acts vs purpose score (for purpose-path tracking)
-- SELECT date, micro_acts_count, purpose_score 
-- FROM soul_metrics sm
-- JOIN daily_scores ds ON sm.user_id = ds.user_id AND sm.date = ds.date
-- WHERE sm.user_id = ? ORDER BY date;

-- Query 4: Get social media impact (high vs low use days)
-- SELECT date, social_media_minutes, mind_score, soul_score
-- FROM mind_metrics mm
-- JOIN daily_scores ds ON mm.user_id = ds.user_id AND mm.date = ds.date
-- WHERE mm.user_id = ? AND date >= date('now', '-14 days');

-- Query 5: Get current week's MDW
-- SELECT * FROM weekly_mdw WHERE user_id = ? AND week = strftime('%Y-%W', 'now');

-- ============================================
-- DIFFERENTIAL PRIVACY AGGREGATION
-- ============================================

-- Server-side table (separate database, no PII)
CREATE TABLE aggregated_insights (
  id TEXT PRIMARY KEY,
  
  -- Pattern metadata (no user info)
  insight_type TEXT NOT NULL,
  source_metric TEXT NOT NULL,
  target_metric TEXT NOT NULL,
  
  -- Aggregated statistics (with Laplace noise)
  sample_size INTEGER NOT NULL, -- Always >= 1000 to prevent re-identification
  avg_impact REAL NOT NULL,
  median_impact REAL NOT NULL,
  confidence REAL NOT NULL,
  
  -- Cohort (very broad categories only)
  age_group TEXT, -- "18-30", "31-45", "46+"
  goal_category TEXT, -- "calm", "strength", "purpose"
  
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_agg_metrics (source_metric, target_metric)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Fast access to recent check-ins for homepage
CREATE INDEX idx_recent_checkins ON check_ins(user_id, date DESC, day_part);

-- Fast calculation of daily scores
CREATE INDEX idx_metrics_calculation ON body_metrics(user_id, date);

-- Fast journal generation (get all day's data)
CREATE INDEX idx_daily_data ON check_ins(user_id, date);

-- Fast insight ranking
CREATE INDEX idx_insights_rank ON insights(user_id, relevance_score DESC, expires_at);

-- ============================================
-- TRIGGERS (Auto-update calculated fields)
-- ============================================

-- Update MDW when daily_scores changes
CREATE TRIGGER update_mdw_on_score_change
AFTER INSERT ON daily_scores
BEGIN
  -- Logic to recalculate weekly MDW
  -- (Implementation depends on ORM/query framework)
END;

-- Update timestamps
CREATE TRIGGER update_journal_timestamp
AFTER UPDATE ON journals
BEGIN
  UPDATE journals SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================
-- SAMPLE QUERIES (Performance Optimized)
-- ============================================

/*

-- Get today's check-ins status
SELECT day_part, id FROM check_ins 
WHERE user_id = ? AND date = date('now')
ORDER BY timestamp;

-- Get last 7 days of scores for timeline
SELECT date, body_score, mind_score, soul_score, purpose_score, is_meaningful_day
FROM daily_scores
WHERE user_id = ? AND date >= date('now', '-7 days')
ORDER BY date;

-- Get top 5 insights for user
SELECT * FROM insights
WHERE user_id = ? 
  AND shown_to_user = FALSE
  AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY relevance_score DESC
LIMIT 5;

-- Calculate current streak
WITH RECURSIVE streak AS (
  SELECT date, 1 as days
  FROM check_ins
  WHERE user_id = ?
  GROUP BY date
  HAVING COUNT(*) >= 1
  ORDER BY date DESC
  LIMIT 1
  
  UNION ALL
  
  SELECT c.date, s.days + 1
  FROM check_ins c
  JOIN streak s ON c.date = date(s.date, '-1 day')
  WHERE c.user_id = ?
  GROUP BY c.date
  HAVING COUNT(*) >= 1
)
SELECT MAX(days) as current_streak FROM streak;

-- Get all data for journal generation (optimized single query)
SELECT
  c.timestamp,
  c.day_part,
  c.mood,
  c.contexts,
  c.micro_act,
  c.purpose_progress,
  b.sleep_hours,
  b.sleep_quality,
  b.steps,
  b.active_minutes,
  b.fuel_quality,
  m.screen_time_minutes,
  m.social_media_minutes,
  m.focus_minutes,
  s.body_score,
  s.mind_score,
  s.soul_score,
  s.purpose_score,
  s.fulfillment_score,
  s.is_meaningful_day
FROM check_ins c
LEFT JOIN body_metrics b ON c.user_id = b.user_id AND c.date = b.date
LEFT JOIN mind_metrics m ON c.user_id = m.user_id AND c.date = m.date
LEFT JOIN daily_scores s ON c.user_id = s.user_id AND c.date = s.date
WHERE c.user_id = ? AND c.date = ?
ORDER BY c.timestamp;

*/

-- ============================================
-- ENCRYPTION NOTES
-- ============================================

/*

ENCRYPTION STRATEGY:

1. Local Storage (SQLite):
   - Entire database encrypted with SQLCipher
   - Key derived from user's passcode via PBKDF2
   - Biometric unlock (Face ID / Touch ID) unlocks key

2. Cloud Sync:
   - Each row encrypted individually with user's cloudKey
   - Server stores encrypted blobs + metadata
   - Server CANNOT decrypt (zero-knowledge)

3. Journals (Extra Layer):
   - Encrypted with separate journalKey
   - Can disable cloud sync for journals only
   - Most sensitive data gets extra protection

4. Data Minimization:
   - Store only counts/scores for aggregation, not raw text
   - Free-form notes only in journals table
   - Contexts as enum, not free text

5. Differential Privacy:
   - Add Laplace noise before contributing to aggregate
   - Aggregate only with sample size >= 1000
   - No user identifiers in aggregated_insights table

*/

