#!/usr/bin/env python3
"""
Signal Deduplication Utility

Removes duplicate signals before sending to LLM to prevent:
- Wasted tokens
- Biased analysis
- Increased costs
"""

from typing import List, Dict, Set
from .models import SignalData
import logging

logger = logging.getLogger(__name__)


def get_signal_unique_key(signal: SignalData) -> str:
    """
    Generate unique key for a signal based on its type and identifiers
    
    Args:
        signal: SignalData object
        
    Returns:
        Unique key string, or None if signal cannot be uniquely identified
    """
    payload = signal.payload
    signal_type = payload.get('signal_type', 'unknown')
    
    if signal_type == 'kpi_metric':
        # Use kpi_id for SaaS KPIs
        kpi_id = payload.get('kpi_id')
        if kpi_id:
            return f"kpi_{kpi_id}"
        # Fallback: account_id + kpi_parameter
        account_id = payload.get('account_id')
        kpi_parameter = payload.get('metric_type') or payload.get('kpi_parameter')
        if account_id and kpi_parameter:
            return f"kpi_{account_id}_{kpi_parameter}"
    
    elif signal_type == 'dc2s_kpi' or signal_type == 'kpi_metric':
        # For DC2S KPIs, use account_id + kpi_code + measured_at
        account_id = payload.get('account_id')
        kpi_code = payload.get('kpi_code') or payload.get('metric_type')
        measured_at = payload.get('measured_at', '')
        if account_id and kpi_code:
            return f"dc2s_{account_id}_{kpi_code}_{measured_at}"
    
    elif signal_type == 'account_note':
        # Use note_id for account notes
        note_id = payload.get('note_id')
        if note_id:
            return f"note_{note_id}"
        # Fallback: account_id + created_at + text hash
        account_id = payload.get('account_id')
        created_at = payload.get('created_at', '')
        text = payload.get('text', '')[:100]  # First 100 chars
        if account_id and text:
            return f"note_{account_id}_{created_at}_{hash(text)}"
    
    elif signal_type == 'qualitative_signal' or signal_type in ['email', 'meeting', 'ticket', 'escalation', 'health_check']:
        # Use signal_id for qualitative signals (from QualitativeSignal table)
        signal_id = payload.get('signal_id')
        if signal_id:
            return f"qual_signal_{signal_id}"
        # Fallback: account_id + signal_type + signal_date
        account_id = payload.get('account_id')
        signal_date = payload.get('signal_date', '')
        signal_type_val = payload.get('signal_type', '')
        if account_id and signal_date and signal_type_val:
            return f"qual_signal_{account_id}_{signal_type_val}_{signal_date}"
    
    elif signal_type == 'account_health_score':
        # Health score is unique per account per calculation timestamp
        account_id = payload.get('account_id')
        calculated_at = payload.get('calculated_at', 'latest')
        week_number = payload.get('week_number')
        if account_id:
            # Use week_number if available for better temporal grouping
            if week_number:
                return f"health_{account_id}_week_{week_number}"
            return f"health_{account_id}_{calculated_at}"
    
    elif signal_type == 'account_metadata':
        # Account metadata is unique per account
        account_id = payload.get('account_id')
        if account_id:
            return f"account_{account_id}"
    
    elif signal_type == 'external_signal':
        # External signals should have signal_id
        signal_id = payload.get('signal_id')
        if signal_id:
            return f"signal_{signal_id}"
        # Fallback: account_id + signal_type + date
        account_id = payload.get('account_id')
        event_type = payload.get('event_type', '')
        date = payload.get('date', '')
        if account_id and event_type and date:
            return f"signal_{account_id}_{event_type}_{date}"
    
    elif signal_type == 'support_ticket':
        # Support tickets should have ticket_id
        ticket_id = payload.get('ticket_id') or payload.get('signal_id')
        if ticket_id:
            return f"ticket_{ticket_id}"
    
    elif signal_type == 'historical_pattern':
        # Historical patterns are unique by pattern type + account
        account_id = payload.get('account_id')
        pattern_type = payload.get('pattern_type', '')
        if account_id and pattern_type:
            return f"pattern_{account_id}_{pattern_type}"
    
    # Fallback: use text hash for unknown types
    text = payload.get('text', '')
    account_id = payload.get('account_id', 'unknown')
    if text:
        return f"text_{account_id}_{hash(text[:200])}"
    
    return None


def deduplicate_signals(signals: List[SignalData], prefer_source: str = 'database') -> List[SignalData]:
    """
    Remove duplicate signals based on unique identifiers
    
    Args:
        signals: List of SignalData objects
        prefer_source: Which source to prefer when duplicates found ('database' or 'qdrant')
        
    Returns:
        Deduplicated list of SignalData objects
    """
    if not signals:
        return signals
    
    seen_keys: Set[str] = set()
    unique_signals: List[SignalData] = []
    duplicate_count = 0
    
    # Group signals by key to handle source preference
    signals_by_key: Dict[str, List[SignalData]] = {}
    
    for signal in signals:
        key = get_signal_unique_key(signal)
        
        if not key:
            # Signals without key - keep all (e.g., account metadata)
            unique_signals.append(signal)
            continue
        
        if key not in signals_by_key:
            signals_by_key[key] = []
        signals_by_key[key].append(signal)
    
    # For each key, keep only one signal (prefer specified source)
    for key, signal_list in signals_by_key.items():
        if len(signal_list) == 1:
            # No duplicates for this key
            unique_signals.append(signal_list[0])
        else:
            # Multiple signals with same key - deduplicate
            duplicate_count += len(signal_list) - 1
            
            # Prefer signal from specified source
            preferred_signal = None
            for signal in signal_list:
                payload = signal.payload
                source = payload.get('signal_source', 'internal')
                
                if prefer_source == 'database' and source == 'internal':
                    preferred_signal = signal
                    break
                elif prefer_source == 'qdrant' and source != 'internal':
                    preferred_signal = signal
                    break
            
            # If no preferred source found, use first signal
            if not preferred_signal:
                preferred_signal = signal_list[0]
            
            unique_signals.append(preferred_signal)
            
            logger.debug(
                f"Deduplicated {len(signal_list)} signals with key '{key}', "
                f"kept signal from source '{preferred_signal.payload.get('signal_source', 'unknown')}'"
            )
    
    if duplicate_count > 0:
        logger.info(
            f"Deduplicated signals: {len(signals)} → {len(unique_signals)} "
            f"(removed {duplicate_count} duplicates)"
        )
    
    return unique_signals


def deduplicate_by_similarity(signals: List[SignalData], similarity_threshold: float = 0.95) -> List[SignalData]:
    """
    Remove signals with very high similarity (alternative deduplication method)
    
    Args:
        signals: List of SignalData objects
        similarity_threshold: Threshold above which signals are considered duplicates
        
    Returns:
        Deduplicated list, keeping signals with highest similarity scores
    """
    if not signals:
        return signals
    
    # Sort by similarity (descending) to keep highest quality signals
    sorted_signals = sorted(signals, key=lambda s: s.similarity, reverse=True)
    
    unique_signals: List[SignalData] = []
    seen_keys: Set[str] = set()
    
    for signal in sorted_signals:
        key = get_signal_unique_key(signal)
        
        if not key:
            # Signals without key - keep all
            unique_signals.append(signal)
            continue
        
        if key not in seen_keys:
            seen_keys.add(key)
            unique_signals.append(signal)
    
    return unique_signals
