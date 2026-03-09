#!/usr/bin/env python3
"""
Generate CSV files from CustomerConfig
Config-aware synthetic data generator for CS Pulse onboarding

CORRECTED VERSION - Matches actual database schema from models.py
"""

import sys
import os
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from utils.config_loader import ConfigLoader
from id_generator import generate_customer_id, generate_account_id
import pandas as pd
from datetime import datetime, timedelta
import random


# ──────────────────────────────────────────────────────────────
# Range-aware KPI value generation
# DC2_S KPIs have diverse units (days, hours, counts, ms, etc.)
# with very different valid ranges. The generator MUST respect these.
# ──────────────────────────────────────────────────────────────
# No longer needed — all codes are P-format only


def _build_kpi_range_map():
    """Build a range map keyed by BOTH P-format and AI/CH/DV/EX/OS-format codes.

    Returns dict: kpi_code → {abs_min, abs_max, healthy_min, healthy_max,
                               risk_min, risk_max, critical_min, critical_max,
                               higher_is_better, unit}
    """
    try:
        from verticals.dc2_s.kpi_definitions import DC2S_KPIS
    except ImportError:
        print("   ⚠️  DC2S_KPIS not available — falling back to generic 0-100 range")
        return {}

    range_map = {}
    for kpi_code, defn in DC2S_KPIS.items():
        ranges = defn.get('ranges', {})
        all_mins, all_maxs = [], []
        healthy = ranges.get('healthy', {})
        risk = ranges.get('risk', {})
        critical = ranges.get('critical', {})
        for band in (healthy, risk, critical):
            if isinstance(band.get('min'), (int, float)):
                all_mins.append(float(band['min']))
            if isinstance(band.get('max'), (int, float)):
                all_maxs.append(float(band['max']))
        if not all_mins or not all_maxs:
            continue
        entry = {
            'abs_min': min(all_mins),
            'abs_max': max(all_maxs),
            'healthy_min': float(healthy.get('min', 0)),
            'healthy_max': float(healthy.get('max', 100)),
            'risk_min': float(risk.get('min', 0)),
            'risk_max': float(risk.get('max', 100)),
            'critical_min': float(critical.get('min', 0)),
            'critical_max': float(critical.get('max', 100)),
            'higher_is_better': defn.get('higher_is_better', True),
            'unit': defn.get('unit', '%'),
        }
        range_map[kpi_code] = entry
    return range_map


def _get_kpi_status(value, kpi_range):
    """Determine health status from actual DC2_S range bands."""
    if not kpi_range:
        return 'healthy' if value >= 70 else ('risk' if value >= 50 else 'critical')
    h_min, h_max = kpi_range['healthy_min'], kpi_range['healthy_max']
    r_min, r_max = kpi_range['risk_min'], kpi_range['risk_max']
    if h_min <= value <= h_max:
        return 'healthy'
    elif r_min <= value <= r_max:
        return 'risk'
    else:
        return 'critical'


def _generate_kpi_value(scenario, month_idx, num_months, kpi_range):
    """Generate a KPI value within the correct range for the given scenario.

    Scenarios:
      - improving: Start in critical/risk → trend toward healthy
      - declining: Start in healthy → trend toward critical/risk
      - stable_healthy: Stay in/near healthy band
    """
    if not kpi_range:
        # Fallback for unknown KPIs
        if scenario == 'improving':
            base = 50 + (month_idx * 3)
        elif scenario == 'declining':
            base = 80 - (month_idx * 2)
        else:
            base = 75
        return max(0, min(100, base + random.uniform(-5, 5)))

    hi_better = kpi_range['higher_is_better']
    abs_min = kpi_range['abs_min']
    abs_max = kpi_range['abs_max']
    h_min = kpi_range['healthy_min']
    h_max = kpi_range['healthy_max']
    c_min = kpi_range['critical_min']
    c_max = kpi_range['critical_max']
    full_span = abs_max - abs_min if abs_max != abs_min else 1.0

    progress = month_idx / max(num_months - 1, 1)  # 0.0 → 1.0

    if scenario == 'improving':
        if hi_better:
            start_val = c_min + (c_max - c_min) * 0.5
            end_val = h_min + (h_max - h_min) * 0.7
        else:
            start_val = c_min + (c_max - c_min) * 0.5
            end_val = h_min + (h_max - h_min) * 0.3
        base = start_val + (end_val - start_val) * progress
    elif scenario == 'declining':
        if hi_better:
            start_val = h_min + (h_max - h_min) * 0.7
            end_val = c_min + (c_max - c_min) * 0.5
        else:
            start_val = h_min + (h_max - h_min) * 0.3
            end_val = c_min + (c_max - c_min) * 0.5
        base = start_val + (end_val - start_val) * progress
    else:  # stable_healthy
        if hi_better:
            base = h_min + (h_max - h_min) * 0.6
        else:
            base = h_min + (h_max - h_min) * 0.4

    # Add noise (±5% of full range)
    noise = random.uniform(-0.05, 0.05) * full_span
    return max(abs_min, min(abs_max, base + noise))


