#!/usr/bin/env python3
"""
Production API Manager
Manages API endpoints with zero-downtime deployment and multi-tenant support
"""

import os
import json
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
import threading
import time
import importlib
import inspect

class APIManager:
    """Production API Manager with hot-reload capabilities"""
    
    def __init__(self, app=None):
        self.app = app
        self.api_registry = {}
        self.tenant_apis = {}
        self.loaded_modules = {}
        self.reload_lock = threading.Lock()
        self.api_config_path = os.path.join(os.path.dirname(__file__), 'api_configs')
        
        # Create directories
        os.makedirs(self.api_config_path, exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(__file__), 'apis'), exist_ok=True)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
        # Register API management endpoints
        self._register_management_endpoints()
        
        # Load existing API configurations
        self._load_existing_configs()
    
    def _register_management_endpoints(self):
        """Register API management endpoints"""
        mgmt_bp = Blueprint('api_management', __name__)
        
        @mgmt_bp.route('/api/admin/apis', methods=['GET'])
        def list_apis():
            """List all registered APIs"""
            return jsonify({
                'apis': list(self.api_registry.keys()),
                'tenant_apis': {tenant: list(apis.keys()) for tenant, apis in self.tenant_apis.items()},
                'loaded_modules': list(self.loaded_modules.keys()),
                'timestamp': datetime.now().isoformat()
            })
        
        @mgmt_bp.route('/api/admin/apis/<api_name>', methods=['GET'])
        def get_api_info(api_name):
            """Get information about a specific API"""
            if api_name not in self.api_registry:
                return jsonify({'error': 'API not found'}), 404
            
            return jsonify(self.api_registry[api_name])
        
        @mgmt_bp.route('/api/admin/apis', methods=['POST'])
        def register_api():
            """Register a new API"""
            data = request.get_json()
            
            try:
                result = self.register_api(
                    name=data['name'],
                    version=data.get('version', '1.0.0'),
                    endpoints=data['endpoints'],
                    tenant_id=data.get('tenant_id'),
                    config=data.get('config', {})
                )
                
                return jsonify({
                    'status': 'success',
                    'message': f"API {data['name']} registered successfully",
                    'api_info': result,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 400
        
        @mgmt_bp.route('/api/admin/apis/<api_name>', methods=['PUT'])
        def update_api(api_name):
            """Update an existing API"""
            data = request.get_json()
            
            try:
                result = self.update_api(api_name, data)
                return jsonify({
                    'status': 'success',
                    'message': f"API {api_name} updated successfully",
                    'api_info': result,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 400
        
        @mgmt_bp.route('/api/admin/apis/<api_name>', methods=['DELETE'])
        def unregister_api(api_name):
            """Unregister an API"""
            try:
                result = self.unregister_api(api_name)
                return jsonify({
                    'status': 'success',
                    'message': f"API {api_name} unregistered successfully",
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 400
        
        @mgmt_bp.route('/api/admin/apis/reload', methods=['POST'])
        def reload_apis():
            """Reload all APIs"""
            try:
                result = self.reload_all_apis()
                return jsonify({
                    'status': 'success',
                    'message': 'All APIs reloaded successfully',
                    'reloaded': result['reloaded'],
                    'errors': result['errors'],
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @mgmt_bp.route('/api/admin/tenants/<tenant_id>/apis', methods=['GET'])
        def get_tenant_apis(tenant_id):
            """Get APIs for a specific tenant"""
            if tenant_id not in self.tenant_apis:
                return jsonify({'apis': [], 'message': 'No APIs found for tenant'})
            
            return jsonify({
                'tenant_id': tenant_id,
                'apis': list(self.tenant_apis[tenant_id].keys()),
                'timestamp': datetime.now().isoformat()
            })
        
        self.app.register_blueprint(mgmt_bp)
    
    def register_api(self, name: str, version: str, endpoints: List[Dict], 
                    tenant_id: Optional[str] = None, config: Dict = None) -> Dict:
        """Register a new API with hot-reload capability"""
        
        with self.reload_lock:
            api_key = f"{name}_v{version}"
            
            # Create API configuration
            api_config = {
                'name': name,
                'version': version,
                'endpoints': endpoints,
                'tenant_id': tenant_id,
                'config': config or {},
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            # Generate API module
            module_path = self._generate_api_module(api_key, endpoints, config)
            
            # Load the module
            try:
                module = self._load_module(module_path, api_key)
                blueprints = self._extract_blueprints(module)
                
                # Register blueprints with Flask
                for blueprint in blueprints:
                    self.app.register_blueprint(blueprint)
                
                # Store API info
                self.api_registry[api_key] = {
                    **api_config,
                    'module_path': module_path,
                    'blueprints': [bp.name for bp in blueprints],
                    'loaded_at': datetime.now().isoformat()
                }
                
                # Store in tenant-specific registry
                if tenant_id:
                    if tenant_id not in self.tenant_apis:
                        self.tenant_apis[tenant_id] = {}
                    self.tenant_apis[tenant_id][api_key] = self.api_registry[api_key]
                
                # Save configuration
                self._save_api_config(api_key, api_config)
                
                return self.api_registry[api_key]
                
            except Exception as e:
                # Cleanup on failure
                if api_key in self.api_registry:
                    del self.api_registry[api_key]
                raise Exception(f"Failed to register API {name}: {str(e)}")
    
    def update_api(self, api_name: str, update_data: Dict) -> Dict:
        """Update an existing API"""
        
        with self.reload_lock:
            if api_name not in self.api_registry:
                raise Exception(f"API {api_name} not found")
            
            # Update configuration
            api_info = self.api_registry[api_name]
            api_info.update(update_data)
            api_info['updated_at'] = datetime.now().isoformat()
            
            # Regenerate module if endpoints changed
            if 'endpoints' in update_data:
                module_path = self._generate_api_module(
                    api_name, 
                    update_data['endpoints'], 
                    api_info.get('config', {})
                )
                api_info['module_path'] = module_path
                
                # Reload module
                module = self._load_module(module_path, api_name)
                blueprints = self._extract_blueprints(module)
                
                # Update blueprints
                for blueprint in blueprints:
                    self.app.register_blueprint(blueprint)
            
            # Save updated configuration
            self._save_api_config(api_name, api_info)
            
            return api_info
    
    def unregister_api(self, api_name: str) -> Dict:
        """Unregister an API"""
        
        with self.reload_lock:
            if api_name not in self.api_registry:
                raise Exception(f"API {api_name} not found")
            
            api_info = self.api_registry[api_name]
            
            # Note: Flask doesn't support unregistering blueprints directly
            # In production, you might need to restart the app or use versioning
            
            # Remove from registries
            del self.api_registry[api_name]
            
            # Remove from tenant registry
            for tenant_id, tenant_apis in self.tenant_apis.items():
                if api_name in tenant_apis:
                    del tenant_apis[api_name]
            
            # Remove configuration file
            config_file = os.path.join(self.api_config_path, f"{api_name}.json")
            if os.path.exists(config_file):
                os.remove(config_file)
            
            return {'unregistered': api_name}
    
    def reload_all_apis(self) -> Dict:
        """Reload all registered APIs"""
        
        with self.reload_lock:
            reloaded = []
            errors = []
            
            for api_name, api_info in self.api_registry.items():
                try:
                    # Reload the module
                    module_path = api_info['module_path']
                    module = self._load_module(module_path, api_name)
                    
                    # Extract and re-register blueprints
                    blueprints = self._extract_blueprints(module)
                    for blueprint in blueprints:
                        self.app.register_blueprint(blueprint)
                    
                    reloaded.append(api_name)
                    
                except Exception as e:
                    errors.append(f"{api_name}: {str(e)}")
            
            return {
                'reloaded': reloaded,
                'errors': errors
            }
    
    def _generate_api_module(self, api_name: str, endpoints: List[Dict], config: Dict) -> str:
        """Generate API module from endpoint definitions"""
        
        module_content = f'''#!/usr/bin/env python3
"""
Auto-generated API module: {api_name}
Generated at: {datetime.now().isoformat()}
"""

from flask import Blueprint, request, jsonify
from extensions import db

{api_name}_api = Blueprint('{api_name}_api', __name__)

'''
        
        # Add configuration
        if config:
            module_content += f"""
# API Configuration
API_CONFIG = {json.dumps(config, indent=2)}

"""
        
        # Add endpoints
        for endpoint in endpoints:
            route = endpoint.get('route', f"/{endpoint['name']}")
            methods = endpoint.get('methods', ['GET'])
            handler_name = endpoint['name']
            handler_code = endpoint.get('handler', f'def {handler_name}(): return jsonify({{"message": "Hello from {handler_name}"}})')
            
            module_content += f'''
@_{api_name}_api.route('{route}', methods={methods})
{handler_code}

'''
        
        # Write module file
        module_path = os.path.join(os.path.dirname(__file__), 'apis', f'{api_name}.py')
        with open(module_path, 'w') as f:
            f.write(module_content)
        
        return module_path
    
    def _load_module(self, module_path: str, module_name: str):
        """Load a Python module dynamically"""
        
        import importlib.util
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        self.loaded_modules[module_name] = module
        return module
    
    def _extract_blueprints(self, module) -> List[Blueprint]:
        """Extract Blueprint objects from a module"""
        
        blueprints = []
        for name, obj in inspect.getmembers(module):
            if isinstance(obj, Blueprint):
                blueprints.append(obj)
        
        return blueprints
    
    def _save_api_config(self, api_name: str, config: Dict):
        """Save API configuration to file"""
        
        config_file = os.path.join(self.api_config_path, f"{api_name}.json")
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _load_existing_configs(self):
        """Load existing API configurations on startup"""
        
        for config_file in os.listdir(self.api_config_path):
            if config_file.endswith('.json'):
                try:
                    with open(os.path.join(self.api_config_path, config_file), 'r') as f:
                        config = json.load(f)
                    
                    api_name = config_file[:-5]  # Remove .json extension
                    self.api_registry[api_name] = config
                    
                    # Load the module
                    if 'module_path' in config and os.path.exists(config['module_path']):
                        module = self._load_module(config['module_path'], api_name)
                        blueprints = self._extract_blueprints(module)
                        
                        # Register blueprints
                        for blueprint in blueprints:
                            self.app.register_blueprint(blueprint)
                    
                except Exception as e:
                    print(f"❌ Failed to load config {config_file}: {e}")

# Usage example
def setup_production_api_manager(app):
    """Setup production API manager"""
    
    api_manager = APIManager(app)
    return api_manager

# Example API definition
EXAMPLE_API_DEFINITION = {
    "name": "example_api",
    "version": "1.0.0",
    "endpoints": [
        {
            "name": "get_data",
            "route": "/api/example/data",
            "methods": ["GET"],
            "handler": """
def get_data():
    return jsonify({
        "message": "Hello from example API",
        "timestamp": datetime.now().isoformat()
    })
"""
        },
        {
            "name": "post_data",
            "route": "/api/example/data",
            "methods": ["POST"],
            "handler": """
def post_data():
    data = request.get_json()
    return jsonify({
        "received": data,
        "timestamp": datetime.now().isoformat()
    })
"""
        }
    ],
    "config": {
        "rate_limit": "100/hour",
        "auth_required": True
    }
}
