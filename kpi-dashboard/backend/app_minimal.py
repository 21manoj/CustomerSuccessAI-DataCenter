from flask import Flask
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
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
CORS(app)

# Import models
import models

# Import only essential APIs
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

# Basic health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'version': '3.0.0',
        'timestamp': datetime.datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5059, debug=False)
