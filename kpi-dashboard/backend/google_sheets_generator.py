#!/usr/bin/env python3
"""
DC2_S Google Sheets Generator
Creates master Google Sheet with 10 pilot accounts

Dependencies:
    pip install gspread oauth2client

Setup:
    1. Enable Google Sheets API in Google Cloud Console
    2. Create Service Account and download credentials JSON
    3. Share sheet with service account email
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from verticals.dc2_s import (
    DC2S_KPIS,
    DC2S_PILLARS,
    calculate_pillar_score,
    calculate_overall_health,
    get_triggered_alerts
)

class DC2SSheetsGenerator:
    """Generator for DC2_S master Google Sheet"""
    
    def __init__(self, credentials_path):
        """
        Initialize sheets generator
        
        Args:
            credentials_path: Path to Google service account JSON
        """
        self.credentials_path = credentials_path
        self.client = None
        self.sheet = None
        
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
            print("✅ Authenticated with Google Sheets API")
            return True
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def create_master_sheet(self, sheet_name="DC2_S Master - Pilot Accounts"):
        """
        Create the master Google Sheet
        
        Args:
            sheet_name: Name for the sheet
            
        Returns:
            Spreadsheet object
        """
        try:
            self.sheet = self.client.create(sheet_name)
            print(f"✅ Created master sheet: {sheet_name}")
            print(f"   URL: {self.sheet.url}")
            return self.sheet
        except Exception as e:
            print(f"❌ Failed to create sheet: {e}")
            return None
    
    def create_index_tab(self, accounts):
        """
        Create index/overview tab
        
        Args:
            accounts: List of account dictionaries
        """
        try:
            # Rename first sheet to "Index"
            worksheet = self.sheet.get_worksheet(0)
            worksheet.update_title("Index")
            
            # Headers
            headers = [
                ["DC2_S Master Sheet - Pilot Accounts"],
                [""],
                ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                ["Total Accounts:", len(accounts)],
                [""],
                ["Account ID", "Account Name", "Phase", "Health Score", "Status", "GPUs", "Value", "Sheet Link"]
            ]
            
            # Account rows
            rows = []
            for acc in accounts:
                health = acc.get('expected_health', 0)
                status = acc.get('expected_status', 'unknown')
                metadata = acc.get('profile_metadata', {})
                
                row = [
                    acc['account_id'],
                    acc['account_name'],
                    metadata.get('phase', ''),
                    f"{health:.1f}",
                    status.upper(),
                    metadata.get('gpu_count', 0),
                    f"${metadata.get('deployment_value', 0):,.0f}",
                    f"=HYPERLINK(\"#gid={acc['account_id']}\", \"View\")"
                ]
                rows.append(row)
            
            # Write to sheet
            all_data = headers + rows
            worksheet.update('A1', all_data)
            
            # Format headers
            worksheet.format('A1:H1', {
                'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.8},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                'horizontalAlignment': 'CENTER'
            })
            
            worksheet.format('A6:H6', {
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                'textFormat': {'bold': True}
            })
            
            print("✅ Created Index tab")
            
        except Exception as e:
            print(f"❌ Failed to create index tab: {e}")
    
    def create_account_tabs(self, account, tab_configs):
        """
        Create 5 tabs for an account
        
        Args:
            account: Account dictionary
            tab_configs: Dictionary of tab configurations
        """
        account_id = account['account_id']
        account_name = account['account_name']
        
        # Create tabs: KPIs, Health, Communications, Actions, Profile
        for tab_name, config in tab_configs.items():
            full_tab_name = f"{account_id}_{tab_name}"
            
            try:
                worksheet = self.sheet.add_worksheet(
                    title=full_tab_name[:100],  # Google Sheets limit
                    rows=100,
                    cols=20
                )
                
                # Populate based on tab type
                if tab_name == "KPIs":
                    self._populate_kpis_tab(worksheet, account)
                elif tab_name == "Health":
                    self._populate_health_tab(worksheet, account)
                elif tab_name == "Communications":
                    self._populate_comms_tab(worksheet, account)
                elif tab_name == "Actions":
                    self._populate_actions_tab(worksheet, account)
                elif tab_name == "Profile":
                    self._populate_profile_tab(worksheet, account)
                
                print(f"   ✅ Created tab: {full_tab_name}")
                
            except Exception as e:
                print(f"   ❌ Failed to create {full_tab_name}: {e}")
    
    def _populate_kpis_tab(self, worksheet, account):
        """Populate KPIs tab"""
        kpi_values = account.get('kpi_values', {})
        
        headers = [
            [account['account_name'] + " - KPIs"],
            [""],
            ["KPI Code", "KPI Name", "Current Value", "Target", "Status", "Last Updated"]
        ]
        
        rows = []
        for kpi_code in sorted(kpi_values.keys()):
            value = kpi_values[kpi_code]
            kpi = DC2S_KPIS.get(kpi_code, {})
            
            # Determine status
            from verticals.dc2_s import get_health_status
            status = get_health_status(kpi_code, value)
            
            row = [
                kpi_code,
                kpi.get('name', ''),
                value,
                str(kpi.get('target', {})),
                status.upper(),
                datetime.now().strftime("%Y-%m-%d")
            ]
            rows.append(row)
        
        all_data = headers + rows
        worksheet.update('A1', all_data)
        
        # Format
        worksheet.format('A1', {'textFormat': {'bold': True, 'fontSize': 14}})
        worksheet.format('A3:F3', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})
    
    def _populate_health_tab(self, worksheet, account):
        """Populate Health tab"""
        kpi_values = account.get('kpi_values', {})
        
        # Calculate pillar scores
        pillar_scores = {}
        for pillar_id in DC2S_PILLARS.keys():
            score = calculate_pillar_score(pillar_id, kpi_values)
            pillar_scores[pillar_id] = score
        
        # Calculate overall
        overall = calculate_overall_health(pillar_scores)
        
        headers = [
            [account['account_name'] + " - Health Score"],
            [""],
            ["Overall Health Score", f"{overall:.1f}/100", account.get('expected_status', '').upper()],
            [""],
            ["Pillar", "Score", "Weight", "Contribution"]
        ]
        
        rows = []
        for pillar_id, score in pillar_scores.items():
            pillar_info = DC2S_PILLARS.get(pillar_id, {})
            weight = pillar_info.get('weight_l2', 0)
            contribution = score * weight
            
            row = [
                pillar_info.get('name', pillar_id),
                f"{score:.1f}",
                f"{weight*100:.0f}%",
                f"{contribution:.1f}"
            ]
            rows.append(row)
        
        all_data = headers + rows
        worksheet.update('A1', all_data)
        
        # Format
        worksheet.format('A1', {'textFormat': {'bold': True, 'fontSize': 14}})
        worksheet.format('A3:C3', {'textFormat': {'bold': True}})
        worksheet.format('A5:D5', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})
    
    def _populate_comms_tab(self, worksheet, account):
        """Populate Communications tab"""
        headers = [
            [account['account_name'] + " - Communications Log"],
            [""],
            ["Date", "Type", "Participant", "Summary", "Next Steps"]
        ]
        
        # Sample communication
        rows = [
            [datetime.now().strftime("%Y-%m-%d"), "QBR", "Account Manager", "Quarterly review completed", "Schedule next QBR"]
        ]
        
        all_data = headers + rows
        worksheet.update('A1', all_data)
        
        worksheet.format('A1', {'textFormat': {'bold': True, 'fontSize': 14}})
        worksheet.format('A3:E3', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})
    
    def _populate_actions_tab(self, worksheet, account):
        """Populate Actions tab"""
        kpi_values = account.get('kpi_values', {})
        alerts = get_triggered_alerts(kpi_values)
        
        headers = [
            [account['account_name'] + " - Recommended Actions"],
            [""],
            ["Priority", "Action", "Triggered By", "Status", "Assigned To"]
        ]
        
        rows = []
        for alert in alerts[:5]:  # Top 5 alerts
            row = [
                alert['priority'].upper(),
                alert['action'],
                alert['kpi'],
                "OPEN",
                "CSM"
            ]
            rows.append(row)
        
        if not rows:
            rows = [["", "No critical actions required", "", "N/A", ""]]
        
        all_data = headers + rows
        worksheet.update('A1', all_data)
        
        worksheet.format('A1', {'textFormat': {'bold': True, 'fontSize': 14}})
        worksheet.format('A3:E3', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})
    
    def _populate_profile_tab(self, worksheet, account):
        """Populate Profile tab"""
        metadata = account.get('profile_metadata', {})
        
        data = [
            [account['account_name'] + " - Account Profile"],
            [""],
            ["Account ID", account['account_id']],
            ["Customer ID", account['customer_id']],
            ["Industry", account.get('industry', '')],
            ["Region", account.get('region', '')],
            [""],
            ["HARDWARE CONFIGURATION"],
            ["GPU Count", metadata.get('gpu_count', 0)],
            ["GPU Model", metadata.get('gpu_model', '')],
            ["Cluster Size", metadata.get('cluster_size', 0)],
            ["Total GPU Memory (GB)", metadata.get('total_gpu_memory_gb', 0)],
            [""],
            ["DEPLOYMENT"],
            ["Deployment Type", metadata.get('deployment_type', '')],
            ["Deployment Date", metadata.get('deployment_date', '')],
            ["Days Since Deployment", metadata.get('days_since_deployment', 0)],
            ["Phase", metadata.get('phase', '')],
            [""],
            ["FINANCIAL"],
            ["Deployment Value", f"${metadata.get('deployment_value', 0):,.0f}"],
            ["ARR", f"${metadata.get('arr', 0):,.0f}"],
            ["Expansion Opportunity", f"${metadata.get('expansion_opportunity_value', 0):,.0f}"],
            [""],
            ["PARTNER"],
            ["Partner Tier", metadata.get('partner_tier', '')],
            ["VAR Partner", metadata.get('var_partner_name', 'Direct')],
        ]
        
        worksheet.update('A1', data)
        
        worksheet.format('A1', {'textFormat': {'bold': True, 'fontSize': 14}})
        worksheet.format('A8', {'textFormat': {'bold': True}})
        worksheet.format('A13', {'textFormat': {'bold': True}})
        worksheet.format('A19', {'textFormat': {'bold': True}})
        worksheet.format('A23', {'textFormat': {'bold': True}})
    
    def generate_full_sheet(self, accounts):
        """
        Generate complete master sheet with all accounts
        
        Args:
            accounts: List of account dictionaries
        """
        if not self.authenticate():
            return False
        
        if not self.create_master_sheet():
            return False
        
        # Create index
        self.create_index_tab(accounts)
        
        # Tab configurations
        tab_configs = {
            "KPIs": {},
            "Health": {},
            "Communications": {},
            "Actions": {},
            "Profile": {}
        }
        
        # Create tabs for each account
        for i, account in enumerate(accounts, 1):
            print(f"\n📊 Creating tabs for account {i}/{len(accounts)}: {account['account_name']}")
            self.create_account_tabs(account, tab_configs)
        
        print(f"\n✅ Master sheet created successfully!")
        print(f"   URL: {self.sheet.url}")
        print(f"   Total tabs: {len(self.sheet.worksheets())}")
        
        return True


def main():
    """Main function"""
    import argparse
    from sample_accounts import get_all_sample_accounts
    
    parser = argparse.ArgumentParser(description='Generate DC2_S master Google Sheet')
    parser.add_argument('credentials', help='Path to Google service account JSON file')
    parser.add_argument('--name', default='DC2_S Master - Pilot Accounts', help='Sheet name')
    
    args = parser.parse_args()
    
    # Get sample accounts
    accounts = get_all_sample_accounts()
    
    print("=" * 60)
    print("DC2_S GOOGLE SHEETS GENERATOR")
    print("=" * 60)
    print(f"Accounts to create: {len(accounts)}")
    print(f"Tabs per account: 5")
    print(f"Total tabs: {len(accounts) * 5 + 1} (including index)")
    print("=" * 60)
    print()
    
    # Generate sheet
    generator = DC2SSheetsGenerator(args.credentials)
    success = generator.generate_full_sheet(accounts)
    
    if success:
        print("\n🎉 Sheet generation complete!")
    else:
        print("\n❌ Sheet generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
