# 🎮 MDW Gamification System - Product Roadmap Feature

## 📋 **Feature Overview**

**Status:** Future Implementation  
**Priority:** High (Core engagement driver)  
**Complexity:** Medium  
**Est. Development Time:** 2-3 weeks  

---

## 🎯 **Three Core Mechanics**

### **1. The Weekly MDW Challenge**

**Goal:** Maximize Meaningful Days per Week from 0 to 7

**Design:**
- **Leaderboard Type:** Private (user vs. their personal best)
- **Display:** Current week vs. All-time best week
- **Target:** Always 7/7 (perfect week)
- **No Social Comparison:** Aligns with "anti-glitter" philosophy

**User Experience:**
```
┌─────────────────────────────────┐
│   Weekly MDW Challenge          │
├─────────────────────────────────┤
│ This Week:    5/7  ████░░       │
│ Your Best:    6/7  █████░       │
│                                 │
│ 2 more days to beat your record│
└─────────────────────────────────┘
```

**Why It Works:**
- Self-competition (intrinsic motivation)
- Clear goal (7/7)
- Positive framing (beat yourself, not others)
- No anxiety from social comparison

---

### **2. "Alchemist" Tier Requirement**

**Unlock Condition:** Maintain MDW ≥ 5/7 for **FOUR consecutive weeks**

**Tier Structure:**
```
Beginner      → MDW < 3/7          (Just starting)
Practitioner  → MDW 3-4/7          (Building consistency)
Alchemist     → MDW ≥ 5/7 × 4 wks  (Sustained excellence) ⭐
Sage          → MDW ≥ 6/7 × 8 wks  (Mastery) ✨
```

**Design Principles:**
- ✅ **Sustained behavior required** (prevents one-week flukes)
- ✅ **Balanced action enforced** (all 4 dimensions must meet thresholds)
- ✅ **Premium status feels earned** (not just purchased)
- ✅ **Identity-based motivation** ("I am an Alchemist")

**Tier Benefits:**
```
Alchemist:
  • Exclusive journal tones
  • Advanced insights
  • Priority support
  • Badge on profile

Sage:
  • All Alchemist benefits
  • Coach summaries
  • Custom purpose programs
  • Early access to features
```

**Implementation Notes:**
- Track 4-week rolling window
- Tier can be lost if performance drops
- Grace period: 1 week below threshold before demotion
- Visual tier indicator throughout app

---

### **3. MDW Restoration System**

**Purpose:** Give users a second chance to "save" a failed day

**How It Works:**

#### **Trigger:**
Day fails MDW test (one or more scores below threshold)

#### **Example Scenario:**
```
8 PM Night Check-in Results:
─────────────────────────────
✅ Body:     72/100 (≥70 ✓)
✅ Mind:     68/100 (≥65 ✓)
❌ Soul:     62/100 (≥80 ✗) ← FAILED
✅ Purpose:  58/100 (≥55 ✓)

Result: Not a Meaningful Day 😔

🔄 RESTORATION CHALLENGE AVAILABLE!
```

#### **LLM Generates Personalized Challenge:**
```
┌────────────────────────────────────────┐
│ 🌟 Restoration Challenge               │
├────────────────────────────────────────┤
│ Your Soul Score (62) fell short       │
│ of the 80 threshold.                  │
│                                        │
│ Complete ONE of these by 11 PM:       │
│                                        │
│ 🌳 Spend 10 min in nature/outdoors    │
│ 💬 Have a meaningful conversation     │
│ 🎨 Do something creative              │
│ 🙏 Practice gratitude or meditation   │
│                                        │
│ Reward: Earn 0.5 MDW                  │
└────────────────────────────────────────┘
```

#### **Completion:**
- User logs the activity
- System verifies (honor system + optional photo/note)
- Awards **0.5 MDW** (half-point)
- Day goes from 0 MDW → 0.5 MDW

