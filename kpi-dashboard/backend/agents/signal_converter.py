"""
Signal Data Converter Utility

Converts existing data models (Account, KPI, AccountNote, etc.) to SignalData format
for use with Signal Analyst Agent
"""

from typing import List, Dict, Optional
import logging
from .models import SignalData
from models import Account, KPI, AccountNote  # SQLAlchemy models

logger = logging.getLogger(__name__)


def convert_account_to_signal_data(
    account: Account,
    similarity: float = 0.9
) -> List[SignalData]:
    """
    Convert Account model to SignalData list
    
    Args:
        account: Account SQLAlchemy model
        similarity: Similarity score to assign
        
    Returns:
        List of SignalData objects
    """
    signals = []
    
    try:
        # Account metadata signal
        payload = {
            'signal_type': 'account_metadata',
            'signal_source': 'internal',
            'account_id': account.account_id,
            'account_name': account.account_name,
            'revenue': float(account.revenue) if account.revenue else 0,
            'industry': account.industry or 'unknown',
            'region': account.region or 'unknown',
            'account_status': account.account_status or 'active',
            'text': f"Account {account.account_name}: ${account.revenue:,.0f} ARR, {account.industry} industry"
        }
        
        signals.append(SignalData(
            similarity=similarity,
            payload=payload
        ))
        
    except Exception as e:
        logger.warning(f"Failed to convert account to signal: {e}")
    
    return signals


def convert_kpi_to_signal_data(
    kpi: KPI,
    similarity: float = 0.85
) -> SignalData:
    """
    Convert KPI model to SignalData
    
    Args:
        kpi: KPI SQLAlchemy model
        similarity: Similarity score to assign
        
    Returns:
        SignalData object
    """
    try:
        # Calculate trend (simplified - would need historical data for real trend)
        trend = 0.0  # Default to no trend
        
        payload = {
            'signal_type': 'kpi_metric',
            'signal_source': 'internal',
            'pillar': kpi.category or 'unknown',
            'metric_type': kpi.kpi_parameter or 'unknown',
            'current_value': float(kpi.data) if kpi.data else 0,
            'trend': trend,
            'account_id': kpi.account_id,
            'kpi_id': kpi.kpi_id,
            'impact_level': kpi.impact_level or 'medium',
            'text': f"{kpi.kpi_parameter}: {kpi.data} ({kpi.category})"
        }
        
        return SignalData(
            similarity=similarity,
            payload=payload
        )
        
    except Exception as e:
        logger.warning(f"Failed to convert KPI to signal: {e}")
        return None


def convert_account_notes_to_signal_data(
    notes: List[AccountNote],
    similarity: float = 0.8
) -> List[SignalData]:
    """
    Convert AccountNote models to SignalData list
    
    Args:
        notes: List of AccountNote SQLAlchemy models
        similarity: Similarity score to assign
        
    Returns:
        List of SignalData objects
    """
    signals = []
    
    for note in notes:
        try:
            payload = {
                'signal_type': 'account_note',
                'signal_source': 'internal',
                'sentiment': 'neutral',  # Would need NLP analysis for real sentiment
                'severity': 'medium',
                'account_id': note.account_id,
                'note_id': note.note_id,
                'note_type': note.note_type or 'general',
                'text': (note.note_content[:500] if note.note_content else ''),  # Truncate
                'created_at': note.created_at.isoformat() if note.created_at else None
            }
            
            signals.append(SignalData(
                similarity=similarity,
                payload=payload
            ))
            
        except Exception as e:
            logger.warning(f"Failed to convert account note to signal: {e}")
            continue
    
    return signals


def convert_database_models_to_signals(
    account: Account,
    kpis: Optional[List[KPI]] = None,
    notes: Optional[List[AccountNote]] = None,
    quantitative_similarity: float = 0.85,
    qualitative_similarity: float = 0.80
) -> Dict[str, List[SignalData]]:
    """
    Convert multiple database models to SignalData lists organized by type
    
    Args:
        account: Account model
        kpis: Optional list of KPI models
        notes: Optional list of AccountNote models
        quantitative_similarity: Similarity score for quantitative signals
        qualitative_similarity: Similarity score for qualitative signals
        
    Returns:
        Dictionary with keys 'quantitative_signals' and 'qualitative_signals'
    """
    quantitative_signals = []
    qualitative_signals = []
    
    # Convert account to quantitative signal
    account_signals = convert_account_to_signal_data(account, quantitative_similarity)
    quantitative_signals.extend(account_signals)
    
    # Convert KPIs to quantitative signals
    if kpis:
        for kpi in kpis:
            kpi_signal = convert_kpi_to_signal_data(kpi, quantitative_similarity)
            if kpi_signal:
                quantitative_signals.append(kpi_signal)
    
    # Convert notes to qualitative signals
    if notes:
        note_signals = convert_account_notes_to_signal_data(notes, qualitative_similarity)
        qualitative_signals.extend(note_signals)
    
    return {
        'quantitative_signals': quantitative_signals,
        'qualitative_signals': qualitative_signals,
        'historical_patterns': []  # Would need historical analysis to populate
    }

