# Enhanced Onboarding Wizard - Modular Structure

## 📁 File Structure

The enhanced onboarding wizard is organized into modular components:

```
OnboardingWizard/
├── OnboardingWizard.types.ts      # TypeScript type definitions
├── OnboardingWizard.config.ts     # Configuration & defaults
├── OnboardingWizard.utils.ts      # Utility functions
├── OnboardingWizard.main.tsx      # Main orchestrator component
│
├── Step0Account.tsx               # Account creation & billing
├── Step1Business.tsx              # Vertical selection & business context
├── Step2Pillars.tsx               # Vertical-specific KPI configuration
├── Step3Events.tsx                # Event severity calibration
├── Step4Criteria.tsx              # Success criteria configuration
├── Step5Sources.tsx               # Data sources (with validation/preview)
├── Step6Review.tsx                # Review & confirm
├── Step7Team.tsx                  # Team setup
└── Step8Training.tsx              # Training & walkthrough (optional)
```

---

## 🎯 Features by Step

### Step 0: Account Creation & Billing
- ✅ Email/password registration with strength validation
- ✅ Subscription plan selection (Free/Starter/Professional/Enterprise)
- ✅ Payment method selection
- ✅ Company domain setup
- ✅ Password strength indicator

### Step 1: Vertical Selection & Business Context
- ✅ **NEW:** Vertical selection (SaaS vs Data Center)
- ✅ Company information
- ✅ Industry & segments
- ✅ Deal size & contract model
- ✅ CSM model selection

### Step 2: Vertical-Specific KPI Configuration
- ✅ **ENHANCED:** Dynamic pillars based on vertical
  - SaaS: Product Usage, Support, Customer Sentiment, Business Outcomes, Relationship Strength
  - Data Center: Deployment, Stability, Performance, Channel Engagement, Expansion
- ✅ Drag-and-drop ranking
- ✅ Weight calculation display

### Step 3: Event Severity Calibration
- ✅ **ENHANCED:** Vertical-specific events
- ✅ Negative & positive events
- ✅ Severity rating (1-10)
- ✅ Visual feedback

### Step 4: Success Criteria
- ✅ Health score thresholds
- ✅ Alert thresholds (churn/expansion)
- ✅ Prediction horizon
- ✅ Visual threshold bars

### Step 5: Data Sources (MAJOR ENHANCEMENT)
- ✅ **NEW:** File validation
  - CSV schema validation
  - Required columns check
  - Row count verification
- ✅ **NEW:** File preview (first 5 rows)
- ✅ **NEW:** Real API connection (not simulated)
  - API endpoint configuration
  - API key setup
  - Connection testing
- ✅ Error handling & validation messages
- ✅ Skip option for optional sources

### Step 6: Review & Confirm
- ✅ Complete configuration summary
- ✅ Account details
- ✅ Business profile
- ✅ Pillar weights
- ✅ Thresholds
- ✅ Data sources status
- ✅ Team members
- ✅ Download configuration JSON

### Step 7: Team Setup (NEW)
- ✅ Add team members
- ✅ Role assignment (Admin, CSM, Analyst, Viewer)
- ✅ Email invitations
- ✅ Invitation status tracking
- ✅ Remove team members

### Step 8: Training & Walkthrough (NEW - Optional)
- ✅ Recommended resources
- ✅ Video tutorials
- ✅ Documentation links
- ✅ Interactive tour option
- ✅ Skip training toggle

---

## 🚀 Usage

### Import and Use

```tsx
import { OnboardingWizard } from './OnboardingWizard.main';
import { OnboardingData } from './OnboardingWizard.types';

function App() {
  const handleComplete = (data: OnboardingData) => {
    console.log('Onboarding complete:', data);
    // Send data to backend API
    // Redirect to dashboard
  };

  const handleCancel = () => {
    // Handle cancellation
  };

  return (
    <OnboardingWizard
      onComplete={handleComplete}
      onCancel={handleCancel}
    />
  );
}
```

### Customizing Configuration

Edit `OnboardingWizard.config.ts` to customize:
- Default values
- Vertical-specific pillars
- Vertical-specific events
- Subscription plans
- Options lists

---

## 📋 Dependencies

- React 18+
- TypeScript
- Lucide React (icons)
- File validation utilities (CSV parsing)

---

## ✅ Implementation Status

All 8 steps are complete and modular:
- ✅ Step 0: Account & Billing
- ✅ Step 1: Business Context with Vertical Selection
- ✅ Step 2: Vertical-Specific Pillars
- ✅ Step 3: Event Severity
- ✅ Step 4: Success Criteria
- ✅ Step 5: Data Sources (with validation/preview)
- ✅ Step 6: Review
- ✅ Step 7: Team Setup
- ✅ Step 8: Training (optional)

---

## 🔧 Customization

### Add New Vertical

1. Add vertical to `VerticalType` in `OnboardingWizard.types.ts`
2. Add pillar definitions in `OnboardingWizard.config.ts`
3. Add event definitions in `OnboardingWizard.config.ts`
4. Update `getDefaultSources()` for vertical-specific sources

### Add New Validation

1. Add validation logic in `OnboardingWizard.utils.ts`
2. Update `Step5Sources.tsx` to use new validation

### Modify Steps

Each step is self-contained. Modify individual step files as needed.

---

## 📝 Notes

- All steps are fully typed with TypeScript
- Vertical selection triggers automatic pillar/event updates
- File validation uses async utilities
- API connections can be tested before proceeding
- Team invitations are simulated (replace with real API calls)
- Configuration can be downloaded as JSON

---

**Status:** ✅ Complete - All 8 steps implemented and modular
