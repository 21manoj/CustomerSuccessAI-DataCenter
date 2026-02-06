import { Router } from 'express';
import { authRouter } from './auth';
import { usersRouter } from './users';

export const apiRouter = Router();

// API version prefix
apiRouter.get('/', (req, res) => {
  res.json({
    message: 'API v1',
    version: '1.0.0',
    endpoints: {
      auth: '/api/auth',
      users: '/api/users'
    }
  });
});

// Route handlers
apiRouter.use('/auth', authRouter);
apiRouter.use('/users', usersRouter);

