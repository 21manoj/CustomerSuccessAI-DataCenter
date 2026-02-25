#!/usr/bin/env python3
"""
CSV Generator — Creates synthetic customer data files for load testing

Generates realistic CSV files matching the DC2_S vertical schema:
  - accounts.csv: Account records with company names, tiers, ARR
  - kpi_data.csv: 15 KPIs × N accounts × M months of measurements
  - products.csv: Product/service records per account
  - contacts.csv: Customer contacts (CSMs, executives, technical leads)

Uses Faker for realistic company/person names.
Convention: account_id = customer_id × 1000 + offset (1-based)
"""

import csv
import io
import random
import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    from faker import Faker
    fake = Faker()
except ImportError:
    fake = None

logger = logging.getLogger(__name__)

# DC2_S KPI definitions (15 KPIs across 5 pillars)
DC2S_KPIS = [
    # Pillar: AI Workload (25%)
    {'code': 'AI-KPI1', 'name': 'GPU Utilization Rate', 'pillar': 'AI', 'weight': 0.35, 'unit': '%'},
    {'code': 'AI-KPI2', 'name': 'AI Model Deployment Frequency', 'pillar': 'AI', 'weight': 0.35, 'unit': 'count/month'},
    {'code': 'AI-KPI3', 'name': 'Inference Latency P95', 'pillar': 'AI', 'weight': 0.30, 'unit': 'ms'},
    # Pillar: Channel (15%)
    {'code': 'CH-KPI1', 'name': 'Partner Engagement Score', 'pillar': 'CH', 'weight': 0.40, 'unit': 'score'},
    {'code': 'CH-KPI2', 'name': 'Channel Revenue Share', 'pillar': 'CH', 'weight': 0.30, 'unit': '%'},
    {'code': 'CH-KPI3', 'name': 'Partner Certification Level', 'pillar': 'CH', 'weight': 0.30, 'unit': 'level'},
    # Pillar: Deployment (15%)
    {'code': 'DV-KPI1', 'name': 'Infrastructure Uptime', 'pillar': 'DV', 'weight': 0.35, 'unit': '%'},
    {'code': 'DV-KPI2', 'name': 'Deployment Success Rate', 'pillar': 'DV', 'weight': 0.35, 'unit': '%'},
    {'code': 'DV-KPI3', 'name': 'Time-to-First-Workload', 'pillar': 'DV', 'weight': 0.30, 'unit': 'days'},
    # Pillar: Expansion (25%)
    {'code': 'EX-KPI1', 'name': 'Capacity Utilization', 'pillar': 'EX', 'weight': 0.35, 'unit': '%'},
    {'code': 'EX-KPI2', 'name': 'Expansion Pipeline Value', 'pillar': 'EX', 'weight': 0.35, 'unit': '$'},
    {'code': 'EX-KPI3', 'name': 'Upsell Conversion Rate', 'pillar': 'EX', 'weight': 0.30, 'unit': '%'},
    # Pillar: Operational (20%)
    {'code': 'OS-KPI1', 'name': 'SLA Compliance Rate', 'pillar': 'OS', 'weight': 0.35, 'unit': '%'},
    {'code': 'OS-KPI2', 'name': 'Mean Time to Recovery', 'pillar': 'OS', 'weight': 0.35, 'unit': 'hours'},
    {'code': 'OS-KPI3', 'name': 'Incident Resolution Rate', 'pillar': 'OS', 'weight': 0.30, 'unit': '%'},
]

# Account tiers and their ARR ranges
TIERS = {
    'Enterprise': (500_000, 5_000_000),
    'Mid-Market': (100_000, 499_999),
    'SMB': (10_000, 99_999),
}

TIER_DISTRIBUTION = {
    'Enterprise': 0.20,
    'Mid-Market': 0.50,
    'SMB': 0.30,
}

# Products commonly associated with DC2_S (data center) accounts
DC2S_PRODUCTS = [
    'GPU Compute Cluster',
    'AI Training Platform',
    'Inference Engine',
    'Data Lake Storage',
    'Edge Deployment Kit',
    'Network Fabric Controller',
    'Cooling Management System',
    'Power Distribution Unit',
    'Security Gateway',
    'Monitoring Dashboard',
]

INDUSTRIES = [
    'Technology', 'Financial Services', 'Healthcare',
    'Manufacturing', 'Retail', 'Energy',
    'Telecommunications', 'Government', 'Education',
    'Media & Entertainment'
]

REGIONS = ['North America', 'EMEA', 'APAC', 'LATAM']


