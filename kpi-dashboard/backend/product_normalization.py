#!/usr/bin/env python3
"""
Product Name Normalization and Similarity Search
Handles product name deduplication, typo detection, and linking to master catalog
"""

from models import db, Account, ProductCatalog
from difflib import SequenceMatcher
import re


def normalize_product_name(name: str) -> str:
    """Normalize product name for comparison"""
    if not name:
        return ""
    # Lowercase, trim, remove extra spaces
    normalized = re.sub(r'\s+', ' ', name.strip().lower())
    # Remove special characters (keep alphanumeric and spaces)
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    return normalized.strip()


def similarity_score(str1: str, str2: str) -> float:
    """Calculate similarity score between two strings (0.0 to 1.0)"""
    if not str1 or not str2:
        return 0.0
    
    norm1 = normalize_product_name(str1)
    norm2 = normalize_product_name(str2)
    
    if norm1 == norm2:
        return 1.0
    
    # Use SequenceMatcher for similarity
    return SequenceMatcher(None, norm1, norm2).ratio()


def find_or_create_product(customer_id: int, product_name: str, product_sku: str = None, 
                          product_type: str = None, similarity_threshold: float = 0.85) -> ProductCatalog:
    """
    Find existing product in catalog or create new one
    Uses similarity search to handle typos and variations
    
    Args:
        customer_id: Customer ID
        product_name: Product name (may have typos/variations)
        product_sku: Optional SKU
        product_type: Optional product type
        similarity_threshold: Minimum similarity to consider a match (default 0.85)
    
    Returns:
        ProductCatalog instance (existing or newly created)
    """
    if not product_name or not product_name.strip():
        raise ValueError("Product name cannot be empty")
    
    normalized_name = normalize_product_name(product_name)
    
    # Step 1: Try exact match (normalized)
    existing = ProductCatalog.query.filter_by(
        customer_id=customer_id,
        product_name=normalized_name
    ).first()
    
    if existing:
        return existing
    
    # Step 2: Try similarity search across all products for this customer
    all_products = ProductCatalog.query.filter_by(customer_id=customer_id).all()
    
    best_match = None
    best_score = 0.0
    
    for product in all_products:
        score = similarity_score(product_name, product.product_name)
        if score > best_score and score >= similarity_threshold:
            best_score = score
            best_match = product
    
    if best_match:
        print(f"🔗 Matched '{product_name}' to existing product '{best_match.product_name}' (similarity: {best_score:.2f})")
        return best_match
    
    # Step 3: Create new product in catalog
    # Use original product_name (capitalized properly) as canonical name
    canonical_name = product_name.strip()
    
    # Double-check if product exists (race condition protection)
    existing_check = ProductCatalog.query.filter_by(
        customer_id=customer_id,
        product_name=canonical_name
    ).first()
    
    if existing_check:
        return existing_check
    
    try:
        new_product = ProductCatalog(
            customer_id=customer_id,
            product_name=canonical_name,
            product_sku=product_sku,
            product_type=product_type,
            status='active'
        )
        
        db.session.add(new_product)
        db.session.flush()  # Get product_id
        
        print(f"✅ Created new product in catalog: '{canonical_name}' (ID: {new_product.product_id})")
        return new_product
    except Exception as e:
        # Handle race condition - product might have been created by another process
        db.session.rollback()
        existing = ProductCatalog.query.filter_by(
            customer_id=customer_id,
            product_name=canonical_name
        ).first()
        if existing:
            print(f"⚠️ Product '{canonical_name}' already exists (race condition), using existing (ID: {existing.product_id})")
            return existing
        raise


def extract_products_from_account(account: Account) -> list:
    """
    Extract product names from account metadata
    Returns list of product names (may have typos/variations)
    """
    products = []
    
    # Priority 1: profile_metadata.products_used (comma-separated string)
    if account.profile_metadata and account.profile_metadata.get('products_used'):
        products_str = account.profile_metadata['products_used']
        if products_str and isinstance(products_str, str):
            products.extend([p.strip() for p in products_str.split(',') if p.strip()])
    
    # Priority 2: products_used from Product table (if exists)
    # Note: Account model doesn't have products_used attribute directly
    # Products are stored in profile_metadata.products_used or in Product table
    
    # Remove duplicates (case-insensitive)
    seen = set()
    unique_products = []
    for p in products:
        normalized = normalize_product_name(p)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique_products.append(p)  # Keep original casing
    
    return unique_products


def sync_account_products_to_catalog(account: Account) -> list:
    """
    Sync account's products to master catalog
    Returns list of ProductCatalog instances linked to this account
    """
    product_names = extract_products_from_account(account)
    
    if not product_names:
        return []
    
    linked_products = []
    for product_name in product_names:
        try:
            product = find_or_create_product(
                customer_id=account.customer_id,
                product_name=product_name
            )
            linked_products.append(product)
        except Exception as e:
            print(f"⚠️ Error processing product '{product_name}' for account {account.account_id}: {str(e)}")
            continue
    
    return linked_products
