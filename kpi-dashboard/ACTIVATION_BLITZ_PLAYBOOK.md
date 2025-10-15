# 🚀 Activation Blitz Playbook - Complete Specification

## 📋 **Overview**

**Purpose**: Compress time-to-value; get more users to first and meaningful outcomes.

**Duration**: 30 days (4 weeks)  
**Version**: 2.0.0  
**Category**: Activation Blitz

---

## 🚨 **Trigger Conditions** (Any of the following)

### **Quantitative Triggers:**
- **Adoption index < 60** (Low feature adoption)
- **Active users < 50** (Low user engagement)
- **DAU/MAU < 25%** (Poor daily/monthly active user ratio)

### **Qualitative Triggers:**
- **Feature X/Y not used but included in plan** (Unused premium features)

---

## 📅 **30-Day Execution Plan**

### **Week 1: In-App Engagement & Office Hours**
**Goal**: Create immediate user engagement and "aha" moments

#### **Step 1: Trigger Assessment** (15 min)
- **Type**: Automation
- **Description**: Evaluate all Activation Blitz triggers against current metrics
- **Data Required**: 
  - Current adoption index
  - Active user count
  - DAU/MAU ratio
  - Feature usage analysis

#### **Step 2: In-App Walkthroughs** (2 hours)
- **Type**: Automation
- **Description**: Deploy targeted in-app walkthroughs for key features
- **Target**: 2 "aha" moments per user
- **Focus Areas**:
  - Core feature demonstrations
  - Value-driven use cases
  - Quick wins and time-saving features

#### **Step 3: Live Office Hours** (3 hours)
- **Type**: Manual
- **Description**: Schedule and conduct live office hours for hands-on support
- **Format**:
  - Group Q&A sessions
  - 1-on-1 troubleshooting
  - Feature deep-dives
  - Best practice sharing

---

### **Week 2: Role-Based Training & Use Cases**
**Goal**: Provide targeted training and demonstrate clear value

#### **Step 4: Role-Based Training** (4 hours)
- **Type**: Manual
- **Description**: Conduct role-specific training sessions
- **Audiences**:
  - **Power Users**: Advanced features and workflows
  - **Viewers**: Basic functionality and reporting
- **Format**:
  - Interactive workshops
  - Hands-on exercises
  - Role-specific scenarios

#### **Step 5: Publish KPI-Aligned Use Cases** (3 hours)
- **Type**: Manual
- **Description**: Create and publish 3 KPI-aligned use cases
- **Use Case Requirements**:
  - Clear value demonstration
  - Measurable outcomes
  - Step-by-step implementation
  - ROI calculations
- **Distribution**:
  - Customer portal
  - Email campaigns
  - In-app notifications

---

### **Week 3: Executive Checkpoint**
**Goal**: Demonstrate value and secure continued support

#### **Step 6: Executive Checkpoint** (1.5 hours)
- **Type**: Manual
- **Description**: Present executive checkpoint with value story
- **Presentation Elements**:
  - Before/after screenshots
  - KPI improvements and trends
  - User engagement metrics
  - Success stories and testimonials
- **Outcomes**:
  - Continued executive support
  - Resource allocation confirmation
  - Strategic alignment validation

---

### **Week 4: Nudge Campaign & Success Stories**
**Goal**: Drive final adoption push and secure success stories

#### **Step 7: Nudge Campaign** (2 hours)
- **Type**: Automation
- **Description**: Launch targeted nudge campaign to non-adopters
- **Campaign Elements**:
  - Personalized activation paths
  - Feature-specific nudges
  - Progress tracking and reminders
  - Incentive programs
- **Targeting**:
  - Users with low adoption scores
  - Feature-specific non-users
  - Inactive user segments

#### **Step 8: Secure Success Stories** (2.5 hours)
- **Type**: Manual
- **Description**: Identify and secure 2 success stories for QBR
- **Success Story Requirements**:
  - Quantifiable business impact
  - Before/after metrics
  - User testimonials
  - Implementation timeline
- **Use Cases**:
  - QBR presentations
  - Case study development
  - Marketing materials
  - Reference calls

#### **Step 9: Generate Activation Plan** (15 min)
- **Type**: Automation
- **Description**: Use RAG to generate comprehensive activation plan
- **RAG Prompt**: 
  ```
  "Given {Account}'s low adoption and usage metrics, propose a 4-week activation plan with in-app steps, emails, and two KPIs to prove value by day 30."
  ```
- **Output Format**:
  - 4-week structured activation plan
  - Detailed in-app onboarding steps
  - Targeted email campaign sequence
  - Two specific KPIs to prove value
  - Day 30 success measurement criteria

---

## 👥 **Ownership Structure**

### **Primary Owner**: CSM (Customer Success Manager)
- Lead program execution and coordination
- Primary customer contact and relationship management
- Progress tracking and reporting

### **Co-Owners**:
- **Enablement**: Training materials, use cases, and knowledge transfer
- **Admin Champion at Customer**: Internal champion and change management

---

## 📊 **KPIs to Move**

### **Primary Metrics**:
- **Adoption**: +10-15 points improvement
- **Active Users**: +20-30% increase
- **Time-to-Value**: Reduction in days to first meaningful outcome
- **DAU/MAU**: Improvement to ≥ 25%

