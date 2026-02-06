"""
Qualitative Signals Query - Adapted for Existing Schema
========================================================

Maps existing qualitative_signals table to API response format.

Existing Schema:
  - signal_id (varchar)
  - account_id (integer)
  - signal_date (date)
  - signal_type (varchar)
  - stakeholder_level (varchar)
  - stakeholder_title (varchar)
  - content (text)
  - sentiment (varchar)
  - sentiment_score (numeric)
  - keywords (text)
  - is_narrative_signal (boolean)

API Response Format:
  - signal_id, account_id, signal_type, date, week_number
  - subject, summary, from_contact, from_role
  - sentiment, sentiment_score, priority, health_impact
  - tags
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from datetime import datetime
import math

# If integrating into existing journey_api.py, just copy these functions


def derive_priority(sentiment: str, sentiment_score: float) -> str:
    """Derive priority from sentiment"""
    if sentiment == 'negative' and sentiment_score and sentiment_score < -0.5:
        return 'critical'
    elif sentiment == 'negative':
        return 'high'
    elif sentiment == 'neutral':
        return 'medium'
    else:
        return 'low'


def derive_health_impact(sentiment: str, sentiment_score: float) -> int:
    """Derive health impact from sentiment score (-20 to +20)"""
    if sentiment_score is None:
        if sentiment == 'positive':
            return 5
        elif sentiment == 'negative':
            return -5
        return 0
    
    # Scale sentiment_score (-1 to 1) to health_impact (-15 to +15)
    return int(sentiment_score * 15)


def calculate_week_number(signal_date) -> int:
    """Calculate ISO week number from date"""
    if signal_date is None:
        return 0
    if isinstance(signal_date, str):
        signal_date = datetime.fromisoformat(signal_date)
    return signal_date.isocalendar()[1]


def parse_keywords_to_tags(keywords: str) -> list:
    """Parse keywords string to tags list"""
    if not keywords:
        return []
    # Handle comma-separated or space-separated
    if ',' in keywords:
        return [k.strip() for k in keywords.split(',') if k.strip()]
    return [k.strip() for k in keywords.split() if k.strip()]


def transform_signal_row(row) -> dict:
    """Transform database row to API response format"""
    
    # Get content and derive subject
    content = row.content or ''
    subject = content[:100] + '...' if len(content) > 100 else content
    # Try to get first sentence as subject
    if '. ' in content[:150]:
        subject = content[:content.index('. ', 0, 150) + 1]
    
    # Derive priority and health impact
    sentiment = row.sentiment or 'neutral'
    sentiment_score = float(row.sentiment_score) if row.sentiment_score else None
    priority = derive_priority(sentiment, sentiment_score)
    health_impact = derive_health_impact(sentiment, sentiment_score)
    
    return {
        'signal_id': row.signal_id,
        'account_id': row.account_id,
        'signal_type': row.signal_type,
        'date': row.signal_date.isoformat() if row.signal_date else None,
        'week_number': calculate_week_number(row.signal_date),
        'subject': subject,
        'summary': content,
        'from_contact': row.stakeholder_title,  # Map stakeholder_title → from_contact
        'from_role': row.stakeholder_level,     # Map stakeholder_level → from_role
        'to_contact': None,
        'sentiment': sentiment,
        'sentiment_score': sentiment_score,
        'priority': priority,
        'health_impact': health_impact,
        'source': 'database',
        'tags': parse_keywords_to_tags(row.keywords),
        'is_narrative': row.is_narrative_signal,
        'created_at': None  # Not available in existing schema
    }


# =============================================================================
# SQL QUERIES (Use these in journey_api.py)
# =============================================================================

GET_SIGNALS_QUERY = """
    SELECT 
        signal_id,
        account_id,
        signal_date,
        signal_type,
        stakeholder_level,
        stakeholder_title,
        content,
        sentiment,
        sentiment_score,
        keywords,
        is_narrative_signal
    FROM qualitative_signals
    WHERE account_id = :account_id
    {type_filter}
    {sentiment_filter}
    ORDER BY signal_date DESC
    LIMIT :limit OFFSET :offset
