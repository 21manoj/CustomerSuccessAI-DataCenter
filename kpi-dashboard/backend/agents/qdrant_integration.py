"""
Qdrant Integration Helper for Signal Analyst Agent

Retrieves signals from existing Qdrant collections and converts them to SignalData format

FIXED VERSION: Now directly queries kpi_dashboard_vectors_customer_{customer_id} collection
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
    
    FIXED: Now directly queries kpi_dashboard_vectors_customer_{customer_id} collection
    instead of using RAG abstraction layer that looked for non-existent collections.
    
    Args:
        rag_system: Instance of EnhancedRAGSystemQdrant (contains qdrant_client)
        account_id: Account ID to query for
        customer_id: Customer ID (for tenant isolation)
        collection_type: Type of collection ('quantitative', 'qualitative', 'historical')
        query_text: Query text (optional, will auto-generate if not provided)
        top_k: Number of results to return
        
    Returns:
        List of SignalData objects
    """
    try:
        # Get Qdrant client from RAG system
        qdrant_client = rag_system.qdrant_client
        
        # Use per-customer collection for ALL signal types (quantitative, qualitative, temporal)
        # All data types go into the same customer-specific collection
        # Use payload metadata to distinguish signal types instead of separate collections
        collection_name = f"kpi_dashboard_vectors_customer_{customer_id}"
        
        logger.info(f"Querying Qdrant collection: {collection_name} for account {account_id} (type: {collection_type})")
        
        # Generate query text if not provided
        if not query_text:
            if collection_type == 'quantitative':
                query_text = f"account {account_id} KPI metrics usage revenue health score quantitative data"
            elif collection_type == 'qualitative':
                query_text = f"account {account_id} support tickets emails notes sentiment qualitative data"
            else:  # historical
                query_text = f"account {account_id} historical trends patterns time series churn expansion outcomes"
        
        # Generate embedding for the query using RAG system's _generate_embedding method
        query_embedding = rag_system._generate_embedding(query_text, customer_id)
        
        # Query Qdrant directly using query_points (the correct method name)
        query_response = qdrant_client.query_points(
            collection_name=collection_name,
            query=query_embedding,  # Direct embedding vector
            limit=top_k * 3,  # Get more results, then filter by account_id
            with_payload=True
        )
        
        # Extract results from query_response
        search_results = query_response.points
        
        # Convert results to SignalData format and filter by account_id
        filtered_signals = []
        
        for result in search_results:
            payload = result.payload
            
            # Filter by account_id - only include signals for this specific account
            result_account_id = payload.get('account_id')
            if result_account_id and str(result_account_id) == str(account_id):
                # Create SignalData with similarity score from Qdrant
                # Qdrant query_points returns results with 'score' attribute
                signal = SignalData(
                    similarity=float(result.score),
                    payload=payload
                )
                filtered_signals.append(signal)
                
                # Stop when we have enough signals
                if len(filtered_signals) >= top_k:
                    break
        
        logger.info(
            f"Retrieved {len(filtered_signals)} {collection_type} signals for account {account_id} "
            f"from collection {collection_name}"
        )
        
        return filtered_signals
        
    except Exception as e:
        collection_name = f"kpi_dashboard_vectors_customer_{customer_id}"
        logger.error(f"Error querying Qdrant for signals: {e}", exc_info=True)
        logger.error(f"Collection: {collection_name}, Account: {account_id}, Type: {collection_type}")
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