**Rules:**
- ✅ ONE restoration per day maximum
- ✅ Must complete before midnight (same day)
- ✅ Awards 0.5 MDW (not full 1.0 - prevents abuse)
- ✅ LLM tailors challenge to the specific dimension that failed
- ✅ Multiple options given (user chooses one)

**Why Half-Point?**
- Prevents "always restore" pattern
- Maintains integrity of full MDW
- Still valuable (5.5/7 is better than 5/7)
- Encourages trying vs. giving up

---

## 💡 **Strategic Benefits**

### **Retention:**
- Failed days don't feel permanent → less discouragement
- Always a path to recover → maintains hope
- Second chance mechanics proven to increase engagement

### **Conversion:**
- Tier system creates aspiration ("I want to be Alchemist!")
- Restoration shows app cares about user success
- Premium feels earned, not purchased

### **Engagement:**
- Weekly goal creates consistent touchpoint
- Tier progress builds long-term commitment
- Restoration challenges drive evening engagement

---

## 🛠️ **Technical Implementation**

### **Database Schema Changes:**

```sql
-- MDW tracking (change from boolean to decimal)
ALTER TABLE scores 
  ADD COLUMN mdw_value DECIMAL(2,1) DEFAULT 0.0 CHECK (mdw_value IN (0.0, 0.5, 1.0));

-- Weekly tier tracking
CREATE TABLE user_tiers (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) REFERENCES users(user_id),
  tier VARCHAR(50), -- beginner, practitioner, alchemist, sage
  achieved_at TIMESTAMP,
  weeks_at_threshold INTEGER DEFAULT 0,
  current_streak_weeks INTEGER DEFAULT 0,
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Restoration challenges
CREATE TABLE restoration_challenges (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) REFERENCES users(user_id),
  date DATE NOT NULL,
  failed_dimension VARCHAR(50), -- body, mind, soul, purpose
  challenge_options JSONB, -- Array of LLM-generated challenges
  selected_challenge TEXT,
  completed BOOLEAN DEFAULT FALSE,
  completed_at TIMESTAMP,
  proof_text TEXT,
  proof_image_url TEXT,
  mdw_awarded DECIMAL(2,1) DEFAULT 0.0,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Weekly MDW summary
CREATE TABLE weekly_mdw_summary (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) REFERENCES users(user_id),
  week_start_date DATE NOT NULL,
  week_end_date DATE NOT NULL,
  total_mdw DECIMAL(3,1), -- Can be 0.0 to 7.0 (with half-points)
  is_personal_best BOOLEAN DEFAULT FALSE,
  tier_eligible VARCHAR(50), -- Which tier this qualifies for
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, week_start_date)
);
```

### **Backend Services:**

```javascript
// services/MDWGamificationService.js

class MDWGamificationService {
  
  // Check if day qualifies for MDW
  async checkMDWStatus(userId, date) {
    const scores = await getScores(userId, date);
    
    const isMDW = 
      scores.body >= 70 &&
      scores.mind >= 65 &&
      scores.soul >= 80 &&
      scores.purpose >= 55;
    
    if (!isMDW) {
      // Offer restoration challenge
      const failedDimension = this.getFailedDimension(scores);
      await this.offerRestorationChallenge(userId, date, failedDimension);
      return { mdw: 0.0, restorationAvailable: true };
    }
    
    return { mdw: 1.0, restorationAvailable: false };
  }
  
  // Generate personalized restoration challenge
  async generateRestorationChallenge(userId, failedDimension, scores) {
    const prompt = `
      User's ${failedDimension} score (${scores[failedDimension]}) 
      failed to meet the threshold.
      
      Generate 3-4 quick, actionable activities they can do 
      in the next 2-3 hours to improve this dimension.
      
      Make it specific, achievable, and personalized.
    `;
    
    const challenges = await LLM.generate(prompt);
    return challenges;
  }
  
  // Calculate weekly MDW
  async calculateWeeklyMDW(userId, weekStart) {
    const week = await getWeekScores(userId, weekStart);
    const totalMDW = week.reduce((sum, day) => sum + day.mdw_value, 0);
    
    // Check if personal best
    const previousBest = await getPreviousBestWeek(userId);
    const isPersonalBest = totalMDW > (previousBest?.total_mdw || 0);
    
    return {
      total: totalMDW,
      isPersonalBest,
      tierEligible: this.calculateTierEligibility(totalMDW),
    };
  }
  
  // Update tier status
  async updateTierStatus(userId) {
    const last4Weeks = await getLast4WeeksMDW(userId);
    const qualifies = last4Weeks.every(week => week.total_mdw >= 5.0);
    
    if (qualifies) {
      await setUserTier(userId, 'alchemist');
    } else {
      // Check for demotion with grace period
      await checkTierDemotion(userId);
    }
  }
}
```

