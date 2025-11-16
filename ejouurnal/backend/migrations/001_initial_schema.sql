-- FULFILLMENT APP - INITIAL DATABASE SCHEMA
-- Run this to create all tables

-- ============================================================================
-- USERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255),
  email VARCHAR(255) UNIQUE,
  is_premium BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================================
-- CHECK-INS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS check_ins (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  day_part VARCHAR(50) NOT NULL,  -- morning, day, evening, night
  mood INTEGER CHECK (mood BETWEEN 1 AND 5),
  arousal VARCHAR(50),  -- low, medium, high
  contexts JSONB,  -- array of contexts
  micro_act VARCHAR(255),  -- gratitude, meditation, walk, etc.
  duration_seconds INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_check_ins_user_id ON check_ins(user_id);
CREATE INDEX idx_check_ins_created_at ON check_ins(created_at);
CREATE INDEX idx_check_ins_day_part ON check_ins(day_part);

-- ============================================================================
-- DETAILS TABLE (Sleep, Food, Exercise, etc.)
-- ============================================================================

CREATE TABLE IF NOT EXISTS details (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  
  -- Sleep
  sleep_hours DECIMAL(4,2),
  sleep_quality INTEGER CHECK (sleep_quality BETWEEN 1 AND 5),
  
  -- Activity
  steps INTEGER,
  exercise_type VARCHAR(100),
  exercise_duration INTEGER,  -- minutes
  exercise_intensity VARCHAR(50),  -- light, moderate, vigorous
  
  -- Food
  breakfast VARCHAR(50),  -- good, ok, poor
  lunch VARCHAR(50),
  dinner VARCHAR(50),
  snacks VARCHAR(50),
  
  -- Screen time
  screen_time_minutes INTEGER,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_details_user_id ON details(user_id);
CREATE INDEX idx_details_created_at ON details(created_at);

-- ============================================================================
-- JOURNALS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS journals (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  content TEXT,
  tone VARCHAR(50),  -- reflective, coach-like, poetic, factual
  personal_notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_journals_user_id ON journals(user_id);
CREATE INDEX idx_journals_created_at ON journals(created_at);

-- ============================================================================
-- SCORES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS scores (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  date DATE NOT NULL,
  body_score INTEGER CHECK (body_score BETWEEN 0 AND 100),
  mind_score INTEGER CHECK (mind_score BETWEEN 0 AND 100),
  soul_score INTEGER CHECK (soul_score BETWEEN 0 AND 100),
  purpose_score INTEGER CHECK (purpose_score BETWEEN 0 AND 100),
  fulfillment_score INTEGER CHECK (fulfillment_score BETWEEN 0 AND 100),
  is_meaningful_day BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, date)
);

CREATE INDEX idx_scores_user_id ON scores(user_id);
CREATE INDEX idx_scores_date ON scores(date);
CREATE INDEX idx_scores_meaningful ON scores(is_meaningful_day);

-- ============================================================================
-- STREAKS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS streaks (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  current_streak INTEGER DEFAULT 0,
  longest_streak INTEGER DEFAULT 0,
  last_check_in_date DATE,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id)
);

CREATE INDEX idx_streaks_user_id ON streaks(user_id);

-- ============================================================================
-- INSIGHTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS insights (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  insight_type VARCHAR(100),  -- same-day, lag, breakpoint, purpose-path
  title VARCHAR(255),
  description TEXT,
  impact_score INTEGER,
  confidence VARCHAR(50),  -- low, medium, high
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_insights_user_id ON insights(user_id);
CREATE INDEX idx_insights_type ON insights(insight_type);
CREATE INDEX idx_insights_created_at ON insights(created_at);

-- ============================================================================
-- ANALYTICS EVENTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS analytics_events (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255),
  event_type VARCHAR(100) NOT NULL,
  event_data JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_analytics_user_id ON analytics_events(user_id);
CREATE INDEX idx_analytics_event_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_created_at ON analytics_events(created_at);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert sample data (optional, for testing)
-- INSERT INTO users (user_id, name, email) VALUES 
--   ('user_001', 'Test User', 'test@example.com');

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fulfillment_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fulfillment_user;

