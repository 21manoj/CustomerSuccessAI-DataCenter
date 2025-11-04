#!/usr/bin/env python3
"""
Hot Reload API System for Production
Enables dynamic loading of new API endpoints without server restart
"""

import os
import sys
import importlib
import inspect
from typing import Dict, Any, List
from flask import Blueprint, current_app
from auth_middleware import get_current_customer_id, get_current_user_id
import threading
import time
from datetime import datetime

class HotReloadManager:
    """Manages hot reloading of API endpoints in production"""
    
    def __init__(self, app=None):
        self.app = app
        self.loaded_modules = {}
        self.blueprint_registry = {}
        self.reload_lock = threading.Lock()
        self.watch_directory = os.path.join(os.path.dirname(__file__), 'apis')
        
        # Create APIs directory if it doesn't exist
        os.makedirs(self.watch_directory, exist_ok=True)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
        # Register hot reload endpoints
        hot_reload_bp = Blueprint('hot_reload', __name__)
        
        @hot_reload_bp.route('/api/admin/reload-apis', methods=['POST'])
        def reload_apis():
            """Reload all API modules"""
            try:
                result = self.reload_all_apis()
                return {
                    'status': 'success',
                    'message': 'APIs reloaded successfully',
                    'reloaded_modules': result['reloaded'],
                    'errors': result['errors'],
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                return {'error': f'Failed to reload APIs: {str(e)}'}, 500
        
        @hot_reload_bp.route('/api/admin/load-module', methods=['POST'])
        def load_module():
            """Load a specific API module"""
            data = request.get_json()
            module_name = data.get('module_name')
            
            if not module_name:
                return {'error': 'module_name is required'}, 400
            
            try:
                result = self.load_api_module(module_name)
                return {
                    'status': 'success',
                    'message': f'Module {module_name} loaded successfully',
                    'blueprints': result['blueprints'],
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                return {'error': f'Failed to load module {module_name}: {str(e)}'}, 500
        
        @hot_reload_bp.route('/api/admin/unload-module', methods=['POST'])
        def unload_module():
            """Unload a specific API module"""
            data = request.get_json()
            module_name = data.get('module_name')
            
            if not module_name:
                return {'error': 'module_name is required'}, 400
            
            try:
                result = self.unload_api_module(module_name)
                return {
                    'status': 'success',
                    'message': f'Module {module_name} unloaded successfully',
                    'unregistered_blueprints': result['blueprints'],
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                return {'error': f'Failed to unload module {module_name}: {str(e)}'}, 500
        
        @hot_reload_bp.route('/api/admin/loaded-modules', methods=['GET'])
        def get_loaded_modules():
            """Get list of loaded modules and their blueprints"""
            return {
                'loaded_modules': list(self.loaded_modules.keys()),
                'registered_blueprints': list(self.blueprint_registry.keys()),
                'timestamp': datetime.now().isoformat()
            }
        
        app.register_blueprint(hot_reload_bp)
    
    def load_api_module(self, module_name: str) -> Dict[str, Any]:
        """Load a specific API module dynamically"""
        with self.reload_lock:
            try:
                # Import the module
                if module_name in sys.modules:
                    module = importlib.reload(sys.modules[module_name])
                else:
                    module = importlib.import_module(module_name)
                
                # Find all Blueprint objects in the module
                blueprints = []
                for name, obj in inspect.getmembers(module):
                    if isinstance(obj, Blueprint):
                        # Register blueprint if not already registered
                        if obj.name not in self.blueprint_registry:
                            self.app.register_blueprint(obj)
                            self.blueprint_registry[obj.name] = obj
                            blueprints.append(obj.name)
                
                # Store module info
                self.loaded_modules[module_name] = {
                    'module': module,
                    'blueprints': blueprints,
                    'loaded_at': datetime.now().isoformat()
                }
                
                return {
                    'blueprints': blueprints,
                    'module_name': module_name
                }
                
            except Exception as e:
                raise Exception(f"Failed to load module {module_name}: {str(e)}")
    
    def unload_api_module(self, module_name: str) -> Dict[str, Any]:
        """Unload a specific API module"""
        with self.reload_lock:
            if module_name not in self.loaded_modules:
                raise Exception(f"Module {module_name} is not loaded")
            
            module_info = self.loaded_modules[module_name]
            unregistered_blueprints = []
            
            # Unregister blueprints
            for blueprint_name in module_info['blueprints']:
                if blueprint_name in self.blueprint_registry:
                    # Note: Flask doesn't have a direct way to unregister blueprints
                    # In production, you might need to restart the app or use a more sophisticated approach
                    del self.blueprint_registry[blueprint_name]
                    unregistered_blueprints.append(blueprint_name)
            
            # Remove from loaded modules
            del self.loaded_modules[module_name]
            
            return {
                'blueprints': unregistered_blueprints,
                'module_name': module_name
            }
    
    def reload_all_apis(self) -> Dict[str, Any]:
        """Reload all API modules"""
        with self.reload_lock:
            reloaded = []
            errors = []
            
            # Get all Python files in the APIs directory
            api_files = [f for f in os.listdir(self.watch_directory) 
                        if f.endswith('.py') and not f.startswith('__')]
            
            for file_name in api_files:
                module_name = f"apis.{file_name[:-3]}"  # Remove .py extension
                
                try:
                    result = self.load_api_module(module_name)
                    reloaded.append(module_name)
                except Exception as e:
                    errors.append(f"{module_name}: {str(e)}")
            
            return {
                'reloaded': reloaded,
                'errors': errors
            }
    
    def auto_reload_on_change(self, check_interval: int = 5):
        """Auto-reload APIs when files change (development mode)"""
        def watch_files():
            last_modified = {}
            
            while True:
                try:
                    current_modified = {}
                    
                    # Check all Python files in APIs directory
                    for file_name in os.listdir(self.watch_directory):
                        if file_name.endswith('.py'):
                            file_path = os.path.join(self.watch_directory, file_name)
                            current_modified[file_name] = os.path.getmtime(file_path)
                    
                    # Check for changes
                    for file_name, mtime in current_modified.items():
                        if file_name not in last_modified or last_modified[file_name] != mtime:
                            print(f"🔄 File {file_name} changed, reloading APIs...")
                            try:
                                self.reload_all_apis()
                                print("✅ APIs reloaded successfully")
                            except Exception as e:
                                print(f"❌ Failed to reload APIs: {e}")
                    
                    last_modified = current_modified
                    time.sleep(check_interval)
                    
                except Exception as e:
                    print(f"❌ Error in auto-reload watcher: {e}")
                    time.sleep(check_interval)
        
        # Start watcher in background thread
        watcher_thread = threading.Thread(target=watch_files, daemon=True)
        watcher_thread.start()
        return watcher_thread

# Production-ready API loading system
class ProductionAPILoader:
    """Production-ready API loading system with zero-downtime deployment"""
    
    def __init__(self, app):
        self.app = app
        self.api_versions = {}
        self.current_version = None
    
    def load_api_version(self, version: str, module_path: str) -> bool:
        """Load a new API version without downtime"""
        try:
            # Import the new version
            spec = importlib.util.spec_from_file_location(f"api_v{version}", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find blueprints in the new version
            new_blueprints = []
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, Blueprint):
                    # Register with versioned name
                    versioned_name = f"{obj.name}_v{version}"
                    obj.name = versioned_name
                    self.app.register_blueprint(obj)
                    new_blueprints.append(versioned_name)
            
            # Store version info
            self.api_versions[version] = {
                'module': module,
                'blueprints': new_blueprints,
                'loaded_at': datetime.now().isoformat()
            }
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load API version {version}: {e}")
            return False
    
    def switch_to_version(self, version: str) -> bool:
        """Switch to a specific API version"""
        if version not in self.api_versions:
            return False
        
        self.current_version = version
        return True
    
    def get_available_versions(self) -> List[str]:
        """Get list of available API versions"""
        return list(self.api_versions.keys())

# Usage example for production deployment
def setup_production_hot_reload(app):
    """Setup hot reload system for production"""
    
    # Initialize hot reload manager
    hot_reload_manager = HotReloadManager(app)
    
    # Initialize production API loader
    production_loader = ProductionAPILoader(app)
    
    # Add production loader to app context
    app.production_loader = production_loader
    
    # Add hot reload manager to app context
    app.hot_reload_manager = hot_reload_manager
    
    return hot_reload_manager, production_loader

# Utility function to create API modules dynamically
def create_api_module(module_name: str, endpoints: Dict[str, Any]) -> str:
    """Create an API module dynamically from endpoint definitions"""
    
    module_content = f'''#!/usr/bin/env python3
"""
Auto-generated API module: {module_name}
Generated at: {datetime.now().isoformat()}
"""

from flask import Blueprint, request, jsonify
from extensions import db

{module_name}_api = Blueprint('{module_name}_api', __name__)

'''
    
    # Add endpoints
    for endpoint_name, endpoint_config in endpoints.items():
        route = endpoint_config.get('route', f'/{endpoint_name}')
        methods = endpoint_config.get('methods', ['GET'])
        handler = endpoint_config.get('handler', f'def {endpoint_name}(): return jsonify({{"message": "Hello from {endpoint_name}"}})')
        
        module_content += f'''
@_{module_name}_api.route('{route}', methods={methods})
{handler}
'''
    
    # Write module file
    module_path = os.path.join(os.path.dirname(__file__), 'apis', f'{module_name}.py')
    with open(module_path, 'w') as f:
        f.write(module_content)
    
    return module_path