### **Frontend Components:**

```typescript
// components/WeeklyMDWChallenge.tsx
interface WeeklyMDWProps {
  currentWeekMDW: number;  // 0.0 to 7.0 (with half-points)
  personalBest: number;
  daysCompleted: DayMDW[];  // Array of 7 days
}

// components/RestorationChallenge.tsx
interface RestorationChallengeProps {
  failedDimension: 'body' | 'mind' | 'soul' | 'purpose';
  currentScore: number;
  threshold: number;
  challenges: string[];  // LLM-generated options
  onComplete: (selected: string, proof: string) => void;
}

// components/TierBadge.tsx
interface TierBadgeProps {
  tier: 'beginner' | 'practitioner' | 'alchemist' | 'sage';
  weeksAtThreshold: number;
  weeksRemaining: number;  // To next tier
}
```

---

## 📊 **Analytics to Track**

### **Weekly Challenge:**
- % of users who check their weekly progress
- Avg MDW per week
- Personal best achievement rate
- Week-over-week improvement

### **Tier System:**
- Distribution of users across tiers
- Time to reach Alchemist (avg days)
- Tier retention rate (% who maintain status)
- Conversion rate by tier

### **Restoration:**
- Restoration offer rate (% of failed days)
- Restoration attempt rate (% who try)
- Restoration completion rate (% who succeed)
- Impact on retention (users with restoration vs. without)
- MDW lift from restorations

---

## 🎯 **Success Metrics**

### **Weekly Challenge:**
- **Target:** 60%+ users check weekly progress
- **Target:** Avg MDW increases 0.5-1.0 per month
- **Target:** 30%+ beat personal best each month

### **Tier System:**
- **Target:** 15-20% reach Alchemist
- **Target:** 3-5% reach Sage
- **Target:** 85%+ tier retention rate
- **Target:** Alchemist users have 2X conversion rate

### **Restoration:**
- **Target:** 50%+ attempt restoration when offered
- **Target:** 70%+ complete the challenge
- **Target:** 15-20% MDW boost from restorations
- **Target:** 10-15% retention boost for restoration users

---

## 🚀 **Implementation Phases**

### **Phase 1: Foundation (Week 1)**
- Change MDW from boolean to decimal (0.0, 0.5, 1.0)
- Build weekly MDW calculation logic
- Create weekly summary table
- Basic UI for weekly progress

### **Phase 2: Weekly Challenge (Week 2)**
- Personal best tracking
- Current week vs. best week display
- Weekly goal UI (7/7 target)
- Analytics tracking

### **Phase 3: Restoration System (Week 2-3)**
- Failed day detection
- LLM challenge generation service
- Restoration challenge UI
- Completion verification
- 0.5 MDW awarding logic

### **Phase 4: Tier System (Week 3)**
- 4-week rolling window calculation
- Tier status tracking
- Promotion/demotion logic
- Grace period implementation
- Tier badge UI

### **Phase 5: Polish & Test (Week 3)**
- A/B testing framework
- Analytics dashboard
- Edge case handling
- Performance optimization

---

## 💻 **Files to Create/Modify**

