# 📔 AI-Generated E-Journal - Feature Specification

## 🎯 **Overview**

Auto-generate reflective, story-like daily journals using AI based on check-ins, device data, and patterns. Premium feature with full encryption and cloud sync.

---

## ⏰ **When Journals are Generated**

### **Trigger: Night Check-in Completion**
- After user completes 4th check-in (🌙 Night)
- AI generates journal in background (~5-10 seconds)
- Notification: "Your daily journal is ready ✨"
- User can tap to view/edit

### **Alternative Access**
- Home screen: "View Today's Journal" button
- Profile > Journal History (calendar view)
- Weekly Ritual: "Review This Week's Journals"

---

## 📝 **Journal Content Structure**

### **Data Sources**

1. **Check-ins (4x daily)**
   - Mood trends (morning → night)
   - Contexts (work, sleep, social)
   - Micro-acts performed
   - Night purpose check

2. **Device Data**
   - Sleep hours (from morning check-in or HealthKit)
   - Activity/steps
   - Screen time breakdown
   - Social media minutes

3. **Manual Entries** (Optional Details)
   - Food quality & notes
   - Exercise type/duration/intensity
   - Social interactions (quality + optional details)
   - Free-form notes

4. **Weekly Context**
   - Current intention
   - Micro-moves progress (3 checkboxes)
   - Days toward MDW goal

5. **Pattern Detection**
   - Compare to yesterday
   - Compare to last week (same day)
   - Detect recurring patterns (e.g., "3rd day of <7h sleep")
   - Correlations from Fulfillment Lineage

---

## 🎨 **Journal Format**

### **Story-Like Narrative Structure**

```
[Date] - [Day of Week]
[Weather/Time Context if available]

Opening Reflection
------------------
[How the day unfolded, starting with morning mood/energy]

Body & Energy
-------------
[Sleep quality, activity, fuel - narrative style]
[Pattern detection: "This is your 3rd consecutive day with..."]

Mind & Focus
------------
[Mood progression through the day, contexts encountered]
[Screen time, focus periods, stress relief used]

Soul & Connection
-----------------
[Micro-acts performed, social quality]
[What brought meaning today]

Purpose & Direction
-------------------
[Progress on weekly intention]
[Which micro-moves completed]
[Night purpose check response]

Patterns & Insights
-------------------
[AI-detected correlations]
[Comparison to previous days/weeks]
[From Fulfillment Lineage: "Your morning walk yesterday may have..."]

Tomorrow's Opportunity
---------------------
[Forward-looking suggestion based on patterns]

---
Overall Fulfillment: [Score]/100
Meaningful Day: [Yes/No + why]
```

### **Example Journal Entry**

```
Wednesday, October 16, 2024

You started the morning feeling good 🙂 after a solid 7.5 hours 
of sleep. Your energy carried through the day - you logged 45 
minutes of activity and chose nourishing fuel.

Mind-wise, you encountered work stress in the afternoon but 
took a 10-minute walk (a micro-act that's been boosting your 
MindScore by +7 points lately). Your mood lifted to "great" 😊 
by evening.

You felt energized after a deep conversation with a colleague - 
your 4th "energized" social interaction this week. This aligns 
with your intention to "show up with more presence."

Purpose progress: You completed 2 of 3 micro-moves today 
(morning walk ✓, read 2 chapters ✓, call friend ⏸). That's 67% 
weekly adherence, up from 50% last week.

Pattern Alert: This is your best Wednesday in 3 weeks. Last 
Wednesday, you scored 58 overall after heavy social media use 
(82 minutes). Today, you kept it to 32 minutes and scored 74.

Tomorrow: You're on a 3-day streak of quality sleep. If you 
maintain 7+ hours tomorrow, your data suggests a +12 MindScore 
boost is likely.

---
Overall Fulfillment: 74/100
Meaningful Day: Yes - all dimensions met thresholds and you 
advanced your weekly purpose.
```

---

## 🎙️ **Tone Options** (User Setting)

Users can select in Profile > Settings > Journal Tone:

