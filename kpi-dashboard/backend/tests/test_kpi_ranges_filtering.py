#!/usr/bin/env python3
"""
Simulation tests for tenant-scoped KPI Reference Ranges filtering.
Validates:
- API returns ranges only for KPIs present in the tenant's catalog (Account Health)
- customer_id query param targets a specific tenant
"""
import json
import pytest

from app_v3_minimal import app
from models import db, Customer, KPI, KPIUpload
import json as _json


def get_catalog_kpi_names(customer_id: int):
    rows = (
        db.session.query(KPI.kpi_parameter)
        .join(KPIUpload, KPI.upload_id == KPIUpload.upload_id)
        .filter(KPIUpload.customer_id == customer_id)
        .all()
    )
    return {str(name) for (name,) in rows if name}


@pytest.fixture(scope="module")
def client():
    app.testing = True
    with app.test_client() as c:
        yield c


def test_ranges_filtered_for_test_company(client):
    cust = Customer.query.filter(Customer.customer_name == 'Test Company').first()
    assert cust is not None, "Test Company tenant must exist"
    catalog = get_catalog_kpi_names(cust.customer_id)
    # Call API explicitly for this tenant
    resp = client.get(f"/api/kpi-reference-ranges?customer_id={cust.customer_id}")
    assert resp.status_code == 200, f"Unexpected status: {resp.status_code}"
    data = resp.get_json()
    assert isinstance(data.get('ranges'), list), "ranges must be a list"
    names = {r['kpi_name'] for r in data['ranges']}
    # API should return only catalog KPIs
    assert names.issubset(catalog), f"API returned non-catalog KPIs: {names - catalog}"
    # And should include most catalog KPIs that have defaults/overrides
    assert len(names) > 0, "Expected at least one KPI range for Test Company"


def test_ranges_filtered_for_dcmp(client):
    cust = Customer.query.filter(Customer.customer_name == 'DCMarketPlace').first()
    assert cust is not None, "DCMarketPlace tenant must exist"
    catalog = get_catalog_kpi_names(cust.customer_id)
    resp = client.get(f"/api/kpi-reference-ranges?customer_id={cust.customer_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    names = {r['kpi_name'] for r in data.get('ranges', [])}
    assert names.issubset(catalog), f"API returned non-catalog KPIs for DCMP: {names - catalog}"


def test_cross_tenant_param_overrides_session(client):
    # Call with an explicit tenant and ensure response changes when tenant changes
    test_cust = Customer.query.filter(Customer.customer_name == 'Test Company').first()
    dcmp_cust = Customer.query.filter(Customer.customer_name == 'DCMarketPlace').first()
    assert test_cust and dcmp_cust
    r1 = client.get(f"/api/kpi-reference-ranges?customer_id={test_cust.customer_id}").get_json()
    r2 = client.get(f"/api/kpi-reference-ranges?customer_id={dcmp_cust.customer_id}").get_json()
    names1 = {r['kpi_name'] for r in r1.get('ranges', [])}
    names2 = {r['kpi_name'] for r in r2.get('ranges', [])}
    # The sets don't have to be disjoint, but they should not be completely identical in most cases
    assert names1 != names2 or (len(names1) == 0 and len(names2) == 0), "Expected tenant-specific differences in KPI catalogs"


def test_generate_and_apply_flow_for_dcmp(client):
    dcmp = Customer.query.filter(Customer.customer_name == 'DCMarketPlace').first()
    assert dcmp is not None
    # Generate draft (not persisted)
    g = client.post("/api/kpi-reference-ranges/generate", json={'customer_id': dcmp.customer_id})
    assert g.status_code == 200
    gdata = g.get_json()
    assert 'kpis' in gdata and isinstance(gdata['kpis'], list) and len(gdata['kpis']) > 0
    # Apply a subset (first 5) to ensure persistence works
    subset = gdata['kpis'][:5]
    a = client.post("/api/kpi-reference-ranges/apply-generated", json={'customer_id': dcmp.customer_id, 'kpis': subset})
    assert a.status_code == 200
    adata = a.get_json()
    assert adata.get('status') == 'success'
    assert adata.get('updated_count') == len(subset)
    # Fetch again and ensure at least those KPI names appear in ranges
    r = client.get(f"/api/kpi-reference-ranges?customer_id={dcmp.customer_id}").get_json()
    names = {r1['kpi_name'] for r1 in r.get('ranges', [])}
    for it in subset:
        assert it['kpi_name'] in names, f"Applied KPI {it['kpi_name']} missing in fetched ranges"