class CSVGenerator:
    """
    Generates synthetic CSV files for load testing the CS Pulse platform

    Usage:
        gen = CSVGenerator(customer_id=1, num_accounts=50, seed=42)
        gen.generate_all('/tmp/customer1_data/')

    Or get CSV content as strings:
        accounts_csv = gen.generate_accounts_csv()
        kpi_csv = gen.generate_kpi_csv(months=3)
    """

    def __init__(
        self,
        customer_id: int = 1,
        num_accounts: int = 50,
        seed: int = None
    ):
        self.customer_id = customer_id
        self.num_accounts = num_accounts
        self.account_base = customer_id * 1000 + 1

        if seed is not None:
            random.seed(seed)
            if fake:
                Faker.seed(seed)

    def generate_all(self, output_dir: str) -> Dict[str, str]:
        """
        Generate all CSV files to the specified directory

        Returns:
            Dict of filename → file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files = {}

        accounts_csv = self.generate_accounts_csv()
        accounts_file = output_path / 'accounts.csv'
        accounts_file.write_text(accounts_csv)
        files['accounts.csv'] = str(accounts_file)

        kpi_csv = self.generate_kpi_csv(months=3)
        kpi_file = output_path / 'kpi_data.csv'
        kpi_file.write_text(kpi_csv)
        files['kpi_data.csv'] = str(kpi_file)

        products_csv = self.generate_products_csv()
        products_file = output_path / 'products.csv'
        products_file.write_text(products_csv)
        files['products.csv'] = str(products_file)

        contacts_csv = self.generate_contacts_csv()
        contacts_file = output_path / 'contacts.csv'
        contacts_file.write_text(contacts_csv)
        files['contacts.csv'] = str(contacts_file)

        logger.info(f"Generated {len(files)} CSV files in {output_dir}")
        for name, path in files.items():
            logger.info(f"  {name}: {path}")

        return files

    def generate_accounts_csv(self) -> str:
        """Generate accounts.csv with N realistic account records"""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'account_id', 'account_name', 'industry', 'region',
            'tier', 'arr', 'contract_start', 'contract_end',
            'csm_name', 'csm_email', 'account_status'
        ])

        for i in range(self.num_accounts):
            account_id = self.account_base + i
            tier = self._pick_tier()
            arr_min, arr_max = TIERS[tier]

            if fake:
                company = fake.company()
                csm_name = fake.name()
                csm_email = fake.email()
            else:
                company = f"DataCenter-Corp-{account_id}"
                csm_name = f"CSM-{account_id}"
                csm_email = f"csm{account_id}@example.com"

            contract_start = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 180))
            contract_end = contract_start + timedelta(days=365)

            writer.writerow([
                account_id,
                company,
                random.choice(INDUSTRIES),
                random.choice(REGIONS),
                tier,
                round(random.uniform(arr_min, arr_max), 2),
                contract_start.strftime('%Y-%m-%d'),
                contract_end.strftime('%Y-%m-%d'),
                csm_name,
                csm_email,
                random.choice(['active', 'active', 'active', 'at_risk', 'churning']),
            ])

        return output.getvalue()

    def generate_kpi_csv(self, months: int = 3) -> str:
        """
        Generate kpi_data.csv with 15 KPIs × N accounts × M months

        Args:
            months: Number of months of data (default 3)
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'account_id', 'kpi_code', 'kpi_name', 'pillar',
            'measured_at', 'value', 'target', 'weight', 'unit'
        ])

        base_date = datetime(2024, 10, 1)  # Start from Oct 2024

        for i in range(self.num_accounts):
            account_id = self.account_base + i

            for month_offset in range(months):
                measured_at = (base_date + timedelta(days=30 * month_offset)).strftime('%Y-%m-%d')

                for kpi in DC2S_KPIS:
                    target = self._get_kpi_target(kpi['code'])
                    value = self._generate_kpi_value(kpi['code'], target, month_offset)

                    writer.writerow([
                        account_id,
                        kpi['code'],
                        kpi['name'],
                        kpi['pillar'],
                        measured_at,
                        round(value, 2),
                        round(target, 2),
                        kpi['weight'],
                        kpi['unit'],
                    ])

        return output.getvalue()

    def generate_products_csv(self) -> str:
        """Generate products.csv with 1-4 products per account"""
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'account_id', 'product_name', 'product_category',
            'quantity', 'unit_price', 'deployment_date', 'status'
        ])

        for i in range(self.num_accounts):
            account_id = self.account_base + i
            num_products = random.randint(1, 4)
            products = random.sample(DC2S_PRODUCTS, min(num_products, len(DC2S_PRODUCTS)))

            for product in products:
                deploy_date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))
                writer.writerow([
                    account_id,
                    product,
                    self._product_category(product),
                    random.randint(1, 100),
                    round(random.uniform(1000, 50000), 2),
                    deploy_date.strftime('%Y-%m-%d'),
                    random.choice(['active', 'active', 'active', 'provisioning', 'decommissioned']),
                ])

        return output.getvalue()

    def generate_contacts_csv(self) -> str:
        """Generate contacts.csv with 2-5 contacts per account"""
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'account_id', 'contact_name', 'contact_email',
            'role', 'department', 'is_primary'
        ])

        roles = [
            'VP Engineering', 'CTO', 'Director IT',
            'Data Center Manager', 'Cloud Architect',
            'Infrastructure Lead', 'DevOps Manager',
            'Procurement Manager', 'CFO'
        ]

        departments = [
            'Engineering', 'IT', 'Operations',
            'Infrastructure', 'Finance', 'Executive'
        ]

        for i in range(self.num_accounts):
            account_id = self.account_base + i
            num_contacts = random.randint(2, 5)

            for j in range(num_contacts):
                if fake:
                    name = fake.name()
                    email = fake.email()
                else:
                    name = f"Contact-{account_id}-{j}"
                    email = f"contact{j}@account{account_id}.com"

                writer.writerow([
                    account_id,
                    name,
                    email,
                    random.choice(roles),
                    random.choice(departments),
                    'true' if j == 0 else 'false',  # First contact is primary
                ])

        return output.getvalue()

    def _pick_tier(self) -> str:
        """Pick tier based on distribution"""
        return random.choices(
            list(TIER_DISTRIBUTION.keys()),
            weights=list(TIER_DISTRIBUTION.values()),
            k=1
        )[0]

    def _get_kpi_target(self, kpi_code: str) -> float:
        """Get realistic target value for a KPI code"""
        targets = {
            'AI-KPI1': 85.0,   # GPU Utilization %
            'AI-KPI2': 12.0,   # Deployments/month
            'AI-KPI3': 50.0,   # Latency ms (lower is better, but stored as score)
            'CH-KPI1': 80.0,   # Partner engagement score
            'CH-KPI2': 30.0,   # Channel revenue %
            'CH-KPI3': 4.0,    # Certification level (1-5)
            'DV-KPI1': 99.9,   # Uptime %
            'DV-KPI2': 95.0,   # Deploy success %
            'DV-KPI3': 14.0,   # Days to first workload (lower better)
            'EX-KPI1': 75.0,   # Capacity util %
            'EX-KPI2': 500000, # Pipeline $
            'EX-KPI3': 25.0,   # Upsell conversion %
            'OS-KPI1': 98.0,   # SLA compliance %
            'OS-KPI2': 4.0,    # MTTR hours (lower better)
            'OS-KPI3': 90.0,   # Incident resolution %
        }
        return targets.get(kpi_code, 85.0)

    def _generate_kpi_value(self, kpi_code: str, target: float, month: int) -> float:
        """Generate a realistic KPI value with some variance"""
        # Base variance: ±20% around target
        variance = target * 0.20
        value = target + random.gauss(0, variance * 0.5)

        # Month trend: slight improvement over time
        value += month * target * 0.01

        # Ensure reasonable bounds
        if kpi_code in ('DV-KPI1', 'OS-KPI1'):  # Uptime/SLA should be high
            value = max(90.0, min(100.0, value))
        elif kpi_code in ('AI-KPI3', 'DV-KPI3', 'OS-KPI2'):  # Lower is better
            value = max(1.0, value)
        elif kpi_code == 'CH-KPI3':  # Certification level 1-5
            value = max(1.0, min(5.0, value))
        elif kpi_code == 'EX-KPI2':  # Pipeline value (dollar amount)
            value = max(0, value)
        else:
            value = max(0, min(100, value))

        return value

    def _product_category(self, product_name: str) -> str:
        """Map product name to category"""
        categories = {
            'GPU': 'Compute',
            'AI': 'AI/ML',
            'Inference': 'AI/ML',
            'Data Lake': 'Storage',
            'Edge': 'Edge',
            'Network': 'Networking',
            'Cooling': 'Facilities',
            'Power': 'Facilities',
            'Security': 'Security',
            'Monitoring': 'Observability',
        }
        for keyword, category in categories.items():
            if keyword in product_name:
                return category
        return 'Other'


def main():
    """CLI entry point for standalone CSV generation"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate synthetic CSV data for CS Pulse load testing')
    parser.add_argument('--customer-id', type=int, default=1, help='Customer ID (default: 1)')
    parser.add_argument('--num-accounts', type=int, default=50, help='Number of accounts (default: 50)')
    parser.add_argument('--months', type=int, default=3, help='Months of KPI data (default: 3)')
    parser.add_argument('--output-dir', default='./generated_data', help='Output directory')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')

    args = parser.parse_args()

    gen = CSVGenerator(
        customer_id=args.customer_id,
        num_accounts=args.num_accounts,
        seed=args.seed
    )
    files = gen.generate_all(args.output_dir)

    print(f"\nGenerated {len(files)} files:")
    for name, path in files.items():
        print(f"  {name}: {path}")


if __name__ == '__main__':
    main()
