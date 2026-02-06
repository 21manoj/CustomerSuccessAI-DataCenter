"""
Prompt Template Library for Signal Analyst
Jinja2-based templates for different analysis types
"""

from jinja2 import Template
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

HEALTH_ASSESSMENT_TEMPLATE = Template("""
You are a Customer Success AI analyzing account health for {{ account_name }}, a {{industry}} company with ${{revenue}} ARR.

CURRENT KPI STATUS ({{analysis_date}}):
{% for kpi in kpis %}
- {{kpi.code}}: {{kpi.value}}{{kpi.unit}} (target: {{kpi.target}}{{kpi.unit}}) - {% if kpi.value >= kpi.target %}✅ ABOVE TARGET{% else %}⚠️ BELOW TARGET{% endif %}
{% endfor %}

CUSTOMER SIGNALS (Last 30 days):
{% for signal in signals %}
[{{signal.date}}] {{signal.type|upper}}: {{signal.subject}}
Summary: {{signal.summary}}
Sentiment: {{signal.sentiment}} | Priority: {{signal.priority}}
---
{% endfor %}

ANALYSIS REQUIRED:
1. **Overall Health Status**: Rate as Healthy / At-Risk / Critical
2. **Top 3 Risk Factors**: List specific risks with supporting evidence from KPIs and signals
3. **CSM Actions (Next 7 Days)**: Specific, actionable steps for the Customer Success Manager
4. **Churn Risk Assessment**: Provide churn probability percentage (0-100%) with reasoning

Format your response clearly with headers. Be specific, actionable, and data-driven.
""")


EXPANSION_OPPORTUNITY_TEMPLATE = Template("""
You are a Customer Success AI identifying expansion opportunities for {{ account_name }}.

ACCOUNT PROFILE:
- Company: {{ account_name }}
- Industry: {{ industry }}
- Current ARR: ${{ revenue }}
- Region: {{ region }}

PRODUCT USAGE INDICATORS:
{% for kpi in usage_kpis %}
- {{kpi.name}}: {{kpi.value}} ({{kpi.status}})
{% endfor %}

POSITIVE SIGNALS:
{% for signal in positive_signals %}
- {{signal.subject}} ({{signal.date}})
{% endfor %}

GROWTH INDICATORS:
{% for indicator in growth_indicators %}
- {{indicator.name}}: {{indicator.value}} {{indicator.trend}}
{% endfor %}

ANALYSIS REQUIRED:
1. **Expansion Readiness Score**: Rate 1-10 with explanation
2. **Recommended Expansion Path**: Suggest specific products/features to upsell
3. **Timing**: When to approach (immediate, 30 days, 90 days)
4. **Expected ARR Increase**: Estimate potential expansion value
5. **Key Talking Points**: What to emphasize in expansion conversation

Focus on data-driven insights that support a compelling business case.
""")


RISK_ANALYSIS_TEMPLATE = Template("""
You are a Customer Success AI performing risk analysis for {{ account_name }}.

RISK SIGNALS DETECTED:
{% for signal in risk_signals %}
- [{{signal.severity}}] {{signal.description}}
  Evidence: {{signal.evidence}}
{% endfor %}

DECLINING KPIs:
{% for kpi in declining_kpis %}
- {{kpi.code}}: {{kpi.current_value}} (was {{kpi.previous_value}}) - {{kpi.change_pct}}% decline
{% endfor %}

NEGATIVE CUSTOMER FEEDBACK:
{% for feedback in negative_feedback %}
- {{feedback.source}}: "{{feedback.summary}}" ({{feedback.sentiment}})
{% endfor %}

COMPETITIVE INTEL:
{% for intel in competitive_signals %}
- {{intel.description}}
{% endfor %}

ANALYSIS REQUIRED:
1. **Risk Level**: Critical / High / Medium / Low
2. **Root Cause Analysis**: What's driving the risk?
3. **Immediate Actions**: What must be done in next 48 hours?
4. **Recovery Plan**: 30/60/90 day plan to mitigate risk
5. **Escalation Needed**: Should this be escalated? To whom?

Be direct, urgent, and specific. This account needs immediate attention.
""")


CHURN_PREDICTION_TEMPLATE = Template("""
You are a Customer Success AI predicting churn risk for {{ account_name }}.

ACCOUNT CONTEXT:
- Customer Since: {{ customer_since }}
- Contract Value: ${{ contract_value }}
- Renewal Date: {{ renewal_date }}
- Days to Renewal: {{ days_to_renewal }}

CHURN INDICATORS:
{% for indicator in churn_indicators %}
- {{indicator.type}}: {{indicator.value}} (weight: {{indicator.weight}})
{% endfor %}

HISTORICAL PATTERNS:
- Similar accounts that churned had these patterns:
{% for pattern in historical_patterns %}
  - {{pattern.description}} ({{pattern.frequency}}% of churned accounts)
{% endfor %}

CURRENT STATE:
- Engagement Level: {{engagement_level}}
- Support Ticket Trend: {{support_trend}}
- Product Usage Trend: {{usage_trend}}
- Executive Sponsor Active: {{exec_sponsor_active}}

ANALYSIS REQUIRED:
1. **Churn Probability**: Percentage (0-100%) with confidence interval
2. **Key Churn Drivers**: Top 3 factors most likely to cause churn
3. **Win-Back Strategy**: Specific actions to retain the account
4. **Budget Required**: Resources needed for retention effort
5. **Success Probability**: Likelihood that retention efforts will succeed

Provide quantitative, data-driven predictions with clear reasoning.
""")


