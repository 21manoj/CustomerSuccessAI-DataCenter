#!/usr/bin/env python3
"""
Create RAG Knowledge Base Tables
Creates the necessary database tables for the RAG system
"""

from app import app
from extensions import db
from rag_knowledge_schema import (
    RAGKnowledgeBase, 
    FinancialProjection, 
    KPIBestPractices, 
    IndustryBenchmarks, 
    CustomerInsights, 
    RAGQueryLog
)

def create_rag_tables():
    """Create all RAG-related database tables"""
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            print("✅ Successfully created RAG knowledge base tables:")
            print("   - RAGKnowledgeBase")
            print("   - FinancialProjection") 
            print("   - KPIBestPractices")
            print("   - IndustryBenchmarks")
            print("   - CustomerInsights")
            print("   - RAGQueryLog")
            
    except Exception as e:
        print(f"❌ Error creating RAG tables: {e}")
        raise e

if __name__ == '__main__':
    create_rag_tables()
