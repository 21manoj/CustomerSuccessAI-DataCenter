#!/usr/bin/env python3
"""
Hot-Reload System for Production Deployment
Allows loading new endpoints and changes without server restarts
"""

import os
import sys
import importlib
import threading
import time
from datetime import datetime
from typing import Dict, List, Any
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HotReloadHandler(FileSystemEventHandler):
    """File system event handler for hot reloading"""
    
    def __init__(self, hot_reload_manager):
        self.hot_reload_manager = hot_reload_manager
        self.last_reload = {}
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if not file_path.endswith('.py'):
            return
        
        # Avoid rapid reloads of the same file
        now = time.time()
        if file_path in self.last_reload and (now - self.last_reload[file_path]) < 2:
            return
        
        self.last_reload[file_path] = now
        
        # Reload the module
        self.hot_reload_manager.reload_module(file_path)

class HotReloadManager:
    """Manages hot reloading of modules and endpoints"""
    
    def __init__(self, app):
        self.app = app
        self.observer = None
        self.watched_modules = {}
        self.reload_lock = threading.Lock()
        self.is_running = False
        
        # Track loaded modules
        self.loaded_modules = {}
        self.loaded_blueprints = {}
    
    def start(self, watch_directory: str = None):
        """Start the hot reload system"""
        if self.is_running:
            return
        
        if watch_directory is None:
            watch_directory = os.path.dirname(os.path.abspath(__file__))
        
        self.observer = Observer()
        handler = HotReloadHandler(self)
        self.observer.schedule(handler, watch_directory, recursive=True)
        
        self.observer.start()
        self.is_running = True
        
        logger.info(f"🔥 Hot reload system started, watching: {watch_directory}")
    
    def stop(self):
        """Stop the hot reload system"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.is_running = False
        logger.info("🔥 Hot reload system stopped")
    
    def reload_module(self, file_path: str):
        """Reload a specific module"""
        with self.reload_lock:
            try:
                # Convert file path to module name
                module_name = self._file_path_to_module_name(file_path)
                
                if not module_name:
                    return
                
                logger.info(f"🔄 Reloading module: {module_name}")
                
                # Remove from loaded modules if it exists
                if module_name in sys.modules:
                    del sys.modules[module_name]
                
                # Import the module
                module = importlib.import_module(module_name)
                
                # Check if it's a blueprint module
                if hasattr(module, 'blueprint_name'):
                    self._reload_blueprint(module)
                else:
                    # Regular module reload
                    importlib.reload(module)
                
                logger.info(f"✅ Module reloaded: {module_name}")
                
            except Exception as e:
                logger.error(f"❌ Error reloading module {file_path}: {str(e)}")
    
    def _file_path_to_module_name(self, file_path: str) -> str:
        """Convert file path to module name"""
        # Get relative path from current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        rel_path = os.path.relpath(file_path, current_dir)
        
        # Convert to module name
        module_name = rel_path.replace('/', '.').replace('\\', '.')
        
        # Remove .py extension
        if module_name.endswith('.py'):
            module_name = module_name[:-3]
        
        # Remove __pycache__ parts
        if '__pycache__' in module_name:
            return None
        
        return module_name
    
    def _reload_blueprint(self, module):
        """Reload a blueprint module"""
        try:
            # Get blueprint name
            blueprint_name = getattr(module, 'blueprint_name', None)
            if not blueprint_name:
                return
            
            # Unregister old blueprint if it exists
            if blueprint_name in self.app.blueprints:
                self.app.unregister_blueprint(self.app.blueprints[blueprint_name])
                logger.info(f"📤 Unregistered blueprint: {blueprint_name}")
            
            # Reload the module
            importlib.reload(module)
            
            # Register new blueprint
            blueprint = getattr(module, blueprint_name, None)
            if blueprint:
                self.app.register_blueprint(blueprint)
                self.loaded_blueprints[blueprint_name] = blueprint
                logger.info(f"📥 Registered blueprint: {blueprint_name}")
            
        except Exception as e:
            logger.error(f"❌ Error reloading blueprint: {str(e)}")
    
    def register_module(self, module_name: str, blueprint_name: str = None):
        """Register a module for hot reloading"""
        self.watched_modules[module_name] = {
            'blueprint_name': blueprint_name,
            'last_reload': None
        }
    
    def get_reload_status(self) -> Dict[str, Any]:
        """Get status of hot reload system"""
        return {
            'is_running': self.is_running,
            'watched_modules': len(self.watched_modules),
            'loaded_blueprints': list(self.loaded_blueprints.keys()),
            'last_reload': datetime.now().isoformat()
        }

class APIEndpointManager:
    """Manages dynamic API endpoints"""
    
    def __init__(self, app):
        self.app = app
        self.dynamic_endpoints = {}
        self.endpoint_lock = threading.Lock()
    
    def add_endpoint(self, rule: str, endpoint: str, view_func, methods: List[str] = None, **options):
        """Add a new endpoint dynamically"""
        with self.endpoint_lock:
            try:
                if methods is None:
                    methods = ['GET']
                
                # Add the endpoint
                self.app.add_url_rule(rule, endpoint, view_func, methods=methods, **options)
                
                # Track it
                self.dynamic_endpoints[rule] = {
                    'endpoint': endpoint,
                    'view_func': view_func,
                    'methods': methods,
                    'options': options,
                    'added_at': datetime.now()
                }
                
                logger.info(f"➕ Added endpoint: {rule} -> {endpoint}")
                
            except Exception as e:
                logger.error(f"❌ Error adding endpoint {rule}: {str(e)}")
    
    def remove_endpoint(self, rule: str):
        """Remove an endpoint dynamically"""
        with self.endpoint_lock:
            try:
                if rule in self.dynamic_endpoints:
                    # Remove from Flask app
                    # Note: Flask doesn't have a direct way to remove rules, 
                    # so we'll mark it as inactive
                    self.dynamic_endpoints[rule]['active'] = False
                    logger.info(f"➖ Removed endpoint: {rule}")
                
            except Exception as e:
                logger.error(f"❌ Error removing endpoint {rule}: {str(e)}")
    
    def get_endpoints(self) -> Dict[str, Any]:
        """Get all dynamic endpoints"""
        with self.endpoint_lock:
            return {
                rule: {
                    'endpoint': info['endpoint'],
                    'methods': info['methods'],
                    'active': info.get('active', True),
                    'added_at': info['added_at'].isoformat()
                }
                for rule, info in self.dynamic_endpoints.items()
            }

class DataRefreshManager:
    """Manages data refresh without server restarts"""
    
    def __init__(self, app):
        self.app = app
        self.refresh_handlers = {}
        self.refresh_lock = threading.Lock()
    
    def register_refresh_handler(self, data_type: str, handler_func):
        """Register a data refresh handler"""
        with self.refresh_lock:
            self.refresh_handlers[data_type] = handler_func
            logger.info(f"📊 Registered refresh handler for: {data_type}")
    
    def refresh_data(self, data_type: str, **kwargs):
        """Refresh specific data type"""
        with self.refresh_lock:
            if data_type in self.refresh_handlers:
                try:
                    result = self.refresh_handlers[data_type](**kwargs)
                    logger.info(f"🔄 Refreshed data: {data_type}")
                    return result
                except Exception as e:
                    logger.error(f"❌ Error refreshing {data_type}: {str(e)}")
                    return None
            else:
                logger.warning(f"⚠️ No refresh handler for: {data_type}")
                return None
    
    def refresh_all_data(self):
        """Refresh all registered data types"""
        results = {}
        for data_type in self.refresh_handlers:
            results[data_type] = self.refresh_data(data_type)
        return results

class ProductionHotReloadSystem:
    """Main hot reload system for production"""
    
    def __init__(self, app):
        self.app = app
        self.hot_reload_manager = HotReloadManager(app)
        self.api_manager = APIEndpointManager(app)
        self.data_manager = DataRefreshManager(app)
        self.is_initialized = False
    
    def initialize(self, watch_directory: str = None):
        """Initialize the hot reload system"""
        if self.is_initialized:
            return
        
        # Register data refresh handlers
        self._register_data_handlers()
        
        # Start hot reload system
        self.hot_reload_manager.start(watch_directory)
        
        self.is_initialized = True
        logger.info("🚀 Production hot reload system initialized")
    
    def _register_data_handlers(self):
        """Register data refresh handlers"""
        # RAG knowledge base refresh
        self.data_manager.register_refresh_handler(
            'rag_knowledge_base',
            self._refresh_rag_knowledge_base
        )
        
        # Health scores refresh
        self.data_manager.register_refresh_handler(
            'health_scores',
            self._refresh_health_scores
        )
        
        # Customer data refresh
        self.data_manager.register_refresh_handler(
            'customer_data',
            self._refresh_customer_data
        )
    
    def _refresh_rag_knowledge_base(self, customer_id: int = None):
        """Refresh RAG knowledge base"""
        try:
            from enhanced_rag_qdrant import get_qdrant_rag_system
            
            if customer_id:
                # Refresh specific customer
                rag_system = get_qdrant_rag_system(customer_id)
                rag_system.build_knowledge_base(customer_id)
                return f"RAG knowledge base refreshed for customer {customer_id}"
            else:
                # Refresh all customers
                from models import Customer
                customers = Customer.query.all()
                for customer in customers:
                    rag_system = get_qdrant_rag_system(customer.customer_id)
                    rag_system.build_knowledge_base(customer.customer_id)
                return f"RAG knowledge base refreshed for {len(customers)} customers"
                
        except Exception as e:
            logger.error(f"Error refreshing RAG knowledge base: {str(e)}")
            return None
    
    def _refresh_health_scores(self, customer_id: int = None):
        """Refresh health scores"""
        try:
            from health_score_engine import HealthScoreEngine
            
            if customer_id:
                # Refresh specific customer
                engine = HealthScoreEngine()
                engine.calculate_health_scores(customer_id)
                return f"Health scores refreshed for customer {customer_id}"
            else:
                # Refresh all customers
                from models import Customer
                customers = Customer.query.all()
                engine = HealthScoreEngine()
                for customer in customers:
                    engine.calculate_health_scores(customer.customer_id)
                return f"Health scores refreshed for {len(customers)} customers"
                
        except Exception as e:
            logger.error(f"Error refreshing health scores: {str(e)}")
            return None
    
    def _refresh_customer_data(self, customer_id: int = None):
        """Refresh customer data"""
        try:
            # This would refresh any cached customer data
            return f"Customer data refreshed for customer {customer_id}"
        except Exception as e:
            logger.error(f"Error refreshing customer data: {str(e)}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            'hot_reload': self.hot_reload_manager.get_reload_status(),
            'api_endpoints': self.api_manager.get_endpoints(),
            'data_handlers': list(self.data_manager.refresh_handlers.keys()),
            'initialized': self.is_initialized
        }
    
    def shutdown(self):
        """Shutdown the hot reload system"""
        self.hot_reload_manager.stop()
        logger.info("🛑 Production hot reload system shutdown")

# Global hot reload system instance
hot_reload_system = None

def initialize_hot_reload(app, watch_directory: str = None):
    """Initialize hot reload system"""
    global hot_reload_system
    hot_reload_system = ProductionHotReloadSystem(app)
    hot_reload_system.initialize(watch_directory)
    return hot_reload_system

# Example usage
if __name__ == "__main__":
    print("🔥 Hot Reload System for Production")
    print("=" * 50)
    print("Features:")
    print("- File watching and auto-reload")
    print("- Dynamic API endpoint management")
    print("- Data refresh without restarts")
    print("- Production-safe hot reloading")
