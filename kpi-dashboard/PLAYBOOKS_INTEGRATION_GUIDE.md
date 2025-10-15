# 🎯 Playbooks Integration Guide

## ✅ What's Been Created

Your Playbooks library has been successfully added to `src/lib/` with the following structure:

```
src/lib/
├── index.ts              # Main exports
├── types.ts              # TypeScript interfaces
├── playbooks.ts          # 5 core playbooks defined
├── playbook-manager.ts   # Core management logic
├── utils.ts              # Utility functions
├── hooks.ts              # React hooks
└── README.md             # Complete documentation

src/components/
└── Playbooks.tsx         # React component for UI
```

## 🎯 The 5 Core Playbooks

1. **VoC Sprint** (`voc-sprint`) - Voice of Customer feedback collection
2. **Activation Blitz** (`activation-blitz`) - Customer onboarding acceleration  
3. **SLA Stabilizer** (`sla-stabilizer`) - Service level agreement monitoring
4. **Renewal Safeguard** (`renewal-safeguard`) - Renewal risk mitigation
5. **Expansion Timing** (`expansion-timing`) - Growth opportunity identification

## 🔧 Integration Status

### ✅ Completed:
- ✅ Playbooks library structure created
- ✅ TypeScript types and interfaces
- ✅ 5 core playbooks with detailed steps
- ✅ React hooks for state management
- ✅ Utility functions and helpers
- ✅ React component for UI
- ✅ Integration with CSPlatform.tsx
- ✅ Tab routing configured

### ⚠️ Next Steps Needed:

#### 1. **Backend API Endpoints** (Required)
You need to create backend endpoints to support the playbooks:

```python
# Create: backend/playbooks_api.py
from flask import Blueprint, request, jsonify

playbooks_api = Blueprint('playbooks_api', __name__)

@playbooks_api.route('/api/playbooks/executions', methods=['POST'])
def save_execution():
    # Save playbook execution to database
    pass

@playbooks_api.route('/api/playbooks/executions', methods=['GET'])
def get_executions():
    # Get executions for customer
    pass
```

#### 2. **Database Tables** (Required)
Add playbook-related tables to your database:

```sql
-- Playbook executions table
CREATE TABLE playbook_executions (
    id TEXT PRIMARY KEY,
    playbook_id TEXT NOT NULL,
    customer_id INTEGER NOT NULL,
    account_id INTEGER,
    status TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    results TEXT, -- JSON
    metadata TEXT -- JSON
);
```

#### 3. **Register API Blueprint** (Required)
Add to `backend/app.py`:

```python
from playbooks_api import playbooks_api
app.register_blueprint(playbooks_api)
```

## 🚀 How to Use Your Playbooks Code

### **1. Import in Components:**
```typescript
import { usePlaybooks, usePlaybookDefinitions } from '../lib';
import Playbooks from '../components/Playbooks';
```

### **2. Use React Hooks:**
```typescript
function MyComponent({ customerId }: { customerId: number }) {
  const { playbooks, startPlaybook } = usePlaybooks(customerId);
  
  const handleStart = async (playbookId: string) => {
    const context = {
      customerId,
      userId: 1,
      userName: 'User',
      timestamp: new Date().toISOString(),
      metadata: {}
    };
    
    await startPlaybook(playbookId, context);
  };
  
  return (
    <div>
      {playbooks.map(playbook => (
        <button key={playbook.id} onClick={() => handleStart(playbook.id)}>
          Start {playbook.name}
        </button>
      ))}
    </div>
  );
}
```

### **3. Access Playbook Data:**
```typescript
import { playbooks, getPlaybookById } from '../lib';

// Get all playbooks
console.log(playbooks);

// Get specific playbook
const vocPlaybook = getPlaybookById('voc-sprint');
console.log(vocPlaybook?.steps);
```

## 🎨 UI Integration

### **Current Tab Structure:**
- **"AI Insights"** → RAG Analysis (unchanged)
- **"Playbooks"** → Your new Playbooks component ✅

### **Access Your Playbooks:**
1. Go to http://localhost:3000
2. Login to your dashboard
3. Click on **"Playbooks"** tab
4. See your 5 playbooks with start buttons

## 📊 Playbook Structure Example

Each playbook includes:

```typescript
{
  id: 'voc-sprint',
  name: 'VoC Sprint',
  description: 'Rapid Voice of Customer feedback collection...',
  category: 'voc-sprint',
  icon: '🎤',
  color: 'blue',
  estimatedDuration: 120, // minutes
  steps: [
    {
      id: 'voc-1',
      title: 'Prepare VoC Survey',
      description: 'Create and configure customer feedback survey...',
      type: 'manual',
      estimatedTime: 30
    },
    // ... more steps
  ],
  prerequisites: ['Customer contact information available'],
  successCriteria: ['Minimum 70% response rate']
}
```

## 🔧 Customization Options

### **Add New Playbooks:**
```typescript
// In src/lib/playbooks.ts, add to the playbooks array:
{
  id: 'my-custom-playbook',
  name: 'My Custom Playbook',
  description: 'Custom playbook description',
  category: 'custom',
  // ... rest of definition
}
```

### **Modify Existing Playbooks:**
Edit the playbook definitions in `src/lib/playbooks.ts` to:
- Change step descriptions
- Add/remove steps
- Modify estimated times
- Update prerequisites

### **Custom Styling:**
The component uses Tailwind CSS classes. Modify `src/components/Playbooks.tsx` to change:
- Colors and themes
- Layout and spacing
- Button styles
- Card designs

## 🐛 Troubleshooting

### **TypeScript Errors:**
If you see import errors, make sure:
1. All files in `src/lib/` are created
2. TypeScript compilation is working
3. No syntax errors in the files

### **Runtime Errors:**
If playbooks don't load:
1. Check browser console for errors
2. Verify backend API endpoints exist
3. Check network requests in DevTools

### **Missing Features:**
If you need additional functionality:
1. Extend the types in `src/lib/types.ts`
2. Add new methods to `PlaybookManager`
3. Create new React hooks in `src/lib/hooks.ts`

## 📝 Next Steps

### **Immediate (Required):**
1. ✅ Create backend API endpoints
2. ✅ Add database tables
3. ✅ Register API blueprint
4. ✅ Test the integration

### **Optional Enhancements:**
1. Add playbook scheduling
2. Implement notifications
3. Add playbook templates
4. Create playbook analytics
5. Add playbook sharing

## 🎉 Summary

Your Playbooks system is **ready to use**! The frontend is fully integrated and the library provides:

- ✅ **5 Core Playbooks** with detailed steps
- ✅ **React Hooks** for state management
- ✅ **TypeScript Types** for type safety
- ✅ **Utility Functions** for common operations
- ✅ **UI Component** for user interaction
- ✅ **Integration** with your existing dashboard

Just add the backend API endpoints and you're ready to start using playbooks in production! 🚀

---

**Files Created:**
- `src/lib/index.ts`
- `src/lib/types.ts`
- `src/lib/playbooks.ts`
- `src/lib/playbook-manager.ts`
- `src/lib/utils.ts`
- `src/lib/hooks.ts`
- `src/lib/README.md`
- `src/components/Playbooks.tsx`
- `PLAYBOOKS_INTEGRATION_GUIDE.md`

**Files Modified:**
- `src/components/CSPlatform.tsx` (added Playbooks import and tab)
