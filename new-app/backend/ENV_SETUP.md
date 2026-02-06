# .env File Setup

Create a `.env` file in the `backend` directory with the following content (lines 1-8 from docker.env):

```env
# Docker Environment Configuration
# Copy this to .env in backend/ directory

# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=8001
```

You can also add:
```env
DATABASE_URL=sqlite:///instance/app.db
SECRET_KEY=your-secret-key-change-in-production
```

The app will now read:
- `FLASK_RUN_PORT` for the port (defaults to 8001)
- `FLASK_RUN_HOST` for the host (defaults to 0.0.0.0)
- `FLASK_ENV` for debug mode (development = debug=True)