1. **Reflective** (Default)
   - "You started the morning feeling..."
   - "Your energy carried through..."
   - Encouraging, personal, present-tense

2. **Factual**
   - "4 check-ins completed. Average mood: Good."
   - "Sleep: 7.5h. Activity: 45min. Screen: 32min."
   - Data-focused, third-person

3. **Coach-Like**
   - "Great job maintaining 7+ hours of sleep!"
   - "Consider reducing screen time tomorrow..."
   - Motivational, action-oriented

4. **Poetic**
   - "Dawn broke with promise, and you rose to meet it..."
   - More literary, contemplative
   - For users who journal as art

---

## ✏️ **User Interactions**

### **1. View Journal**
- Tap notification or "View Today's Journal" button
- Full-screen reader view
- Scroll through sections

### **2. Edit Text**
- Tap ✏️ icon → Edit mode
- Can modify AI text
- Can add/remove sections
- Auto-saves changes

### **3. Add Personal Notes**
- "Add Your Thoughts" section at bottom
- Free-form text area
- Voice-to-text option
- Supports markdown formatting

### **4. Regenerate**
- 🔄 "Regenerate" button
- Choose different tone
- Choose focus (e.g., "Focus on sleep patterns")
- Keeps edit history

### **5. Share**
- 📤 Export as PDF
- Export as text
- Email to therapist/coach
- Copy to clipboard

### **6. Delete**
- Encrypted deletion
- 30-day recovery window
- GDPR compliance

---

## 📊 **Additional Data Inputs**

### **"Add Details" Flow**

**Home Screen:**
```
┌─────────────────────────────┐
│ How's your day unfolding?   │
│                              │
│ [🌅✓] [☀️✓] [🌆] [🌙]      │
│                              │
│ ┌─────────────────────────┐ │
│ │ 📊 Add Details          │ │
│ │ Track sleep, food,      │ │
│ │ exercise & more         │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

### **Details Screen Sections**

#### **1. Sleep (Morning Check-in)**
```
💤 Sleep
─────────
How many hours? [Slider: 0-12h] → 7.5h
Quality: [⭐⭐⭐⭐☆] → 4/5

[Pre-filled from HealthKit if available]
[User can edit/override]
```

#### **2. Food**
```
🍽️ Fuel & Nutrition
───────────────────
Breakfast: [Good / Ok / Poor] → Good
  Optional note: "Oatmeal + fruit"

Lunch: [Good / Ok / Poor] → Ok
  Optional note: ""

Dinner: [Good / Ok / Poor] → Good
  Optional note: "Home-cooked meal"

Snacks: [Good / Ok / Poor] → Ok

Overall Feel: [💚 Nourished / 😐 Neutral / 😕 Heavy]
```

#### **3. Exercise**
```
💪 Activity & Exercise
──────────────────────
[Pre-filled: 8,234 steps from device]

Manual Activity:
Type: [Walk / Run / Gym / Yoga / Sport / Other]
Duration: [Slider: 0-120 min] → 30 min
Intensity: [Light / Moderate / Vigorous] → Moderate

How you feel: [Energized / Good / Tired]
```

#### **4. Social Interactions**
```
👥 Social Connections
─────────────────────
Quality: [Energized ⚡ / Neutral 😐 / Drained 😔]

Optional Details:
Who: [Friend / Family / Colleague / Other]
      or [Free text: "Coffee with Sarah"]
Duration: [15min / 30min / 1h / 2h+ ]
Type: [Deep talk / Casual / Meeting / Group]

[+ Add Another Interaction]
```

#### **5. Screen Time**
```
📱 Screen Time
──────────────
[Pre-filled from iOS Screen Time API]

Total: 3h 42min
├─ Social Media: 32min  (↓ vs 70min avg)
├─ Work: 2h 15min
├─ Entertainment: 45min
└─ Other: 10min

