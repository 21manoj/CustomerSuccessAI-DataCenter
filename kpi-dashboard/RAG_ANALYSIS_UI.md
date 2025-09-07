# RAG Analysis UI Documentation

## Overview
The RAG Analysis UI provides an intuitive interface for customers to interact with the AI-powered RAG system through pre-defined query templates and custom queries. This makes advanced data analysis accessible to non-technical users.

## Features

### 🎯 **Pre-defined Query Templates**
Organized into 6 categories with 16 ready-to-use queries:

#### 1. **Revenue Analysis** (4 templates)
- **Top Revenue Accounts**: Identify accounts with highest revenue
- **Total Revenue Overview**: Get total revenue across all accounts  
- **Revenue Growth Analysis**: Analyze revenue growth patterns and trends
- **Industry Revenue Breakdown**: Compare revenue performance by industry

#### 2. **Account Health** (4 templates)
- **Account Health Overview**: Comprehensive account health analysis
- **At-Risk Accounts**: Identify accounts at risk of churn
- **Account Performance Ranking**: Rank accounts by overall performance
- **Account Engagement Analysis**: Analyze account engagement levels

#### 3. **KPI Performance** (4 templates)
- **Top Performing KPIs**: Identify best performing KPIs
- **Customer Satisfaction Analysis**: Analyze customer satisfaction scores
- **KPI Category Performance**: Compare performance across KPI categories
- **KPI Trends & Patterns**: Identify trends and patterns in KPI data

#### 4. **Industry Analysis** (2 templates)
- **Industry Performance**: Compare performance across industries
- **Regional Performance**: Analyze performance by geographic region

#### 5. **Strategic Insights** (2 templates)
- **Strategic Recommendations**: AI-powered strategic recommendations
- **Growth Opportunities**: Identify potential growth opportunities

### 🔍 **Custom Query Interface**
- **Natural Language Input**: Ask any question about KPI and account data
- **Real-time Character Count**: Track query length
- **Smart Query Processing**: Automatic query type detection
- **Instant Results**: Fast AI-powered responses

### 🤖 **AI-Powered Analysis**
- **OpenAI GPT-4 Integration**: Advanced language understanding
- **Context-Aware Responses**: Responses based on actual customer data
- **Relevant Source Attribution**: Shows which data sources were used
- **Similarity Scoring**: Indicates how relevant each result is

### 📊 **Rich Results Display**
- **Formatted Responses**: Easy-to-read AI analysis
- **Source Data Preview**: See the underlying data used for analysis
- **Copy to Clipboard**: Easy sharing of results
- **Query Metadata**: Shows query type, similarity threshold, and customer context

## User Interface Components

### 1. **Header Section**
- **Title**: "AI-Powered RAG Analysis" with brain icon
- **Description**: Brief explanation of functionality
- **Build Knowledge Base Button**: One-click setup for new customers

### 2. **Status Indicators**
- **Knowledge Base Status**: Green indicator when ready for queries
- **Error Messages**: Clear error reporting with red indicators
- **Loading States**: Spinner animations during processing

### 3. **Query Templates Panel** (Left Side)
- **Category Organization**: Templates grouped by analysis type
- **Visual Icons**: Color-coded icons for each template type
- **Template Cards**: Clickable cards with title and description
- **Selection State**: Visual feedback for selected template

### 4. **Query Interface** (Right Side)
- **Custom Query Textarea**: Multi-line input for custom questions
- **Character Counter**: Real-time character count display
- **Execute Button**: Process custom queries with loading state

### 5. **Results Display**
- **Query Information**: Shows the executed query and metadata
- **AI Response**: Formatted analysis with proper styling
- **Source Attribution**: List of relevant data sources used
- **Similarity Scores**: Percentage relevance for each source
- **Copy Functionality**: One-click copying of responses

## Technical Implementation

### **API Integration**
```typescript
// Build knowledge base
POST /api/rag-openai/build
Headers: X-Customer-ID: {customer_id}

// Execute query
POST /api/rag-openai/query
Headers: X-Customer-ID: {customer_id}
Body: {
  "query": "Which accounts have the highest revenue?",
  "query_type": "revenue_analysis"
}
```

