# Fulfillment App - Complete API & Database Documentation

## Table of Contents
1. [User-Facing API Endpoints](#user-facing-api-endpoints)
2. [Internal App Endpoints](#internal-app-endpoints)
3. [Database Schemas](#database-schemas)
4. [Insights Algorithm](#insights-algorithm)

---

## User-Facing API Endpoints

### Health Check
```
GET /health
```
Returns overall system health and analytics.

---

### Daily User Flow

#### 1. Check-in (4 times per day)
```
POST /api/check-ins
Body:
{
  "user_id": "user_123",
  "day_part": "morning|day|evening|night",
  "mood": "very-low|low|neutral|good|great",
  "contexts": ["work", "health", "social"],
  "micro_act": "gratitude|meditation|walk|water"
}
```
**Frequency:** 4x per day  
**Purpose:** Capture mood and micro-activities

#### 2. Add Daily Details
```
POST /api/details
Body:
{
  "userId": "user_123",
  "sleepHours": 7.5,
  "sleepQuality": 4,
  "exerciseType": "running",
  "exerciseDuration": 30,
  "exerciseIntensity": "moderate",
  "breakfastNotes": "oatmeal with berries",
  "lunchNotes": "grilled chicken salad",
  "dinnerNotes": "salmon with vegetables"
}
```
**Frequency:** 1x per day (optional)  
**Purpose:** Capture detailed sleep, exercise, and nutrition data

#### 3. Generate AI Journal
```
POST /api/journals/generate
Body:
{
  "userId": "user_123",
  "tone": "reflective|coach-like|poetic|factual|insightful"
}
```
**Frequency:** 1-2x per day  
**Purpose:** AI-generated personalized journal  
**Requires:** Minimum 3 check-ins

---

### Weekly User Flow

#### 4. Set Weekly Intention (Sunday)
```
POST /api/intentions
Body:
{
  "userId": "user_123",
  "intention": "Establish morning routine",
  "microMoves": ["Wake up 6 AM", "Drink water", "Meditate 10 min"],
  "antiGlitter": "Limit social media before bed"
}
```
**Frequency:** 1x per week (Sunday)  
**Purpose:** Set weekly goal with actionable micro-moves

#### 5. Generate Insights
```
POST /api/insights/generate
Body:
{
  "userId": "user_123"
}
```
**Frequency:** 1-2x per week  
**Purpose:** AI-generated data-driven insights  
**Requires:** Minimum 4 check-ins  
**Returns:** Up to 10 ranked insights

#### 6. Premium Conversion
```
POST /api/conversion/calculate
Body:
{
  "userId": "user_123",
  "currentDay": 5
}

POST /api/conversion/offer
Body:
{
  "userId": "user_123",
  "tier": "premium"
}

POST /api/users/:userId/premium
Body:
{
  "tier": "premium|premium_plus",
  "plan": "monthly|annual"
}
```
**Frequency:** As triggered by conversion logic  
**Purpose:** Calculate probability, show offer, upgrade user

---

## Internal App Endpoints

### Analytics
```
GET /api/analytics
```
Returns system-wide metrics:
- Total users, check-ins, journals, insights
- Premium conversion rate

### User Management
```
GET /api/users/:userId
POST /api/users
```
Get user details or create new user.

### Batch Operations
```
POST /api/check-ins/batch
```
Batch create multiple check-ins (for testing/simulation).

### Journal Regeneration
```
POST /api/journals/:id/regenerate
Body:
{
  "tone": "reflective"
}
```
Regenerate journal with new tone.

### Onboarding Optimization
```
POST /api/onboarding/flow
Body:
{
  "userId": "user_123"
}
```
Get personalized onboarding flow based on persona.

### Value Proposition
```
POST /api/value-proposition
Body:
{
  "userId": "user_123"
}
```
Get personalized value proposition based on engagement.

---

## Database Schemas

### Users Table
```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  user_id TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  persona TEXT DEFAULT 'casual',
  passcode_hash TEXT NOT NULL,
  biometric_enabled BOOLEAN DEFAULT FALSE,
  premium_status BOOLEAN DEFAULT FALSE,
  is_premium BOOLEAN DEFAULT FALSE,
  premium_since DATETIME,
  premium_tier TEXT,
  premium_expires_at TIMESTAMP,
  total_checkins INTEGER DEFAULT 0,
  total_journals INTEGER DEFAULT 0,
  total_insights INTEGER DEFAULT 0,
  meaningful_days INTEGER DEFAULT 0,
  last_activity_at DATETIME,
  conversion_probability REAL DEFAULT 0.0,
  churned BOOLEAN DEFAULT FALSE,
  churned_at DATETIME,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Check-ins Table
```sql
CREATE TABLE check_ins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL REFERENCES users(id),
  timestamp DATETIME NOT NULL,
  date DATE NOT NULL,
  day_part TEXT NOT NULL, -- morning, day, evening, night
  mood TEXT NOT NULL, -- very-low, low, neutral, good, great
  contexts TEXT, -- JSON array
  micro_act TEXT, -- gratitude, meditation, etc.
  purpose_progress TEXT, -- yes, partly, no
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Details Table
```sql
CREATE TABLE details (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL REFERENCES users(id),
  sleep_hours REAL,
  sleep_quality INTEGER, -- 1-5
  exercise_type TEXT,
  exercise_duration INTEGER,
  exercise_intensity TEXT, -- low, moderate, high
  exercise_feeling TEXT, -- energized, tired, satisfied
  breakfast_notes TEXT,
  lunch_notes TEXT,
  dinner_notes TEXT,
  hydration INTEGER, -- glasses of water
  food_quality INTEGER, -- 1-5
  social_minutes INTEGER,
  screen_minutes INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Intentions Table
```sql
CREATE TABLE intentions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL REFERENCES users(id),
  intention TEXT NOT NULL,
  micro_moves TEXT, -- JSON array
  anti_glitter TEXT,
  week_start DATE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Journals Table
```sql
CREATE TABLE journals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL REFERENCES users(id),
  content TEXT NOT NULL,
  tone TEXT,
  personal_notes TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Insights Table
```sql
CREATE TABLE insights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL REFERENCES users(id),
  insight_type TEXT NOT NULL, -- correlation, pattern, breakpoint, purpose-path
  title TEXT NOT NULL,
  description TEXT,
  impact REAL,
  confidence TEXT, -- high, medium, low
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Scores Table
```sql
CREATE TABLE scores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL REFERENCES users(id),
  date DATE NOT NULL,
  body_score INTEGER, -- 0-100
  mind_score INTEGER, -- 0-100
  soul_score INTEGER, -- 0-100
  purpose_score INTEGER, -- 0-100
  fulfillment_score INTEGER, -- 0-100
  is_meaningful_day BOOLEAN,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Insights Algorithm

### Algorithm Overview
The **InsightEngine** generates 4 types of insights:

### 1. SAME-DAY Correlations (FREE)
**Purpose:** Immediate effects analysis  
**Requirements:** 6+ check-ins  
**Algorithm:**
- Correlate check-in mood with micro-activities
- Match same-day details (sleep, exercise) to mood
- Calculate Pearson correlation coefficients
- Confidence levels: high (>0.7), medium (>0.5), low (>0.3)

**Example:**
```
"Your sleep quality (4/5) strongly correlates with your morning energy (good mood). 
On days you sleep 7+ hours, your mood averages 4.2/5 vs 2.8/5 on days with <6 hours."
```

### 2. LAG Correlations (FREE)
**Purpose:** Delayed effects (1-7 days)  
**Requirements:** 7+ days of data  
**Algorithm:**
- Test lag correlations between metrics
- Example: Sunday exercise → Wednesday mood improvement
- Uses time-series correlation analysis
- Tests lags from 1-7 days

**Example:**
```
"Your exercise on Monday correlates with elevated mood on Wednesday (+0.3 days lag).
When you exercise ≥30 min on Monday, your mid-week mood improves by 0.8 points."
```

### 3. BREAKPOINT Detection (PREMIUM)
**Purpose:** Identify personal thresholds  
**Requirements:** 10+ days of data, Premium membership  
**Algorithm:**
- Find threshold values where outcomes change significantly
- Example: Sleep <7 hours → dramatic mood drop
- Uses regression trees and threshold analysis
- Calculates confidence based on sample size

**Example:**
```
"Your personal sleep threshold is 7 hours. Below this, your mood drops by 1.5 points.
Above 8 hours, benefits plateau. Your 'sweet spot': 7-8 hours."
```

### 4. PURPOSE-PATH Tracking (PREMIUM)
**Purpose:** Intent → outcome analysis  
**Requirements:** 14+ days of data, Premium membership  
**Algorithm:**
- Track weekly intentions to daily outcomes
- Measure adherence to micro-moves
- Correlate micro-move completion with fulfillment scores
- Calculate path success probability

**Example:**
```
"Your 'morning routine' intention shows 80% micro-move completion.
On days you complete all 3 micro-moves, your fulfillment scores 15 points higher."
```

### 5. Social Media Impact (FREE)
**Purpose:** Screen time effects  
**Requirements:** 5+ days of details  
**Algorithm:**
- Correlate screen_minutes with sleep_quality
- Test impact on mood and scores
- Calculate threshold where benefits reverse

**Example:**
```
"Screen time over 2 hours before bed correlates with 0.8-hour sleep reduction.
Your mood is 0.5 points lower on days with >3 hours screen time."
```

### Insight Ranking
Insights are ranked by **Impact Score**:
```
Impact Score = (Confidence × Outcome Magnitude) × Personal Relevance
```

### Confidence Calculation
- **High (0.7-1.0):** Strong statistical correlation, clear pattern
- **Medium (0.5-0.7):** Moderate correlation, visible trend
- **Low (0.3-0.5):** Weak correlation, emerging pattern

### Privacy & Performance
- All calculations done server-side
- No data sent to external services (except OpenAI for journals)
- Optimized queries with indexes
- Cached results for 24 hours

---

## Daily Flow Summary

### Morning (6:00 AM - 12:00 PM)
1. Morning check-in (`POST /api/check-ins`)
2. Add details if applicable (`POST /api/details`)

### Afternoon (12:00 PM - 6:00 PM)
3. Day check-in (`POST /api/check-ins`)

### Evening (6:00 PM - 10:00 PM)
4. Evening check-in (`POST /api/check-ins`)
5. Generate journal (`POST /api/journals/generate`)

### Night (10:00 PM - 2:00 AM)
6. Night check-in (`POST /api/check-ins`)

### Weekly (Sunday)
7. Set intention (`POST /api/intentions`)
8. Generate insights (`POST /api/insights/generate`)
9. Check conversion probability (`POST /api/conversion/calculate`)

---

## Data Flow Architecture

```
User → POST /api/check-ins → SQLite DB
                              ↓
                              InsightEngine (daily batch)
                              ↓
                              Insights stored
                              ↓
User → POST /api/journals/generate → JournalGenerator
                                    → OpenAI GPT-4o-mini
                                    → Returns personalized journal
                                    ↓
                                    Journal stored
                                    ↓
User → POST /api/insights/generate → InsightEngine
                                    → Returns 10 ranked insights
```

---

## Testing & Development

### Simulation Endpoints
All production endpoints work in simulation mode for testing.

### Rate Limiting
- Default: 5000 requests/minute
- Configurable via `RATE_LIMIT_MAX` in `backend/server-fixed.js`

### Environment Variables
```env
OPENAI_API_KEY=your_key_here
PORT=3005
NODE_ENV=production|development
```