Felt comparison trigger? [✨ Sparkle Tag]
```

### **Input Timing**
- Available anytime via "Add Details" button on home
- Suggested after each check-in (optional popup)
- Reminded at night check-in: "Want to add details for today?"
- Can fill in multiple times (lunch, dinner separately)

---

## ☁️ **Cloud Storage & Encryption**

### **What Gets Saved**

```
User Data Tree:
├─ Check-ins (4x daily)
│  ├─ Mood, context, micro-act
│  └─ Timestamps, daypart
├─ Device Data
│  ├─ Sleep, activity, screen time
│  └─ Auto-synced, encrypted
├─ Detail Entries
│  ├─ Food logs
│  ├─ Exercise logs
│  └─ Social interactions
├─ AI Journals
│  ├─ Original AI text
│  ├─ User edits
│  └─ Personal notes
├─ Weekly Intentions
│  └─ Micro-moves progress
└─ Settings
   └─ Journal tone preference
```

### **Encryption Strategy**

**Local Storage:**
- SQLite database (encrypted with SQLCipher)
- User's passcode = encryption key
- Biometric unlock (Face ID / Touch ID)

**Cloud Sync:**
- End-to-end encryption (E2EE)
- Only user has decryption key
- Even server can't read data
- AWS S3 / Firebase Storage with encryption at rest
- TLS 1.3 in transit

**Journal-Specific:**
- Extra layer of encryption (most sensitive)
- Separate encryption key
- Can disable cloud sync for journals only

### **Sync Behavior**

**Real-time:**
- Check-ins → immediate sync
- Details → sync on save
- Journal edits → debounced (5s after last edit)

**Offline-first:**
- Works without internet
- Queue syncs for later
- Merge conflicts: user chooses (local vs cloud)

**Backup:**
- Daily encrypted backup to cloud
- 30-day version history
- Can restore any day's data

---

## 💎 **Premium Features**

### **Free vs Premium**

| Feature | Free | Premium |
|---------|------|---------|
| Check-ins (4x daily) | ✅ | ✅ |
| Basic scores | ✅ | ✅ |
| 7-day lineage | ✅ | ✅ |
| **AI Journal** | ❌ 3-day trial | ✅ Unlimited |
| **Tone options** | ❌ | ✅ 4 tones |
| **Regenerate** | ❌ | ✅ Unlimited |
| **Personal notes** | ❌ | ✅ |
| **Add Details** | ❌ | ✅ |
| **Food/Exercise logs** | ❌ | ✅ |
| **Cloud sync** | ❌ Local only | ✅ E2E encrypted |
| **Export journal** | ❌ | ✅ PDF/Text |
| **Share with coach** | ❌ | ✅ |
| **Pattern detection** | ❌ Basic only | ✅ Advanced |
| **30-day history** | ❌ 7 days | ✅ Unlimited |

### **Pricing**
- **$7.99/month** or **$49.99/year** (save 48%)
- **7-day free trial** (3 AI journals included)
- Trigger paywall: After 3 journals OR 10 meaningful check-ins

---

## 🤖 **AI Implementation**

### **Backend Architecture**

```
User completes night check-in
         ↓
Backend collects all data:
  - Today's 4 check-ins
  - Device data (sleep, activity, screen)
  - Detail entries (food, exercise, social)
  - Weekly intention + micro-moves
  - User's journal tone preference
         ↓
Call AI API (OpenAI GPT-4 or Claude):
  - Structured prompt with all data
  - User's tone preference
  - Pattern detection queries
  - Compare to past 7 days data
         ↓
AI generates narrative (5-10s)
         ↓
Store in encrypted database
         ↓
