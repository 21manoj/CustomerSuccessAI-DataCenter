# Fulfillment App - Mobile UI Guide

A **quiet 4-check-ins/day app** that fuses body data, attention habits, and micro-journals into a **Fulfillment Lineage**—showing how daily choices ripple into calm, strength, and purpose.

## 🎯 North Star Metric

**Meaningful Days per Week (MDW)**: Days where Body, Mind, Soul each meet personalized thresholds and the day advances your weekly purpose.

---

## 📱 Screen Walkthrough

### 1. **Home Screen** (`HomeScreen.tsx`)

The main dashboard where users start their day.

#### Features:
- **Daypart Chips**: 4 interactive cards for 🌅 Morning, ☀️ Day, 🌆 Evening, 🌙 Night
  - Shows completion status with green checkmark
  - Current time-appropriate daypart highlighted with blue border
  - Quick tap to start check-in

- **Today's Fulfillment Card**:
  - Large centered score (0-100)
  - 4 horizontal progress bars: Body (red), Mind (teal), Soul (mint), Purpose (yellow)
  - "✨ Meaningful Day" badge when thresholds are met

- **This Week Card**:
  - Large green number showing MDW count
  - Purpose adherence percentage
  - Social minutes delta vs. baseline
  - "Review →" link to Weekly Ritual

- **Fulfillment Lineage Button**:
  - 🔗 icon with clear CTA
  - "See how your choices connect"

#### Design Details:
```
Colors:
- Background: #FAFBFC (light gray)
- Cards: #FFF with subtle shadow
- Primary: #007AFF (iOS blue)
- Success: #34C759 (green)

Typography:
- Greeting: 28pt, bold
- Card titles: 18pt, bold
- Body: 14-16pt

Spacing:
- Cards: 16px horizontal margin
- Inner padding: 20px
- Chip gap: 4px
```

---

### 2. **Quick Check-In** (`QuickCheckIn.tsx`)

Lightning-fast flow: **≤20 seconds** to complete.

#### Flow:
```
Step 1: Mood (5 faces) → auto-advance
Step 2: Context (0-2 tags: Work/Sleep/Social) → manual next
Step 3: Micro-act (gratitude/walk/meditate/etc.) → optional skip
Step 4: [Night only] Purpose progress (yes/partly/no)
```

#### Features:
- **Header**: Daypart emoji + label, close button
- **Progress Dots**: Visual stepper (completed = green, current = blue, pending = gray)
- **Mood Grid**: 5 emoji buttons (😢 😕 😐 🙂 😊)
  - Selected state: blue border + light blue background
  - Auto-advances 300ms after selection

- **Context Chips**: Toggle buttons (max 2)
  - Emoji + label (💼 Work, 😴 Sleep, 👥 Social)
  
- **Micro-Act Grid**: 4×2 grid of small cards
  - Icons: 🙏 🧘 🚶 🌳 💝 📚 🌬️ ✍️
  - Selected: green border
  - Skip button at bottom

- **Purpose Screen** (night only):
  - 3 large buttons: ✅ Yes / ◐ Partly / ⭕ Not yet
  - Yellow highlight on selection

#### Design Details:
```
Layout:
- Full screen modal
- Fixed header + progress dots
- Scrollable content
- Footer: "⚡ Takes ~15 seconds"

Interaction:
- All selections have 0.7 opacity on press
- Smooth fade transitions between steps
- Timer logged to console for optimization
```

---

### 3. **Fulfillment Lineage** (`FulfillmentLineage.tsx`)

The core insight engine—how choices connect.

#### Sections:

**A. Your Journey (Timeline)**
- Horizontal scroll of last 7 days
- Each day shows 4 vertical bars (Body/Mind/Soul/Purpose)
- Bar height = score (0-100)
- ⭐ marker for Meaningful Days
- Legend at bottom

