# New App - Flask Backend + React Frontend

A new full-stack application built following the patterns from kpi-dashboard.

## Project Structure

```
new-app/
├── backend/          # Flask backend server
│   ├── app.py       # Main Flask application
│   ├── models.py    # SQLAlchemy models
│   ├── extensions.py # Database extensions
│   ├── auth_api.py  # Authentication endpoints
│   └── users_api.py # User management endpoints
├── frontend/        # React TypeScript frontend
│   └── src/
│       ├── App.tsx
│       └── components/
└── README.md
```

## Tech Stack

### Backend
- **Framework**: Flask
- **Database**: SQLite (can be upgraded to PostgreSQL)
- **ORM**: SQLAlchemy
- **Migrations**: Flask-Migrate
- **CORS**: Flask-CORS

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Routing**: React Router
- **Build Tool**: Create React App

## Getting Started

### Backend Setup

1. Navigate to backend directory:
```bash
cd new-app/backend
```

2. Create virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

5. Run the server:
```bash
python3 app.py
```

Backend will run on `http://localhost:8001`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd new-app/frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm start
```

Frontend will run on `http://localhost:3000` (proxies API requests to backend on port 8001)

## API Endpoints

### Authentication (`/api/auth`)
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user

### Users (`/api/users`)
- `GET /api/users` - Get all users
- `GET /api/users/:id` - Get user by ID
- `PUT /api/users/:id` - Update user
- `DELETE /api/users/:id` - Delete user

### Health
- `GET /api/health` - Health check
- `GET /api/test` - Test endpoint

## Database Models

- **Customer**: Customer/organization information
- **User**: User accounts linked to customers

## Next Steps

- [ ] Add authentication middleware (JWT or session-based)
- [ ] Add input validation
- [ ] Add error handling improvements
- [ ] Add database migrations for production
- [ ] Add environment configuration
- [ ] Add testing setup
- [ ] Upgrade to PostgreSQL for production

## Notes

This application follows the same patterns as the kpi-dashboard project:
- Flask backend structure
- SQLAlchemy models
- Blueprint-based API organization
- React frontend with TypeScript
- Similar authentication flow

