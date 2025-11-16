# 🎭 100-User Load Testing Simulator

Simulates 100 users with realistic behavior patterns over 12 simulated days (2 hours real time).

## 🚀 Quick Start

```bash
cd simulator
node run-simulation.js
```

That's it! The simulation will run for 2 hours (12 simulated days).

## ⏰ Time Scale

- **10 minutes real time = 1 simulated day**
- **2 hours total = 12 simulated days**
- Check-ins happen throughout each "day" (10-minute period)

## 👥 User Personas

The simulator creates 4 types of users with realistic behavior:

### 1. **Engaged Users (30%)** 📈
- 85% check-in rate
- Good sleep (7-8h)
- Low social media (30-60 min/day)
- High motivation
- **Most likely to convert to premium**

### 2. **Casual Users (45%)** 😊
- 55% check-in rate
- Average sleep (5.5-7h)
- Moderate social media (45-90 min/day)
- Medium motivation
- **Baseline conversion rate**

### 3. **Strugglers (20%)** 😓
- 30% check-in rate
- Poor sleep (<5.5h)
- High social media (60-120 min/day)
- Low motivation
- **Low conversion, high churn risk**

### 4. **Power Users (5%)** ⚡
- 95% check-in rate
- Excellent sleep (7.5-8.5h)
- Very low social media (15-45 min/day)
- Very high motivation
- **Highest conversion rate**

## 📊 What Gets Simulated

### ✅ User Actions:
- 4× daily check-ins (Morning, Day, Evening, Night)
- Mood ratings (1-5 scale)
- Micro-acts (Gratitude, Meditation, Walk, etc.)
- Details logging (sleep, steps, screen time)
- Premium conversions

### 📈 Metrics Tracked:
- Daily active users
- Check-in completion rates
- Meaningful Days per Week (MDW)
- Retention (D1, D7)
- Premium conversion rate
- Avg fulfillment scores
- Engagement metrics
- Churn risk

## 🎯 Behavioral Patterns

### Check-in Probability Factors:
1. **Persona type** (engaged vs struggler)
2. **Day of simulation** (novelty decay)
3. **Time of day** (morning highest)
4. **Current streak** (momentum bonus)
5. **Premium status** (25% boost)

### Premium Conversion Triggers:
1. **3+ Meaningful Days** → High conversion probability
2. **Day 7+ with high engagement** → Conversion eligible
3. **Persona affects conversion rate:**
   - Power users: 40%
   - Engaged: 25%
   - Casual: 8%
   - Strugglers: 2%

### Meaningful Day Criteria:
All of these must be met:
- Body Score ≥ 70
- Mind Score ≥ 65
- Soul Score ≥ 80
- Purpose Score ≥ 55

## 📊 Output

### Console Output:
- Real-time progress for each simulated day
- Daily active users
- Check-in counts
- Meaningful days
- Premium conversions

### JSON File:
Saved to `output/simulation-[timestamp].json`:
```json
{
  "users": [...],        // All 100 user profiles with final stats
  "checkIns": [...],     // All check-in events
  "details": [...],      // Detailed data entries
  "analytics": [...],    // All tracked events
  "report": {...}        // Summary analytics
}
```

## 📈 Key Metrics Reported

### Overview:
- Total Users: 100
- Active Users (made ≥1 check-in)
- Premium Users & Conversion Rate
- Total Check-ins
- Avg Meaningful Days/Week
- Avg Fulfillment Score

### Revenue:
- MRR (Monthly Recurring Revenue)
- ARR (Annual Recurring Revenue)
- Projected at $7.99/month

### Example Output:
```
📊 FINAL ANALYTICS REPORT
═══════════════════════════════════════════════

👥 USER METRICS:
   Total Users: 100
   Active Users: 87
   Premium Users: 18 (18.0%)

✅ ENGAGEMENT:
   Total Check-ins: 1,247
   Avg MDW: 2.34
   Avg Fulfillment Score: 68.5/100

💰 REVENUE:
   MRR: $143.82
   ARR: $1,725.84
```

## 🔄 What Happens During Simulation

### Each "Day" (10 minutes):
1. **Morning (0-2.5 min)**: Users perform morning check-ins
2. **Day (2.5-5 min)**: Daytime check-ins
3. **Evening (5-7.5 min)**: Evening check-ins
4. **Night (7.5-10 min)**: Night check-ins + journal generation
5. **End of day**: Update scores, detect MDW, process conversions

### Score Evolution:
- Scores start at 50-70 (baseline)
- Increase with:
  - Positive mood ratings
  - Completing micro-acts
  - Good sleep quality
  - Consistent check-ins
- Decrease with:
  - Missed check-ins
  - Broken streaks
  - Poor sleep

## 🎲 Realistic Randomness

The simulator includes:
- **Variability** in check-in times
- **Decay** in engagement over time (novelty wears off)
- **Momentum** effects (streaks boost probability)
- **Persona-consistent** behavior patterns
- **Natural churn** (some users stop checking in)

## 🧪 Use Cases

1. **Load Testing**: See how 100 concurrent users behave
2. **Metrics Validation**: Test analytics calculations
3. **Business Model**: Validate pricing and conversion assumptions
4. **Retention Analysis**: Identify churn patterns
5. **A/B Testing Prep**: Baseline metrics for experiments

## ⚙️ Configuration

Edit `run-simulation.js` to adjust:

```javascript
const TOTAL_USERS = 100;        // Number of users
const MINUTES_PER_DAY = 10;     // Real time per simulated day
const TOTAL_DAYS = 12;          // Number of days to simulate
```

### Example Configurations:

**Quick Test (30 minutes):**
```javascript
const MINUTES_PER_DAY = 5;      // 5 minutes = 1 day
const TOTAL_DAYS = 6;           // 6 days
```

**Full Week (70 minutes):**
```javascript
const MINUTES_PER_DAY = 10;
const TOTAL_DAYS = 7;
```

**Two Weeks (2.3 hours):**
```javascript
const MINUTES_PER_DAY = 10;
const TOTAL_DAYS = 14;
```

## 📊 Analytics You'll See

1. **Cohort Analysis**: Daily retention rates
2. **Conversion Funnel**: Sign-up → Check-in → Premium
3. **Persona Breakdown**: Metrics by user type
4. **Revenue Projection**: MRR, ARR, LTV
5. **Churn Risk**: High/medium/low risk users
6. **Engagement Metrics**: DAU, stickiness, session duration

## 🚨 Note

This is a **simulation**, not a real load test against actual servers. It:
- ✅ Models realistic user behavior
- ✅ Generates realistic data
- ✅ Tests analytics calculations
- ❌ Does NOT test server performance
- ❌ Does NOT hit actual API endpoints

For actual load testing, use tools like:
- Apache JMeter
- k6
- Locust
- Artillery

## 🎉 Expected Results

After 2 hours, you should see approximately:
- **85-90 active users** (85-90% activation)
- **1,200-1,500 check-ins** (avg 14/user)
- **15-20 premium conversions** (15-20% conversion rate)
- **$120-$160 MRR**
- **Avg MDW: 2-3 meaningful days**
- **D7 retention: 60-75%**

These align with best-in-class wellness app benchmarks! 🎯

