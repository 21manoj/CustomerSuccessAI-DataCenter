#!/usr/bin/env python3
"""
Test Normalized Health Scoring Algorithm
Demonstrates how categories are normalized to 100 units before applying weights
"""

from health_score_engine import HealthScoreEngine
from health_score_config import CATEGORY_WEIGHTS, IMPACT_WEIGHTS

def test_normalized_scoring():
    """Test the normalized scoring algorithm with examples"""
    
    print("🔬 NORMALIZED HEALTH SCORING ALGORITHM TEST")
    print("=" * 60)
    
    # Example 1: Product Usage Category (20% weight)
    print("\n📊 Example 1: Product Usage Category (20% weight)")
    print("-" * 50)
    
    # Simulate KPIs in Product Usage category
    product_usage_kpis = [
        {
            'kpi_parameter': 'Product Activation Rate',
            'data': '75%',
            'impact_level': 'High',
            'category': 'Product Usage'
        },
        {
            'kpi_parameter': 'Customer Retention Rate',
            'data': '85%',
            'impact_level': 'High',
            'category': 'Product Usage'
        },
        {
            'kpi_parameter': 'Training Participation Rate',
            'data': '60%',
            'impact_level': 'Medium',
            'category': 'Product Usage'
        }
    ]
    
    print(f"KPIs in Product Usage category: {len(product_usage_kpis)}")
    print("KPI Details:")
    for kpi in product_usage_kpis:
        enhanced = HealthScoreEngine.calculate_kpi_health_score(kpi)
        print(f"  • {kpi['kpi_parameter']}: {kpi['data']} (Impact: {kpi['impact_level']})")
        print(f"    Health Score: {enhanced['health_score']:.1f}%")
        print(f"    Impact Weight: {enhanced['impact_weight']}x")
        print(f"    Weighted Score: {enhanced['weighted_score']:.1f}")
    
    # Calculate category score
    category_result = HealthScoreEngine.calculate_category_health_score(product_usage_kpis, 'Product Usage')
    
    print(f"\nCategory Calculation:")
    print(f"  Total Units: {category_result['total_units']}")
    print(f"  Total Score: {category_result['total_score']:.1f}")
    print(f"  Normalized Score: {category_result['normalized_score']:.1f}%")
    print(f"  Category Weight: {category_result['category_weight']:.1%}")
    print(f"  Weighted Category Score: {category_result['weighted_category_score']:.1f}")
    print(f"  Health Status: {category_result['health_status']}")
    
    # Example 2: Support Category (20% weight) - More KPIs
    print("\n📊 Example 2: Support Category (20% weight) - More KPIs")
    print("-" * 50)
    
    support_kpis = [
        {
            'kpi_parameter': 'First Response Time',
            'data': '1.5',
            'impact_level': 'High',
            'category': 'Support'
        },
        {
            'kpi_parameter': 'Mean Time to Resolution',
            'data': '8',
            'impact_level': 'High',
            'category': 'Support'
        },
        {
            'kpi_parameter': 'Customer Support Satisfaction',
            'data': '4.2',
            'impact_level': 'Medium',
            'category': 'Support'
        },
        {
            'kpi_parameter': 'Ticket Volume',
            'data': '150',
            'impact_level': 'Medium',
            'category': 'Support'
        },
        {
            'kpi_parameter': 'Ticket Backlog',
            'data': '15%',
            'impact_level': 'Low',
            'category': 'Support'
        }
    ]
    
    print(f"KPIs in Support category: {len(support_kpis)}")
    print("KPI Details:")
    for kpi in support_kpis:
        enhanced = HealthScoreEngine.calculate_kpi_health_score(kpi)
        print(f"  • {kpi['kpi_parameter']}: {kpi['data']} (Impact: {kpi['impact_level']})")
        print(f"    Health Score: {enhanced['health_score']:.1f}%")
        print(f"    Impact Weight: {enhanced['impact_weight']}x")
        print(f"    Weighted Score: {enhanced['weighted_score']:.1f}")
    
    # Calculate category score
    support_result = HealthScoreEngine.calculate_category_health_score(support_kpis, 'Support')
    
    print(f"\nCategory Calculation:")
    print(f"  Total Units: {support_result['total_units']}")
    print(f"  Total Score: {support_result['total_score']:.1f}")
    print(f"  Normalized Score: {support_result['normalized_score']:.1f}%")
    print(f"  Category Weight: {support_result['category_weight']:.1%}")
    print(f"  Weighted Category Score: {support_result['weighted_category_score']:.1f}")
    print(f"  Health Status: {support_result['health_status']}")
    
    # Example 3: Overall Health Score
    print("\n📊 Example 3: Overall Health Score Calculation")
    print("-" * 50)
    
    # Simulate all categories
    all_categories = [
        category_result,
        support_result,
        {
            'category': 'Customer Sentiment',
            'normalized_score': 65.0,
            'category_weight': 0.20,
            'health_status': 'medium',
            'color': 'yellow'
        },
        {
            'category': 'Business Outcomes',
            'normalized_score': 45.0,
            'category_weight': 0.25,
            'health_status': 'medium',
            'color': 'yellow'
        },
        {
            'category': 'Relationship Strength',
            'normalized_score': 70.0,
            'category_weight': 0.15,
            'health_status': 'high',
            'color': 'green'
        }
    ]
    
    overall_result = HealthScoreEngine.calculate_overall_health_score(all_categories)
    
    print("Category Breakdown:")
    for cat in all_categories:
        print(f"  • {cat['category']}: {cat['normalized_score']:.1f}% (Weight: {cat['category_weight']:.1%})")
        print(f"    Weighted Contribution: {cat['normalized_score'] * cat['category_weight']:.1f}")
    
    print(f"\nOverall Health Score: {overall_result['overall_score']:.1f}%")
    print(f"Overall Health Status: {overall_result['health_status']}")
    
    # Algorithm explanation
    print("\n🔬 ALGORITHM EXPLANATION")
    print("=" * 60)
    print("""
1. KPI Level:
   • Parse KPI value (e.g., "75%" → 75.0)
   • Calculate health score (0-100) based on reference ranges
   • Apply impact weight (High=3x, Medium=2x, Low=1x)

2. Category Level (NORMALIZATION):
   • Sum all weighted scores in category
   • Sum all impact weights in category
   • Calculate average: total_score / total_units
   • This gives normalized category score (0-100)
   • Ensures categories with more KPIs don't get inflated scores

3. Overall Level:
   • Each category is already normalized (0-100)
   • Apply category weights (Product Usage=20%, Support=20%, etc.)
   • Calculate weighted average across all categories
   • Final score is 0-100 representing overall health
    """)

if __name__ == "__main__":
    test_normalized_scoring() 