### **State Management**
- **Loading States**: Track async operations
- **Error Handling**: Comprehensive error management
- **Response Caching**: Store and display query results
- **Template Selection**: Track selected query templates

### **Responsive Design**
- **Mobile-First**: Optimized for all screen sizes
- **Grid Layout**: Responsive grid system
- **Touch-Friendly**: Large clickable areas for mobile
- **Accessible**: Proper ARIA labels and keyboard navigation

## Usage Workflow

### 1. **Initial Setup**
1. Navigate to "RAG Analysis" tab
2. Click "Build Knowledge Base" button
3. Wait for confirmation that knowledge base is ready

### 2. **Using Pre-defined Templates**
1. Browse template categories in left panel
2. Click on desired template card
3. View instant AI analysis results
4. Review source data and similarity scores

### 3. **Custom Queries**
1. Type question in custom query textarea
2. Click "Ask Question" button
3. Review AI-powered analysis
4. Copy results if needed

### 4. **Understanding Results**
1. Read AI analysis in blue-highlighted section
2. Review "Relevant Data Sources" for context
3. Check similarity scores for relevance
4. Use copy button to share insights

## Query Template Categories

### **Revenue Analysis Templates**
- Focus on financial performance and revenue metrics
- Help identify top-performing accounts and growth opportunities
- Provide industry and regional revenue comparisons

### **Account Health Templates**
- Assess customer relationship strength and engagement
- Identify at-risk accounts for proactive intervention
- Rank accounts by overall performance metrics

### **KPI Performance Templates**
- Analyze individual KPI performance across categories
- Identify trends and patterns in KPI data
- Compare performance across different KPI types

### **Industry & Regional Analysis**
- Compare performance across different industries
- Analyze geographic performance patterns
- Identify industry-specific opportunities

### **Strategic Insights**
- Get AI-powered strategic recommendations
- Identify growth opportunities in the data
- Receive actionable business insights

## Best Practices

### **For Users**
1. **Start with Templates**: Use pre-defined templates for common questions
2. **Be Specific**: Ask specific questions for better results
3. **Review Sources**: Always check the source data for context
4. **Iterate**: Refine queries based on initial results

### **For Developers**
1. **Error Handling**: Always handle API errors gracefully
2. **Loading States**: Show clear loading indicators
3. **Responsive Design**: Ensure mobile compatibility
4. **Accessibility**: Follow WCAG guidelines

## Future Enhancements

### **Planned Features**
- **Query History**: Save and reuse previous queries
- **Favorites**: Mark frequently used templates
- **Export Results**: Download analysis as PDF/Excel
- **Advanced Filters**: Filter results by date, category, etc.
- **Collaboration**: Share queries and results with team members

### **Integration Opportunities**
- **Dashboard Integration**: Embed insights into main dashboard
- **Alert System**: Set up alerts for specific query results
- **Scheduled Reports**: Automate regular analysis reports
- **API Access**: Allow external systems to query the RAG system

## Troubleshooting

### **Common Issues**
1. **Knowledge Base Not Built**: Click "Build Knowledge Base" button
2. **No Results**: Check if customer has data uploaded
3. **Slow Responses**: Large datasets may take longer to process
4. **API Errors**: Check network connection and try again

### **Error Messages**
- **"Failed to build knowledge base"**: Check backend connectivity
- **"Failed to execute query"**: Verify API endpoints are working
- **"No relevant information found"**: Try different query or check data

## Security Considerations

### **Data Privacy**
- All queries are customer-scoped using X-Customer-ID header
- No cross-customer data leakage
- Secure API communication over HTTPS

### **Access Control**
- Requires valid user session
- Customer-specific data isolation
- Role-based access control integration ready

## Performance Optimization

### **Frontend**
- Lazy loading of components
- Efficient state management
- Optimized re-renders
- Responsive image loading

### **Backend**
- Cached knowledge base building
- Efficient vector search
- Optimized API responses
- Connection pooling

This RAG Analysis UI makes advanced AI-powered data analysis accessible to all users, regardless of technical expertise, while providing powerful insights for business decision-making.
