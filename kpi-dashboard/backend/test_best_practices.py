#!/usr/bin/env python3
"""
Test best practices API
"""

from app import app
from extensions import db
from rag_knowledge_schema import KPIBestPractices, IndustryBenchmarks

def test_best_practices():
    with app.app_context():
        try:
            # Test querying best practices
            practices = KPIBestPractices.query.all()
            print(f"Found {len(practices)} best practices")
            
            if practices:
                practice = practices[0]
                print(f"First practice: {practice.title}")
                print(f"KPI: {practice.kpi_name}")
                print(f"Category: {practice.category}")
            
            # Test querying benchmarks
            benchmarks = IndustryBenchmarks.query.all()
            print(f"Found {len(benchmarks)} industry benchmarks")
            
            if benchmarks:
                benchmark = benchmarks[0]
                print(f"First benchmark: {benchmark.kpi_name} - {benchmark.industry}")
                print(f"50th percentile: {benchmark.percentile_50}")
            
        except Exception as e:
            import traceback
            print(f"Error: {e}")
            print(f"Traceback: {traceback.format_exc()}")

if __name__ == '__main__':
    test_best_practices()