**B. Key Connections (Insights)**
- Color-coded cards by type:
  - 🟦 Same-day (teal)
  - 🟨 Lag (yellow)
  - 🟥 Breakpoint (red)
  - 🟩 Purpose-path (mint)

Each card shows:
- Title + confidence badge (HIGH/MEDIUM/LOW)
- Description with actionable advice
- Metric flow: `Source → Target` with impact (+12 pts)
- Lag days if applicable (e.g., "1d lag")

**C. What to Try**
- Highlighted suggestion card (yellow background)
- 💡 icon + personalized recommendation
- Based on highest-impact insight

#### Design Details:
```
Timeline:
- Bar width: 10px
- Gap: 4px between bars
- Height: 120px max
- Colors match dimension legend

Insight Cards:
- 4px left border in type color
- White background
- 16px padding
- Subtle shadow

Empty State:
- 📊 emoji + encouraging message
- "Keep checking in! We'll show insights after a few days."
```

---

### 4. **Weekly Ritual** (`WeeklyRitual.tsx`)

Sunday 10-minute planning session.

#### Sections:

**A. Last Week's Fulfillment**
- Large MDW number with trend emoji (📈 📉 →)
- 4 colored dots with average scores (Body/Mind/Soul/Purpose)
- Top 2 insights from the week

**B. This Week's Intention**
- Large text input (multiline, 120 char max)
- Placeholder: "e.g., Show up with more presence for my family"
- Character counter

**C. 3 Micro-Moves**
- Numbered inputs (1, 2, 3) with blue circle badges
- Specific, actionable items
- Examples: "10-min morning walk 3x", "Read 2 chapters"

**D. Anti-Glitter Experiment** (optional)
- Chip selector with 7 preset experiments:
  - 30-min morning no-feed
  - Grayscale home screen
  - No phone first hour after waking
  - Social apps only after 6pm
  - 10-min no-scroll before bed
  - Leave phone outside bedroom
  - One social app at a time

**E. Commitment Box**
- ✨ emoji + affirmation
- Light green background
- "This week, I'll check in 4× daily and focus on these intentions."

#### Design Details:
```
Header:
- Blue "Save" button (top right)
- Saves intention + navigates to home

Inputs:
- White cards with light border
- 16px padding
- Rounded corners (12px)

Chips:
- Toggle selection (blue border when selected)
- Wrap to multiple rows
- 10px gap
```

---

### 5. **Anti-Glitter Card** (`AntiGlitterCard.tsx`)

Gentle nudge system for social media awareness.

#### Features:
- **Content Diet Header**: Today's social minutes vs. baseline
- **Metrics Row**: Large numbers with delta badge (+/-18m)
  - Orange background if over baseline
  - Green if under

- **Sparkle Tag**:
  - "Felt worse after scrolling?" prompt
  - ✨ Tag Sparkle button (gray, rounded)
  - Shows count: "3 sparkles today"

- **Insight Box** (conditional):
  - Blue background
  - 📊 icon
  - Personalized correlation: "You were +22 calm on days with <45 min social"

#### Design Details:
```
Card:
- White background
- 20px padding
- Subtle shadow
- Full width minus 32px margin

Colors:
- Over baseline: #FFF5E6 (light orange)
- Under baseline: #F0F9F6 (light green)
- Insight: #E5F1FF (light blue)

Typography:
- Metric values: 32pt, bold
- Labels: 12pt, gray
- Insight: 13pt, dark blue
```

---

## 🎨 Design System

### Colors
```
Primary:     #007AFF (iOS blue)
Success:     #34C759 (green)
Warning:     #FF9500 (orange)
Error:       #FF6B6B (red)

Body:        #FF6B6B (coral)
Mind:        #4ECDC4 (teal)
Soul:        #95E1D3 (mint)
Purpose:     #FFD93D (yellow)

Background:  #FAFBFC (light gray)
Card:        #FFFFFF (white)
Border:      #E8E8E8 (light gray)
Text:        #1A1A1A (near black)
Secondary:   #666666 (gray)
Tertiary:    #999999 (light gray)
```

