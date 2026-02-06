"""
Qdrant Integration Helper for Signal Analyst Agent

Retrieves signals from existing Qdrant collections and converts them to SignalData format
"""

from typing import List, Dict, Optional
import logging
from .models import SignalData

logger = logging.getLogger(__name__)


def convert_qdrant_results_to_signal_data(
    qdrant_results: List[Dict],
    default_similarity: float = 0.5
) -> List[SignalData]:
    """
    Convert Qdrant search results to SignalData format
    
    Args:
        qdrant_results: List of results from Qdrant query
                       Expected format: [{'similarity': float, 'text': str, 'metadata': dict}, ...]
        default_similarity: Default similarity score if not present in result
        
    Returns:
        List of SignalData objects
    """
    signal_data_list = []
    
    for result in qdrant_results:
        try:
            # Extract similarity score
            similarity = result.get('similarity', default_similarity)
            
            # Extract payload (metadata + text)
            metadata = result.get('metadata', {})
            text = result.get('text', '')
            
            # Build payload dictionary
            payload = {
                'text': text,
                **metadata  # Merge metadata into payload
            }
            
            # Create SignalData
            signal_data = SignalData(
                similarity=float(similarity),
                payload=payload
            )
            
            signal_data_list.append(signal_data)
            
        except Exception as e:
            logger.warning(f"Failed to convert Qdrant result to SignalData: {e}")
            continue
    
    return signal_data_list


def query_qdrant_for_signals(
    rag_system,
    account_id: str,
    customer_id: int,
    collection_type: str = 'quantitative',
    query_text: Optional[str] = None,
    top_k: int = 20
) -> List[SignalData]:
    """
    Query Qdrant collection for signals related to an account
    
    This function uses the RAG system's internal query method to search for signals.
    Note: Currently uses the main collection. For separate quantitative/qualitative/historical
    collections, the RAG system would need to be extended.
    
    Args:
        rag_system: Instance of EnhancedRAGSystemQdrant
        account_id: Account ID to query for
        customer_id: Customer ID (for tenant isolation)
        collection_type: Type of collection ('quantitative', 'qualitative', 'historical')
        query_text: Query text (optional, will auto-generate if not provided)
        top_k: Number of results to return
        
    Returns:
        List of SignalData objects
    """
    try:
        # Generate query text if not provided
        if not query_text:
            if collection_type == 'quantitative':
                query_text = f"account {account_id} KPI metrics usage revenue health score quantitative data"
            elif collection_type == 'qualitative':
                query_text = f"account {account_id} support tickets emails notes sentiment qualitative data"
            else:  # historical
                query_text = f"account {account_id} historical trends patterns time series churn expansion outcomes"
        
        # Query the RAG system with appropriate collection type
        # Note: The RAG system's query method handles the collection internally
        result = rag_system.query(query_text, query_type='general', collection=collection_type)
        
        # Check for errors
        if 'error' in result:
            logger.warning(f"Qdrant query error: {result['error']}")
            return []
        
        # Extract relevant results
        relevant_results = result.get('relevant_results', [])
        
        # Convert to SignalData format
        signal_data_list = convert_qdrant_results_to_signal_data(relevant_results)
        
        # Filter by account_id if metadata contains it
        filtered_signals = []
        for signal in signal_data_list:
            payload = signal.payload
            signal_account_id = payload.get('account_id')
            
            # Include if account_id matches or if no account_id (general signals)
            if not signal_account_id or str(signal_account_id) == str(account_id):
                filtered_signals.append(signal)
        
        return filtered_signals[:top_k]
        
    except Exception as e:
        logger.error(f"Error querying Qdrant for signals: {e}", exc_info=True)
        return []


def get_quantitative_signals_from_qdrant(
    rag_system,
    account_id: str,
    customer_id: int,
    top_k: int = 20
) -> List[SignalData]:
    """Get quantitative signals from Qdrant for an account"""
    query_text = f"account {account_id} KPI metrics usage revenue health score quantitative data"
    return query_qdrant_for_signals(
        rag_system=rag_system,
        account_id=account_id,
        customer_id=customer_id,
        collection_type='quantitative',
        query_text=query_text,
        top_k=top_k
    )


def get_qualitative_signals_from_qdrant(
    rag_system,
    account_id: str,
    customer_id: int,
    top_k: int = 20
) -> List[SignalData]:
    """Get qualitative signals from Qdrant for an account"""
    query_text = f"account {account_id} support tickets emails notes sentiment qualitative data"
    return query_qdrant_for_signals(
        rag_system=rag_system,
        account_id=account_id,
        customer_id=customer_id,
        collection_type='qualitative',
        query_text=query_text,
        top_k=top_k
    )


def get_historical_patterns_from_qdrant(
    rag_system,
    account_id: str,
    customer_id: int,
    top_k: int = 10
) -> List[SignalData]:
    """Get historical patterns from Qdrant for an account"""
    query_text = f"account {account_id} historical trends patterns time series churn expansion outcomes"
    return query_qdrant_for_signals(
        rag_system=rag_system,
        account_id=account_id,
        customer_id=customer_id,
        collection_type='historical',
        query_text=query_text,
        top_k=top_k
    )