MONTHLY_REVIEW_TEMPLATE = Template("""
You are a Customer Success AI preparing a monthly business review for {{ account_name }}.

MONTH: {{ review_month }}

PERFORMANCE SUMMARY:
{% for kpi in kpi_summary %}
- {{kpi.name}}: {{kpi.value}} ({{kpi.vs_target}}) {{kpi.trend_arrow}}
{% endfor %}

KEY ACHIEVEMENTS:
{% for achievement in achievements %}
- {{achievement.description}} ({{achievement.impact}})
{% endfor %}

CHALLENGES ADDRESSED:
{% for challenge in challenges %}
- {{challenge.description}}
  Resolution: {{challenge.resolution}}
{% endfor %}

UPCOMING INITIATIVES:
{% for initiative in initiatives %}
- {{initiative.name}} (Target: {{initiative.target_date}})
{% endfor %}

ANALYSIS REQUIRED:
1. **Executive Summary**: 3-4 sentence overview for executives
2. **Month Highlights**: Top 3 wins
3. **Areas for Improvement**: Top 3 challenges
4. **Next Month Goals**: Specific, measurable objectives
5. **Resource Needs**: What additional support is needed

Format for presentation to executive stakeholders. Be concise but comprehensive.
""")


# =============================================================================
# PROMPT MANAGER
# =============================================================================

class PromptManager:
    """
    Manages prompt templates and rendering
    
    Usage:
        pm = PromptManager()
        prompt = pm.render('health_assessment', account_data)
    """
    
    TEMPLATES = {
        'health_assessment': HEALTH_ASSESSMENT_TEMPLATE,
        'expansion_opportunity': EXPANSION_OPPORTUNITY_TEMPLATE,
        'risk_analysis': RISK_ANALYSIS_TEMPLATE,
        'churn_prediction': CHURN_PREDICTION_TEMPLATE,
        'monthly_review': MONTHLY_REVIEW_TEMPLATE,
    }
    
    def __init__(self):
        self.templates = self.TEMPLATES.copy()
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with given context
        
        Args:
            template_name: Name of template to use
            context: Dictionary of variables to pass to template
        
        Returns:
            Rendered prompt string
        
        Raises:
            ValueError: If template not found
        """
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found. Available: {list(self.templates.keys())}")
        
        try:
            template = self.templates[template_name]
            rendered = template.render(**context)
            
            logger.debug(f"Rendered template '{template_name}' ({len(rendered)} chars)")
            
            return rendered
        
        except Exception as e:
            logger.error(f"Error rendering template '{template_name}': {e}")
            raise
    
    def add_template(self, name: str, template_string: str):
        """Add a custom template"""
        self.templates[name] = Template(template_string)
        logger.info(f"Added custom template: {name}")
    
    def list_templates(self) -> List[str]:
        """List available template names"""
        return list(self.templates.keys())


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_kpi_for_prompt(kpi_row) -> Dict[str, Any]:
    """
    Format KPI database row for template
    
    Args:
        kpi_row: SQLAlchemy row from dc2s_kpis table
    
    Returns:
        Dictionary formatted for template
    """
    return {
        'code': kpi_row.kpi_code,
        'value': round(kpi_row.value, 2),
        'target': round(kpi_row.target, 2),
        'unit': '%' if 'pct' in kpi_row.kpi_code.lower() else '',
        'status': kpi_row.status if hasattr(kpi_row, 'status') else 'unknown'
    }


def format_signal_for_prompt(signal_row) -> Dict[str, Any]:
    """
    Format signal database row for template
    
    Args:
        signal_row: Row from qualitative_signals table
    
    Returns:
        Dictionary formatted for template
    """
    return {
        'date': str(signal_row.date) if signal_row.date else 'Unknown',
        'type': signal_row.signal_type,
        'subject': signal_row.subject,
        'summary': signal_row.summary,
        'sentiment': signal_row.sentiment,
        'priority': signal_row.priority
    }


def format_qdrant_result_for_prompt(qdrant_result) -> Dict[str, Any]:
    """
    Format Qdrant search result for template
    
    Args:
        qdrant_result: Qdrant search result with score and payload
    
    Returns:
        Dictionary formatted for template
    """
    payload = qdrant_result.payload
    return {
        'date': payload.get('date', 'Unknown'),
        'type': payload.get('signal_type', 'unknown'),
        'subject': payload.get('subject', ''),
        'summary': payload.get('summary', ''),
        'sentiment': payload.get('sentiment', 'neutral'),
        'priority': payload.get('priority', 'medium'),
        'relevance_score': round(qdrant_result.score, 3)
    }


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Initialize prompt manager
    pm = PromptManager()
    
    # Example context for health assessment
    context = {
        'account_name': 'Acme Corp',
        'industry': 'SaaS',
        'revenue': '1,500,000',
        'region': 'North America',
        'analysis_date': '2025-01-04',
        'kpis': [
            {'code': 'P1-KPI1', 'value': 21, 'target': 14, 'unit': ' days'},
            {'code': 'P2-KPI1', 'value': 3.8, 'target': 2.0, 'unit': '%'},
            {'code': 'P3-KPI1', 'value': 450, 'target': 300, 'unit': ' tickets'},
        ],
        'signals': [
            {
                'date': '2025-01-03',
                'type': 'email',
                'subject': 'Q4 Budget Review',
                'summary': 'Customer expressed concerns about budget constraints',
                'sentiment': 'negative',
                'priority': 'high'
            },
            {
                'date': '2025-01-02',
                'type': 'meeting',
                'subject': 'Capacity Planning Discussion',
                'summary': 'Positive discussion about future expansion',
                'sentiment': 'positive',
                'priority': 'medium'
            }
        ]
    }
    
    # Render health assessment prompt
    prompt = pm.render('health_assessment', context)
    print(prompt)
    print("\n" + "="*70 + "\n")
    
    # List available templates
    print("Available templates:")
    for template_name in pm.list_templates():
        print(f"  - {template_name}")
