"""
Signal Data Converter Utility

Converts existing data models (Account, KPI, AccountNote, etc.) to SignalData format
for use with Signal Analyst Agent
"""

from typing import List, Dict, Optional
import logging
from .models import SignalData
from models import Account, KPI, AccountNote, DC2SKPI, QualitativeSignal  # SQLAlchemy models

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


def convert_dc2s_kpi_to_signal_data(
    dc_kpi: DC2SKPI,
    similarity: float = 0.85
) -> SignalData:
    """
    Convert DC2SKPI model to SignalData (for Data Center vertical)
    
    Args:
        dc_kpi: DC2SKPI SQLAlchemy model
        similarity: Similarity score to assign
        
    Returns:
        SignalData object
    """
    try:
        # Try to get KPI definition for better name. dc2s_kpis is a shared
        # table across every non-SaaS vertical, so the name must come from
        # the owning account's OWN vertical catalog, not dc2_s's.
        kpi_name = dc_kpi.kpi_code
        try:
            from models import Account
            from utils.vertical_registry import get_kpis, get_vertical_for_customer
            account = Account.query.get(dc_kpi.account_id)
            vertical = get_vertical_for_customer(account.customer_id) if account else 'dc2_s'
            kpi_def = get_kpis(vertical).get(dc_kpi.kpi_code, {})
            kpi_name = kpi_def.get('name', dc_kpi.kpi_code)
        except Exception:
            # Resolution failed (no account, no CustomerConfig, unknown
            # vertical) — fall back to the raw kpi_code, never guess dc2_s.
            pass
        
        # Calculate trend (simplified - would need historical data for real trend)
        trend = 0.0  # Default to no trend
        
        # Calculate status based on value vs target if target exists
        status = dc_kpi.status or 'unknown'
        if dc_kpi.target and dc_kpi.value:
            if float(dc_kpi.value) >= float(dc_kpi.target):
                status = 'healthy'
            elif float(dc_kpi.value) >= float(dc_kpi.target) * 0.8:
                status = 'at_risk'
            else:
                status = 'critical'
        
        # Build descriptive text
        value_str = str(dc_kpi.value)
        target_str = f" (Target: {dc_kpi.target})" if dc_kpi.target else ""
        pillar_str = f" ({dc_kpi.pillar})" if dc_kpi.pillar else ""
        
        payload = {
            'signal_type': 'kpi_metric',
            'signal_source': 'internal',
            'pillar': dc_kpi.pillar or 'unknown',
            'metric_type': kpi_name,
            'current_value': float(dc_kpi.value) if dc_kpi.value else 0,
            'target_value': float(dc_kpi.target) if dc_kpi.target else None,
            'trend': trend,
            'status': status,
            'account_id': dc_kpi.account_id,
            'kpi_id': dc_kpi.kpi_id,
            'kpi_code': dc_kpi.kpi_code,
            'weight': float(dc_kpi.weight) if dc_kpi.weight else None,
            'text': f"{kpi_name}: {value_str}{target_str}{pillar_str}"
        }
        
        return SignalData(
            similarity=similarity,
            payload=payload
        )
        
    except Exception as e:
        logger.warning(f"Failed to convert DC2SKPI to signal: {e}", exc_info=True)
        return None


def convert_database_models_to_signals(
    account: Account,
    kpis: Optional[List[KPI]] = None,
    dc_kpis: Optional[List[DC2SKPI]] = None,
    notes: Optional[List[AccountNote]] = None,
    account_health_score: Optional[float] = None,
    quantitative_similarity: float = 0.85,
    qualitative_similarity: float = 0.80
) -> Dict[str, List[SignalData]]:
    """
    Convert multiple database models to SignalData lists organized by type
    
    Args:
        account: Account model
        kpis: Optional list of KPI models (for SaaS vertical)
        dc_kpis: Optional list of DC2SKPI models (for Data Center vertical)
        notes: Optional list of AccountNote models
        account_health_score: Optional overall account health score (0-100)
        quantitative_similarity: Similarity score for quantitative signals
        qualitative_similarity: Similarity score for qualitative signals
        
    Returns:
        Dictionary with keys 'quantitative_signals' and 'qualitative_signals'
    """
    from datetime import datetime
    
    quantitative_signals = []
    qualitative_signals = []
    
    # Convert account to quantitative signal
    account_signals = convert_account_to_signal_data(account, quantitative_similarity)
    quantitative_signals.extend(account_signals)
    
    # Add account health score as a quantitative signal (for temporal grouping)
    if account_health_score is not None:
        now = datetime.utcnow()
        week_number = now.isocalendar()[1]  # ISO week (1-52/53)
        year = now.year
        month = now.month
        month_year = f"{year}-{month:02d}"
        
        # Determine health status
        if account_health_score >= 67:
            health_status = 'high'
            health_color = 'green'
        elif account_health_score >= 34:
            health_status = 'medium'
            health_color = 'yellow'
        else:
            health_status = 'low'
            health_color = 'red'
        
        health_payload = {
            'signal_type': 'account_health_score',
            'signal_source': 'health_score_rollup',
            'account_id': account.account_id,
            'overall_health_score': account_health_score,
            'health_status': health_status,
            'health_color': health_color,
            'calculated_at': now.isoformat(),
            'week_number': week_number,  # For temporal grouping
            'month': month,
            'year': year,
            'month_year': month_year,  # For temporal grouping
            'text': f"Account Health Score: {account_health_score:.1f}/100 ({health_status})"
        }
        
        health_signal = SignalData(
            similarity=1.0,  # Always include health score
            payload=health_payload
        )
        quantitative_signals.append(health_signal)
        logger.info(f"Added account health score signal: {account_health_score:.1f}/100 (Week {week_number}, {month_year})")
    
    # Convert SaaS KPIs to quantitative signals
    if kpis:
        for kpi in kpis:
            kpi_signal = convert_kpi_to_signal_data(kpi, quantitative_similarity)
            if kpi_signal:
                quantitative_signals.append(kpi_signal)
    
    # Convert DC2S KPIs to quantitative signals
    if dc_kpis:
        for dc_kpi in dc_kpis:
            dc_kpi_signal = convert_dc2s_kpi_to_signal_data(dc_kpi, quantitative_similarity)
            if dc_kpi_signal:
                quantitative_signals.append(dc_kpi_signal)
    
    # Convert notes to qualitative signals
    if notes:
        note_signals = convert_account_notes_to_signal_data(notes, qualitative_similarity)
        qualitative_signals.extend(note_signals)
    
    return {
        'quantitative_signals': quantitative_signals,
        'qualitative_signals': qualitative_signals,
        'historical_patterns': []  # Would need historical analysis to populate
    }