# Column order for accounts.csv: matches sample_account_profiles_dc2_s.xlsx
# (Customer Profile Input sheet + Champion & Stakeholder sheet + Last updated)
ACCOUNTS_CSV_COLUMNS = [
    'account_id', 'customer_id', 'account_name', 'industry', 'vertical', 'region',
    'account_status', 'account_tier', 'assigned_csm', 'csm_manager', 'executive_sponsor',
    'strategic_account', 'products_used', 'contract_start_date', 'contract_end_date',
    'renewal_date', 'revenue', 'arr', 'mrr',
    'primary_champion_name', 'champion_title', 'champion_email', 'champion_status',
    'champion_tenure_months', 'champion_influence_level', 'economic_buyer_name',
    'economic_buyer_title', 'executive_sponsor_name', 'executive_sponsor_title',
    'technical_champion_name', 'number_active_champions',
    'created_at', 'last_updated',  # last_updated = "Last updated" in Excel
]


def generate_accounts_csv(customer_id, num_accounts=10, company_name=None):
    """
    Generate comprehensive accounts.csv aligned with Customer Profile + Champion & Stakeholder
    (same structure as sample_account_profiles_dc2_s.xlsx, one row per account).
    Includes all profile + champion columns plus Last updated. All values derived from
    customer_id and num_accounts; no hardcoded account IDs.
    """
    company_name = company_name or f"Customer {customer_id}"
    # Account IDs are auto-incremented by DB; use index-based placeholders for CSV
    base_account_id = customer_id * 1000  # Kept for CSV column ordering; DB auto-assigns real IDs
    now = datetime.now()
    last_updated = now.strftime('%Y-%m-%d %H:%M:%S')

    env_names = [
        'Production', 'Staging', 'Development', 'QA', 'UAT',
        'DR', 'Sandbox', 'Integration', 'Performance', 'Lab'
    ]
    industries = ['Data Center Infrastructure', 'Colocation & Interconnection', 'Cloud Infrastructure', 'Edge & Colocation', 'Colocation']
    regions = ['us-west-2', 'us-east-1', 'eu-west-1']
    tiers = ['Enterprise', 'Strategic', 'Professional']
    csm_names = ['Jordan Lee', 'Casey Kim', 'Riley Adams']
    csm_manager = 'Sam Rivera'
    champion_first = ['Chris', 'Sam', 'Jamie', 'Taylor', 'Jordan', 'Riley', 'Morgan', 'Casey', 'Alex', 'Dana']
    champion_last = ['Martinez', 'Patel', 'Foster', 'Reed', 'Blake', 'Adams', 'Taylor', 'Kim', 'Chen', 'Wright']
    titles = ['VP Infrastructure', 'Director of Cloud Ops', 'CTO', 'Infrastructure Manager', 'VP Engineering', 'Cloud Architect', 'SVP Data Center Ops', 'Director of Infrastructure', 'VP Technology', 'Director Global Infrastructure']
    influence = ['High', 'Executive', 'Medium']
    products_used = ['DC2_S Platform', 'DC2_S Platform, Monitoring Suite']

    rows = []
    for i in range(num_accounts):
        account_id = base_account_id + i + 1
        env = env_names[i] if i < len(env_names) else f'Account-{i+1}'
        account_name = f"{company_name} - {env}"

        tier = random.choice(tiers)
        arr = round(random.uniform(200000, 2500000), 0)
        mrr = round(arr / 12, 0)
        start = now - timedelta(days=random.randint(180, 540))
        end = start + timedelta(days=365 * random.randint(1, 2))
        renewal = end

        csm = csm_names[i % len(csm_names)]
        champ_fn = champion_first[i % len(champion_first)]
        champ_ln = champion_last[i % len(champion_last)]
        champion_name = f"{champ_fn} {champ_ln}"
        champion_email = f"{champ_fn[0].lower()}{champ_ln.lower()}@account{i+1}.example.com"
        exec_sponsor = random.choice(champion_first + ['']) + (' ' + random.choice(champion_last) if random.random() > 0.3 else '')
        exec_sponsor = exec_sponsor.strip() or champion_name
        tech_champ = random.choice(champion_first) + ' ' + random.choice(champion_last)
        econ_buyer = random.choice(champion_first) + ' ' + random.choice(champion_last)
        num_champions = random.randint(1, 4)

        rows.append({
            'account_id': account_id,
            'customer_id': customer_id,
            'uuid': generate_account_id('dc'),
            'account_name': account_name,
            'industry': random.choice(industries),
            'vertical': 'dc2_s',
            'region': random.choice(regions),
            'account_status': 'active',
            'account_tier': tier,
            'assigned_csm': csm,
            'csm_manager': csm_manager,
            'executive_sponsor': exec_sponsor,
            'strategic_account': 'Yes' if tier in ('Enterprise', 'Strategic') else 'No',
            'products_used': random.choice(products_used),
            'contract_start_date': start.strftime('%Y-%m-%d'),
            'contract_end_date': end.strftime('%Y-%m-%d'),
            'renewal_date': renewal.strftime('%Y-%m-%d'),
            'revenue': arr,
            'arr': arr,
            'mrr': mrr,
            'primary_champion_name': champion_name,
            'champion_title': titles[i % len(titles)],
            'champion_email': champion_email,
            'champion_status': 'Active',
            'champion_tenure_months': random.randint(6, 30),
            'champion_influence_level': random.choice(influence),
            'economic_buyer_name': econ_buyer,
            'economic_buyer_title': random.choice(['CFO', 'CTO', 'VP Operations', 'Director IT', 'VP Engineering']),
            'executive_sponsor_name': exec_sponsor,
            'executive_sponsor_title': random.choice(['CTO', 'VP Sales', 'EVP', 'VP Technology']),
            'technical_champion_name': tech_champ,
            'number_active_champions': num_champions,
            'created_at': now.strftime('%Y-%m-%d'),
            'last_updated': last_updated,
        })

    df = pd.DataFrame(rows)
    # Enforce column order matching Excel (Profile + Champion + Last updated)
    df = df[[c for c in ACCOUNTS_CSV_COLUMNS if c in df.columns]]
    return df


