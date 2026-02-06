#!/usr/bin/env python3
"""
Test Script for Signals Query Helper
====================================

Tests the qualitative_signals query with your existing schema.

Usage:
    # Set your database URL
    export DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"
    
    # Run test
    python test_signals_query.py
    
    # Test specific account
    python test_signals_query.py --account-id 12345
    
    # Test with filters
    python test_signals_query.py --account-id 12345 --type email --sentiment negative
"""

import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_db_connection():
    """Get database connection"""
    from sqlalchemy import create_engine
    
    database_url = os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_DATABASE_URI')
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print("   Set it with: export DATABASE_URL='postgresql://user:pass@host:5432/dbname'")
        sys.exit(1)
    
    print(f"📡 Connecting to: {database_url[:50]}...")
    engine = create_engine(database_url)
    return engine.connect()


def test_table_exists(conn):
    """Test that qualitative_signals table exists"""
    from sqlalchemy import text
    
    print("\n" + "="*60)
    print("TEST 1: Table Exists")
    print("="*60)
    
    try:
        result = conn.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_name = 'qualitative_signals'
        """))
        row = result.fetchone()
        
        if row and row.count > 0:
            print("✅ qualitative_signals table exists")
            return True
        else:
            print("❌ qualitative_signals table NOT found")
            return False
    except Exception as e:
        print(f"❌ Error checking table: {e}")
        return False


def test_table_schema(conn):
    """Test and display table schema"""
    from sqlalchemy import text
    
    print("\n" + "="*60)
    print("TEST 2: Table Schema")
    print("="*60)
    
    try:
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'qualitative_signals'
            ORDER BY ordinal_position
        """))
        
        print(f"{'Column':<25} {'Type':<20} {'Nullable':<10}")
        print("-"*55)
        
        columns = []
        for row in result:
            print(f"{row.column_name:<25} {row.data_type:<20} {row.is_nullable:<10}")
            columns.append(row.column_name)
        
        # Check required columns exist
        required = ['signal_id', 'account_id', 'signal_date', 'signal_type', 
                   'content', 'sentiment', 'sentiment_score']
        missing = [c for c in required if c not in columns]
        
        if missing:
            print(f"\n⚠️  Missing expected columns: {missing}")
        else:
            print(f"\n✅ All required columns present")
        
        return columns
        
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        return []


def test_row_count(conn):
    """Test total row count"""
    from sqlalchemy import text
    
    print("\n" + "="*60)
    print("TEST 3: Row Count")
    print("="*60)
    
    try:
        result = conn.execute(text("SELECT COUNT(*) as count FROM qualitative_signals"))
        row = result.fetchone()
        count = row.count if row else 0
        
        print(f"📊 Total signals in table: {count}")
        
        if count == 0:
            print("⚠️  Table is empty - no data to test with")
        
        return count
        
    except Exception as e:
        print(f"❌ Error counting rows: {e}")
        return 0


def test_account_ids(conn):
    """Get list of account IDs with signals"""
    from sqlalchemy import text
    
    print("\n" + "="*60)
    print("TEST 4: Available Account IDs")
    print("="*60)
    
    try:
        result = conn.execute(text("""
            SELECT account_id, COUNT(*) as signal_count
            FROM qualitative_signals
            GROUP BY account_id
            ORDER BY signal_count DESC
            LIMIT 10
        """))
        
        account_ids = []
        print(f"{'Account ID':<15} {'Signal Count':<15}")
        print("-"*30)
        
        for row in result:
            print(f"{row.account_id:<15} {row.signal_count:<15}")
            account_ids.append(row.account_id)
        
        if account_ids:
            print(f"\n💡 Use --account-id {account_ids[0]} to test with most signals")
        
        return account_ids
        
    except Exception as e:
        print(f"❌ Error getting account IDs: {e}")
        return []


