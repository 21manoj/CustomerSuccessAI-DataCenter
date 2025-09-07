# KPI Dashboard

A comprehensive SaaS KPI dashboard with Excel upload, versioning, and AI-powered analysis capabilities.

## Features

### 📊 KPI Management
- **Excel Upload**: Upload Excel files with KPI data
- **Automatic Parsing**: Intelligently parses Excel sheets and extracts KPI information
- **Real-time Editing**: Edit KPI values directly in the dashboard
- **Category Grouping**: KPIs are automatically grouped by category

### 🔄 Versioning System
- **Automatic Versioning**: Each upload creates a new version
- **Version History**: View and switch between different upload versions
- **Upload Tracking**: Track upload dates, file names, and KPI counts

### 🤖 AI-Powered Analysis (RAG)
- **Natural Language Queries**: Ask questions about your KPIs in plain English
- **Semantic Search**: Find relevant KPIs using AI-powered search
- **Intelligent Insights**: Get automated recommendations and insights
- **Comprehensive Analysis**: Analyze all KPIs with detailed statistics

## Quick Start

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python3 -m backend.add_default_data  # Add default customer/user
flask run
```

### Frontend Setup
```bash
npm install
npm start
```

## API Endpoints

### Upload & Versioning
- `POST /api/upload` - Upload Excel file
- `GET /api/uploads` - Get upload history
- `GET /api/upload/<id>` - Get specific upload details
- `GET /api/kpis/<upload_id>` - Get KPIs for an upload

### KPI Management
- `PATCH /api/kpi/<kpi_id>` - Edit a KPI
- `GET /api/download/<upload_id>` - Download original Excel file

### AI Analysis (RAG)
- `POST /api/rag/query` - Query KPIs using natural language
- `POST /api/rag/analyze` - Get comprehensive analysis

## Example RAG Queries

- "Show me high-impact KPIs"
- "What are the measurement frequencies?"
- "Find KPIs with high weight"
- "Which KPIs are in the Business Outcomes category?"
- "Show me critical KPIs"

## Technology Stack

- **Frontend**: React, TypeScript, Tailwind CSS
- **Backend**: Flask, SQLAlchemy, PostgreSQL
- **AI/ML**: scikit-learn, TF-IDF vectorization, cosine similarity
- **Database**: PostgreSQL with Neon

## Data Structure

The system expects Excel files with:
- First sheet: Ignored (metadata)
- Middle sheets: KPI data (one category per sheet)
- Last sheet: Ignored (rollup/summary)

Each KPI sheet should have columns:
- Health Score Component
- Weight
- Data
- Source Review
- KPI/Parameter
- Impact level
- Measurement Frequency

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License 