# 🎭 100-User Simulator - Complete Guide

## 🚀 **QUICK START** (Run Now!)

```bash
cd /Users/manojgupta/ejouurnal/simulator
node run-simulation.js
```

**That's it!** The simulation will run for 2 hours (12 simulated days) and show you real-time analytics.

---

## ⏰ **What to Expect**

### **Timeline:**
- **2 hours total runtime**
- **10 minutes = 1 simulated day**
- **12 simulated days total**
- Real-time console output every 10 minutes

### **While Running:**
You'll see output like this every 10 minutes:

```
📅 DAY 1 - 6:43:15 PM
────────────────────────────────────────────────────────────
   Active Users: 87/100
   Check-ins: 142
   Meaningful Days: 12

📅 DAY 2 - 6:53:15 PM
────────────────────────────────────────────────────────────
   Active Users: 83/100
   Check-ins: 136
   Meaningful Days: 18
   💰 Premium Conversions: 2
```

---

## 👥 **The 100 Users**

The simulator creates 4 types of users:

| Persona | Count | Check-in Rate | Sleep | Social Media | Conversion Rate |
|---------|-------|---------------|-------|--------------|-----------------|
| **Engaged** | 30 | 85% | Good (7-8h) | Low (30-60min) | 25% |
| **Casual** | 45 | 55% | Average (5.5-7h) | Medium (45-90min) | 8% |
| **Struggler** | 20 | 30% | Poor (<5.5h) | High (60-120min) | 2% |
| **Power User** | 5 | 95% | Excellent (7.5-8.5h) | Very Low (15-45min) | 40% |

---

## 📊 **What Gets Simulated**

### **Every 10 Minutes (1 "Day"):**
1. ✅ **Morning check-ins** (0-2.5 min)
2. ✅ **Daytime check-ins** (2.5-5 min)
3. ✅ **Evening check-ins** (5-7.5 min)
4. ✅ **Night check-ins** (7.5-10 min)
5. 📊 **Update scores & detect Meaningful Days**
6. 💰 **Process premium conversions**

### **User Actions:**
- Mood ratings (1-5 faces)
- Micro-acts (Gratitude, Meditation, Walk)
- Details logging (sleep, steps, screen time)
- Streak tracking
- Premium upgrades

### **Behavioral Realism:**
- ✅ Engagement decays over time (novelty wears off)
- ✅ Streaks boost check-in probability
- ✅ Premium users are more engaged
- ✅ Morning has highest completion rate
- ✅ Different personas behave differently
- ✅ Natural churn (some users stop)

---

## 🎯 **Key Metrics You'll See**

### **At the End:**
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

### **Metrics Explained:**

**MDW (Meaningful Days per Week):**
- Days where ALL scores meet thresholds:
  - Body ≥ 70
  - Mind ≥ 65
  - Soul ≥ 80
  - Purpose ≥ 55

**Activation Rate:**
- % of users who completed at least 1 check-in
- Target: 85-90%

**Conversion Rate:**
- % of users who upgraded to Premium
- Target: 15-20%

**D7 Retention:**
- % of Day 1 users still active on Day 7
- Target: 65-75%

---

## 💾 **Output Files**

After completion, find this in `simulator/output/`:

### **`simulation-[timestamp].json`**
Contains:
```json
{
  "users": [
    {
      "userId": "user_001",
      "name": "Alex Chen",
      "persona": "engaged",
      "totalCheckIns": 38,
      "meaningfulDays": 4,
      "fulfillmentScore": 74.2,
      "isPremium": true
    },
    // ... 99 more users
  ],
  "checkIns": [...],        // Every check-in event
  "details": [...],         // Sleep, steps, screen time
  "analytics": [...],       // All events tracked
  "report": {...}           // Summary analytics
}
```

---

## 🎮 **How to Run Different Scenarios**

### **Quick Test (30 minutes = 6 days):**
Edit `run-simulation.js`:
```javascript
const MINUTES_PER_DAY = 5;
const TOTAL_DAYS = 6;
```

### **Full Week (70 minutes = 7 days):**
```javascript
const MINUTES_PER_DAY = 10;
const TOTAL_DAYS = 7;
```

### **Two Weeks (2.3 hours = 14 days):**
```javascript
const MINUTES_PER_DAY = 10;
const TOTAL_DAYS = 14;
```

### **Instant Test (no delays, 2 seconds total):**
```javascript
const MINUTES_PER_DAY = 0.033;  // 2 seconds per day
const TOTAL_DAYS = 12;
```

---

## 🔍 **What to Look For**