def generate_kpi_measurements_csv(customer_id, accounts_df, num_months=12):
    """Generate KPI measurements from config (ENABLED KPIs only).

    Range-aware: uses DC2S_KPIS reference ranges to generate values
    in the correct units (days, hours, counts, etc.) — not a flat 0-100 scale.
    """

    with app.app_context():
        loader = ConfigLoader(customer_id)
        enabled_kpis = loader.get_enabled_kpis()

        # Build range map from DC2S_KPIS (keyed by both P-format and AI/CH/DV/EX/OS-format)
        kpi_range_map = _build_kpi_range_map()
        range_aware_count = sum(1 for k in enabled_kpis if k in kpi_range_map)

        print(f"   Config-aware: Using {len(enabled_kpis)} enabled KPIs")
        print(f"   Range-aware: {range_aware_count}/{len(enabled_kpis)} KPIs have DC2S reference ranges")
        print(f"   KPIs: {', '.join(sorted(enabled_kpis)[:5])}..." if enabled_kpis else "   No enabled KPIs!")

        measurements = []
        start_date = datetime(2024, 1, 1)

        # For each account
        for _, account in accounts_df.iterrows():
            account_id = account['account_id']

            # Determine scenario based on account
            scenario_idx = account_id % 3
            scenarios = ['improving', 'stable_healthy', 'declining']
            scenario = scenarios[scenario_idx]

            # For each month — use calendar-aligned 1st-of-month dates
            for month_idx in range(num_months):
                month_offset = start_date.month - 1 + month_idx
                year = start_date.year + month_offset // 12
                month = month_offset % 12 + 1
                measured_at = datetime(year, month, 1)

                # For each ENABLED KPI (config-aware!)
                config = loader.customer_config
                kpi_overrides = (config or {}).get('kpi_overrides', {})
                for kpi_code in enabled_kpis:
                    kpi_def = loader.get_kpi_definition(kpi_code)

                    if not kpi_def:
                        continue

                    # Look up real range for this KPI
                    kpi_range = kpi_range_map.get(kpi_code)

                    # Get target: apply dc2s_kpi_overrides (custom target) from config
                    override = kpi_overrides.get(kpi_code, {})
                    target_value = override.get('target')
                    if target_value is None:
                        target_value = kpi_def.get('target', {})
                    if isinstance(target_value, dict):
                        target_value = target_value.get('value', 85.0)
                    elif target_value is None:
                        target_value = 85.0

                    # Fix generic 85.0 default — use healthy midpoint for range-aware KPIs
                    if kpi_range and target_value == 85.0:
                        target_value = round(
                            (kpi_range['healthy_min'] + kpi_range['healthy_max']) / 2, 2
                        )

                    # Generate value within the correct range for this KPI's unit
                    value = _generate_kpi_value(scenario, month_idx, num_months, kpi_range)

                    # Determine status from actual range bands (not hardcoded 70/50 thresholds)
                    status = _get_kpi_status(value, kpi_range)

                    measurements.append({
                        'account_id': account_id,
                        'kpi_code': kpi_code,
                        'measured_at': measured_at.strftime('%Y-%m-%d'),
                        'value': round(value, 2),
                        'target': target_value,
                        'pillar': kpi_def.get('pillar', 'Unknown'),
                        'weight': kpi_def.get('weight', 0.25),
                        'status': status,
                    })

        print(f"   Generated {len(measurements)} KPI measurements")
        print(f"     Accounts: {len(accounts_df)}")
        print(f"     Enabled KPIs: {len(enabled_kpis)}")
        print(f"     Months: {num_months}")

        # Quick sanity check: report value ranges per KPI
        if measurements:
            df_tmp = pd.DataFrame(measurements)
            for kpi in sorted(df_tmp['kpi_code'].unique())[:5]:
                subset = df_tmp[df_tmp['kpi_code'] == kpi]['value']
                rng = kpi_range_map.get(kpi, {})
                unit = rng.get('unit', '?')
                print(f"     {kpi}: {subset.min():.1f} – {subset.max():.1f} {unit}")

        return pd.DataFrame(measurements)


