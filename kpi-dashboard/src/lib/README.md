# 🎯 Playbooks Library

A comprehensive library for managing Customer Success playbooks with React integration.

## 📁 Structure

```
src/lib/
├── index.ts              # Main exports
├── types.ts              # TypeScript interfaces
├── playbooks.ts          # Playbook definitions (5 core playbooks)
├── playbook-manager.ts   # Core playbook management
├── utils.ts              # Utility functions and helpers
├── hooks.ts              # React hooks for UI integration
└── README.md             # This documentation
```

## 🚀 Quick Start

### 1. Import the Library

```typescript
// Import everything
import { PlaybookManager, playbooks, usePlaybooks } from '../lib';

// Or import specific components
import { PlaybookDefinition, PlaybookExecution } from '../lib/types';
import { usePlaybooks, usePlaybookExecution } from '../lib/hooks';
```

### 2. Use in React Components

```typescript
import React from 'react';
import { usePlaybooks, usePlaybookDefinitions } from '../lib';

function PlaybooksComponent({ customerId }: { customerId: number }) {
  const { 
    executions, 
    loading, 
    startPlaybook, 
    executeStep 
  } = usePlaybooks(customerId);
  
  const { playbooks, getPlaybook } = usePlaybookDefinitions();

  const handleStartPlaybook = async (playbookId: string) => {
    const context = {
      customerId,
      userId: 1,
      userName: 'Current User',
      timestamp: new Date().toISOString(),
      metadata: {}
    };
    
    await startPlaybook(playbookId, context);
  };

  if (loading) return <div>Loading playbooks...</div>;

  return (
    <div>
      <h2>Available Playbooks</h2>
      {playbooks.map(playbook => (
        <div key={playbook.id} className="playbook-card">
          <h3>{playbook.icon} {playbook.name}</h3>
          <p>{playbook.description}</p>
          <button onClick={() => handleStartPlaybook(playbook.id)}>
            Start {playbook.name}
          </button>
        </div>
      ))}
      
      <h2>Active Executions</h2>
      {executions.map(execution => (
        <div key={execution.id} className="execution-card">
          <h4>Execution {execution.id}</h4>
          <p>Status: {execution.status}</p>
          <p>Progress: {execution.results.length} steps completed</p>
        </div>
      ))}
    </div>
  );
}
```

## 📚 Core Components

### 1. Playbook Definitions (`playbooks.ts`)

Contains the 5 core playbooks:

- **VoC Sprint** (`voc-sprint`) - Voice of Customer feedback collection
- **Activation Blitz** (`activation-blitz`) - Customer onboarding acceleration  
- **SLA Stabilizer** (`sla-stabilizer`) - Service level agreement monitoring
- **Renewal Safeguard** (`renewal-safeguard`) - Renewal risk mitigation
- **Expansion Timing** (`expansion-timing`) - Growth opportunity identification

### 2. Playbook Manager (`playbook-manager.ts`)

Core class for managing playbook execution:

```typescript
const manager = new PlaybookManager();

// Start a playbook
const execution = await manager.startPlaybook('voc-sprint', context);

// Execute a step
const result = await manager.executeStep(execution.id, 'voc-1', { data: 'example' });

// Update status
await manager.updateExecutionStatus(execution.id, 'completed');
```

### 3. React Hooks (`hooks.ts`)

#### `usePlaybooks(customerId)`
- Manages all playbook executions for a customer
- Provides functions to start, update, and execute playbooks
- Returns loading states and error handling

#### `usePlaybookExecution(executionId)`
- Manages a single playbook execution
- Provides step execution and status updates
- Returns execution details and playbook definition

#### `usePlaybookDefinitions()`
- Provides access to all playbook definitions
- Helper functions for filtering and searching
- Returns loading states and error handling

### 4. Utilities (`utils.ts`)

#### `PlaybookUtils`
- `calculateEstimatedTime()` - Calculate total playbook duration
- `getProgressPercentage()` - Get completion percentage
- `canExecuteStep()` - Check if step can be executed
- `formatDuration()` - Format time in human-readable format
- `getStatusColor()` / `getStatusIcon()` - UI helpers

#### `PlaybookValidator`
- `validatePlaybook()` - Validate playbook definition
- `validateContext()` - Validate execution context

#### `PlaybookRenderer`
- `renderDescription()` - Convert markdown-like text to HTML
- `renderStepList()` - Generate step list HTML
- `renderProgressBar()` - Generate progress bar HTML

## 🎯 Usage Examples

### Starting a Playbook

