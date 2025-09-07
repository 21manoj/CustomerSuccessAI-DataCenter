#!/usr/bin/env python3
"""
Best Practices API
Provides access to KPI best practices and industry benchmarks
"""

from flask import Blueprint, request, jsonify
from extensions import db
from rag_knowledge_schema import KPIBestPractices, IndustryBenchmarks

best_practices_api = Blueprint('best_practices_api', __name__)

@best_practices_api.route('/api/best-practices', methods=['GET'])
def get_best_practices():
    """Get all best practices"""
    try:
        practices = KPIBestPractices.query.all()
        
        result = []
        for practice in practices:
            result.append({
                'id': practice.id,
                'kpi_name': practice.kpi_name,
                'category': practice.category,
                'title': practice.title,
                'description': practice.description,
                'implementation_steps': practice.implementation_steps,
                'expected_impact': practice.expected_impact,
                'typical_improvement_percentage': practice.typical_improvement_percentage,
                'implementation_timeframe': practice.implementation_timeframe,
                'difficulty_level': practice.difficulty_level,
                'cost_estimate': practice.cost_estimate,
                'industry_applicability': practice.industry_applicability,
                'company_size_applicability': practice.company_size_applicability,
                'created_at': practice.created_at.isoformat() if practice.created_at else None
            })
        
        return jsonify({
            'best_practices': result,
            'total_count': len(result)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@best_practices_api.route('/api/best-practices/kpi/<kpi_name>', methods=['GET'])
def get_best_practices_for_kpi(kpi_name):
    """Get best practices for a specific KPI"""
    try:
        practices = KPIBestPractices.query.filter_by(kpi_name=kpi_name).all()
        
        result = []
        for practice in practices:
            result.append({
                'id': practice.id,
                'title': practice.title,
                'description': practice.description,
                'implementation_steps': practice.implementation_steps,
                'expected_impact': practice.expected_impact,
                'typical_improvement_percentage': practice.typical_improvement_percentage,
                'implementation_timeframe': practice.implementation_timeframe,
                'difficulty_level': practice.difficulty_level,
                'cost_estimate': practice.cost_estimate
            })
        
        return jsonify({
            'kpi_name': kpi_name,
            'best_practices': result,
            'total_count': len(result)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@best_practices_api.route('/api/industry-benchmarks', methods=['GET'])
def get_industry_benchmarks():
    """Get industry benchmarks"""
    try:
        kpi_name = request.args.get('kpi_name')
        industry = request.args.get('industry')
        company_size = request.args.get('company_size')
        
        query = IndustryBenchmarks.query
        
        if kpi_name:
            query = query.filter_by(kpi_name=kpi_name)
        if industry:
            query = query.filter_by(industry=industry)
        if company_size:
            query = query.filter_by(company_size=company_size)
        
        benchmarks = query.all()
        
        result = []
        for benchmark in benchmarks:
            result.append({
                'id': benchmark.id,
                'kpi_name': benchmark.kpi_name,
                'industry': benchmark.industry,
                'company_size': benchmark.company_size,
                'percentile_25': benchmark.percentile_25,
                'percentile_50': benchmark.percentile_50,
                'percentile_75': benchmark.percentile_75,
                'percentile_90': benchmark.percentile_90,
                'sample_size': benchmark.sample_size,
                'data_source': benchmark.data_source,
                'last_updated': benchmark.last_updated.isoformat() if benchmark.last_updated else None
            })
        
        return jsonify({
            'benchmarks': result,
            'total_count': len(result)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@best_practices_api.route('/api/rag-readiness', methods=['GET'])
def get_rag_readiness():
    """Get RAG system readiness assessment"""
    try:
        from rag_knowledge_schema import get_rag_readiness_assessment
        
        assessment = get_rag_readiness_assessment()
        
        return jsonify(assessment)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