def test_signal_types(conn):
    """Get distribution of signal types"""
    from sqlalchemy import text
    
    print("\n" + "="*60)
    print("TEST 5: Signal Type Distribution")
    print("="*60)
    
    try:
        result = conn.execute(text("""
            SELECT signal_type, COUNT(*) as count
            FROM qualitative_signals
            GROUP BY signal_type
            ORDER BY count DESC
        """))
        
        print(f"{'Signal Type':<20} {'Count':<10}")
        print("-"*30)
        
        for row in result:
            print(f"{row.signal_type or 'NULL':<20} {row.count:<10}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_sentiment_distribution(conn):
    """Get distribution of sentiments"""
    from sqlalchemy import text
    
    print("\n" + "="*60)
    print("TEST 6: Sentiment Distribution")
    print("="*60)
    
    try:
        result = conn.execute(text("""
            SELECT 
                sentiment, 
                COUNT(*) as count,
                AVG(sentiment_score) as avg_score
            FROM qualitative_signals
            GROUP BY sentiment
            ORDER BY count DESC
        """))
        
        print(f"{'Sentiment':<15} {'Count':<10} {'Avg Score':<15}")
        print("-"*40)
        
        for row in result:
            avg = f"{row.avg_score:.2f}" if row.avg_score else "N/A"
            print(f"{row.sentiment or 'NULL':<15} {row.count:<10} {avg:<15}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_transformation(conn, account_id):
    """Test the transformation function with real data"""
    from sqlalchemy import text
    
    print("\n" + "="*60)
    print(f"TEST 7: Signal Transformation (Account {account_id})")
    print("="*60)
    
    # Import helper functions
    try:
        from signals_query_helper import transform_signal_row, get_signals_for_account, derive_priority, derive_health_impact
        use_helper = True
    except ImportError:
        print("⚠️  signals_query_helper.py not found in path")
        print("   Testing with inline transformation...")
        use_helper = False
        
        # Inline transformation for testing
        def derive_priority(sentiment, sentiment_score):
            if sentiment == 'negative' and sentiment_score and sentiment_score < -0.5:
                return 'critical'
            elif sentiment == 'negative':
                return 'high'
            elif sentiment == 'neutral':
                return 'medium'
            return 'low'
        
        def derive_health_impact(sentiment, sentiment_score):
            if sentiment_score is None:
                return 5 if sentiment == 'positive' else (-5 if sentiment == 'negative' else 0)
            return int(float(sentiment_score) * 15)
    
    try:
        # Get sample signals
        result = conn.execute(text("""
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
            ORDER BY signal_date DESC
            LIMIT 3
        """), {'account_id': account_id})
        
        rows = result.fetchall()
        
        if not rows:
            print(f"⚠️  No signals found for account {account_id}")
            return False
        
        print(f"📋 Found {len(rows)} signals, showing transformation:\n")
        
        for i, row in enumerate(rows):
            print(f"--- Signal {i+1} ---")
            print(f"  Raw signal_date: {row.signal_date}")
            print(f"  Raw content: {(row.content or '')[:80]}...")
            print(f"  Raw sentiment: {row.sentiment} (score: {row.sentiment_score})")
            print(f"  Raw stakeholder_level: {row.stakeholder_level}")
            print(f"  Raw stakeholder_title: {row.stakeholder_title}")
            
            # Transform
            sentiment_score = float(row.sentiment_score) if row.sentiment_score else None
            priority = derive_priority(row.sentiment, sentiment_score)
            health_impact = derive_health_impact(row.sentiment, sentiment_score)
            
            print(f"\n  → Transformed:")
            print(f"     date: {row.signal_date.isoformat() if row.signal_date else None}")
            print(f"     from_contact: {row.stakeholder_title}")
            print(f"     from_role: {row.stakeholder_level}")
            print(f"     priority: {priority}")
            print(f"     health_impact: {health_impact}")
            print()
        
        print("✅ Transformation test passed")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_query(conn, account_id, signal_type=None, sentiment=None):
    """Test the full query with filters"""
    from sqlalchemy import text
    
    print("\n" + "="*60)
    print(f"TEST 8: Full Query (Account {account_id})")
    if signal_type:
        print(f"         Filter: type={signal_type}")
    if sentiment:
        print(f"         Filter: sentiment={sentiment}")
    print("="*60)
    
    try:
        # Build query
        query = """
            SELECT 
                signal_id,
                account_id,
                signal_date,
                signal_type,
                stakeholder_level,
                stakeholder_title,
                LEFT(content, 100) as content_preview,
                sentiment,
                sentiment_score,
                keywords
            FROM qualitative_signals
            WHERE account_id = :account_id
        """
        params = {'account_id': account_id}
        
        if signal_type:
            query += " AND signal_type = :signal_type"
            params['signal_type'] = signal_type
        
        if sentiment:
            query += " AND sentiment = :sentiment"
            params['sentiment'] = sentiment
        
        query += " ORDER BY signal_date DESC LIMIT 5"
        
        result = conn.execute(text(query), params)
        rows = result.fetchall()
        
        print(f"\n📋 Results: {len(rows)} signals\n")
        
        for row in rows:
            print(f"  [{row.signal_type}] {row.signal_date} | {row.sentiment} ({row.sentiment_score})")
            print(f"    {row.content_preview}...")
            print()
        
        # Get counts
        count_query = """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE sentiment = 'positive') as positive,
                COUNT(*) FILTER (WHERE sentiment = 'negative') as negative,
                COUNT(*) FILTER (WHERE sentiment = 'neutral') as neutral
            FROM qualitative_signals
            WHERE account_id = :account_id
        """
        count_result = conn.execute(text(count_query), {'account_id': account_id})
        counts = count_result.fetchone()
        
        print(f"📊 Counts for account {account_id}:")
        print(f"   Total: {counts.total}")
        print(f"   Positive: {counts.positive}")
        print(f"   Negative: {counts.negative}")
        print(f"   Neutral: {counts.neutral}")
        
        print("\n✅ Full query test passed")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Test Signals Query Helper')
    parser.add_argument('--account-id', type=int, help='Specific account ID to test')
    parser.add_argument('--type', dest='signal_type', help='Filter by signal type')
    parser.add_argument('--sentiment', help='Filter by sentiment')
    parser.add_argument('--quick', action='store_true', help='Quick test only')
    args = parser.parse_args()
    
    print("="*60)
    print("   QUALITATIVE SIGNALS QUERY TEST")
    print("="*60)
    
    # Connect
    conn = get_db_connection()
    
    # Run tests
    if not test_table_exists(conn):
        print("\n❌ Cannot continue - table doesn't exist")
        conn.close()
        return
    
    test_table_schema(conn)
    count = test_row_count(conn)
    
    if count == 0:
        print("\n⚠️  No data to test - add some signals first")
        conn.close()
        return
    
    account_ids = test_account_ids(conn)
    
    if args.quick:
        print("\n✅ Quick test complete")
        conn.close()
        return
    
    test_signal_types(conn)
    test_sentiment_distribution(conn)
    
    # Use provided account ID or first available
    test_account = args.account_id or (account_ids[0] if account_ids else None)
    
    if test_account:
        test_transformation(conn, test_account)
        test_full_query(conn, test_account, args.signal_type, args.sentiment)
    else:
        print("\n⚠️  No account ID available for transformation test")
    
    conn.close()
    
    print("\n" + "="*60)
    print("   TEST COMPLETE")
    print("="*60)


if __name__ == '__main__':
    main()
