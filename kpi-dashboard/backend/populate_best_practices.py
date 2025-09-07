#!/usr/bin/env python3
"""
Populate Best Practices Database
Creates initial best practices data for RAG knowledge base
"""

from app import app
from extensions import db
from rag_knowledge_schema import KPIBestPractices, IndustryBenchmarks

def populate_best_practices():
    """Populate the best practices database with initial data"""
    
    best_practices_data = [
        {
            'kpi_name': 'Time to First Value (TTFV)',
            'category': 'Product Usage KPI',
            'title': 'Implement Progressive Onboarding',
            'description': 'Break down the onboarding process into smaller, achievable milestones that provide immediate value to users.',
            'implementation_steps': [
                'Identify the core value proposition of your product',
                'Create 3-5 progressive milestones that build upon each other',
                'Design quick wins that can be achieved within the first session',
                'Implement progress tracking and celebration mechanisms',
                'A/B test different milestone sequences'
            ],
            'expected_impact': 'Reduces TTFV by 40-60% and improves user activation rates by 25-35%',
            'typical_improvement_percentage': 50.0,
            'implementation_timeframe': '4-6 weeks',
            'difficulty_level': 'medium',
            'cost_estimate': 'Medium - requires product development resources',
            'industry_applicability': ['SaaS', 'Technology', 'Software'],
            'company_size_applicability': ['startup', 'smb', 'enterprise']
        },
        {
            'kpi_name': 'Customer Retention Rate',
            'category': 'Product Usage KPI',
            'title': 'Implement Proactive Customer Success Management',
            'description': 'Establish a dedicated customer success team to proactively identify and address customer issues before they lead to churn.',
            'implementation_steps': [
                'Define customer health scoring criteria',
                'Implement automated health monitoring',
                'Create playbooks for different risk levels',
                'Establish regular check-in cadences',
                'Develop intervention strategies for at-risk customers'
            ],
            'expected_impact': 'Increases retention rates by 15-25% and reduces churn by 30-40%',
            'typical_improvement_percentage': 20.0,
            'implementation_timeframe': '8-12 weeks',
            'difficulty_level': 'high',
            'cost_estimate': 'High - requires dedicated team and tools',
            'industry_applicability': ['SaaS', 'Technology', 'Professional Services'],
            'company_size_applicability': ['smb', 'enterprise']
        },
        {
            'kpi_name': 'First Response Time',
            'category': 'Support KPI',
            'title': 'Implement AI-Powered Ticket Routing and Auto-Responses',
            'description': 'Use AI to automatically categorize and route support tickets, and provide instant responses for common queries.',
            'implementation_steps': [
                'Analyze historical ticket data to identify common issues',
                'Implement AI-powered ticket classification',
                'Create auto-response templates for frequent queries',
                'Set up intelligent routing to appropriate agents',
                'Monitor and optimize response accuracy'
            ],
            'expected_impact': 'Reduces first response time by 60-80% and improves customer satisfaction by 20-30%',
            'typical_improvement_percentage': 70.0,
            'implementation_timeframe': '6-8 weeks',
            'difficulty_level': 'medium',
            'cost_estimate': 'Medium - requires AI tools and integration',
            'industry_applicability': ['Technology', 'E-commerce', 'Financial Services'],
            'company_size_applicability': ['smb', 'enterprise']
        },
        {
            'kpi_name': 'Net Promoter Score (NPS)',
            'category': 'Customer Sentiment KPI',
            'title': 'Implement Continuous Feedback Collection and Action',
            'description': 'Establish systematic feedback collection processes and ensure quick action on customer insights.',
            'implementation_steps': [
                'Implement multi-channel feedback collection (in-app, email, surveys)',
                'Create feedback analysis and categorization system',
                'Establish feedback-to-action workflows',
                'Implement closed-loop feedback processes',
                'Regularly communicate improvements back to customers'
            ],
            'expected_impact': 'Improves NPS by 10-20 points and increases customer advocacy by 35-50%',
            'typical_improvement_percentage': 15.0,
            'implementation_timeframe': '4-6 weeks',
            'difficulty_level': 'medium',
            'cost_estimate': 'Low-Medium - requires survey tools and process changes',
            'industry_applicability': ['All Industries'],
            'company_size_applicability': ['startup', 'smb', 'enterprise']
        },
        {
            'kpi_name': 'Revenue Growth',
            'category': 'Business Outcomes KPI',
            'title': 'Implement Data-Driven Upselling and Cross-selling',
            'description': 'Use customer usage data and behavior patterns to identify upsell and cross-sell opportunities.',
            'implementation_steps': [
                'Analyze customer usage patterns and feature adoption',
                'Identify upsell/cross-sell opportunity signals',
                'Create targeted campaigns based on customer segments',
                'Implement automated opportunity scoring',
                'Train sales team on data-driven selling approaches'
            ],
            'expected_impact': 'Increases revenue growth by 20-35% and improves customer lifetime value by 25-40%',
            'typical_improvement_percentage': 27.5,
            'implementation_timeframe': '6-10 weeks',
            'difficulty_level': 'high',
            'cost_estimate': 'High - requires analytics tools and sales training',
            'industry_applicability': ['SaaS', 'Technology', 'E-commerce'],
            'company_size_applicability': ['smb', 'enterprise']
        },
        {
            'kpi_name': 'Customer Acquisition Cost (CAC)',
            'category': 'Business Outcomes KPI',
            'title': 'Optimize Marketing Attribution and Channel Performance',
            'description': 'Implement comprehensive marketing attribution to identify and optimize high-performing acquisition channels.',
            'implementation_steps': [
                'Implement multi-touch attribution tracking',
                'Analyze channel performance and ROI',
                'Reallocate budget to high-performing channels',
                'Optimize conversion funnels for each channel',
                'Implement A/B testing for marketing campaigns'
            ],
            'expected_impact': 'Reduces CAC by 25-40% and improves marketing ROI by 30-50%',
            'typical_improvement_percentage': 32.5,
            'implementation_timeframe': '8-12 weeks',
            'difficulty_level': 'high',
            'cost_estimate': 'High - requires marketing analytics tools',
            'industry_applicability': ['Technology', 'E-commerce', 'SaaS'],
            'company_size_applicability': ['smb', 'enterprise']
        },
        {
            'kpi_name': 'Account Engagement Score',
            'category': 'Relationship Strength KPI',
            'title': 'Implement Account-Based Marketing (ABM) Strategies',
            'description': 'Develop personalized engagement strategies for high-value accounts to strengthen relationships.',
            'implementation_steps': [
                'Identify high-value target accounts',
                'Create personalized engagement plans',
                'Develop account-specific content and campaigns',
                'Implement multi-channel touchpoint strategies',
                'Measure and optimize engagement metrics'
            ],
            'expected_impact': 'Increases account engagement by 40-60% and improves relationship strength by 30-45%',
            'typical_improvement_percentage': 50.0,
            'implementation_timeframe': '10-14 weeks',
            'difficulty_level': 'high',
            'cost_estimate': 'High - requires dedicated resources and tools',
            'industry_applicability': ['B2B Technology', 'Professional Services', 'Enterprise Software'],
            'company_size_applicability': ['enterprise']
        }
    ]
    
    industry_benchmarks_data = [
        # SaaS Industry Benchmarks
        {
            'kpi_name': 'Time to First Value (TTFV)',
            'industry': 'SaaS',
            'company_size': 'startup',
            'percentile_25': 7.0,
            'percentile_50': 14.0,
            'percentile_75': 21.0,
            'percentile_90': 30.0,
            'sample_size': 150,
            'data_source': 'SaaS Metrics Report 2024'
        },
        {
            'kpi_name': 'Time to First Value (TTFV)',
            'industry': 'SaaS',
            'company_size': 'enterprise',
            'percentile_25': 14.0,
            'percentile_50': 21.0,
            'percentile_75': 30.0,
            'percentile_90': 45.0,
            'sample_size': 200,
            'data_source': 'SaaS Metrics Report 2024'
        },
        {
            'kpi_name': 'Customer Retention Rate',
            'industry': 'SaaS',
            'company_size': 'startup',
            'percentile_25': 70.0,
            'percentile_50': 80.0,
            'percentile_75': 88.0,
            'percentile_90': 93.0,
            'sample_size': 300,
            'data_source': 'SaaS Metrics Report 2024'
        },
        {
            'kpi_name': 'Customer Retention Rate',
            'industry': 'SaaS',
            'company_size': 'enterprise',
            'percentile_25': 85.0,
            'percentile_50': 92.0,
            'percentile_75': 96.0,
            'percentile_90': 98.0,
            'sample_size': 250,
            'data_source': 'SaaS Metrics Report 2024'
        },
        {
            'kpi_name': 'First Response Time',
            'industry': 'Technology',
            'company_size': 'smb',
            'percentile_25': 2.0,
            'percentile_50': 4.0,
            'percentile_75': 8.0,
            'percentile_90': 12.0,
            'sample_size': 400,
            'data_source': 'Support Metrics Benchmark 2024'
        },
        {
            'kpi_name': 'First Response Time',
            'industry': 'Technology',
            'company_size': 'enterprise',
            'percentile_25': 1.0,
            'percentile_50': 2.0,
            'percentile_75': 4.0,
            'percentile_90': 6.0,
            'sample_size': 350,
            'data_source': 'Support Metrics Benchmark 2024'
        },
        {
            'kpi_name': 'Net Promoter Score (NPS)',
            'industry': 'Technology',
            'company_size': 'startup',
            'percentile_25': 20.0,
            'percentile_50': 35.0,
            'percentile_75': 50.0,
            'percentile_90': 65.0,
            'sample_size': 200,
            'data_source': 'Customer Experience Benchmark 2024'
        },
        {
            'kpi_name': 'Net Promoter Score (NPS)',
            'industry': 'Technology',
            'company_size': 'enterprise',
            'percentile_25': 30.0,
            'percentile_50': 45.0,
            'percentile_75': 60.0,
            'percentile_90': 75.0,
            'sample_size': 300,
            'data_source': 'Customer Experience Benchmark 2024'
        },
        {
            'kpi_name': 'Revenue Growth',
            'industry': 'SaaS',
            'company_size': 'startup',
            'percentile_25': 15.0,
            'percentile_50': 25.0,
            'percentile_75': 40.0,
            'percentile_90': 60.0,
            'sample_size': 180,
            'data_source': 'SaaS Growth Metrics 2024'
        },
        {
            'kpi_name': 'Revenue Growth',
            'industry': 'SaaS',
            'company_size': 'enterprise',
            'percentile_25': 8.0,
            'percentile_50': 15.0,
            'percentile_75': 25.0,
            'percentile_90': 35.0,
            'sample_size': 120,
            'data_source': 'SaaS Growth Metrics 2024'
        }
    ]
    
    try:
        with app.app_context():
            # Clear existing data
            db.session.query(KPIBestPractices).delete()
            db.session.query(IndustryBenchmarks).delete()
            
            # Insert best practices
            for practice_data in best_practices_data:
                practice = KPIBestPractices(**practice_data)
                db.session.add(practice)
            
            # Insert industry benchmarks
            for benchmark_data in industry_benchmarks_data:
                benchmark = IndustryBenchmarks(**benchmark_data)
                db.session.add(benchmark)
            
            db.session.commit()
            print(f"✅ Successfully populated {len(best_practices_data)} best practices")
            print(f"✅ Successfully populated {len(industry_benchmarks_data)} industry benchmarks")
            
    except Exception as e:
        print(f"❌ Error populating best practices: {e}")
        db.session.rollback()
        raise e

if __name__ == '__main__':
    populate_best_practices()
