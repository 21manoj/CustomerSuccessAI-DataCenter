# Full-Stack Application

A modern full-stack application with React frontend and Express.js backend, both built with TypeScript.

## Project Structure

```
.
├── server/          # Backend Express.js server
├── client/          # Frontend React application
└── README.md
```

## Tech Stack

### Backend
- **Runtime**: Node.js 18+
- **Framework**: Express.js
- **Language**: TypeScript
- **Security**: Helmet, CORS, Rate Limiting
- **Development**: tsx (TypeScript execution)

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **Routing**: React Router
- **HTTP Client**: Axios

## Getting Started

### Prerequisites

- Node.js 18 or higher
- npm or yarn

### Backend Setup

1. Navigate to the server directory:
```bash
cd server
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

4. Update `.env` with your configuration:
```env
PORT=5000
NODE_ENV=development
CORS_ORIGIN=http://localhost:5173
JWT_SECRET=your-secret-key-change-in-production
JWT_EXPIRES_IN=7d
```

5. Start the development server:
```bash
npm run dev
```

The backend will be running on `http://localhost:5000`

### Frontend Setup

1. Navigate to the client directory:
```bash
cd client
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be running on `http://localhost:5173`

## Available Scripts

### Backend (server/)

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

### Frontend (client/)

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user

### Users
- `GET /api/users` - Get all users
- `GET /api/users/:id` - Get user by ID
- `PUT /api/users/:id` - Update user
- `DELETE /api/users/:id` - Delete user

### Health Check
- `GET /health` - Server health check

## Development

The frontend is configured to proxy API requests to the backend during development. Make sure both servers are running:

1. Start backend: `cd server && npm run dev`
2. Start frontend: `cd client && npm run dev`

## Production Build

### Backend
```bash
cd server
npm run build
npm start
```

### Frontend
```bash
cd client
npm run build
# Serve the dist/ directory with a static file server
```

## Next Steps

- [ ] Add database integration (PostgreSQL/MongoDB)
- [ ] Implement JWT authentication middleware
- [ ] Add input validation
- [ ] Set up testing (Jest, React Testing Library)
- [ ] Add environment-specific configurations
- [ ] Set up CI/CD pipeline
- [ ] Add Docker configuration
- [ ] Implement error logging and monitoring

## License

MIT