def generate_customers_csv(customer_id, company_name):
    """Generate customers.csv with prefixed UUID v7"""

    return pd.DataFrame([{
        'customer_id': customer_id,  # Integer PK (legacy, kept for FK compatibility)
        'uuid': generate_customer_id('dc'),  # Prefixed UUID v7 (e.g. dc_cust_019...)
        'customer_name': company_name,
        'vertical': 'dc2_s',
        'created_at': datetime.now().strftime('%Y-%m-%d')
    }])


def generate_qualitative_signals_csv(customer_id, accounts_df, num_months=12):
    """Generate qualitative_signals.csv with scenario-aware content.

    Signal content and sentiment are tied to the account's scenario (improving/stable/declining)
    so that the Signal Analyst receives meaningful qualitative data to work with.
    """
    # Scenario-specific signal templates: (signal_type, content_template, sentiment, score_range)
    SIGNAL_TEMPLATES = {
        'improving': [
            ('customer_feedback', 'NPS survey response: Score improved from {prev} to {curr}. Customer praised faster GPU provisioning.', 'positive', (0.4, 0.9)),
            ('meeting', 'QBR held — customer reported improved deployment times and wants to expand AI workloads.', 'positive', (0.5, 0.8)),
            ('milestone', 'Customer achieved 99.9% uptime target for the first time this quarter.', 'positive', (0.6, 1.0)),
            ('health_check', 'Proactive health review: RMA rates declining, PUE improving toward target.', 'positive', (0.3, 0.7)),
            ('customer_feedback', 'Support ticket satisfaction: 4.5/5 — team resolved batch processing issue within SLA.', 'positive', (0.4, 0.8)),
            ('meeting', 'Expansion discussion: customer evaluating additional rack capacity for Q{quarter} growth.', 'positive', (0.5, 0.9)),
            ('incident', 'Minor network latency spike detected; auto-resolved within 15 minutes. No customer impact.', 'neutral', (-0.1, 0.2)),
            ('customer_feedback', 'Champion {champion} confirmed renewal intent and requested pricing for GPU cluster expansion.', 'positive', (0.6, 0.95)),
        ],
        'stable_healthy': [
            ('health_check', 'Routine health check: all KPIs within healthy ranges. No action required.', 'neutral', (-0.1, 0.3)),
            ('meeting', 'Monthly sync — customer satisfied with current service levels. No escalations.', 'neutral', (0.0, 0.4)),
            ('customer_feedback', 'NPS survey: Score steady at {curr}/10. Customer values reliability.', 'neutral', (0.1, 0.4)),
            ('milestone', 'Contract renewal processed — 12-month extension at current terms.', 'positive', (0.3, 0.6)),
            ('health_check', 'Quarterly review: GPU utilization stable at ~75%, power efficiency on target.', 'neutral', (0.0, 0.3)),
            ('customer_feedback', 'Feedback form: "Service meets expectations. Would like more proactive reporting."', 'neutral', (0.0, 0.3)),
            ('meeting', 'Stakeholder check-in: no open issues. Discussed roadmap for next quarter.', 'neutral', (0.1, 0.4)),
            ('incident', 'Scheduled maintenance window completed successfully. All systems nominal.', 'neutral', (0.0, 0.2)),
        ],
        'declining': [
            ('incident', 'Critical: GPU cluster outage lasted {hours}h. Customer escalated to VP level.', 'negative', (-0.9, -0.4)),
            ('customer_feedback', 'NPS score dropped from {prev} to {curr}. Customer cited repeated provisioning delays.', 'negative', (-0.8, -0.3)),
            ('meeting', 'Emergency call: customer threatened to evaluate competitors due to ongoing RMA issues.', 'negative', (-0.7, -0.4)),
            ('health_check', 'Health review flagged declining PUE and rising support ticket volume.', 'negative', (-0.6, -0.2)),
            ('customer_feedback', 'Champion {champion} expressed frustration with batch throughput degradation.', 'negative', (-0.7, -0.3)),
            ('incident', 'SLA breach: network latency exceeded threshold for {hours}h. Root cause under investigation.', 'negative', (-0.8, -0.5)),
            ('meeting', 'QBR cancelled by customer — cited "lack of visible improvement" in service quality.', 'negative', (-0.6, -0.3)),
            ('customer_feedback', 'Support satisfaction: 2.1/5. Customer requests executive-level engagement.', 'negative', (-0.9, -0.5)),
        ],
    }

    champion_names = ['Alex Chen', 'Sarah Johnson', 'Mike Thompson', 'Lisa Wang', 'David Kumar']

    signals = []
    start_date = datetime(2024, 1, 1)
    signal_counter = 1

    for _, account in accounts_df.iterrows():
        account_id = account['account_id']
        account_name = account.get('account_name', f'Account-{account_id}')

        # Same scenario assignment as KPI generator
        scenario_idx = account_id % 3
        scenarios = ['improving', 'stable_healthy', 'declining']
        scenario = scenarios[scenario_idx]
        templates = SIGNAL_TEMPLATES[scenario]
        champion = random.choice(champion_names)

        for month_idx in range(num_months):
            month_offset = start_date.month - 1 + month_idx
            year = start_date.year + month_offset // 12
            month = month_offset % 12 + 1
            signal_date = datetime(year, month, random.randint(1, 28))
            quarter = (month - 1) // 3 + 1

            # 2-3 signals per account per month
            for _ in range(random.randint(2, 3)):
                signal_id = f'sig_{account_id}_{signal_counter:04d}'
                signal_counter += 1

                template = random.choice(templates)
                sig_type, content_tmpl, sentiment, (score_lo, score_hi) = template

                content = content_tmpl.format(
                    account_name=account_name,
                    prev=random.randint(4, 7),
                    curr=random.randint(5, 9) if scenario != 'declining' else random.randint(2, 5),
                    hours=random.randint(2, 8),
                    quarter=quarter,
                    champion=champion,
                )

                signals.append({
                    'signal_id': signal_id,
                    'account_id': account_id,
                    'signal_date': signal_date.strftime('%Y-%m-%d'),
                    'signal_type': sig_type,
                    'content': content,
                    'sentiment': sentiment,
                    'sentiment_score': round(random.uniform(score_lo, score_hi), 2)
                })

    return pd.DataFrame(signals)


