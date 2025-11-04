from flask import Flask
from auth_middleware import get_current_customer_id, get_current_user_id
from flask_migrate import Migrate
from flask_cors import CORS
from extensions import db
from flask import request, jsonify
import datetime
import pytz
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Use local path for development, Docker path for production
import os
if os.path.exists('/app/instance'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/instance/kpi_dashboard.db'
else:
    # Local development
    basedir = os.path.abspath(os.path.dirname(__file__))
    instance_path = os.path.join(os.path.dirname(basedir), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'kpi_dashboard.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

CORS(app)

db.init_app(app)
migrate = Migrate(app, db)

# Import models
import models
from models import Customer, User, Account, KPIUpload, KPI, CustomerConfig

# Import only essential APIs for V3
from kpi_api import kpi_api
from corporate_api import corporate_api
from playbook_triggers_api import playbook_triggers_api
from playbook_execution_api import playbook_execution_api
from playbook_reports_api import playbook_reports_api
from playbook_recommendations_api import playbook_recommendations_api
from feature_toggle_api import feature_toggle_api
from registration_api import registration_api

# Register blueprints
app.register_blueprint(kpi_api)
app.register_blueprint(corporate_api)
app.register_blueprint(playbook_triggers_api)
app.register_blueprint(playbook_execution_api)
app.register_blueprint(playbook_reports_api)
app.register_blueprint(playbook_recommendations_api)
app.register_blueprint(feature_toggle_api)
app.register_blueprint(registration_api)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'version': '3.0.0',
        'timestamp': datetime.datetime.utcnow().isoformat()
    })

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate a user and return session info."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid email or password'}), 401
    return jsonify({
        'customer_id': user.customer_id,
        'user_id': user.user_id,
        'user_name': user.user_name,
        'email': user.email
    }), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5059, debug=False)