### **Good Signs:**
- ✅ 85-90% activation rate
- ✅ 15-20% premium conversion
- ✅ 60-75% D7 retention
- ✅ Avg MDW: 2-3
- ✅ Power users converting at 40%+
- ✅ Engaged users converting at 25%+

### **Red Flags:**
- ❌ <70% activation
- ❌ <10% conversion
- ❌ <50% D7 retention
- ❌ Avg MDW < 1.5
- ❌ High churn in premium users

### **Insights to Extract:**

1. **When do users convert?**
   - Look at `analytics` → `premium_conversion` events
   - Check `day` field (when it happened)
   - Check `metadata.trigger` (what caused it)

2. **Which personas are valuable?**
   - Compare conversion rates
   - Compare avg MDW
   - Look at engagement patterns

3. **What drives Meaningful Days?**
   - Filter users with MDW ≥ 3
   - Look at their check-in patterns
   - Compare sleep, screen time, micro-acts

4. **Where is churn happening?**
   - Users with decreasing check-ins
   - Long gaps between check-ins
   - Broken streaks

---

## 🎯 **Premium Conversion Logic**

Users convert when:
1. **They hit 3+ Meaningful Days** (strong trigger)
2. **OR Day 7+ with high engagement** (3+ check-ins/day)

**Conversion probability by persona:**
- Power User: 40%
- Engaged: 25%
- Casual: 8%
- Struggler: 2%

**This models real behavior:**
- Users who see value (MDW) → convert
- Users who are engaged → convert
- Strugglers rarely convert (need help first)

---

## 📈 **Expected Results (Benchmarks)**

After 2 hours (12 days), typical results:

| Metric | Expected Range | Best-in-Class |
|--------|----------------|---------------|
| Activation Rate | 80-90% | 85-90% |
| Premium Conversion | 15-20% | 18-22% |
| D7 Retention | 60-75% | 70-80% |
| Avg MDW | 2.0-3.0 | 2.5-3.5 |
| MRR | $120-$160 | $150-$200 |
| Avg Check-ins/User | 12-18 | 15-20 |

**Compare your simulation to these!**

---

## 🧪 **Use Cases**

1. **Validate Business Model:**
   - Is 15-20% conversion realistic?
   - What's our projected ARR?
   - How much revenue per user?

2. **Test Analytics:**
   - Do our metrics calculations work?
   - Can we identify churn risk?
   - Do conversion triggers make sense?

3. **Understand User Journey:**
   - What path do users take to premium?
   - When do users churn?
   - What drives engagement?

4. **Product Decisions:**
   - Should we focus on strugglers or engaged users?
   - When should we show premium paywall?
   - What features drive retention?

---

## 🛠️ **Troubleshooting**

### **"Command not found"**
```bash
# Make sure you're in the right directory:
cd /Users/manojgupta/ejouurnal/simulator

# Run with explicit node:
node run-simulation.js
```

### **"Cannot find module"**
Node.js is not installed. Install it:
```bash
# Mac (with Homebrew):
brew install node

# Or download from: https://nodejs.org
```

### **Simulation runs too fast/slow**
Edit `MINUTES_PER_DAY`:
- Faster: Set to 1 (1 min = 1 day)
- Slower: Set to 15 (15 min = 1 day)
- Instant: Set to 0.01 (0.6 seconds = 1 day)

### **Want more/fewer users**
Edit `TOTAL_USERS`:
```javascript
const TOTAL_USERS = 50;   // 50 users
const TOTAL_USERS = 200;  // 200 users
const TOTAL_USERS = 1000; // 1000 users (takes longer)
```

---

## 🎉 **You're Ready!**

Run the simulator:
```bash
cd simulator
node run-simulation.js
```

Sit back and watch 100 users interact with your app over 12 simulated days!

**Pro tip:** Open the terminal in full screen to see all the output clearly.

---

## 📊 **After the Simulation**

1. **Review the console output** (final analytics report)
2. **Open the JSON file** in `simulator/output/`
3. **Analyze the data:**
   - Who converted to premium? (filter by `isPremium: true`)
   - What was their journey? (look at check-ins over time)
   - When did they convert? (check `analytics` events)
   - What's their MDW? (filter by `meaningfulDays >= 3`)

4. **Compare to benchmarks** (see table above)
5. **Identify opportunities:**
   - Can we improve activation? (get more users to 1st check-in)
   - Can we improve conversion? (better paywall trigger?)
   - Can we reduce churn? (re-engagement campaigns?)

---

**🎯 Goal:** Learn if our product model works and where to focus efforts!

**Questions? Check `simulator/README.md` for more details.**

**Ready? Let's simulate! 🚀**

