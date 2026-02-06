#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend')

from templates.prompt_templates import PromptManager

print("="*70)
print("PROMPT TEMPLATES TEST")
print("="*70)

# Initialize
pm = PromptManager()

# List templates
print("\n✅ Available templates:")
for template_name in pm.list_templates():
    print(f"  - {template_name}")

# Test rendering
context = {
    'account_name': 'Syntara',
    'industry': 'Technology',
    'revenue': '1,500,000',
    'region': 'North America',
    'analysis_date': '2025-01-04',
    'kpis': [
        {'code': 'P1-KPI1', 'value': 15, 'target': 14, 'unit': ' days'},
    ],
    'signals': [
        {
            'date': '2025-01-03',
            'type': 'email',
            'subject': 'Budget Review',
            'summary': 'Customer discussing budget',
            'sentiment': 'neutral',
            'priority': 'medium'
        }
    ]
}

prompt = pm.render('health_assessment', context)
print(f"\n✅ Prompt rendereccessfully ({len(prompt)} characters)")
print(f"\nFirst 200 characters of prompt:")
print(prompt[:200] + "...")

print("\n" + "="*70)
print("PROMPT TESTS PASSED!")
print("="*70)
