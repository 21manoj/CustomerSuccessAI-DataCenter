from flask import Flask, request, jsonify
from flask_migrate import Migrate
from flask_cors import CORS
from extensions import db
import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Database configuration - use DATABASE_URL from environment if available
database_url = os.getenv('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
elif os.path.exists('/app/instance'):
    # Production/Docker path
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/instance/app.db'
else:
    # Local development - default path
    basedir = os.path.abspath(os.path.dirname(__file__))
    instance_path = os.path.join(os.path.dirname(basedir), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

CORS(app)

db.init_app(app)
migrate = Migrate(app, db)

# Import models
import models
from models import Customer, User

# Import API blueprints
from auth_api import auth_api
from users_api import users_api

# Register blueprints
app.register_blueprint(auth_api)
app.register_blueprint(users_api)

@app.route('/')
def home():
    """Root endpoint for health check and timestamp."""
    local_tz = datetime.datetime.now().astimezone().tzinfo
    now = datetime.datetime.now(local_tz).isoformat()
    return f"Backend is running! Timestamp: {now}"

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.datetime.now().isoformat(),
        'uptime': 'running'
    })

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Simple test endpoint."""
    return jsonify({
        'status': 'success',
        'message': 'Backend is working correctly',
        'timestamp': datetime.datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('FLASK_RUN_PORT', os.getenv('PORT', 8001)))
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug, host=host, port=port)