Push notification: "Journal ready ✨"
```

### **Prompt Template**

```javascript
const journalPrompt = `
You are a reflective personal journal writer. Generate a 
story-like daily journal entry based on the following data:

DATE: ${date}
USER TONE PREFERENCE: ${tone} // reflective, factual, coach-like, poetic

TODAY'S CHECK-INS:
- Morning: Mood=${morningMood}, Contexts=${contexts}, MicroAct=${microAct}
- Day: Mood=${dayMood}, ...
- Evening: ...
- Night: Mood=${nightMood}, PurposeProgress=${purposeProgress}

DEVICE DATA:
- Sleep: ${sleepHours}h (quality: ${sleepQuality}/5)
- Activity: ${steps} steps, ${activeMinutes} active minutes
- Screen Time: Total=${screenTotal}, Social=${socialMinutes}

MANUAL ENTRIES:
- Food: Breakfast=${breakfast}, Lunch=${lunch}, Dinner=${dinner}
- Exercise: ${exerciseType} for ${exerciseDuration} min, ${intensity}
- Social: ${socialQuality} interaction with ${socialWho}, ${socialDuration}

WEEKLY CONTEXT:
- Intention: "${weeklyIntention}"
- Micro-moves: ${microMove1}=${completed1}, ${microMove2}=${completed2}, ...
- Progress: ${completedCount}/3 completed (${percentage}%)

PATTERNS TO DETECT:
- Compare to yesterday: ${yesterdayScores}
- Compare to last ${dayOfWeek}: ${lastWeekScores}
- Sleep streak: ${consecutiveDays} days of ${sleepRange}h
- Fulfillment Lineage insight: "${topInsight}"

SCORES:
- Body: ${bodyScore}/100
- Mind: ${mindScore}/100
- Soul: ${soulScore}/100
- Purpose: ${purposeScore}/100
- Overall: ${overallScore}/100
- Meaningful Day: ${isMeaningfulDay}

Generate a ${tone} narrative journal entry following this structure:
1. Opening reflection (how the day unfolded)
2. Body & Energy section
3. Mind & Focus section
4. Soul & Connection section
5. Purpose & Direction section
6. Patterns & Insights (compare to past)
7. Tomorrow's Opportunity (forward-looking)
8. Summary with scores

Write in ${tone === 'reflective' ? 'second person (You...)' : 
         tone === 'factual' ? 'third person' : 
         tone === 'coach-like' ? 'encouraging tone' : 
         'poetic, contemplative style'}.

Keep it concise but meaningful (300-500 words).
`;
```

### **Cost Estimation**
- GPT-4: ~$0.03 per journal (500 tokens input + 800 tokens output)
- Claude: ~$0.02 per journal
- Monthly cost per premium user: $0.60 - $0.90 (30 journals)
- Margin: $7.99 - $0.90 = $7.09 profit per user/month

---

## 🎨 **UI Mockup Screens**

### **1. Home Screen (After Night Check-in)**
```
┌─────────────────────────────────┐
│ How's your day unfolding?       │
│                                  │
│ [🌅✓] [☀️✓] [🌆✓] [🌙✓]        │
│ All check-ins complete!          │
│                                  │
│ ┌─────────────────────────────┐ │
│ │ ✨ Your Daily Journal        │ │
│ │    is ready!                 │ │
│ │                              │ │
│ │    [View Journal →]          │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

### **2. Journal Reader View**
```
┌─────────────────────────────────┐
│ ← [Edit] Wednesday, Oct 16 [⋮] │
├─────────────────────────────────┤
│                                  │
│  You started the morning        │
│  feeling good 🙂 after a solid  │
│  7.5 hours of sleep. Your       │
│  energy carried through...      │
│                                  │
│  [Scroll to read more...]       │
│                                  │
│  ┌──────────────────────────┐  │
│  │ 💭 Add Your Thoughts     │  │
│  │ [Tap to write...]        │  │
│  └──────────────────────────┘  │
│                                  │
│  [🔄 Regenerate] [📤 Share]     │
└─────────────────────────────────┘
```

### **3. Add Details Screen**
```
┌─────────────────────────────────┐
│ ← Add Details for Today          │
├─────────────────────────────────┤
│                                  │
│  💤 Sleep                        │
│  Hours: [========○] 7.5h        │
│  Quality: ⭐⭐⭐⭐☆              │
│                                  │
│  🍽️ Fuel & Nutrition            │
│  Breakfast: [Good ✓] Ok  Poor   │
│  Note: "Oatmeal + fruit"        │
│                                  │
│  💪 Exercise                     │
│  [Pre-filled: 8,234 steps]      │
│  + Add Manual Activity          │
│                                  │
│  👥 Social                       │
│  Quality: [Energized ⚡]         │
│  + Add Optional Details         │
│                                  │
│  📱 Screen Time                  │
│  [Auto: 3h 42min]               │
│  Social: 32min ↓                │
│                                  │
│  [Save Details]                 │
└─────────────────────────────────┘
```

