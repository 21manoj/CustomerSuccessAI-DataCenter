# Minimal script to initialize the SQLite database for local development
import os
from flask import Flask
from extensions import db
from flask_session import Session
import models  # noqa: ensure models are registered

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'kpi_dashboard.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db

db.init_app(app)

# Initialize Flask-Session to create sessions table
Session(app)

with app.app_context():
    db.create_all()
    print(f"Database initialized at {DB_PATH}")
    print("✅ Sessions table created (if needed)")

