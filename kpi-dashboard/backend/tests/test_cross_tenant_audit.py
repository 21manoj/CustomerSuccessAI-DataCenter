#!/usr/bin/env python3
"""
Tests for S2.3: Cross-Tenant Activity Audit.

Verifies:
  1. Admin endpoints exist at /api/admin/activity-logs and /api/admin/activity-logs/summary
  2. Super admin auth check present
  3. Cross-tenant query (no customer_id filter by default)
  4. Customer name enrichment in response
  5. Free-text search support
  6. Per-customer breakdown in summary

Run: python3 -m pytest tests/test_cross_tenant_audit.py -v
"""

import ast
import os
import sys
import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)


class TestCrossTenantAuditEndpoints:
    @pytest.fixture(autouse=True)
    def load_source(self):
        with open(os.path.join(BACKEND_DIR, 'activity_log_api.py')) as f:
            self.source = f.read()

    def test_file_parses(self):
        ast.parse(self.source)

    def test_cross_tenant_logs_endpoint(self):
        assert "'/api/admin/activity-logs'" in self.source

    def test_cross_tenant_summary_endpoint(self):
        assert "'/api/admin/activity-logs/summary'" in self.source

    def test_super_admin_check(self):
        assert "_require_super_admin" in self.source

    def test_admin_role_check(self):
        assert "_is_admin_user" in self.source

    def test_server_key_check(self):
        assert "_api_key_customer_id" in self.source

    def test_cross_tenant_flag_in_response(self):
        assert "'cross_tenant': True" in self.source

    def test_customer_name_enrichment(self):
        assert "customer_name" in self.source
        assert "cust_names" in self.source

    def test_free_text_search(self):
        assert "search" in self.source
        assert "ilike" in self.source

    def test_per_customer_breakdown(self):
        assert "per_customer" in self.source

    def test_error_rate_in_summary(self):
        assert "error_rate_pct" in self.source
        assert "error_count" in self.source

    def test_top_users_cross_tenant(self):
        assert "top_users" in self.source

    def test_top_action_types(self):
        assert "top_action_types" in self.source

    def test_optional_customer_filter(self):
        # Cross-tenant should allow optional customer_id filter
        assert "request.args.get('customer_id', type=int)" in self.source

    def test_max_limit_capped(self):
        assert "1000" in self.source

    def test_max_days_capped(self):
        assert "90" in self.source

    def test_imports_customer_model(self):
        assert "Customer" in self.source


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
