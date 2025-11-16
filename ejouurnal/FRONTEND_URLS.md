# Frontend URLs

## ✅ Both Frontends Running

### V1 (Original Frontend)
**URL:** http://localhost:3006
**Status:** ✅ Running
**Features:**
- Complete UI/UX
- All core workflows
- User creation
- Check-ins
- Journal generation
- Insights generation
- Progress tracking

### V2 (React Mockup with Backend)
**URL:** http://localhost:3008
**Status:** ✅ Running - Beautiful UI from mockup!
**Features:**
- Same as V1 +
- **Interaction tracking**
- **Locked insight previews**
- **Conversion offer modal**
- **Real premium upgrade**
- **Premium unlock animations**

## Backend
**URL:** http://localhost:3005
**Status:** ✅ Running
**Health Check:** http://localhost:3005/health

## How to Test

### Test V1 (Original):
1. Open: http://localhost:3006
2. Create account
3. Log check-ins
4. Generate insights
5. View journal

### Test V2 (Premium Conversion):
1. Open: http://localhost:3007/v2-index.html
2. Everything from V1 +
3. Click "Insights" tab
4. Click "Unlock Premium" on locked insights
5. See conversion offer modal
6. Accept offer to upgrade
7. See all insights unlocked

## Quick Test V2 Features

### Interaction Tracking:
1. Navigate to Insights
2. Click "Unlock Premium" button
3. Check Profile tab → see interaction count

### Real Premium Upgrade:
1. Click "Unlock Premium"
2. Accept offer
3. Verify premium badge shows
4. All insights unlocked

## API Endpoints

Both V1 and V2 use:
- `POST /api/users` - Create user
- `POST /api/check-ins` - Log check-in
- `POST /api/journals/generate` - Generate journal
- `POST /api/insights/generate` - Generate insights
- `GET /api/analytics` - Get stats

V2 additionally uses (Phase 3):
- `POST /api/users/:userId/interactions` - Track interactions
- `GET /api/users/:userId/interactions` - Get interactions
- `POST /api/conversion/offer` - Get conversion offer
- `POST /api/users/:userId/premium` - Upgrade to premium

## Notes

- Both frontends share the same backend
- Backend is running on port 3005
- V1 is on port 3006
- V2 is on port 3007
- All data persists in the database

