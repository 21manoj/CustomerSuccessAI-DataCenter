# Create .env file

Create a `.env` file in the `backend` directory with the following content:

```
FLASK_APP=app.py
FLASK_ENV=development
DATABASE_URL=sqlite:///instance/app.db
SECRET_KEY=your-secret-key-change-in-production
PORT=8001
```

You can create it by running:
```bash
cd new-app/backend
cat > .env << 'EOF'
FLASK_APP=app.py
FLASK_ENV=development
DATABASE_URL=sqlite:///instance/app.db
SECRET_KEY=your-secret-key-change-in-production
PORT=8001
EOF
```

Or manually create the file with the content above.