### **Backend:**
```
services/
├── MDWGamificationService.js          ← NEW
├── RestorationChallengeGenerator.js   ← NEW (LLM-powered)
└── TierCalculationService.js          ← NEW

database/migrations/
└── 003_mdw_gamification.sql           ← NEW

routes/
├── mdw-challenge.js                   ← NEW
├── restoration.js                     ← NEW
└── tiers.js                           ← NEW
```

### **Frontend (React Native):**
```
components/
├── WeeklyMDWChallenge.tsx             ← NEW
├── RestorationChallengeModal.tsx      ← NEW
├── TierBadge.tsx                      ← NEW
├── TierProgress.tsx                   ← NEW
└── PersonalBestCelebration.tsx        ← NEW

screens/
└── WeeklySummaryScreen.tsx            ← MODIFY (add MDW challenge)
```

---

## 🎨 **UX/UI Specifications**

### **Weekly Challenge Display:**

**Location:** Home screen, top section (above daypart chips)

**Design:**
```
┌──────────────────────────────────────────┐
│ 🎯 Weekly MDW Challenge                  │
├──────────────────────────────────────────┤
│                                          │
│ Mon Tue Wed Thu Fri Sat Sun              │
│  ✓   ✓   ✓   ½   -   -   -              │
│                                          │
│ This Week:  3.5/7  ████░░░              │
│ Your Best:  5.0/7  █████░░              │
│                                          │
│ "You're on track! 3 more meaningful     │
│  days to beat your record."             │
└──────────────────────────────────────────┘
```

### **Restoration Challenge:**

**Trigger:** After night check-in, if day failed MDW

**Modal Design:**
```
╔══════════════════════════════════════════╗
║  🔄 You Can Still Save This Day!        ║
╠══════════════════════════════════════════╣
║                                          ║
║  Your Soul Score (62) didn't quite      ║
║  reach 80. But it's not too late!       ║
║                                          ║
║  Complete one challenge by 11 PM:       ║
║                                          ║
║  ○ Spend 10 min in nature/outdoors      ║
║  ○ Call a friend for a real chat        ║
║  ○ Journal your gratitude               ║
║  ○ Do something creative                ║
║                                          ║
║  Earn: 0.5 MDW → Keep your streak alive!║
║                                          ║
║  [Select Challenge]  [Skip for Today]   ║
╚══════════════════════════════════════════╝
```

### **Tier Badge:**

**Location:** Profile screen, next to name

**Design:**
```
Sarah Chen  [⚗️ Alchemist]  🔥 12-day streak

Status: Alchemist (Week 6 of maintenance)
Progress: ████████████░░░░ 5.2/7 this week

Keep MDW ≥ 5/7 to maintain Alchemist status
```

---

## 📈 **Expected Impact**

### **On Engagement:**
- **+15-20%** retention (second chances reduce churn)
- **+10-15%** weekly active users (weekly goal)
- **+20-30%** evening check-ins (restoration challenges)

### **On Conversion:**
- **+25-35%** conversion rate for Alchemist-track users
- **+15-20%** overall conversion (tier aspiration)
- **Shorter time-to-convert** (tier unlocks premium value)

### **On MDW Achievement:**
- **+15-25%** more MDW days (from restorations)
- **+30-40%** users hitting 3+ MDW/week
- **Better score distribution** (fewer discouraged users)

---

## 🧪 **A/B Testing Plan**

### **Test 1: Restoration System**
- **Control:** No restoration (current system)
- **Variant:** Restoration challenges offered
- **Metrics:** MDW rate, retention, evening engagement

### **Test 2: Half-point vs. Full-point**
- **Control:** 0.5 MDW for restoration
- **Variant:** 1.0 MDW for restoration
- **Metrics:** Abuse rate, MDW inflation, user effort

### **Test 3: Weekly Challenge Display**
- **Control:** No weekly summary
- **Variant A:** Simple weekly count
- **Variant B:** Current vs. best comparison
- **Metrics:** Weekly check rate, MDW improvement

