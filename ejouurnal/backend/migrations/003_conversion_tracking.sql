-- Phase 1: Conversion Tracking Migration
-- Add interaction tracking columns to users table
-- Create user_interactions table for granular tracking

-- Add conversion tracking columns to users table
ALTER TABLE users ADD COLUMN locked_feature_clicks INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN premium_preview_time INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN missed_intention BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN recent_fulfillment_drop BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN locked_insight_count INTEGER DEFAULT 0;

-- Create user_interactions table for granular tracking
CREATE TABLE IF NOT EXISTS user_interactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL REFERENCES users(id),
  interaction_type TEXT NOT NULL, -- 'locked_insight_click', 'premium_preview_view', 'conversion_offer_dismissed', etc.
  interaction_data TEXT, -- JSON
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_interactions_user_time ON user_interactions(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON user_interactions(interaction_type);

