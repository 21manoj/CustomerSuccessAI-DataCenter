# Onboarding & Profile Information

## Overview

User onboarding and profile information is stored in **multiple locations**:

1. **Frontend (React Native)** - Onboarding flow and profile UI
2. **Backend Database** - User data and preferences
3. **Local Storage** - Onboarding completion status

---

## 1. Onboarding Flow

### Frontend Location
**File:** `components/OnboardingScreen.tsx`

### Flow Steps

```
FIRST-TIME USER:
App Launch
  ↓
Onboarding Screen (purple gradient)
  ↓
User clicks "Start Your Journey →"
  ↓
Weekly Ritual (Set Intention)
  ↓
AI suggests micro-moves
  ↓
User selects 3 moves
  ↓
Saves intention
  ↓
Home Screen (start check-ins)

RETURNING USER:
App Launch
  ↓
Load saved intention
  ↓
Go straight to Home Screen
```

### Onboarding Screen Content

```typescript
// components/OnboardingScreen.tsx
interface OnboardingScreenProps {
  onComplete: () => void;
}

// Shows:
// 1️⃣ Set your intention
//    One meaningful shift you want to make this week
// 2️⃣ AI suggests micro-moves
//    Proven actions that support your intention
// 3️⃣ Discover your formula
//    Track check-ins → AI discovers what works for YOU
```

### Onboarding Status Storage

**Location:** Local Storage (AsyncStorage)

**Key:** `'onboarding_complete'`

**Service:** `services/StorageService.ts`

```typescript
// Get onboarding status
async getOnboardingStatus(): Promise<boolean>
// Returns: true if user has seen onboarding

// Set onboarding status
async setOnboardingStatus(complete: boolean): Promise<void>
// Saves: true when user completes onboarding
```

### Integration in App

**File:** `App-Fulfillment.tsx`

```typescript
// Check onboarding status on app launch
const hasCompletedOnboarding = await storageService.getOnboardingStatus();

// Route logic
if (!hasCompletedOnboarding) {
  setCurrentScreen('onboarding');
} else {
  setCurrentScreen('home');
}

// Complete onboarding handler
const handleCompleteOnboarding = async () => {
  await storageService.setOnboardingStatus(true);
  setHasCompletedOnboarding(true);
  setCurrentScreen('ritual'); // Go to intention setting
};
```

---

## 2. Profile Information

### Frontend Location
**File:** `components/ProfileScreen.tsx`

### Displayed Information

#### User Info Card (Top Section)
```typescript
interface ProfileScreenProps {
  userName: string;
  userEmail: string;
  isPremium: boolean;
  currentStreak: number;
  totalCheckIns: number;
  joinDate: Date;
  currentTone: string;
  notificationsEnabled: boolean;
}

// Shows:
// - Avatar with initials
// - Premium badge (💎) if premium
// - Name and email
// - Stats: Check-ins count, Current streak, Member days
```

#### Profile Menu Items

1. **👤 Edit Profile**
   - Update name, email
   - Change profile photo (coming soon)
   - Delete account option

2. **🔔 Notifications**
   - Master toggle: ON/OFF
   - Shows all 4 daily reminders:
     - 🌅 Morning - 8:00 AM
     - ☀️ Day - 1:00 PM
     - 🌆 Evening - 6:00 PM
     - 🌙 Night - 9:00 PM
   - Customize times (coming soon)

3. **🎨 Journal Tone**
   - Reflective (Personal & encouraging)
   - Coach-Like (Motivational & action-oriented)
   - Poetic (Literary & contemplative)
   - Factual (Data-focused & clinical)

4. **⚙️ App Settings**
   - Theme (Light/Dark - coming soon)
   - Language preferences
   - Data sync options
   - Auto-backup settings

5. **💎 Manage Premium**
   - If FREE: Shows "Upgrade" badge → Opens paywall
   - If PREMIUM: Shows subscription details

6. **📤 Export Data**
   - Export all user data as JSON

7. **📚 View Journal History**
   - Navigate to journal history screen

8. **❓ Help & Support**
   - FAQ section
   - Contact support

9. **🚪 Logout**
   - Clear local session

---

## 3. Database Storage

