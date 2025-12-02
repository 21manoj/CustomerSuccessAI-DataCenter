#!/usr/bin/env python3
"""
Quick Query Validation Script

Validates that all KPI queries are using the helper functions correctly.
Checks for any remaining direct KPI.query.filter_by(account_id=...) calls.
"""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_file_for_direct_queries(filepath):
    """Check if file has direct KPI queries that should use helpers"""
    issues = []
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
        # Pattern 1: KPI.query.filter_by(account_id=...)
        pattern1 = r'KPI\.query\.filter_by\(account_id\s*='
        
        # Pattern 2: KPI.query.filter_by(account_id=...).count()
        pattern2 = r'KPI\.query\.filter_by\(account_id\s*=.*?\.count\(\)'
        
        # Pattern 3: KPI.query.filter_by(account_id=...).all()
        pattern3 = r'KPI\.query\.filter_by\(account_id\s*=.*?\.all\(\)'
        
        for i, line in enumerate(lines, 1):
            # Skip if it's in a comment or already using helper
            if 'kpi_queries' in line.lower() or 'get_account_level_kpis' in line:
                continue
            
            if re.search(pattern1, line):
                issues.append({
                    'line': i,
                    'content': line.strip(),
                    'issue': 'Direct KPI.query.filter_by(account_id=...) call - should use get_account_level_kpis()'
                })
    
    except Exception as e:
        return [{'error': f"Error reading {filepath}: {e}"}]
    
    return issues

def validate_all_files():
    """Validate all backend files"""
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Files that should NOT have direct queries (critical files)
    critical_files = [
        'health_score_storage.py',
        'playbook_recommendations_api.py',
        'customer_performance_summary_api.py',
        'corporate_api.py',
        'kpi_api.py',
        'unified_query_api.py',
        'analytics_api.py',
        'playbook_triggers_api.py',
    ]
    
    # RAG files
    rag_files = [
        'enhanced_rag_openai.py',
        'enhanced_rag_qdrant.py',
        'direct_rag_api.py',
        'rag_api.py',
    ]
    
    all_files = critical_files + rag_files
    
    print("="*60)
    print("QUERY VALIDATION REPORT")
    print("="*60)
    print()
    
    total_issues = 0
    
    for filename in all_files:
        filepath = os.path.join(backend_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"⚠️  {filename}: File not found")
            continue
        
        issues = check_file_for_direct_queries(filepath)
        
        if issues:
            print(f"❌ {filename}: {len(issues)} issue(s) found")
            for issue in issues:
                if 'error' in issue:
                    print(f"   ERROR: {issue['error']}")
                else:
                    print(f"   Line {issue['line']}: {issue['issue']}")
                    print(f"      {issue['content'][:80]}...")
            total_issues += len(issues)
        else:
            print(f"✅ {filename}: No direct queries found")
    
    print()
    print("="*60)
    if total_issues == 0:
        print("✅ All files validated - no direct queries found!")
    else:
        print(f"⚠️  Found {total_issues} potential issues - review above")
    print("="*60)
    
    return total_issues == 0

if __name__ == "__main__":
    success = validate_all_files()
    sys.exit(0 if success else 1)


