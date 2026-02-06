#!/usr/bin/env python3
"""
Qualitative Signal Converter

Converts QualitativeSignal database models to SignalData format
for use with Signal Analyst Agent.
"""

from typing import List
from datetime import datetime
import logging
from .models import SignalData
from models import QualitativeSignal

logger = logging.getLogger(__name__)


def convert_qualitative_signal_to_signal_data(
    qual_signal: QualitativeSignal,
    similarity: float = 0.80
) -> SignalData:
    """
    Convert QualitativeSignal model to SignalData
    
    Args:
        qual_signal: QualitativeSignal SQLAlchemy model
        similarity: Similarity score to assign
        
    Returns:
        SignalData object
    """
    try:
        # Get signal date for temporal grouping
        signal_date = qual_signal.signal_date
        if signal_date:
            # Handle different date types
            if isinstance(signal_date, str):
                try:
                    signal_date = datetime.fromisoformat(signal_date.replace('Z', '+00:00'))
                except:
                    from dateutil.parser import parse
                    signal_date = parse(signal_date)
            
            # Calculate temporal grouping fields
            if hasattr(signal_date, 'isocalendar'):
                week_number = signal_date.isocalendar()[1]
            else:
                week_number = None
            year = signal_date.year if hasattr(signal_date, 'year') else None
            month = signal_date.month if hasattr(signal_date, 'month') else None
            month_year = f"{year}-{month:02d}" if year and month else None
        else:
            week_number = None
            year = None
            month = None
            month_year = None
        
        # Determine signal source (internal vs external)
        # If signal_type is in external types, mark as external
        external_types = ['funding_raised', 'executive_change', 'market_event', 'competitor_mention']
        # Also check if signal_type indicates external (e.g., 'escalation', 'meeting', 'email' are usually internal)
        internal_types = ['email', 'meeting', 'ticket', 'escalation', 'health_check', 'support_ticket']
        if qual_signal.signal_type in external_types:
            signal_source = 'external'
        elif qual_signal.signal_type in internal_types:
            signal_source = 'internal'
        else:
            # Default to internal for unknown types
            signal_source = 'internal'
        
        payload = {
            'signal_type': qual_signal.signal_type or 'qualitative_signal',
            'signal_source': signal_source,
            'signal_id': qual_signal.signal_id,  # ✅ Unique identifier for deduplication
            'account_id': qual_signal.account_id,
            'signal_date': signal_date.isoformat() if signal_date and hasattr(signal_date, 'isoformat') else str(signal_date) if signal_date else None,
            'sentiment': qual_signal.sentiment or 'neutral',
            'sentiment_score': float(qual_signal.sentiment_score) if qual_signal.sentiment_score else None,
            'content': qual_signal.content or '',
            'text': qual_signal.content or '',  # For compatibility
            'stakeholder_level': qual_signal.stakeholder_level,
            'stakeholder_title': qual_signal.stakeholder_title,
            'keywords': qual_signal.keywords,
            'is_narrative_signal': qual_signal.is_narrative_signal or False,
            # Temporal grouping fields
            'week_number': week_number,
            'month': month,
            'year': year,
            'month_year': month_year
        }
        
        return SignalData(
            similarity=similarity,
            payload=payload
        )
        
    except Exception as e:
        logger.warning(f"Failed to convert QualitativeSignal to SignalData: {e}", exc_info=True)
        return None


def convert_qualitative_signals_to_signal_data(
    qual_signals: List[QualitativeSignal],
    similarity: float = 0.80
) -> List[SignalData]:
    """
    Convert list of QualitativeSignal models to SignalData list
    
    Args:
        qual_signals: List of QualitativeSignal SQLAlchemy models
        similarity: Similarity score to assign
        
    Returns:
        List of SignalData objects
    """
    signals = []
    
    for qual_signal in qual_signals:
        signal_data = convert_qualitative_signal_to_signal_data(qual_signal, similarity)
        if signal_data:
            signals.append(signal_data)
    
    return signals