### **Secondary Metrics**:
- **Feature Usage**: Increase in specific feature adoption
- **User Engagement**: Higher session frequency and duration
- **Support Tickets**: Reduction in onboarding-related issues

---

## ✅ **Exit Criteria**

### **Must Have**:
- [ ] **Two features activated successfully** with measurable usage
- [ ] **DAU/MAU ≥ 25%** or significant improvement from baseline
- [ ] **Adoption index ≥ 60** (or +10 vs. baseline)
- [ ] **Two success stories secured** for QBR presentation

### **Success Indicators**:
- [ ] **Executive validation** of value demonstration
- [ ] **User engagement increase** across all segments
- [ ] **Support ticket reduction** for onboarding issues
- [ ] **Customer satisfaction improvement** with product value

---

## 🤖 **RAG Integration**

### **Automated Activation Plan Generation**:
The playbook includes a RAG-powered step that automatically generates a comprehensive activation plan using:

**Data Sources**:
- Current adoption and usage metrics
- Feature utilization data
- User engagement patterns
- Support ticket analysis
- Customer feedback and surveys

**Output Structure**:
```json
{
  "activation_plan": {
    "week_1": "In-app walkthroughs and office hours",
    "week_2": "Role-based training and use cases",
    "week_3": "Executive checkpoint and value story",
    "week_4": "Nudge campaign and success stories"
  },
  "in_app_steps": [
    {
      "step": "Feature tour for core functionality",
      "target": "All users",
      "duration": "5-10 minutes",
      "success_metric": "Feature usage increase"
    }
  ],
  "email_sequence": [
    {
      "day": 1,
      "subject": "Welcome to your activation journey",
      "content": "Personalized welcome with quick wins",
      "cta": "Start feature tour"
    }
  ],
  "kpi_targets": {
    "primary_kpi": "Adoption index increase by 10-15 points",
    "secondary_kpi": "Active users increase by 20-30%",
    "measurement_period": "30 days"
  },
  "success_metrics": {
    "day_7": "50% of users complete onboarding",
    "day_14": "25% increase in feature usage",
    "day_30": "Adoption index ≥ 60 or +10 vs baseline"
  }
}
```

---

## 🔧 **Technical Implementation**

### **Trigger Monitoring**:
```typescript
interface ActivationTriggerData {
  adoption_index_threshold: 60;
  active_users_threshold: 50;
  dau_mau_threshold: 0.25;
  unused_feature_check: true;
  target_features?: "Feature X, Feature Y";
}
```

### **RAG Configuration**:
```typescript
interface ActivationRAGData {
  rag_prompt: "Given {Account}'s low adoption and usage metrics, propose a 4-week activation plan with in-app steps, emails, and two KPIs to prove value by day 30.";
  output_format: {
    activation_plan: "4-week structured activation plan";
    in_app_steps: "Detailed in-app onboarding steps";
    email_sequence: "Targeted email campaign sequence";
    kpi_targets: "Two specific KPIs to prove value";
    success_metrics: "Day 30 success measurement criteria";
  };
}
```

---

## 📈 **Success Metrics Timeline**

### **Week 1**: Engagement & Awareness
- In-app walkthrough completion: 70%+
- Office hours attendance: 40% of target users
- "Aha" moment feedback: 2+ per user

### **Week 2**: Training & Value Demonstration
- Role-based training completion: 80%+
- Use case downloads: 60% of users
- Feature usage increase: 15%+

### **Week 3**: Executive Alignment
- Executive checkpoint approval: 100%
- Value story validation: Clear ROI demonstration
- Continued support commitment: Confirmed

### **Week 4**: Final Push & Success Stories
- Nudge campaign engagement: 50%+ response rate
- Success story collection: 2+ documented cases
- Final adoption metrics: Target thresholds met

### **30 Days Post**: Impact Measurement
- Adoption improvement: +10-15 points
- Active users increase: +20-30%
- DAU/MAU ratio: ≥ 25%
- Time-to-value: Measurable reduction

---

## 🎯 **Integration with Existing System**

### **Data Sources**:
- **KPI Object**: Adoption metrics and feature usage data
- **Account Object**: User counts and engagement metrics
- **Usage Analytics**: DAU/MAU ratios and feature adoption
- **Support Tickets**: Onboarding and training-related issues

### **API Integration**:
- **Unified Query API**: For RAG-powered activation planning
- **Analytics API**: For adoption and usage trend analysis
- **Cache API**: For performance optimization

### **Frontend Integration**:
- **Playbooks Component**: UI for execution tracking
- **Settings Component**: Trigger configuration management
- **Real-time Updates**: Progress tracking and notifications

---

## 🔄 **Trigger Configuration in Settings**

### **Configurable Thresholds**:
- **Adoption Index**: Default 60 (trigger if below)
- **Active Users**: Default 50 (trigger if below)
- **DAU/MAU Ratio**: Default 0.25 (trigger if below)
- **Unused Feature Check**: Enabled by default
- **Target Features**: Customizable feature list
- **Auto-Trigger**: Optional automatic suggestions

### **Settings UI Features**:
- Real-time threshold adjustment
- Test trigger conditions
- Save/load configurations
- Visual feedback and validation

---

This comprehensive Activation Blitz playbook provides a structured approach to improving user adoption and time-to-value, with clear triggers, detailed execution steps, and measurable success criteria.