```typescript
import { usePlaybooks } from '../lib';

function MyComponent() {
  const { startPlaybook } = usePlaybooks(customerId);
  
  const handleStartVoC = async () => {
    const context = {
      customerId: 1,
      accountId: 123,
      userId: 456,
      userName: 'John Doe',
      timestamp: new Date().toISOString(),
      metadata: {
        priority: 'high',
        notes: 'Urgent customer feedback needed'
      }
    };
    
    const execution = await startPlaybook('voc-sprint', context);
    console.log('Started execution:', execution.id);
  };
  
  return <button onClick={handleStartVoC}>Start VoC Sprint</button>;
}
```

### Executing Steps

```typescript
import { usePlaybookExecution } from '../lib';

function ExecutionComponent({ executionId }: { executionId: string }) {
  const { execution, playbook, executeStep } = usePlaybookExecution(executionId);
  
  const handleExecuteStep = async (stepId: string) => {
    const stepData = {
      surveyQuestions: ['How satisfied are you?', 'What can we improve?'],
      targetResponseRate: 70
    };
    
    await executeStep(stepId, stepData);
  };
  
  if (!playbook) return <div>Loading...</div>;
  
  return (
    <div>
      <h2>{playbook.name}</h2>
      {playbook.steps.map(step => (
        <div key={step.id}>
          <h4>{step.title}</h4>
          <p>{step.description}</p>
          <button onClick={() => handleExecuteStep(step.id)}>
            Execute Step
          </button>
        </div>
      ))}
    </div>
  );
}
```

### Getting Playbook Information

```typescript
import { usePlaybookDefinitions } from '../lib';

function PlaybookInfo() {
  const { playbooks, getPlaybook, getPlaybooksByCategory } = usePlaybookDefinitions();
  
  const vocPlaybook = getPlaybook('voc-sprint');
  const activationPlaybooks = getPlaybooksByCategory('activation-blitz');
  
  return (
    <div>
      <h2>VoC Sprint Details</h2>
      {vocPlaybook && (
        <div>
          <h3>{vocPlaybook.name}</h3>
          <p>{vocPlaybook.description}</p>
          <p>Duration: {vocPlaybook.estimatedDuration} minutes</p>
          <p>Steps: {vocPlaybook.steps.length}</p>
        </div>
      )}
    </div>
  );
}
```

## 🔧 Integration with Existing UI

### 1. Add to CSPlatform.tsx

```typescript
// In CSPlatform.tsx, add playbooks tab content
{activeTab === 'insights' && (
  <div className="space-y-6">
    <h2 className="text-2xl font-bold text-gray-900">Playbooks</h2>
    <PlaybooksComponent customerId={session.customer_id} />
  </div>
)}
```

### 2. Create Playbook Components

```typescript
// Create src/components/Playbooks.tsx
import React from 'react';
import { usePlaybooks, usePlaybookDefinitions } from '../lib';

export default function PlaybooksComponent({ customerId }: { customerId: number }) {
  // Implementation using the hooks
}
```

### 3. Add API Endpoints

You'll need to add backend API endpoints for playbook management:

```python
# In backend/playbooks_api.py
@playbooks_api.route('/api/playbooks/executions', methods=['POST'])
def save_execution():
    # Save playbook execution to database
    pass

@playbooks_api.route('/api/playbooks/executions', methods=['GET'])
def get_executions():
    # Get executions for customer
    pass
```

## 📊 Data Flow

```
User Action → React Hook → PlaybookManager → API Call → Backend → Database
     ↓              ↓              ↓              ↓
UI Update ← Hook State ← Manager State ← API Response ← Backend Response
```

## 🎨 Styling

The library provides utility classes and functions for styling:

```css
.playbook-card {
  @apply bg-white rounded-lg shadow-sm border border-gray-200 p-6;
}

.execution-card {
  @apply bg-gray-50 rounded-lg p-4 border border-gray-200;
}

.progress-bar {
  @apply w-full bg-gray-200 rounded-full h-2;
}

.progress-fill {
  @apply h-2 rounded-full transition-all duration-300;
}
```

## 🚀 Next Steps

1. **Add Backend API**: Create playbook API endpoints
2. **Create UI Components**: Build React components using the hooks
3. **Add Database Tables**: Store playbook executions
4. **Integration Testing**: Test with real customer data
5. **Advanced Features**: Add notifications, scheduling, etc.

## 📝 Notes

- All playbooks are defined in `playbooks.ts` and can be easily modified
- The library is designed to be extensible - add new playbooks by extending the definitions
- Hooks provide automatic state management and error handling
- Utilities help with common operations like validation and formatting
- TypeScript provides full type safety throughout the library