---

## 🔐 **Anti-Abuse Measures**

### **Restoration System:**
- ✅ One challenge per day maximum
- ✅ Must complete same day (can't bank)
- ✅ Half-point prevents full gaming
- ✅ Challenge must address failed dimension
- ✅ Optional proof required (note/photo)

### **Tier System:**
- ✅ 4-week sustained requirement (prevents flukes)
- ✅ Demotion if performance drops
- ✅ All scores must meet thresholds (holistic)
- ✅ Grace period (1 week) prevents harsh penalties

---

## 📝 **Implementation Checklist**

### **Phase 1 (Foundation):**
- [ ] Update scores table (mdw_value decimal)
- [ ] Create weekly summary calculation
- [ ] Build weekly MDW API endpoint
- [ ] Basic weekly progress UI

### **Phase 2 (Weekly Challenge):**
- [ ] Personal best tracking
- [ ] Current vs. best comparison
- [ ] Weekly challenge card UI
- [ ] Analytics events

### **Phase 3 (Restoration):**
- [ ] Failed day detection
- [ ] LLM challenge generation
- [ ] Restoration challenge modal
- [ ] Completion verification
- [ ] 0.5 MDW awarding

### **Phase 4 (Tier System):**
- [ ] Tier calculation service
- [ ] 4-week rolling window
- [ ] Promotion/demotion logic
- [ ] Tier badge component
- [ ] Tier benefits implementation

### **Phase 5 (Testing):**
- [ ] A/B test framework setup
- [ ] Metrics collection
- [ ] Performance testing
- [ ] Edge case fixes

---

## 💰 **Business Impact (Estimated)**

### **Revenue:**
- **+20-30% conversion** from tier aspiration
- **+15-20% retention** from restoration system
- **Net: +25-35% MRR growth**

**Example (1,000 users):**
- Current: 15% conversion = 150 premium = $1,198 MRR
- With gamification: 20% conversion = 200 premium = $1,598 MRR
- **Lift: +$400 MRR** (+33%)

### **Engagement:**
- **+25% WAU** (weekly active users)
- **+15% DAU** (daily active users)
- **+20% session frequency**

---

## 🎯 **Product Fit**

### **✅ Aligns With:**
- Anti-glitter philosophy (private, self-competition)
- North Star metric (MDW is the goal)
- Compassionate design (restoration, not punishment)
- Earned status (Alchemist through action)
- Holistic wellness (all 4 dimensions matter)

### **❌ Avoids:**
- Social comparison leaderboards
- Punitive mechanics (streak anxiety)
- Pay-to-win (tier can't be bought)
- Superficial gamification
- Single-dimension optimization

---

## 📚 **References**

**Behavioral Psychology:**
- Self-Determination Theory (autonomy, competence, mastery)
- Growth mindset (failure → learning opportunity)
- Identity-based habits ("I am an Alchemist")

**Game Design:**
- Second-chance mechanics (Duolingo streak freeze)
- Private competition (Strava personal records)
- Tiered progression (RPG skill trees)

---

## 🎉 **Summary**

This gamification system is **brilliant** because it:
1. ✅ **Drives the North Star** (MDW)
2. ✅ **Maintains app philosophy** (anti-glitter, private)
3. ✅ **Creates long-term engagement** (tier system)
4. ✅ **Reduces churn** (restoration system)
5. ✅ **Feels earned, not purchased** (Alchemist status)

**Status:** Saved for future implementation  
**Priority:** High  
**Impact:** High retention, high conversion, perfect product fit  

---

## 📋 **Next Steps (When Ready to Implement):**

1. Review and approve this spec
2. Create detailed wireframes
3. Build backend services
4. Develop frontend components
5. A/B test with small cohort
6. Roll out to all users

---

**Feature saved to roadmap!** 🎯

No code changes made (per your request). Ready to implement when you decide!

