# Frontend Registration UI Setup

## Current Status

✅ **RegistrationForm.tsx** - Created and ready to use  
❌ **LoginComponent.tsx** - Integration in progress (file getting corrupted)

## What Needs to Be Done

### 1. Import RegistrationForm in LoginComponent.tsx
Add this line at the top:
```typescript
import RegistrationForm from './RegistrationForm';
```

### 2. Add State for Signup Toggle
Add this state variable:
```typescript
const [showSignup, setShowSignup] = useState(false);
```

### 3. Add "Create Account" Button
Add this before the demo credentials section (around line 159):
```tsx
<div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
  <p className="text-sm text-gray-700 text-center mb-2">New Company?</p>
  <button
    type="button"
    onClick={() => setShowSignup(true)}
    className="w-full py-2 px-4 border border-green-600 rounded-lg text-sm font-medium text-green-700 hover:bg-green-100"
  >
    Create New Account
  </button>
</div>
```

### 4. Add Conditional Rendering
Wrap the entire login form in a conditional:
```tsx
{!showSignup ? (
  // ... existing login form code ...
) : (
  <RegistrationForm
    onSuccess={() => setShowSignup(false)}
    onCancel={() => setShowSignup(false)}
  />
)}
```

## Current Working Status

✅ Backend APIs ready
✅ RegistrationForm component ready
⏳ LoginComponent integration needs manual completion

## Recommendation

Due to file corruption issues during automated editing, please manually make the above changes to `src/components/LoginComponent.tsx`.

---

**Alternative:** I can create a separate standalone registration page if you prefer.