"""

GET_SIGNAL_COUNTS_QUERY = """
    SELECT 
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE sentiment = 'positive') as positive,
        COUNT(*) FILTER (WHERE sentiment = 'negative') as negative,
        COUNT(*) FILTER (WHERE sentiment = 'neutral') as neutral,
        COUNT(*) FILTER (WHERE sentiment = 'negative' AND sentiment_score < -0.5) as critical,
        COUNT(*) FILTER (WHERE signal_type = 'email') as emails,
        COUNT(*) FILTER (WHERE signal_type = 'meeting') as meetings,
        COUNT(*) FILTER (WHERE signal_type = 'support_ticket') as tickets,
        COUNT(*) FILTER (WHERE signal_type = 'call') as calls
    FROM qualitative_signals
    WHERE account_id = :account_id
"""


# =============================================================================
# ENDPOINT HANDLER (Add to journey_api.py)
# =============================================================================

def get_signals_for_account(conn, account_id, signal_type: str = None, 
                            sentiment: str = None, limit: int = 50, offset: int = 0):
    """
    Get qualitative signals for an account using existing schema.
    
    Args:
        conn: Database connection
        account_id: Account ID to filter by
        signal_type: Optional filter (email, meeting, support_ticket, call)
        sentiment: Optional filter (positive, negative, neutral)
        limit: Max results (default 50)
        offset: Pagination offset
    
    Returns:
        dict with signals list and counts
    """
    
    # Build dynamic filters
    type_filter = ""
    sentiment_filter = ""
    # Convert account_id to int if it's a string (from URL parameter)
    account_id_int = int(account_id) if isinstance(account_id, str) else account_id
    params = {'account_id': account_id_int, 'limit': limit, 'offset': offset}
    
    if signal_type:
        type_filter = "AND signal_type = :signal_type"
        params['signal_type'] = signal_type
    
    if sentiment:
        sentiment_filter = "AND sentiment = :sentiment"
        params['sentiment'] = sentiment
    
    # Execute main query
    query = GET_SIGNALS_QUERY.format(
        type_filter=type_filter,
        sentiment_filter=sentiment_filter
    )
    result = conn.execute(text(query), params)
    
    signals = []
    for row in result:
        signals.append(transform_signal_row(row))
    
    # Get counts
    counts_result = conn.execute(text(GET_SIGNAL_COUNTS_QUERY), {'account_id': account_id_int})
    counts_row = counts_result.fetchone()
    
    counts = {
        'total': counts_row.total if counts_row else 0,
        'positive': counts_row.positive if counts_row else 0,
        'negative': counts_row.negative if counts_row else 0,
        'neutral': counts_row.neutral if counts_row else 0,
        'critical': counts_row.critical if counts_row else 0,
        'by_type': {
            'email': counts_row.emails if counts_row else 0,
            'meeting': counts_row.meetings if counts_row else 0,
            'support_ticket': counts_row.tickets if counts_row else 0,
            'call': counts_row.calls if counts_row else 0
        }
    }
    
    return {
        'signals': signals,
        'counts': counts,
        'pagination': {
            'limit': limit,
            'offset': offset,
            'has_more': len(signals) == limit
        }
    }


# =============================================================================
# INTEGRATION SNIPPET (Copy into journey_api.py)
# =============================================================================

"""
# Replace the existing get_signals endpoint with this:

@journey_api.route('/api/journey/<account_id>/signals', methods=['GET'])
def get_signals(account_id):
    '''Get qualitative signals for an account'''
    try:
        conn = get_db_connection()
        
        # Query parameters
        signal_type = request.args.get('type')
        sentiment = request.args.get('sentiment')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Import the helper function
        from signals_query_helper import get_signals_for_account
        
        result = get_signals_for_account(
            conn=conn,
            account_id=account_id,
            signal_type=signal_type,
            sentiment=sentiment,
            limit=limit,
            offset=offset
        )
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
"""
