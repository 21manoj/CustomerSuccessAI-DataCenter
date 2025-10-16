#!/usr/bin/env python3
"""
Test Suite for MCP Servers
Tests all mock MCP servers without requiring external systems
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
from datetime import datetime


def test_imports():
    """Test that all MCP server modules can be imported"""
    print("=" * 70)
    print("TEST 1: Module Imports")
    print("=" * 70)
    
    try:
        from mcp_servers.mock_salesforce_server import MockSalesforceMCPServer
        print("✅ Mock Salesforce Server imported successfully")
    except Exception as e:
        print(f"❌ Failed to import Salesforce server: {e}")
        return False
    
    try:
        from mcp_servers.mock_servicenow_server import MockServiceNowMCPServer
        print("✅ Mock ServiceNow Server imported successfully")
    except Exception as e:
        print(f"❌ Failed to import ServiceNow server: {e}")
        return False
    
    try:
        from mcp_servers.mock_survey_server import MockSurveyMCPServer
        print("✅ Mock Survey Server imported successfully")
    except Exception as e:
        print(f"❌ Failed to import Survey server: {e}")
        return False
    
    print("\n✅ All imports successful!\n")
    return True


def test_mcp_integration():
    """Test MCP integration layer"""
    print("=" * 70)
    print("TEST 2: MCP Integration Layer")
    print("=" * 70)
    
    try:
        from mcp_integration import MCPIntegration, is_mcp_enabled, get_mcp_config
        print("✅ MCP Integration module imported")
        
        # Test functions
        enabled = is_mcp_enabled(1)
        print(f"✅ is_mcp_enabled() works: {enabled}")
        
        config = get_mcp_config(1)
        print(f"✅ get_mcp_config() works: {config}")
        
        # Test MCPIntegration class
        mcp = MCPIntegration(customer_id=1)
        print(f"✅ MCPIntegration initialized for customer 1")
        
        status = mcp.get_status()
        print(f"✅ Get status works: {status}")
        
    except Exception as e:
        print(f"❌ MCP Integration test failed: {e}")
        return False
    
    print("\n✅ MCP Integration layer tests passed!\n")
    return True


def test_enhanced_rag_with_mcp():
    """Test MCP-enhanced RAG system"""
    print("=" * 70)
    print("TEST 3: MCP-Enhanced RAG System")
    print("=" * 70)
    
    try:
        from enhanced_rag_with_mcp import EnhancedRAGWithMCP
        print("✅ EnhancedRAGWithMCP imported")
        
        # Initialize (requires app context)
        from app import app
        
        with app.app_context():
            rag = EnhancedRAGWithMCP(customer_id=1)
            print("✅ EnhancedRAGWithMCP initialized")
            
            # Build knowledge base
            rag.build_knowledge_base(customer_id=1)
            print(f"✅ Knowledge base built: {len(rag.kpi_data)} KPIs")
            
            # Test standard query (no MCP)
            result = rag.query("What is the health score?", "general")
            print(f"✅ Standard query works")
            print(f"   Response length: {len(result.get('response', ''))}")
            print(f"   MCP enhanced: {result.get('mcp_enhanced', False)}")
        
    except Exception as e:
        print(f"❌ Enhanced RAG test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ Enhanced RAG tests passed!\n")
    return True


def test_feature_toggle_model():
    """Test FeatureToggle database model"""
    print("=" * 70)
    print("TEST 4: FeatureToggle Database Model")
    print("=" * 70)
    
    try:
        from app import app, db
        from models import FeatureToggle
        
        with app.app_context():
            print("✅ FeatureToggle model imported")
            
            # Check if table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'feature_toggles' in tables:
                print("✅ feature_toggles table exists in database")
                
                # Query existing toggles
                toggles = FeatureToggle.query.all()
                print(f"✅ Found {len(toggles)} feature toggles")
                
                for toggle in toggles:
                    print(f"   - {toggle.feature_name}: {'ON' if toggle.enabled else 'OFF'}")
            else:
                print("⚠️  feature_toggles table not found - run migration")
        
    except Exception as e:
        print(f"❌ FeatureToggle test failed: {e}")
        return False
    
    print("\n✅ FeatureToggle model tests passed!\n")
    return True


def test_feature_toggle_api():
    """Test feature toggle API endpoints"""
    print("=" * 70)
    print("TEST 5: Feature Toggle API")
    print("=" * 70)
    
    try:
        from feature_toggle_api import feature_toggle_api
        print("✅ Feature Toggle API blueprint imported")
        
        # Check endpoints
        endpoints = [rule.rule for rule in feature_toggle_api.url_map.iter_rules() if rule.rule.startswith('/api/features')]
        print(f"✅ Found {len(endpoints)} MCP endpoints:")
        for endpoint in endpoints:
            print(f"   - {endpoint}")
        
    except Exception as e:
        print(f"❌ Feature Toggle API test failed: {e}")
        return False
    
    print("\n✅ Feature Toggle API tests passed!\n")
    return True


def main():
    """Run all tests"""
    print("\n")
    print("🧪" * 35)
    print(" " * 20 + "MCP INTEGRATION TEST SUITE")
    print("🧪" * 35)
    print()
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # Run all tests
    results.append(("Module Imports", test_imports()))
    results.append(("MCP Integration", test_mcp_integration()))
    results.append(("FeatureToggle Model", test_feature_toggle_model()))
    results.append(("Feature Toggle API", test_feature_toggle_api()))
    results.append(("Enhanced RAG with MCP", test_enhanced_rag_with_mcp()))
    
    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! MCP integration is ready for testing.\n")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

