# 🎤 VoC Sprint Playbook - Complete Specification

## 📋 **Overview**

**Purpose**: Rapidly surface value gaps/themes and convert them into actions your execs and product team will stand behind.

**Duration**: 30 days (4 weeks)  
**Version**: 2.0.0  
**Category**: Voice of Customer Sprint

---

## 🚨 **Trigger Conditions** (Any of the following)

### **Quantitative Triggers:**
- **NPS < 10** (Net Promoter Score below 10)
- **CSAT < 3.6** (Customer Satisfaction below 3.6)
- **Churn risk ≥ 0.30** (30% or higher churn probability)
- **Health score drop ≥ 10 points** (in 30-60 days)

### **Qualitative Triggers:**
- **2+ "reason for churn" mentions** in last quarter's notes

---

## 📅 **30-Day Execution Plan**

### **Week 1: Discovery & Recruitment**
**Goal**: Gather comprehensive customer feedback and data

#### **Step 1: Trigger Assessment** (15 min)
- **Type**: Automation
- **Description**: Evaluate all VoC Sprint triggers against current metrics
- **Data Required**: 
  - Current NPS score
  - Current CSAT score
  - Churn risk probability
  - Health score trend (30-60 days)
  - Recent churn mentions in notes

#### **Step 2: Recruit Sponsor/Users** (2 hours)
- **Type**: Manual
- **Description**: Identify and recruit 6-10 sponsor users for interviews
- **Focus Areas**:
  - Power users and champions
  - At-risk accounts
  - Recently churned customers (if applicable)
  - Cross-functional stakeholders

#### **Step 3: Conduct Interviews** (5 hours)
- **Type**: Manual
- **Description**: Run 30-40 minute structured interviews
- **Interview Focus**:
  - Value gaps and unmet needs
  - Adoption challenges
  - Support experience
  - Product roadmap feedback
  - Competitive concerns

#### **Step 4: Mine Tickets & QBR Notes** (3 hours)
- **Type**: Action
- **Description**: Analyze last 60 days of data for recurring themes
- **Data Sources**:
  - Support tickets and resolution notes
  - QBR meeting notes and action items
  - Customer communications
  - Usage analytics and behavior patterns

---

### **Week 2: Analysis & Theme Development**
**Goal**: Transform raw feedback into actionable insights

#### **Step 5: Theme Clustering** (4 hours)
- **Type**: Action
- **Description**: Cluster findings into structured categories
- **Categories**:
  - **Value gaps**: Missing features, unclear ROI
  - **Adoption challenges**: Onboarding, training, complexity
  - **Support issues**: Response time, resolution quality
  - **Roadmap requests**: Feature priorities, timing

#### **Step 6: Draft Evidence & Quick Wins** (3 hours)
- **Type**: Manual
- **Description**: Document evidence of value gaps with customer quotes
- **Deliverables**:
  - Evidence-based theme documentation
  - Customer quote compilation
  - Quick wins vs. longer-term fixes categorization
  - Impact assessment for each theme

---

### **Week 3: Executive Alignment**
**Goal**: Secure executive commitment for action

#### **Step 7: Executive Readout** (1.5 hours)
- **Type**: Manual
- **Description**: Present findings to executive team
- **Presentation Elements**:
  - Clear evidence with customer quotes
  - Theme prioritization and impact
  - Recommended actions and timelines
  - Resource requirements

#### **Step 8: Commit 2-3 Fixes** (2 hours)
- **Type**: Decision
- **Description**: Secure executive commitment for specific actions
- **Commitment Framework**:
  - **1 "Now" fix**: Immediate implementation (1-2 weeks)
  - **1 "Next Release" fix**: Product development (1-3 months)
  - **1 "Process" improvement**: Operational change (ongoing)
- **Requirements**:
  - Clear owners assigned
  - Defined timelines
  - Success metrics established

---

### **Week 4: Communication & Follow-up**
**Goal**: Close the loop with customers and establish monitoring

#### **Step 9: Publish Action Tracker** (1 hour)
- **Type**: Manual
- **Description**: Create and publish VoC → Action tracker
- **Format**: QBR-style document including:
  - Themes identified
  - Committed fixes with owners
  - Implementation timelines
  - Success metrics

#### **Step 10: Customer Communications** (1.5 hours)
- **Type**: Manual
- **Description**: Send "we heard you" communications
- **Audience**:
  - Interviewed customers
  - Broader account base
  - Key stakeholders
- **Message Elements**:
  - Acknowledgment of feedback
  - Specific changes being made
  - Timeline for improvements
  - Thank you for participation

#### **Step 11: Schedule NPS Follow-up** (30 min)
- **Type**: Automation
- **Description**: Set up monitoring and follow-up surveys
- **Monitoring Setup**:
  - NPS follow-up survey (30-60 days)
  - CSAT tracking
  - Ticket sentiment monitoring
  - Renewal intent tracking

#### **Step 12: Generate VoC Sprint Brief** (15 min)
- **Type**: Automation
- **Description**: Use RAG to generate comprehensive brief
- **RAG Prompt**: 
  ```
  "Generate a VoC sprint brief for {Account} using last 60 days of notes, tickets, and KPI deltas. List top 5 themes, customer quotes, and the 3 fastest actions with owners."
  ```
