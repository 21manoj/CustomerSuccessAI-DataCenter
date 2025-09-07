#!/usr/bin/env python3
"""
Health Score Calculation Demonstrator
Shows how the health scoring system works with examples
"""

from health_score_engine import HealthScoreEngine
from health_score_config import KPI_REFERENCE_RANGES, CATEGORY_WEIGHTS, IMPACT_WEIGHTS

def demonstrate_health_calculations():
    """Demonstrate health score calculations with examples"""
    
    print("🏥 HEALTH SCORE CALCULATION DEMONSTRATION")
    print("=" * 60)
    
    # Example 1: Product Activation Rate
    print("\n📊 Example 1: Product Activation Rate")
    print("-" * 40)
    kpi_name = "Product Activation Rate"
    value = "75%"
    impact_level = "High"
    category = "Product Usage"
    
    print(f"KPI: {kpi_name}")
    print(f"Value: {value}")
    print(f"Impact Level: {impact_level}")
    print(f"Category: {category}")
    
    # Get reference range
    ref_range = KPI_REFERENCE_RANGES.get(kpi_name, {})
    print(f"\nReference Ranges:")
    for level, range_info in ref_range.get("ranges", {}).items():
        print(f"  {level.title()}: {range_info['min']}-{range_info['max']}% ({range_info['color']})")
    
    # Calculate health score
    parsed_value = HealthScoreEngine.parse_kpi_value(value)
    health_info = HealthScoreEngine.calculate_health_status(parsed_value, kpi_name)
    
    # Create KPI data dictionary
    kpi_data = {
        'kpi_parameter': kpi_name,
        'data': value,
        'impact_level': impact_level,
        'category': category
    }
    
    enhanced_kpi = HealthScoreEngine.calculate_kpi_health_score(kpi_data)
    score = enhanced_kpi['health_score']
    
    print(f"\nCalculation:")
    print(f"  Parsed Value: {parsed_value}")
    print(f"  Health Status: {health_info['status']}")
    print(f"  Health Score: {score:.1f}%")
    print(f"  Impact Weight: {IMPACT_WEIGHTS[impact_level]}x")
    print(f"  Category Weight: {CATEGORY_WEIGHTS[category]:.1%}")
    print(f"  Weighted Score: {score * IMPACT_WEIGHTS[impact_level] * CATEGORY_WEIGHTS[category]:.1f}")
    
    # Example 2: First Response Time
    print("\n📊 Example 2: First Response Time")
    print("-" * 40)
    kpi_name = "First Response Time"
    value = "1.5"
    impact_level = "High"
    category = "Support"
    
    print(f"KPI: {kpi_name}")
    print(f"Value: {value} hours")
    print(f"Impact Level: {impact_level}")
    print(f"Category: {category}")
    
    # Get reference range
    ref_range = KPI_REFERENCE_RANGES.get(kpi_name, {})
    print(f"\nReference Ranges:")
    for level, range_info in ref_range.get("ranges", {}).items():
        print(f"  {level.title()}: {range_info['min']}-{range_info['max']} hours ({range_info['color']})")
    
    # Calculate health score
    parsed_value = HealthScoreEngine.parse_kpi_value(value)
    health_info = HealthScoreEngine.calculate_health_status(parsed_value, kpi_name)
    
    # Create KPI data dictionary
    kpi_data = {
        'kpi_parameter': kpi_name,
        'data': value,
        'impact_level': impact_level,
        'category': category
    }
    
    enhanced_kpi = HealthScoreEngine.calculate_kpi_health_score(kpi_data)
    score = enhanced_kpi['health_score']
    
    print(f"\nCalculation:")
    print(f"  Parsed Value: {parsed_value}")
    print(f"  Health Status: {health_info['status']}")
    print(f"  Health Score: {score:.1f}%")
    print(f"  Impact Weight: {IMPACT_WEIGHTS[impact_level]}x")
    print(f"  Category Weight: {CATEGORY_WEIGHTS[category]:.1%}")
    print(f"  Weighted Score: {score * IMPACT_WEIGHTS[impact_level] * CATEGORY_WEIGHTS[category]:.1f}")
    
    # Show all reference ranges
    print("\n🔬 ALL KPI REFERENCE RANGES")
    print("=" * 60)
    
    categories = {
        "Product Usage": [],
        "Support": [],
        "Customer Sentiment": [],
        "Business Outcomes": [],
        "Relationship Strength": []
    }
    
    for kpi_name, config in KPI_REFERENCE_RANGES.items():
        # Determine category based on KPI name patterns
        if any(word in kpi_name.lower() for word in ["product", "activation", "retention", "onboarding", "training", "feature", "knowledge", "learning"]):
            categories["Product Usage"].append(kpi_name)
        elif any(word in kpi_name.lower() for word in ["support", "response", "resolution", "ticket", "satisfaction"]):
            categories["Support"].append(kpi_name)
        elif any(word in kpi_name.lower() for word in ["sentiment", "satisfaction", "csat", "nps", "relationship"]):
            categories["Customer Sentiment"].append(kpi_name)
        elif any(word in kpi_name.lower() for word in ["revenue", "growth", "lifetime", "churn", "contract", "expansion", "acquisition", "roi", "market", "competitive"]):
            categories["Business Outcomes"].append(kpi_name)
        elif any(word in kpi_name.lower() for word in ["business review", "engagement", "sla", "delivery", "benchmark", "compliance", "audit", "cross-functional", "process"]):
            categories["Relationship Strength"].append(kpi_name)
    
    for category_name, kpis in categories.items():
        if kpis:
            print(f"\n📈 {category_name} ({CATEGORY_WEIGHTS[category_name]:.1%} weight):")
            for kpi_name in kpis[:5]:  # Show first 5 KPIs per category
                config = KPI_REFERENCE_RANGES[kpi_name]
                ranges = config["ranges"]
                unit = config.get("unit", "score")
                print(f"  • {kpi_name}:")
                for level, range_info in ranges.items():
                    print(f"    {level.title()}: {range_info['min']}-{range_info['max']} {unit}")
            if len(kpis) > 5:
                print(f"    ... and {len(kpis) - 5} more KPIs")

if __name__ == "__main__":
    demonstrate_health_calculations() 