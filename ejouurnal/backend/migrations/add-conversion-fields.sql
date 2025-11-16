-- Migration: Add conversion optimization fields
-- Date: 2025-10-24
-- Purpose: Add persona and other fields needed for conversion optimization

-- Add persona column to users table
ALTER TABLE users ADD COLUMN persona TEXT DEFAULT 'casual';

-- Add conversion tracking fields
ALTER TABLE users ADD COLUMN total_checkins INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN total_journals INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN total_insights INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN meaningful_days INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN last_activity_at DATETIME;
ALTER TABLE users ADD COLUMN conversion_probability REAL DEFAULT 0.0;
ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN premium_since DATETIME;
ALTER TABLE users ADD COLUMN churned BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN churned_at DATETIME;

-- Create indexes for better performance
CREATE INDEX idx_users_persona ON users(persona);
CREATE INDEX idx_users_premium ON users(is_premium);
CREATE INDEX idx_users_churned ON users(churned);
CREATE INDEX idx_users_last_activity ON users(last_activity_at);

-- Update existing users with default values
UPDATE users SET 
  persona = 'casual',
  total_checkins = 0,
  total_journals = 0,
  total_insights = 0,
  meaningful_days = 0,
  conversion_probability = 0.0,
  is_premium = FALSE,
  churned = FALSE
WHERE persona IS NULL;