### Users Table
**Location:** `backend/database-sqlite.js`

```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT UNIQUE NOT NULL,
  name TEXT,
  email TEXT,
  persona TEXT DEFAULT 'casual', -- engaged, casual, struggler, power-user
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

### User Preferences Table
**Location:** `database/schema.sql`

```sql
CREATE TABLE user_preferences (
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  
  -- Fulfillment weights (personalized over time)
  body_weight REAL DEFAULT 0.25,
  mind_weight REAL DEFAULT 0.25,
  soul_weight REAL DEFAULT 0.25,
  purpose_weight REAL DEFAULT 0.25,
  
  -- Thresholds for "Meaningful Day"
  body_threshold REAL DEFAULT 70,
  mind_threshold REAL DEFAULT 65,
  soul_threshold REAL DEFAULT 75,
  purpose_threshold REAL DEFAULT 60,
  
  -- Baselines (calculated from first 2 weeks)
  social_minutes_baseline REAL DEFAULT 70,
  sleep_hours_baseline REAL DEFAULT 7.5,
  activity_minutes_baseline REAL DEFAULT 30,
  
  -- Journal preferences
  journal_tone TEXT DEFAULT 'reflective',
  
  -- Privacy settings
  cloud_sync_enabled BOOLEAN DEFAULT FALSE,
  device_data_sync BOOLEAN DEFAULT TRUE,
  anonymous_aggregation BOOLEAN DEFAULT FALSE,
  
  -- Reminder times (JSON array)
  reminder_times TEXT DEFAULT '{"morning":"8:00","day":"13:00","evening":"18:00","night":"21:00"}',
  
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. API Endpoints

### Get User Profile
```
GET /api/users/:userId
```

### Update User Profile
```
POST /api/users/:userId/profile
Body:
{
  "name": "Updated Name",
  "email": "newemail@example.com"
}
```

### Get User Preferences
```
GET /api/users/:userId/preferences
```

### Update User Preferences
```
POST /api/users/:userId/preferences
Body:
{
  "journal_tone": "coach-like",
  "reminder_times": {"morning":"9:00", "day":"14:00", "evening":"19:00", "night":"22:00"}
}
```

---

## 5. Storage Summary

### Local Storage (Frontend)
- **Key:** `'onboarding_complete'`
- **Type:** Boolean
- **Purpose:** Track if user has seen onboarding
- **Service:** `StorageService.ts`

### Database (Backend)
- **Table:** `users`
- **Columns:** name, email, persona, preferences, premium status, stats
- **Table:** `user_preferences`
- **Columns:** weights, thresholds, baselines, tone, reminders

### Frontend State (React)
- **Component:** `App-Fulfillment.tsx`
- **State:** `hasCompletedOnboarding`, `userName`, `userEmail`, etc.
- **Props:** Passed to `ProfileScreen` component

---

## 6. Testing Onboarding

### Method 1: Clear Local Storage
```javascript
// In browser console:
localStorage.removeItem('onboarding_complete');
location.reload();
```

### Method 2: Reset Database
```bash
# Clear users table
sqlite3 backend/fulfillment.db "DELETE FROM users;"
```

### Method 3: Fresh Install
- Delete app data
- Reinstall app
- Will show onboarding screen

---

## 7. Key Files

| File | Purpose |
|------|---------|
| `components/OnboardingScreen.tsx` | Onboarding UI component |
| `components/ProfileScreen.tsx` | Profile UI component |
| `services/StorageService.ts` | Local storage operations |
| `App-Fulfillment.tsx` | Main app routing logic |
| `backend/database-sqlite.js` | User data storage |
| `database/schema.sql` | User preferences schema |
| `backend/server-fixed.js` | Profile API endpoints |

---

## Summary

**Onboarding Flow:**
- ✅ Stored in local storage (AsyncStorage)
- ✅ Managed by `StorageService.ts`
- ✅ UI in `OnboardingScreen.tsx`
- ✅ Routing in `App-Fulfillment.tsx`

**Profile Information:**
- ✅ Stored in `users` and `user_preferences` tables
- ✅ Displayed in `ProfileScreen.tsx`
- ✅ Managed via API endpoints
- ✅ Includes: name, email, persona, tone, reminders, premium status

