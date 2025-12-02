"""
Helper functions for querying KPIs with product dimension support.

⚠️ CRITICAL: These functions ensure correct filtering to prevent double-counting
in health score calculations and other account-level operations.

All queries should use these helpers instead of direct KPI.query.filter_by() calls.
"""

from models import KPI, Account, Product
from extensions import db
from sqlalchemy import and_, or_
import logging

logger = logging.getLogger(__name__)


def get_account_level_kpis(
    account_id: int, 
    customer_id: int = None,
    aggregation_type: str = None
) -> list:
    """
    Get account-level KPIs only (excludes product-level KPIs).
    
    Args:
        account_id: Account ID
        customer_id: Optional customer ID for tenant isolation
        aggregation_type: Optional filter ('weighted_avg', 'min', 'max', etc.)
                         If None, returns primary aggregates (NULL or 'weighted_avg')
    
    Returns:
        List of account-level KPI objects
    
    ⚠️ CRITICAL: This excludes product-level KPIs. Use this for:
        - Health score calculations
        - Account-level reporting
        - Customer rollup calculations
    """
    query = KPI.query.filter(
        KPI.account_id == account_id,
        KPI.product_id.is_(None)  # ✅ CRITICAL: Only account-level
    )
    
    # Filter by aggregation type
    if aggregation_type:
        query = query.filter(KPI.aggregation_type == aggregation_type)
    else:
        # Default: Get primary aggregates only (weighted_avg or legacy NULL)
        query = query.filter(
            or_(
                KPI.aggregation_type == 'weighted_avg',
                KPI.aggregation_type.is_(None)
            )
        )
    
    if customer_id:
        query = query.join(Account).filter(Account.customer_id == customer_id)
    
    results = query.all()
    
    # Validation: Log if we got unexpected results
    if customer_id:
        logger.info(
            f"Retrieved {len(results)} account-level KPIs for "
            f"account_id={account_id}, customer_id={customer_id}, "
            f"aggregation_type={aggregation_type}"
        )
    
    return results


def get_product_kpis(
    account_id: int, 
    product_id: int = None, 
    customer_id: int = None
) -> list:
    """
    Get product-level KPIs.
    
    Args:
        account_id: Account ID
        product_id: Optional product ID (if None, returns all products for account)
        customer_id: Optional customer ID for tenant isolation
    
    Returns:
        List of product-level KPI objects
        
    ⚠️ This returns ONLY product-level KPIs (product_id IS NOT NULL).
    """
    query = KPI.query.filter(
        KPI.account_id == account_id,
        KPI.product_id.isnot(None)  # ✅ Only product-level
    )
    
    if product_id:
        query = query.filter(KPI.product_id == product_id)
    
    if customer_id:
        query = query.join(Account).filter(Account.customer_id == customer_id)
    
    results = query.all()
    
    # Validation: Ensure all have product_id
    for kpi in results:
        assert kpi.product_id is not None, \
            f"KPI {kpi.kpi_id} has NULL product_id but was returned by get_product_kpis()"
    
    logger.info(
        f"Retrieved {len(results)} product-level KPIs for "
        f"account_id={account_id}, product_id={product_id}"
    )
    
    return results


