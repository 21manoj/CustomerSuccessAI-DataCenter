#!/usr/bin/env python3
"""Load qualitative_signals.csv into PostgreSQL"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

print("=" * 70)
print("LOADING QUALITATIVE SIGNALS INTO POSTGRESQL")
print("=" * 70)

# Read CSV - updated path to match actual location
csv_path = '/Users/manojgupta/Downloads/qualitative_signals.csv'
if not os.path.exists(csv_path):
    print(f"❌ CSV file not found at: {csv_path}")
    sys.exit(1)

df = pd.read_csv(csv_path)

print(f"\nLoaded {len(df)} signals from CSV")
print(f"Unique accounts in CSV: {df['account_id'].nunique()}")
print(f"Signal types: {df['signal_type'].value_counts().to_dict()}")

# Connect to database
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("❌ DATABASE_URL not set")
    sys.exit(1)

engine = create_engine(database_url)

# Get valid account IDs from database
print("\nChecking valid accounts in database...")
with engine.connect() as conn:
    result = conn.execute(text("SELECT DISTINCT account_id FROM accounts ORDER BY account_id")).fetchall()
    valid_account_ids = set([row[0] for row in result])

# Filter to only valid accounts
df = df[df['account_id'].isin(valid_account_ids)]
print(f"Filtered to {len(df)} signals for {df['account_id'].nunique()} valid accounts")
print(f"Valid account IDs: {sorted(df['account_id'].unique())}")

# Check if table exists and has data
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM qualitative_signals")).fetchone()
    existing_count = result[0]
    
    if existing_count > 0:
        print(f"\n⚠️  Table already has {existing_count} signals")
        print("Clearing existing data and reloading...")
        conn.execute(text("DELETE FROM qualitative_signals"))
        conn.commit()
        print("✅ Cleared existing data")

# Prepare data for insertion
print("\nPreparing data for insertion...")

# Add missing columns
df['subject'] = df['summary']  # Use summary as subject
df['keywords'] = None  # Will be populated later
df['priority'] = 'medium'  # Default priority
df['source_system'] = df['signal_type'].apply(lambda x: 
    'email' if x == 'email' else 
    'calendar' if x == 'meeting' else 
    'support_tickets'
)

# Ensure date is datetime
df['date'] = pd.to_datetime(df['date']).dt.date

# Insert into database
print(f"\nInserting {len(df)} signals into PostgreSQL...")

inserted = 0
errors = 0
error_rows = []

# Process in batches with individual transactions per row to handle errors gracefully
batch_size = 100

for batch_start in range(0, len(df), batch_size):
    batch_end = min(batch_start + batch_size, len(df))
    batch_df = df.iloc[batch_start:batch_end]
    
    # Process each row in its own transaction
    for idx, row in batch_df.iterrows():
        try:
            # Handle None/NaN values
            from_contact = str(row.get('from_contact', '')) if pd.notna(row.get('from_contact')) else ''
            to_contact = str(row.get('to_contact', '')) if pd.notna(row.get('to_contact')) else ''
            summary_text = str(row['summary']) if pd.notna(row['summary']) else ''
            subject_text = summary_text[:500]  # Truncate subject to 500 chars
            sentiment = str(row['sentiment']) if pd.notna(row['sentiment']) else 'neutral'
            
            with engine.begin() as conn:  # Each row gets its own transaction
                conn.execute(text("""
                    INSERT INTO qualitative_signals (
                        account_id, date, signal_type, from_contact, to_contact,
                        subject, summary, sentiment, priority, keywords, source_system
                    ) VALUES (
                        :account_id, :date, :signal_type, :from_contact, :to_contact,
                        :subject, :summary, :sentiment, :priority, :keywords, :source_system
                    )
                """), {
                    "account_id": int(row['account_id']),
                    "date": row['date'],
                    "signal_type": str(row['signal_type']),
                    "from_contact": from_contact[:255] if len(from_contact) > 255 else from_contact,
                    "to_contact": to_contact[:255] if len(to_contact) > 255 else to_contact,
                    "subject": subject_text,
                    "summary": summary_text,
                    "sentiment": sentiment,
                    "priority": 'medium',
                    "keywords": None,
                    "source_system": str(row['source_system'])
                })
            inserted += 1
        except Exception as e:
            errors += 1
            error_rows.append((idx + 1, str(e)))
            if errors <= 5:  # Only print first few errors
                print(f"  ⚠️  Error inserting row {idx + 1}: {e}")
    
    if (batch_end) % 100 == 0 or batch_end == len(df):
        print(f"  Processed {batch_end}/{len(df)} signals... (inserted: {inserted}, errors: {errors})")
    
    if errors > 50:  # Stop if too many errors
        print("  ⚠️  Too many errors, stopping...")
        break

print(f"\n✅ Successfully inserted {inserted} signals!")
if errors > 0:
    print(f"⚠️  {errors} errors occurred during insertion")

# Verify
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM qualitative_signals")).fetchone()
    total_count = result[0]
    
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    print(f"\nTotal signals in database: {total_count}")
    
    # Show breakdown by account
    result = conn.execute(text("""
        SELECT account_id, COUNT(*) as signal_count
        FROM qualitative_signals
        GROUP BY account_id
        ORDER BY account_id
    """)).fetchall()
    
    print("\nSignals per account:")
    for row in result:
        print(f"  Account {row[0]}: {row[1]} signals")
    
    # Show sentiment distribution
    result = conn.execute(text("""
        SELECT sentiment, COUNT(*) as count
        FROM qualitative_signals
        GROUP BY sentiment
        ORDER BY count DESC
    """)).fetchall()
    
    print("\nSentiment distribution:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")
    
    # Show signal type distribution
    result = conn.execute(text("""
        SELECT signal_type, COUNT(*) as count
        FROM qualitative_signals
        GROUP BY signal_type
        ORDER BY count DESC
    """)).fetchall()
    
    print("\nSignal type distribution:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")

print("\n" + "=" * 70)
print("READY FOR VECTOR EMBEDDING!")
print("=" * 70)
print("\nNext step: Run embed_signals_openai.py to upload to Qdrant")

