#!/usr/bin/env python3
"""
Enhanced Flask App with Feature Toggles and Hot Reload
Production-ready app with safe feature deployment
"""

from flask import Flask, jsonify
from extensions import db
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import feature toggles
from feature_toggles import feature_toggles, is_feature_enabled, FeatureToggle

# Import hot reload system
from hot_reload_system import initialize_hot_reload

def create_app():
    """Create Flask app with feature toggles and hot reload"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('config.Config')
    
    # Initialize extensions
    db.init_app(app)
    
    # Register core blueprints (always enabled)
    from upload_api import upload_api
    from kpi_api import kpi_api
    from corporate_api import corporate_api
    from health_status_api import health_status_api
    from rag_api import rag_api
    from enhanced_rag_qdrant_api import enhanced_rag_qdrant_api
    from time_series_api import time_series_api
    from export_api import export_api
    from download_api import download_api
    from cleanup_api import cleanup_api
    from data_management_api import data_management_api
    from master_file_api import master_file_api
    from kpi_reference_api import kpi_reference_api
    from reference_ranges_api import reference_ranges_api
    from best_practices_api import best_practices_api
    from financial_projections_api import financial_projections_api
    from health_trend_api import health_trend_api
    
    # Register core blueprints
    app.register_blueprint(upload_api)
    app.register_blueprint(kpi_api)
    app.register_blueprint(corporate_api)
    app.register_blueprint(health_status_api)
    app.register_blueprint(rag_api)
    app.register_blueprint(enhanced_rag_qdrant_api)
    app.register_blueprint(time_series_api)
    app.register_blueprint(export_api)
    app.register_blueprint(download_api)
    app.register_blueprint(cleanup_api)
    app.register_blueprint(data_management_api)
    app.register_blueprint(master_file_api)
    app.register_blueprint(kpi_reference_api)
    app.register_blueprint(reference_ranges_api)
    app.register_blueprint(best_practices_api)
    app.register_blueprint(financial_projections_api)
    app.register_blueprint(health_trend_api)
    
    # Register feature toggle API (always enabled)
    try:
        from feature_toggle_api import feature_toggle_api
        app.register_blueprint(feature_toggle_api)
        print("✅ Feature Toggle API enabled")
    except ImportError as e:
        print(f"⚠️ Feature Toggle API not available: {e}")
    
    # Register feature-gated blueprints
    if is_feature_enabled(FeatureToggle.ENHANCED_UPLOAD):
        try:
            from enhanced_upload_api import enhanced_upload_api
            app.register_blueprint(enhanced_upload_api)
            print("✅ Enhanced Upload API enabled")
        except ImportError as e:
            print(f"⚠️ Enhanced Upload API not available: {e}")
    
    if is_feature_enabled(FeatureToggle.EVENT_DRIVEN_RAG):
        try:
            from event_system import event_manager
            event_manager.start()
            print("✅ Event-driven RAG system enabled")
        except ImportError as e:
            print(f"⚠️ Event system not available: {e}")
    
    if is_feature_enabled(FeatureToggle.CONTINUOUS_LEARNING):
        try:
            from continuous_learning import learning_system
            learning_system.start()
            print("✅ Continuous learning system enabled")
        except ImportError as e:
            print(f"⚠️ Continuous learning not available: {e}")
    
    if is_feature_enabled(FeatureToggle.REAL_TIME_INGESTION):
        try:
            from real_time_ingestion_api import real_time_ingestion_api
            app.register_blueprint(real_time_ingestion_api)
            print("✅ Real-time ingestion API enabled")
        except ImportError as e:
            print(f"⚠️ Real-time ingestion API not available: {e}")
    
    # Add feature status endpoint
    @app.route('/api/feature-status', methods=['GET'])
    def get_feature_status():
        """Get current feature toggle status"""
        return jsonify({
            'features': feature_toggles.get_feature_status(),
            'dependencies': feature_toggles.validate_dependencies()
        })
    
    # Add hot reload status endpoint
    @app.route('/api/hot-reload-status', methods=['GET'])
    def get_hot_reload_status():
        """Get hot reload system status"""
        if 'hot_reload_system' in globals():
            return jsonify(hot_reload_system.get_status())
        else:
            return jsonify({'error': 'Hot reload system not initialized'})
    
    # Add data refresh endpoint
    @app.route('/api/refresh-data/<data_type>', methods=['POST'])
    def refresh_data(data_type):
        """Refresh specific data type"""
        if 'hot_reload_system' in globals():
            result = hot_reload_system.data_manager.refresh_data(data_type)
            if result:
                return jsonify({'status': 'success', 'message': result})
            else:
                return jsonify({'status': 'error', 'message': f'Failed to refresh {data_type}'}), 500
        else:
            return jsonify({'error': 'Hot reload system not initialized'}), 500
    
    # Add health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'features_enabled': len([f for f in feature_toggles.get_feature_status().values() if f['enabled']]),
            'hot_reload_active': 'hot_reload_system' in globals() and hot_reload_system.is_initialized
        })
    
    # Initialize hot reload system in production
    if os.getenv('FLASK_ENV') == 'production' or os.getenv('ENABLE_HOT_RELOAD', 'false').lower() == 'true':
        try:
            initialize_hot_reload(app)
            print("🔥 Hot reload system initialized")
        except Exception as e:
            print(f"⚠️ Hot reload system not available: {e}")
    
    return app

def main():
    """Main application entry point"""
    app = create_app()
    
    # Print feature status
    print("\n🔧 Feature Toggle Status:")
    print("=" * 50)
    status = feature_toggles.get_feature_status()
    for feature, config in status.items():
        status_icon = "✅" if config['enabled'] else "❌"
        print(f"{status_icon} {feature}: {config['description']}")
    
    # Validate dependencies
    validation = feature_toggles.validate_dependencies()
    if not validation['valid']:
        print("\n❌ Feature dependency issues:")
        for issue in validation['issues']:
            print(f"  - {issue}")
        print("\n⚠️ Some features may not work correctly!")
    
    print(f"\n🚀 Starting Flask app on 0.0.0.0:5059")
    print("=" * 50)
    
    # Run the app
    app.run(debug=False, host='0.0.0.0', port=5059)

if __name__ == '__main__':
    main()