def generate_products_csv(customer_id):
    """Generate products.csv. product_id is customer-scoped to avoid global PK collision (Product.product_id is unique)."""
    # Use customer_id * 10000 + n so product_id doesn't collide with account_id (customer_id * 1000 + i)
    base = customer_id * 10000
    return pd.DataFrame([
        {
            'customer_id': customer_id,
            'product_id': base + 1,
            'product_name': 'DC2_S Platform',
            'category': 'Infrastructure',
            'license_type': 'Enterprise'
        },
        {
            'customer_id': customer_id,
            'product_id': base + 2,
            'product_name': 'Monitoring Suite',
            'category': 'Operations',
            'license_type': 'Professional'
        }
    ])


# Profile/champion columns for profiles.csv (one row per account; process-data loads into account_profiles or accounts.profile_metadata)
PROFILES_CSV_COLUMNS = [
    'account_id', 'customer_id', 'account_name',
    'assigned_csm', 'csm_manager', 'executive_sponsor', 'arr', 'mrr', 'last_updated',
    'primary_champion_name', 'champion_title', 'champion_email', 'champion_status',
    'champion_tenure_months', 'champion_influence_level', 'economic_buyer_name',
    'economic_buyer_title', 'executive_sponsor_name', 'executive_sponsor_title',
    'technical_champion_name', 'number_active_champions',
]


