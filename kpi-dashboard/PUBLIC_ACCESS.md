# 🌐 KPI Dashboard - Public Access

## Quick Start

### Option 1: Frontend Only (Recommended for Testing)
```bash
./expose-public.sh
```

### Option 2: Frontend + Backend (For API Testing)
```bash
./expose-full.sh
```

## 🔐 Login Credentials

- **Email**: `test@test.com`
- **Password**: `test123`

## 📊 Available Data

- **25 Accounts** with revenue data
- **1,475 KPIs** across all accounts
- **RAG Analysis** capabilities
- **Health Scores** and analytics
- **Time Series Data** for monthly analysis

## 🎯 Features to Test

### 1. Dashboard Overview
- View account health scores
- KPI category breakdowns
- Revenue analytics

### 2. RAG Analysis
- Ask questions like:
  - "Which accounts have the highest revenue?"
  - "What are the top performing KPIs?"
  - "Show me monthly revenue trends"

### 3. Data Management
- Upload new KPI data
- View reference ranges
- Export reports

## 🔧 API Endpoints (if backend exposed)

- **Health Status**: `https://[ngrok-url]/api/health-status/kpis`
- **Accounts**: `https://[ngrok-url]/api/accounts`
- **KPIs**: `https://[ngrok-url]/api/kpis/customer/all`
- **RAG Query**: `https://[ngrok-url]/api/rag-qdrant/query`

## 📱 Mobile Friendly

The application is fully responsive and works on:
- Desktop browsers
- Tablets
- Mobile phones

## ⚠️ Important Notes

1. **Temporary URLs**: ngrok URLs change each time you restart
2. **Free Tier**: Limited to 1 concurrent tunnel (upgrade for more)
3. **Security**: This is for testing only - not for production use
4. **Performance**: May be slower than local access

## 🆘 Troubleshooting

### If ngrok fails:
1. Check if Docker containers are running: `docker-compose ps`
2. Restart containers: `docker-compose restart`
3. Check ngrok status: `ngrok version`

### If login fails:
- Make sure you're using: `test@test.com` / `test123`
- Check if the backend is responding

## 📞 Support

For issues or questions, contact the development team.

---

**Happy Testing! 🚀**
