import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

collections = client.get_collections()

print("\n📦 QDRANT CLOUD COLLECTIONS:")
print("=" * 70)

for col in collections.collections:
    col_info = client.get_collection(col.name)
    
    print(f"\n🗂️  {col.name}")
    print(f"    Points: {col_info.points_count:,}")
    
    if 'customer_5' in col.name:
        print(f"    ⭐ CUSTOMER 5 DATA")
    elif 'customer_1' in col.name:
        print(f"    ℹ️  Customer 1 data")
        
    try:
        sample = client.scroll(
            collection_name=col.name,
            limit=1,
            with_payload=True
        )
        
        points = sample[0]
        if points:
            payload = points[0].payload
            field_names = list(paylo           print(f"    Fields: {', '.join(field_names[:8])}")
            
            if 'account_id' in payload:
                print(f"    Sample account_id: {payload['account_id']}")
            
            if 'text' in payload:
                text = payload['text']
                if len(text) > 80:
                    text = text[:80] + "..."
                print(f"    Sample: {text}")
                
    except Exception as e:
        print(f"    Error getting sample: {e}")

print("\n" + "=" * 70)
print(f"Total collections: {len(collections.collections)}")

print("\n🎯 KEY FINDINGS:")
collection_names = [col.name for col in collections.collections]
has_customer_5 = any('customer_5' in name for name icollection_names)

if has_customer_5:
    print("✅ Customer 5 collection EXISTS")
else:
    print("❌ Customer 5 collection MISSING")
    print("   → This explains why only 1 qualitative signal!")
    print("   → Qdrant has customer_1 data, not customer_5")

