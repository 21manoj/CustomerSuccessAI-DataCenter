-- ============================================================================
-- NOTIFICATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS notifications (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  type VARCHAR(100) NOT NULL,  -- new_insight, first_insight, premium_gate, etc.
  title VARCHAR(255) NOT NULL,
  body TEXT,
  data JSONB,  -- Additional payload
  sent_at TIMESTAMP DEFAULT NOW(),
  viewed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, viewed_at, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);

-- ============================================================================
-- UPDATE INSIGHTS TABLE (add viewed_at if not exists)
-- ============================================================================

DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'insights' AND column_name = 'viewed_at'
  ) THEN
    ALTER TABLE insights ADD COLUMN viewed_at TIMESTAMP;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_insights_user_viewed ON insights(user_id, viewed_at);

