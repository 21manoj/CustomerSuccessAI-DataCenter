#!/usr/bin/env python3
"""Check playbook executions in the database"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app_v3_minimal import app
from extensions import db
from models import PlaybookExecution, PlaybookReport

def check_executions():
    """Check what executions exist in the database"""
    with app.app_context():
        print("📊 Checking Playbook Executions in Database\n")
        
        # Get all executions
        all_executions = PlaybookExecution.query.all()
        print(f"Total executions in DB: {len(all_executions)}\n")
        
        if len(all_executions) == 0:
            print("⚠️  No executions found in database!")
            return
        
        for exec_record in all_executions:
            print(f"Execution ID: {exec_record.execution_id}")
            print(f"  Customer ID: {exec_record.customer_id}")
            print(f"  Account ID: {exec_record.account_id}")
            print(f"  Playbook ID: {exec_record.playbook_id}")
            print(f"  Status: {exec_record.status}")
            print(f"  Started: {exec_record.started_at}")
            print(f"  Completed: {exec_record.completed_at}")
            print(f"  Current Step: {exec_record.current_step}")
            print(f"  Has execution_data: {exec_record.execution_data is not None}")
            if exec_record.execution_data:
                exec_data = exec_record.execution_data
                print(f"  Execution data keys: {list(exec_data.keys()) if isinstance(exec_data, dict) else 'Not a dict'}")
                if isinstance(exec_data, dict):
                    print(f"  playbookId in data: {exec_data.get('playbookId')}")
                    print(f"  results count: {len(exec_data.get('results', []))}")
                    print(f"  currentStep: {exec_data.get('currentStep')}")
            print()
        
        # Get all reports
        all_reports = PlaybookReport.query.all()
        print(f"\nTotal reports in DB: {len(all_reports)}\n")
        
        for report in all_reports:
            print(f"Report for execution: {report.execution_id}")
            print(f"  Playbook: {report.playbook_id}")
            print(f"  Account: {report.account_name}")
            print(f"  Generated: {report.report_generated_at}")
            print()

if __name__ == '__main__':
    check_executions()