- **Output Format**:
  - Top 5 themes with evidence
  - Supporting customer quotes
  - 3 prioritized actions with owners
  - Expected KPI impact

---

## 👥 **Ownership Structure**

### **Primary Owner**: CSM (Customer Success Manager)
- Lead execution and coordination
- Primary customer contact
- Progress tracking and reporting

### **Co-Owners**:
- **PM (Product Manager)**: Product-related fixes and roadmap items
- **Support Lead**: Support process improvements and ticket resolution

---

## 📊 **KPIs to Move**

### **Primary Metrics**:
- **NPS**: +6-10 points improvement
- **CSAT**: +0.2-0.3 points improvement
- **Ticket Sentiment**: Positive trend increase
- **Renewal Intent**: Measurable improvement

### **Secondary Metrics**:
- **Health Score**: Recovery from trigger threshold
- **Churn Risk**: Reduction below 0.30 threshold
- **Customer Engagement**: Increased interaction and usage

---

## ✅ **Exit Criteria**

### **Must Have**:
- [ ] **Themes logged and categorized** with evidence
- [ ] **3 fixes committed** with clear owners and timelines
- [ ] **"We heard you" communications sent** to customers
- [ ] **NPS follow-up scheduled** for 30-60 days

### **Success Indicators**:
- [ ] **Executive buy-in** for committed actions
- [ ] **Customer acknowledgment** of changes being made
- [ ] **Monitoring systems** in place for ongoing tracking
- [ ] **Action tracker published** and accessible to stakeholders

---

## 🤖 **RAG Integration**

### **Automated Brief Generation**:
The playbook includes a RAG-powered step that automatically generates a comprehensive VoC sprint brief using:

**Data Sources**:
- Last 60 days of customer notes
- Support tickets and resolutions
- KPI deltas and trends
- Interview transcripts
- QBR meeting notes

**Output Structure**:
```json
{
  "top_5_themes": [
    {
      "theme": "Feature Gap",
      "evidence": "Customer quotes and data",
      "impact": "High/Medium/Low",
      "frequency": "Number of mentions"
    }
  ],
  "customer_quotes": [
    {
      "quote": "Direct customer feedback",
      "theme": "Associated theme",
      "source": "Interview/Ticket/Note"
    }
  ],
  "fastest_actions": [
    {
      "action": "Specific fix description",
      "owner": "Assigned person/team",
      "timeline": "Implementation schedule",
      "priority": "Now/Next Release/Process"
    }
  ],
  "kpi_impact": {
    "nps_improvement": "+6-10 points",
    "csat_improvement": "+0.2-0.3 points",
    "sentiment_trend": "Positive trajectory",
    "renewal_impact": "Increased intent"
  }
}
```

---

## 🔧 **Technical Implementation**

### **Trigger Monitoring**:
```typescript
interface VoCTriggerData {
  nps_threshold: 10;
  csat_threshold: 3.6;
  churn_risk_threshold: 0.30;
  health_score_drop_threshold: 10;
  churn_mentions_threshold: 2;
}
```

### **RAG Configuration**:
```typescript
interface VoCRAGData {
  rag_prompt: "Generate a VoC sprint brief for {Account} using last 60 days of notes, tickets, and KPI deltas. List top 5 themes, customer quotes, and the 3 fastest actions with owners.";
  output_format: {
    top_5_themes: "Array of theme objects with evidence";
    customer_quotes: "Direct quotes supporting each theme";
    fastest_actions: "3 prioritized actions with owners and timelines";
    kpi_impact: "Expected NPS, CSAT, and sentiment improvements";
  };
}
```

---

## 📈 **Success Metrics Timeline**

### **Week 1-2**: Data Collection
- Interview completion rate: 80%+
- Theme identification: 5+ distinct themes
- Evidence documentation: 100% of themes

### **Week 3**: Executive Alignment
- Executive commitment: 3 fixes committed
- Owner assignment: 100% of actions
- Timeline establishment: All actions scheduled

### **Week 4**: Communication & Setup
- Customer communications: 100% sent
- Action tracker: Published and accessible
- Monitoring setup: All systems configured

### **30-60 Days Post**: Impact Measurement
- NPS improvement: +6-10 points
- CSAT improvement: +0.2-0.3 points
- Ticket sentiment: Positive trend
- Renewal intent: Measurable increase

---

## 🎯 **Integration with Existing System**

### **Data Sources**:
- **KPI Object**: Category-based KPI data and health scores
- **Account Object**: Industry, region, and status categories
- **KPI Reference Ranges**: Category-based thresholds
- **Customer Config**: Category weights and configuration

### **API Integration**:
- **Unified Query API**: For RAG-powered analysis
- **Analytics API**: For KPI trend analysis
- **Cache API**: For performance optimization

### **Frontend Integration**:
- **Playbooks Component**: UI for execution tracking
- **CSPlatform**: Integration with existing dashboard
- **Real-time Updates**: Progress tracking and notifications

---

This comprehensive VoC Sprint playbook provides a structured, evidence-based approach to customer feedback analysis and action implementation, with clear triggers, detailed execution steps, and measurable success criteria.