### Typography
```
Headings:    SF Pro Display (iOS system font)
Body:        SF Pro Text
Weights:     400 (regular), 600 (semibold), 700 (bold), 800 (extrabold)

Scale:
- Title: 28pt
- Heading: 20-24pt
- Subheading: 18pt
- Body: 15-16pt
- Caption: 12-14pt
- Fine print: 11pt
```

### Spacing
```
Screen padding:     20px horizontal
Card margin:        16px
Card padding:       20px
Section gap:        24px
Element gap:        12-16px
Chip gap:           8-10px
```

### Shadows
```
Card shadow:
- color: #000
- offset: (0, 2)
- opacity: 0.05-0.08
- radius: 8px
- elevation: 2-3 (Android)
```

### Border Radius
```
Cards:       16-20px
Buttons:     12px
Chips:       20px (pill shape)
Inputs:      12px
Badges:      8px
```

---

## ⚡ Key Interactions

### Check-In Flow
1. Tap daypart chip → full-screen modal
2. Select mood → **auto-advance** (300ms delay)
3. Toggle 0-2 contexts → tap Next
4. Select micro-act (or skip) → complete or advance
5. [Night only] Select purpose progress → complete
6. Return to home with updated completion status

### Lineage Navigation
1. Tap "View Fulfillment Lineage" → insights screen
2. Scroll timeline horizontally
3. Tap insight card → expand (future: detailed view)
4. Back button returns to home

### Weekly Ritual
1. From home, tap "Review →" on weekly card
2. Review last week's stats
3. Fill intention + 3 micro-moves
4. Optional: select anti-glitter experiment
5. Tap Save → return to home

---

## 📊 Click Metrics

All interactions are instrumented:
```
Core:
- checkin_start(dayPart)
- mood_select(mood)
- checkin_complete(duration)
- micro_act_select(type)
- purpose_move_check(id, state)
- sparkle_tag_add
- weekly_intention_set

Navigation:
- lineage_insight_view(insight_id)
- weekly_ritual_view
```

---

## 🔒 Privacy

- **Local-first**: All data stored on device by default
- **Opt-in sync**: End-to-end encrypted cloud backups
- **No analytics**: Only aggregated, anonymous usage patterns
- **Export/Delete**: Always accessible in settings

---

## 💎 Premium Features (Post-Paywall)

Trigger: After 10 meaningful check-ins or first MDW ≥ 3

**Unlocks**:
- Deep lineage (lag analysis, breakpoints, personalized weights)
- Purpose programs (4-week guided tracks)
- Coach summaries (weekly PDF export)
- Focus toolkit (app blocking, custom rituals)
- Private backups + data export

---

## 🚀 Implementation Notes

### Tech Stack
- **React Native** (Expo 54)
- **TypeScript** (strict mode)
- **AsyncStorage** (local persistence)
- **HealthKit/Google Fit** (body metrics sync)
- **Screen Time API** (focus/social tracking)

### State Management
- React hooks + Context API for global state
- Local state for UI interactions
- Persistent storage with AsyncStorage

### Performance
- Check-in flow optimized for <1s response
- Animations: 150-300ms durations
- Timeline: virtualized horizontal scroll
- Images: none (emoji-based UI)

---

## 📝 Future Enhancements

1. **Voice notes**: 20s hold-to-record on check-in
2. **Insights drill-down**: Tap insight → see daily examples
3. **Comparison mode**: Week-over-week trends
4. **Coach sharing**: Export weekly summary PDF
5. **Widget**: iOS home screen widget with MDW count
6. **Themes**: Dark mode + color customization

---

This UI balances **speed** (20s check-ins), **depth** (lineage insights), and **calm** (anti-glitter features) to maximize Meaningful Days per Week.