def generate_profiles_csv(accounts_df):
    """
    Generate profiles.csv from accounts DataFrame (one row per account).
    Matches onboarding file_type 'profiles'; process-data loads into account_profiles or accounts.profile_metadata.
    """
    cols = [c for c in PROFILES_CSV_COLUMNS if c in accounts_df.columns]
    return accounts_df[cols].copy()


def save_csvs(customer_id, customer_dir, company_name, num_accounts=10, num_months=12, journey_patterns=None):
    """Generate and save all CSV files"""
    
    customer_dir = Path(customer_dir)
    customer_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📊 Generating config-aware CSV files for customer {customer_id}...")
    print(f"   Company: {company_name}")
    print(f"   Output: {customer_dir}")
    print(f"   Accounts: {num_accounts}")
    print(f"   Months: {num_months}")
    
    files_created = []
    
    # Generate accounts (comprehensive: Profile + Champion + last_updated, per Excel)
    accounts_df = generate_accounts_csv(customer_id, num_accounts, company_name)
    accounts_file = customer_dir / 'accounts.csv'
    accounts_df.to_csv(accounts_file, index=False)
    files_created.append(f"accounts.csv ({accounts_file.stat().st_size} bytes)")
    print(f"   ✅ {accounts_file.name} ({len(accounts_df)} accounts)")
    
    # Generate KPI measurements (config-aware!)
    kpi_df = generate_kpi_measurements_csv(customer_id, accounts_df, num_months)
    kpi_file = customer_dir / 'kpi_measurements.csv'
    kpi_df.to_csv(kpi_file, index=False)
    files_created.append(f"kpi_measurements.csv ({kpi_file.stat().st_size} bytes)")
    print(f"   ✅ {kpi_file.name} ({len(kpi_df)} measurements)")
    
    # Generate customers
    customers_df = generate_customers_csv(customer_id, company_name)
    customers_file = customer_dir / 'customers.csv'
    customers_df.to_csv(customers_file, index=False)
    files_created.append(f"customers.csv ({customers_file.stat().st_size} bytes)")
    print(f"   ✅ {customers_file.name}")
    
    # Generate qualitative signals
    signals_df = generate_qualitative_signals_csv(customer_id, accounts_df, num_months)
    signals_file = customer_dir / 'qualitative_signals.csv'
    signals_df.to_csv(signals_file, index=False)
    files_created.append(f"qualitative_signals.csv ({signals_file.stat().st_size} bytes)")
    print(f"   ✅ {signals_file.name} ({len(signals_df)} signals)")
    
    # Generate products
    products_df = generate_products_csv(customer_id)
    products_file = customer_dir / 'products.csv'
    products_df.to_csv(products_file, index=False)
    files_created.append(f"products.csv ({products_file.stat().st_size} bytes)")
    print(f"   ✅ {products_file.name}")
    
    # Generate profiles (one row per account; process-data loads into account_profiles or accounts.profile_metadata)
    profiles_df = generate_profiles_csv(accounts_df)
    profiles_file = customer_dir / 'profiles.csv'
    profiles_df.to_csv(profiles_file, index=False)
    files_created.append(f"profiles.csv ({profiles_file.stat().st_size} bytes)")
    print(f"   ✅ {profiles_file.name} ({len(profiles_df)} profiles)")
    
    # Generate DEMO_MANIFEST if requested
    if journey_patterns == 'DEMO_MANIFEST':
        manifest_file = customer_dir.parent / 'DEMO_MANIFEST.md'
        
        manifest_content = f"""# Demo Manifest - Customer {customer_id}

## Overview
- **Customer ID:** {customer_id}
- **Company:** {company_name}
- **Accounts:** {num_accounts}
- **Time Period:** {num_months} months
- **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Data Files
{chr(10).join(f'- {f}' for f in files_created)}

## Journey Patterns
This customer uses **DEMO_MANIFEST** journey patterns.

## Accounts
{chr(10).join(f'- **{row["account_id"]}**: {row["account_name"]}' for _, row in accounts_df.iterrows())}

## KPIs (Config-Aware)
- Total measurements: {len(kpi_df)}
- Enabled KPIs: {len(kpi_df['kpi_code'].unique()) if not kpi_df.empty else 0}
- Months of data: {num_months}

## Next Steps
1. Run data loading: `02_load_customer{customer_id}_data_SMART.py`
2. Generate embeddings: `03_embed_customer{customer_id}_OPENAI.py`
3. Generate journeys: Wizard A
"""
        
        with open(manifest_file, 'w') as f:
            f.write(manifest_content)
        
        print(f"   ✅ DEMO_MANIFEST.md ({manifest_file.stat().st_size} bytes)")
    
    print(f"\n🎉 Data generation complete! 6 CSVs: accounts, kpi_measurements, customers, qualitative_signals, products, profiles.")
    return {
        'accounts': accounts_file,
        'kpi_measurements': kpi_file,
        'customers': customers_file,
        'qualitative_signals': signals_file,
        'products': products_file,
        'profiles': profiles_file,
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate config-aware synthetic customer data'
    )
    parser.add_argument('--customer-id', type=int, required=True,
                       help='Customer ID')
    parser.add_argument('--company-name', type=str, default=None,
                       help='Company name (default: Customer {id})')
    parser.add_argument('--output-dir', type=str, required=True,
                       help='Output directory for CSV files')
    parser.add_argument('--num-accounts', type=int, default=10,
                       help='Number of accounts (default: 10)')
    parser.add_argument('--num-months', type=int, default=12,
                       help='Number of months of data (default: 12)')
    parser.add_argument('--journey-patterns', type=str, default=None,
                       help='Journey pattern type (e.g., DEMO_MANIFEST)')
    
    args = parser.parse_args()
    
    company_name = args.company_name or f"Customer {args.customer_id}"
    
    try:
        save_csvs(
            args.customer_id,
            args.output_dir,
            company_name,
            args.num_accounts,
            args.num_months,
            args.journey_patterns
        )
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