def get_all_kpis_for_account(
    account_id: int, 
    customer_id: int = None,
    include_aggregates: bool = True
) -> dict:
    """
    Get ALL KPIs for an account in a structured format.
    
    Args:
        account_id: Account ID
        customer_id: Optional customer ID for tenant isolation
        include_aggregates: Whether to include min/max aggregates
    
    Returns:
        {
            'account_level': [...],  # Account aggregate KPIs
            'products': {
                product_id: [...],   # Product-specific KPIs
                ...
            },
            'aggregates': {
                'min': [...],        # Min aggregates (optional)
                'max': [...],        # Max aggregates (optional)
            }
        }
        
    ⚠️ Use this for UI drill-down, NOT for health score calculations.
    """
    result = {
        'account_level': [],
        'products': {},
        'aggregates': {
            'min': [],
            'max': [],
            'sum': [],
            'equal_weight': []
        }
    }
    
    # Get account-level KPIs (primary)
    account_level_kpis = get_account_level_kpis(
        account_id, 
        customer_id, 
        aggregation_type=None  # Primary only
    )
    # Dedupe: ensure one Account Level row per parameter with precedence:
    # 1) weighted_avg if present  2) latest legacy (NULL aggregation) by kpi_id
    deduped_by_param = {}
    for kpi in account_level_kpis:
        param = kpi.kpi_parameter
        current = deduped_by_param.get(param)
        if current is None:
            deduped_by_param[param] = kpi
            continue
        # Prefer weighted_avg over NULL
        if (kpi.aggregation_type == 'weighted_avg' and
            (current.aggregation_type is None or current.aggregation_type != 'weighted_avg')):
            deduped_by_param[param] = kpi
            continue
        # If both are same precedence, keep the one with higher kpi_id (assumed newer)
        if (kpi.aggregation_type == current.aggregation_type) and (getattr(kpi, 'kpi_id', 0) > getattr(current, 'kpi_id', 0)):
            deduped_by_param[param] = kpi
    deduped_account_level = list(deduped_by_param.values())

    # If the account has zero products, suppress Product Usage KPIs (cannot be derived meaningfully)
    try:
        account = db.session.get(Account, account_id)
        product_count = len(account.products) if account and account.products is not None else 0
    except Exception:
        product_count = 0
    if product_count == 0:
        product_usage_params = {
            "Product Activation Rate",
            "Feature Adoption Rate",
            "Onboarding Completion Rate",
            "Time to First Value (TTFV)",
            "Training Participation Rate",
            "Knowledge Base Usage",
            "Learning Path Completion Rate",
        }
        deduped_account_level = [
            k for k in deduped_account_level
            if k.kpi_parameter not in product_usage_params
        ]

    result['account_level'] = deduped_account_level
    
    # Get aggregates (if requested)
    if include_aggregates:
        for agg_type in ['min', 'max', 'sum', 'equal_weight']:
            query = KPI.query.filter(
                KPI.account_id == account_id,
                KPI.product_id.is_(None),
                KPI.aggregation_type == agg_type
            )
            
            if customer_id:
                query = query.join(Account).filter(Account.customer_id == customer_id)
            
            result['aggregates'][agg_type] = query.all()
    
    # Get product-level KPIs grouped by product
    product_kpis = get_product_kpis(account_id, customer_id=customer_id)
    
    for kpi in product_kpis:
        if kpi.product_id not in result['products']:
            result['products'][kpi.product_id] = []
        result['products'][kpi.product_id].append(kpi)
    
    logger.info(
        f"Retrieved structured KPIs for account_id={account_id}: "
        f"{len(result['account_level'])} account-level, "
        f"{len(result['products'])} products, "
        f"{sum(len(agg) for agg in result['aggregates'].values())} aggregates"
    )
    
    return result


def get_worst_product_kpis(
    account_id: int,
    customer_id: int = None
) -> list:
    """
    Get the "worst case" KPIs for an account (max aggregation_type).
    
    Useful for alerting: "Which product is struggling?"
    
    Returns:
        List of account-level KPIs with aggregation_type='max'
    """
    query = KPI.query.filter(
        KPI.account_id == account_id,
        KPI.product_id.is_(None),
        KPI.aggregation_type == 'max'
    )
    
    if customer_id:
        query = query.join(Account).filter(Account.customer_id == customer_id)
    
    return query.all()


def get_best_product_kpis(
    account_id: int,
    customer_id: int = None
) -> list:
    """
    Get the "best case" KPIs for an account (min aggregation_type).
    
    Useful for reporting: "Which product is performing best?"
    
    Returns:
        List of account-level KPIs with aggregation_type='min'
    """
    query = KPI.query.filter(
        KPI.account_id == account_id,
        KPI.product_id.is_(None),
        KPI.aggregation_type == 'min'
    )
    
    if customer_id:
        query = query.join(Account).filter(Account.customer_id == customer_id)
    
    return query.all()


