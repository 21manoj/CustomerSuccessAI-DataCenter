# AWS Database Migration Strategy

## Current State
- SQLite database (local file)
- Qdrant vector database (local files)
- Data size: ~11.3 MB total

## Migration Options

### Option 1: RDS PostgreSQL (Recommended)
```bash
# Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier kpi-dashboard-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password YourPassword123 \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-12345 \
  --db-subnet-group-name kpi-dashboard-subnet-group
```

### Option 2: Aurora Serverless (Auto-scaling)
```bash
# Create Aurora Serverless cluster
aws rds create-db-cluster \
  --db-cluster-identifier kpi-dashboard-aurora \
  --engine aurora-postgresql \
  --engine-mode serverless \
  --master-username admin \
  --master-user-password YourPassword123 \
  --scaling-configuration MinCapacity=2,MaxCapacity=16
```

## Vector Database Migration

### Option 1: Qdrant Cloud
```bash
# Sign up at https://cloud.qdrant.io/
# Create cluster
# Update connection string in app
```

### Option 2: Self-hosted Qdrant on ECS
```yaml
# qdrant-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qdrant
spec:
  replicas: 1
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:latest
        ports:
        - containerPort: 6333
        volumeMounts:
        - name: qdrant-storage
          mountPath: /qdrant/storage
      volumes:
      - name: qdrant-storage
        persistentVolumeClaim:
          claimName: qdrant-pvc
```

## Data Migration Script

```python
# migrate_to_aws.py
import sqlite3
import psycopg2
from sqlalchemy import create_engine
import pandas as pd

def migrate_sqlite_to_postgres():
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('backend/kpi_dashboard.db')
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(
        host="your-rds-endpoint.amazonaws.com",
        database="kpidashboard",
        user="admin",
        password="YourPassword123"
    )
    
    # Get all tables
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", sqlite_conn)
    
    for table in tables['name']:
        print(f"Migrating table: {table}")
        
        # Read data from SQLite
        df = pd.read_sql(f"SELECT * FROM {table}", sqlite_conn)
        
        # Write to PostgreSQL
        df.to_sql(table, pg_conn, if_exists='replace', index=False)
    
    print("Migration completed!")

if __name__ == "__main__":
    migrate_sqlite_to_postgres()
```

## Environment Variables Update

```bash
# Update for RDS PostgreSQL
export SQLALCHEMY_DATABASE_URI="postgresql://admin:YourPassword123@kpi-dashboard-db.xyz.us-east-1.rds.amazonaws.com:5432/kpidashboard"

# Update for Qdrant Cloud
export QDRANT_URL="https://your-cluster.qdrant.vector"
export QDRANT_API_KEY="your-api-key"
```

## Cost Estimates

### RDS PostgreSQL
- db.t3.micro: ~$15/month
- db.t3.small: ~$30/month

### Aurora Serverless
- Pay per use: ~$10-50/month

### Qdrant Cloud
- Free tier: 1GB storage
- Paid: ~$25-100/month

## Migration Steps

1. **Create AWS database**
2. **Run migration script**
3. **Update application configuration**
4. **Test with new database**
5. **Switch DNS/load balancer**
6. **Monitor and verify**

## Backup Strategy

```bash
# Automated RDS snapshots
aws rds create-db-snapshot \
  --db-instance-identifier kpi-dashboard-db \
  --db-snapshot-identifier kpi-dashboard-backup-$(date +%Y%m%d)

# Cross-region backup
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier kpi-dashboard-backup-20250111 \
  --target-db-snapshot-identifier kpi-dashboard-backup-20250111-dr \
  --source-region us-east-1 \
  --destination-region us-west-2
```