### **4. Journal History (Weekly Ritual)**
```
┌─────────────────────────────────┐
│ ← This Week's Journals           │
├─────────────────────────────────┤
│                                  │
│  Monday, Oct 14  ✨             │
│  "You started Monday with..."   │
│  Fulfillment: 68  [View →]      │
│                                  │
│  Tuesday, Oct 15  ✨            │
│  "Tuesday brought momentum..."  │
│  Fulfillment: 72  [View →]      │
│                                  │
│  Wednesday, Oct 16  ✨          │
│  "You started the morning..."   │
│  Fulfillment: 74  [View →]      │
│                                  │
│  [5 Meaningful Days this week]  │
└─────────────────────────────────┘
```

---

## 📅 **Development Roadmap**

### **Phase 1: Foundation** (Week 1-2)
- [ ] Update data models (types)
- [ ] Create "Add Details" UI screens
- [ ] Implement local storage (encrypted)
- [ ] Sleep input (morning check-in)
- [ ] Food logging UI
- [ ] Exercise logging UI
- [ ] Social detail UI

### **Phase 2: AI Integration** (Week 3-4)
- [ ] Backend API for journal generation
- [ ] OpenAI/Claude integration
- [ ] Prompt engineering & testing
- [ ] Pattern detection logic
- [ ] Compare to past days/weeks
- [ ] Journal storage (encrypted)

### **Phase 3: Journal UI** (Week 5-6)
- [ ] Journal reader view
- [ ] Edit mode
- [ ] Personal notes section
- [ ] Regenerate functionality
- [ ] Tone selection (settings)
- [ ] Export (PDF, text)

### **Phase 4: Cloud Sync** (Week 7-8)
- [ ] End-to-end encryption
- [ ] AWS S3 / Firebase setup
- [ ] Sync engine (offline-first)
- [ ] Conflict resolution
- [ ] Backup & restore

### **Phase 5: Premium** (Week 9-10)
- [ ] Paywall implementation
- [ ] RevenueCat / Stripe integration
- [ ] Free trial (7 days, 3 journals)
- [ ] Feature gating
- [ ] Analytics & tracking

### **Phase 6: Polish** (Week 11-12)
- [ ] Weekly ritual integration
- [ ] Journal history view
- [ ] Share with coach/therapist
- [ ] Onboarding flow
- [ ] Settings & preferences
- [ ] Beta testing

---

## ✅ **Success Metrics**

### **Engagement**
- % of premium users generating journals daily (target: 80%+)
- % who edit AI text (target: 40%+)
- % who add personal notes (target: 60%+)
- Avg journal read time (target: 2+ minutes)

### **Retention**
- Premium retention at 3 months (target: 70%+)
- Free-to-premium conversion (target: 10-15%)
- Weekly active users (target: 85%+)

### **Satisfaction**
- NPS score (target: 50+)
- "Journal quality" rating (target: 4.5+/5)
- Share/export usage (target: 20%+ users)

---

## 🎯 **Summary**

This AI Journal system:
- ✅ Generates daily at night check-in
- ✅ Story-like, reflective tone (customizable)
- ✅ Includes all data sources (check-ins, device, manual)
- ✅ Detects patterns vs past days/weeks
- ✅ Fully editable with personal notes
- ✅ Premium feature ($7.99/month)
- ✅ End-to-end encrypted cloud sync
- ✅ Integrates with weekly ritual
- ✅ Keeps check-in flow fast (≤20s)
- ✅ Optional "Add Details" for power users

**Next step:** Implement in phases, starting with data models and UI mockup.

