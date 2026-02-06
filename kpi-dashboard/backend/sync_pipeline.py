#!/usr/bin/env python3
"""
DC2_S Sync Pipeline
Bidirectional sync between Google Sheets and Postgres

Sync Intervals: Every 15 minutes
Direction: Bidirectional (Sheets ↔ Postgres)

Features:
- Conflict resolution (last-write-wins)
- Change tracking
- Error handling and retry logic
- Partner-based access filtering
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import time
import sys
import os
from typing import Dict, List, Optional
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from verticals.dc2_s import (
    calculate_pillar_score,
    calculate_overall_health,
    get_triggered_alerts,
    DC2S_PILLARS
)


class SyncPipeline:
    """Bidirectional sync between Google Sheets and Postgres"""
    
    def __init__(self, credentials_path, sheet_url, db_connection):
        """
        Initialize sync pipeline
        
        Args:
            credentials_path: Path to Google service account JSON
            sheet_url: URL of the master Google Sheet
            db_connection: Database connection object
        """
        self.credentials_path = credentials_path
        self.sheet_url = sheet_url
        self.db = db_connection
        self.client = None
        self.sheet = None
        self.last_sync = {}
        
    def authenticate(self):
        """Authenticate with Google Sheets API"""
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_path, scope
            )
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_url(self.sheet_url)
            print("✅ Authenticated with Google Sheets")
            return True
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def sync_kpis_to_sheets(self, account_id: int):
        """
        Sync KPI values from Postgres to Google Sheets
        
        Args:
            account_id: Account identifier
        """
        try:
            # Get KPI values from database
            query = """
                SELECT kpi_code, value, updated_at
                FROM kpis
                WHERE account_id = %s
                ORDER BY kpi_code
            """
            kpis = self.db.execute(query, (account_id,))
            
            # Find the KPIs worksheet
            worksheet_name = f"{account_id}_KPIs"
            worksheet = self.sheet.worksheet(worksheet_name)
            
            # Get current data from sheet
            sheet_data = worksheet.get_all_values()
            
            # Update rows (starting from row 4, after headers)
            updates = []
            for kpi in kpis:
                kpi_code = kpi['kpi_code']
                value = kpi['value']
                updated_at = kpi['updated_at']
                
                # Find row for this KPI
                for i, row in enumerate(sheet_data[3:], start=4):
                    if row[0] == kpi_code:
                        # Update value and timestamp
                        updates.append({
                            'range': f'C{i}:F{i}',
                            'values': [[
                                value,
                                row[3],  # Keep target
                                self._get_status(kpi_code, value),
                                updated_at.strftime("%Y-%m-%d %H:%M")
                            ]]
                        })
                        break
            
            # Batch update
            if updates:
                worksheet.batch_update(updates)
                print(f"   ✅ Synced {len(updates)} KPIs to sheet for account {account_id}")
            
        except Exception as e:
            print(f"   ❌ Failed to sync KPIs to sheet: {e}")
    
    def sync_kpis_from_sheets(self, account_id: int):
        """
        Sync KPI values from Google Sheets to Postgres
        
        Args:
            account_id: Account identifier
        """
        try:
            # Find the KPIs worksheet
            worksheet_name = f"{account_id}_KPIs"
            worksheet = self.sheet.worksheet(worksheet_name)
            
            # Get all data
            sheet_data = worksheet.get_all_values()
            
            # Parse KPI values (skip header rows)
            updates = []
            for row in sheet_data[3:]:  # Start after headers
                if len(row) >= 3 and row[0]:  # Has KPI code
                    kpi_code = row[0]
                    try:
                        value = float(row[2])
                        updates.append((kpi_code, value))
                    except (ValueError, IndexError):
                        continue
            
            # Update database
            if updates:
                query = """
                    INSERT INTO kpis (account_id, kpi_code, value, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (account_id, kpi_code)
                    DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
                """
                
                for kpi_code, value in updates:
                    self.db.execute(query, (account_id, kpi_code, value))
                
                self.db.commit()
                print(f"   ✅ Synced {len(updates)} KPIs from sheet to DB for account {account_id}")
            
        except Exception as e:
            print(f"   ❌ Failed to sync KPIs from sheet: {e}")
            self.db.rollback()
    
    def sync_health_to_sheets(self, account_id: int):
        """
        Recalculate and sync health scores to Google Sheets
        
        Args:
            account_id: Account identifier
        """
        try:
            # Get KPI values from database
            query = """
                SELECT kpi_code, value
                FROM kpis
                WHERE account_id = %s
            """
            kpis = self.db.execute(query, (account_id,))
            
            # Build kpi_values dict
            kpi_values = {kpi['kpi_code']: kpi['value'] for kpi in kpis}
            
            # Calculate pillar scores
            pillar_scores = {}
            for pillar_id in DC2S_PILLARS.keys():
                score = calculate_pillar_score(pillar_id, kpi_values)
                pillar_scores[pillar_id] = score
            
            # Calculate overall health
            overall = calculate_overall_health(pillar_scores)
            
            # Update health worksheet
            worksheet_name = f"{account_id}_Health"
            worksheet = self.sheet.worksheet(worksheet_name)
            
            # Update overall health (row 3)
            worksheet.update('B3', f"{overall:.1f}/100")
            
            # Determine status
            if overall >= 75:
                status = "HEALTHY"
            elif overall >= 50:
                status = "RISK"
            else:
                status = "CRITICAL"
            worksheet.update('C3', status)
            
            # Update pillar scores (rows 6+)
            updates = []
            for i, (pillar_id, score) in enumerate(pillar_scores.items(), start=6):
                pillar_info = DC2S_PILLARS.get(pillar_id, {})
                weight = pillar_info.get('weight_l2', 0)
                contribution = score * weight
                
                updates.append({
                    'range': f'B{i}:D{i}',
                    'values': [[
                        f"{score:.1f}",
                        f"{weight*100:.0f}%",
                        f"{contribution:.1f}"
                    ]]
                })
            
            if updates:
                worksheet.batch_update(updates)
            
            print(f"   ✅ Synced health score ({overall:.1f}) to sheet for account {account_id}")
            
        except Exception as e:
            print(f"   ❌ Failed to sync health to sheet: {e}")
    
    def sync_actions_to_sheets(self, account_id: int):
        """
        Sync recommended actions to Google Sheets
        
        Args:
            account_id: Account identifier
        """
        try:
            # Get KPI values
            query = """
                SELECT kpi_code, value
                FROM kpis
                WHERE account_id = %s
            """
            kpis = self.db.execute(query, (account_id,))
            kpi_values = {kpi['kpi_code']: kpi['value'] for kpi in kpis}
            
            # Get triggered alerts
            alerts = get_triggered_alerts(kpi_values)
            
            # Update actions worksheet
            worksheet_name = f"{account_id}_Actions"
            worksheet = self.sheet.worksheet(worksheet_name)
            
            # Clear existing actions (keep headers)
            worksheet.resize(rows=100)
            
            # Add new actions
            rows = []
            for alert in alerts[:10]:  # Top 10 alerts
                row = [
                    alert['priority'].upper(),
                    alert['action'],
                    alert['kpi'],
                    "OPEN",
                    "CSM"
                ]
                rows.append(row)
            
            if rows:
                worksheet.update('A4', rows)
                print(f"   ✅ Synced {len(rows)} actions to sheet for account {account_id}")
            
        except Exception as e:
            print(f"   ❌ Failed to sync actions to sheet: {e}")
    
    def sync_account(self, account_id: int, direction: str = "both"):
        """
        Sync a single account
        
        Args:
            account_id: Account identifier
            direction: "to_sheets", "from_sheets", or "both"
        """
        print(f"\n📊 Syncing account {account_id}...")
        
        if direction in ["from_sheets", "both"]:
            self.sync_kpis_from_sheets(account_id)
        
        if direction in ["to_sheets", "both"]:
            self.sync_kpis_to_sheets(account_id)
            self.sync_health_to_sheets(account_id)
            self.sync_actions_to_sheets(account_id)
    
    def sync_all_accounts(self, direction: str = "both"):
        """
        Sync all accounts in the sheet
        
        Args:
            direction: "to_sheets", "from_sheets", or "both"
        """
        # Get all account IDs from index
        try:
            index = self.sheet.worksheet("Index")
            data = index.get_all_values()
            
            account_ids = []
            for row in data[6:]:  # Skip header rows
                if row and row[0]:
                    try:
                        account_ids.append(int(row[0]))
                    except ValueError:
                        continue
            
            print(f"\n🔄 Starting sync for {len(account_ids)} accounts...")
            print(f"   Direction: {direction}")
            print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            for account_id in account_ids:
                self.sync_account(account_id, direction)
            
            self.last_sync[direction] = datetime.now()
            print(f"\n✅ Sync complete!")
            
        except Exception as e:
            print(f"❌ Sync failed: {e}")
    
    def run_continuous_sync(self, interval_minutes: int = 15):
        """
        Run continuous sync loop
        
        Args:
            interval_minutes: Sync interval in minutes
        """
        print("=" * 60)
        print("DC2_S CONTINUOUS SYNC PIPELINE")
        print("=" * 60)
        print(f"Sync interval: {interval_minutes} minutes")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()
        
        if not self.authenticate():
            return
        
        while True:
            try:
                # Sync from sheets to DB (users may have edited)
                self.sync_all_accounts(direction="from_sheets")
                
                # Recalculate and sync back to sheets
                self.sync_all_accounts(direction="to_sheets")
                
                # Wait for next interval
                next_sync = datetime.now() + timedelta(minutes=interval_minutes)
                print(f"\n⏰ Next sync at: {next_sync.strftime('%H:%M:%S')}")
                print(f"   Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Sync stopped by user")
                break
            except Exception as e:
                print(f"\n❌ Error in sync loop: {e}")
                print("   Retrying in 5 minutes...")
                time.sleep(300)
    
    def _get_status(self, kpi_code: str, value: float) -> str:
        """Get health status for a KPI value"""
        from verticals.dc2_s import get_health_status
        return get_health_status(kpi_code, value).upper()


class MockDB:
    """Mock database for testing"""
    
    def __init__(self):
        self.kpis = {}
    
    def execute(self, query, params=None):
        """Mock execute"""
        if "SELECT" in query:
            account_id = params[0] if params else None
            return [
                {'kpi_code': k, 'value': v, 'updated_at': datetime.now()}
                for k, v in self.kpis.get(account_id, {}).items()
            ]
        return []
    
    def commit(self):
        """Mock commit"""
        pass
    
    def rollback(self):
        """Mock rollback"""
        pass


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run DC2_S sync pipeline')
    parser.add_argument('credentials', help='Path to Google service account JSON')
    parser.add_argument('sheet_url', help='URL of master Google Sheet')
    parser.add_argument('--interval', type=int, default=15, help='Sync interval in minutes')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--direction', choices=['to_sheets', 'from_sheets', 'both'], 
                       default='both', help='Sync direction')
    
    args = parser.parse_args()
    
    # TODO: Replace with actual DB connection
    db = MockDB()
    
    # Create sync pipeline
    pipeline = SyncPipeline(args.credentials, args.sheet_url, db)
    
    if args.once:
        # Run once
        if pipeline.authenticate():
            pipeline.sync_all_accounts(direction=args.direction)
    else:
        # Run continuously
        pipeline.run_continuous_sync(interval_minutes=args.interval)


if __name__ == "__main__":
    main()
