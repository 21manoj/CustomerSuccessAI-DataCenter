#!/usr/bin/env python3
"""
HTTP Client Wrapper for CS Pulse Platform
Handles authentication, session management, retries, and health checks
"""

import warnings
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple

# Suppress LibreSSL/NotOpenSSL warning before importing requests/urllib3
# (macOS ships LibreSSL instead of OpenSSL — harmless for HTTP connections)
warnings.filterwarnings("ignore", message=".*LibreSSL.*")
warnings.filterwarnings("ignore", message=".*NotOpenSSL.*")

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry as UrllibRetry

logger = logging.getLogger(__name__)


class CSPulseClient:
    """
    Authenticated HTTP client with session management, retry logic, and health gates.

    Features:
    - Session-based auth (login → cookie → all subsequent requests)
    - Automatic retry on 5xx errors (exponential backoff)
    - Request logging at DEBUG level
    - Response validation (checks status codes, JSON parsing)
    - Multi-customer support via X-Customer-ID header
    - Health check before executing scenarios
    """

    def __init__(
        self,
        base_url: str = "http://localhost:5059",
        email: Optional[str] = None,
        password: Optional[str] = None,
        customer_id: Optional[int] = None,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.5
    ):
        """
        Initialize CS Pulse client

        Args:
            base_url: CS Pulse backend URL (e.g., http://localhost:5059)
            email: Admin email for login
            password: Admin password for login
            customer_id: Customer ID for X-Customer-ID header (optional)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts on 5xx errors
            backoff_factor: Exponential backoff multiplier (2s, 4s, 8s, 16s)
        """
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.password = password
        self.customer_id = customer_id
        self.customer_uuid = None  # Populated after login from response
        self.auth_customer_id = None  # Populated after login: authenticated user's actual customer
        self.timeout = timeout
        self.session = requests.Session()

        # Setup retry strategy (only for 5xx, not 4xx)
        retry_strategy = UrllibRetry(
            total=max_retries,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            backoff_factor=backoff_factor
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update({
            'User-Agent': 'CS-Pulse-Load-Driver/3.0',
            'Content-Type': 'application/json'
        })

        # If customer_id provided, add to all requests
        if self.customer_id:
            self.session.headers.update({'X-Customer-ID': str(self.customer_id)})

        self._authenticated = False
        logger.info(f"Initialized CS Pulse client: {self.base_url}")

    def health_check(self) -> bool:
        """
        Check if CS Pulse backend is healthy and ready

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/health",
                timeout=self.timeout
            )
            status = response.status_code == 200
            if status:
                logger.info("✅ CS Pulse health check: OK")
            else:
                logger.error(f"❌ CS Pulse health check failed: {response.status_code}")
            return status
        except Exception as e:
            logger.error(f"❌ CS Pulse health check error: {e}")
            return False

    def login(self) -> bool:
        """
        Authenticate user and establish session

        Returns:
            True if login successful, False otherwise

        Note:
            Uses direct request (not self.post) to access raw Set-Cookie header.
            The Flask session cookie may have Secure flag which prevents
            requests.Session from auto-sending it over HTTP. We extract the
            cookie value manually and set it via the Cookie header.
        """
        if not self.email or not self.password:
            logger.error("❌ Email and password required for login")
            return False

        try:
            url = f"{self.base_url}/api/login"
            raw_response = self.session.post(
                url,
                json={'email': self.email, 'password': self.password},
                timeout=self.timeout
            )

            if raw_response.status_code != 200:
                logger.error(f"❌ Login failed: HTTP {raw_response.status_code}")
                return False

            response = raw_response.json()

            if response.get('status') == 'success':
                self._authenticated = True

                # ── Fix Secure cookie issue ──
                # Flask may set Secure flag on session cookie, which prevents
                # requests from sending it over HTTP. Extract manually.
                set_cookie = raw_response.headers.get('Set-Cookie', '')
                for part in set_cookie.split(';'):
                    part = part.strip()
                    if part.startswith('cs_session='):
                        cookie_val = part.split('=', 1)[1]
                        self.session.headers.update({'Cookie': f'cs_session={cookie_val}'})
                        logger.debug(f"Set manual Cookie header (Secure flag workaround)")
                        break

                # Capture UUID from login response
                # UUID may be at top level or nested under 'user'
                customer_uuid = response.get('customer_uuid')
                if not customer_uuid:
                    user_data = response.get('user', {})
                    customer_uuid = user_data.get('customer_uuid')

                if customer_uuid:
                    self.customer_uuid = customer_uuid

                # Set X-Customer-ID header: use target customer_id (from CLI)
                # if provided, otherwise fall back to login user's UUID/ID.
                # This allows admin users to act on behalf of target customers.
                if self.customer_id:
                    self.session.headers.update({'X-Customer-ID': str(self.customer_id)})
                    logger.info(f"✅ Logged in as {self.email} (target customer: {self.customer_id})")
                elif customer_uuid:
                    self.session.headers.update({'X-Customer-ID': customer_uuid})
                    logger.info(f"✅ Logged in as {self.email} (UUID: {customer_uuid})")
                else:
                    logger.info(f"✅ Logged in as {self.email} (no UUID — using session only)")

                # Capture the authenticated user's integer customer_id
                # This may differ from self.customer_id (CLI arg) when admin
                # users belong to a different customer than the target.
                resp_cid = response.get('customer_id')
                if not resp_cid:
                    user_data = response.get('user', {})
                    resp_cid = user_data.get('customer_id')
                self.auth_customer_id = resp_cid  # authenticated user's customer

                return True
            else:
                logger.error(f"❌ Login failed: {response}")
                return False
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        skip_auth_check: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        GET request with error handling

        Args:
            endpoint: API endpoint (e.g., '/api/accounts')
            params: Query parameters
            skip_auth_check: Skip authentication check for public endpoints

        Returns:
            JSON response or None on error
        """
        if not skip_auth_check and not self._authenticated:
            logger.error("Not authenticated. Call login() first.")
            return None

        url = f"{self.base_url}{endpoint}"
        logger.debug(f"GET {url}")

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error {response.status_code}: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def post(
        self,
        endpoint: str,
        data: Dict[str, Any],
        skip_auth_check: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        POST request with error handling

        Args:
            endpoint: API endpoint (e.g., '/api/register')
            data: Request body
            skip_auth_check: Skip authentication check for public endpoints

        Returns:
            JSON response or None on error
        """
        if not skip_auth_check and not self._authenticated:
            logger.error("Not authenticated. Call login() first.")
            return None

        url = f"{self.base_url}{endpoint}"
        logger.debug(f"POST {url}\nBody: {json.dumps(data, indent=2)[:200]}...")

        try:
            response = self.session.post(
                url,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error {response.status_code}: {response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def put(
        self,
        endpoint: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """PUT request with error handling"""
        if not self._authenticated:
            logger.error("Not authenticated")
            return None

        url = f"{self.base_url}{endpoint}"
        logger.debug(f"PUT {url}")

        try:
            response = self.session.put(
                url,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error {response.status_code}: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def delete(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """DELETE request with error handling"""
        if not self._authenticated:
            logger.error("Not authenticated")
            return None

        url = f"{self.base_url}{endpoint}"
        logger.debug(f"DELETE {url}")

        try:
            response = self.session.delete(
                url,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error {response.status_code}: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    def register_customer(
        self,
        company_name: str,
        admin_name: str,
        email: str,
        password: str,
        vertical: str = "dc2_s"
    ) -> Optional[Dict[str, Any]]:
        """
        Register a new customer

        Returns:
            Response with customer_id, user_id, uuids, or None on error
        """
        response = self.post(
            '/api/register',
            {
                'company_name': company_name,
                'admin_name': admin_name,
                'email': email,
                'password': password,
                'vertical': vertical
            },
            skip_auth_check=True
        )
        return response

    def complete_onboarding(
        self,
        customer_id: int,
        customer_name: str,
        vertical: str = "dc2_s",
        num_accounts: int = 3,
        onboarding_mode: str = "demo"
    ) -> Optional[Dict[str, Any]]:
        """
        Complete onboarding (create accounts + provision directory)

        Returns:
            Response with account_ids, directory status, or None on error
        """
        response = self.post(
            '/api/onboarding/complete',
            {
                'customer_id': customer_id,
                'customer_name': customer_name,
                'vertical': vertical,
                'num_accounts': num_accounts,
                'onboarding_mode': onboarding_mode
            },
            skip_auth_check=True
        )
        return response

    def upload_csv(
        self,
        customer_id: int,
        file_type: str,
        csv_content: str,
        filename: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Upload a CSV file to onboarding endpoint (multipart form).

        /api/onboarding/upload is a public endpoint — no auth required.

        Args:
            customer_id: Customer ID
            file_type: e.g. 'accounts', 'kpis', 'stakeholders', etc.
            csv_content: CSV string content
            filename: Override filename (defaults to file_type.csv)
        """
        url = f"{self.base_url}/api/onboarding/upload"
        fname = filename or f"{file_type}.csv"
        try:
            # Temporarily remove Content-Type header — requests must set
            # its own multipart/form-data boundary for file uploads
            saved_ct = self.session.headers.pop('Content-Type', None)
            response = self.session.post(
                url,
                files={'file': (fname, csv_content, 'text/csv')},
                data={'customer_id': customer_id, 'file_type': file_type},
                timeout=self.timeout
            )
            if saved_ct:
                self.session.headers['Content-Type'] = saved_ct
            response.raise_for_status()
            return response.json() if response.content else {}
        except Exception as e:
            if saved_ct:
                self.session.headers['Content-Type'] = saved_ct
            logger.error(f"Upload error ({file_type}): {e}")
            return None

    def process_data(
        self,
        customer_id: int,
        vertical: str = "dc2_s",
        skip_wizard_b: bool = True,
        skip_wizard_c: bool = False,
        strict_kpi_ranges: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Process uploaded data (load CSVs, embeddings, journey, weights)"""
        response = self.post(
            '/api/onboarding/process-data',
            {
                'customer_id': customer_id,
                'vertical': vertical,
                'skip_wizard_b': skip_wizard_b,
                'skip_wizard_c': skip_wizard_c,
                'strict_kpi_ranges': strict_kpi_ranges
            },
            skip_auth_check=True
        )
        return response

    def calculate_scores(
        self,
        customer_id: int,
        measurement_month: str = "2024-12-01"
    ) -> Optional[Dict[str, Any]]:
        """Calculate health, pillar, and KPI scores"""
        response = self.post(
            '/api/dc2s/scores/calculate',
            {
                'customer_id': customer_id,
                'measurement_month': measurement_month
            }
        )
        return response

    def get_accounts(self) -> Optional[list]:
        """List all accounts for current customer"""
        response = self.get('/api/dc2s/accounts')
        return response.get('accounts', []) if response else None

    def get_account_scores(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Get latest health, pillar, and KPI scores for account"""
        response = self.get(f'/api/dc2s/scores/account/{account_id}/latest')
        return response

    def rag_query(self, query: str, customer_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Execute a RAG query against Qdrant"""
        response = self.post(
            '/api/direct-rag/query',
            {
                'query': query,
                'customer_id': customer_id or self.customer_id
            }
        )
        return response

    def trigger_playbook(
        self,
        playbook_id: str,
        account_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Trigger a playbook execution"""
        response = self.post(
            '/api/playbooks/executions',
            {
                'playbook_id': playbook_id,
                'account_id': account_id,
                'context': context or {}
            }
        )
        return response

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get playbook execution status"""
        response = self.get(f'/api/playbooks/executions/{execution_id}')
        return response

    def cleanup_customer(self, customer_id: int, dry_run: bool = False) -> Optional[Dict[str, Any]]:
        """Post-test cleanup: delete all customer data"""
        payload = {'dry_run': dry_run}
        if not dry_run:
            payload['confirm'] = True
        response = self.post(
            f'/api/admin/cleanup/customer/{customer_id}',
            payload
        )
        return response

    def get_qdrant_status(self) -> Optional[Dict[str, Any]]:
        """Check Qdrant vector DB health"""
        try:
            response = requests.get(
                "http://localhost:6333/health",
                timeout=5
            )
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.warning(f"Qdrant unavailable: {e}")
            return None

    def is_context_graph_enabled(self, customer_id: int = None) -> bool:
        """
        Check if context graph feature is enabled for the given customer.
        Checks the /api/features/context-graph endpoint which returns
        'active' = (global_enabled AND customer_enabled).

        Args:
            customer_id: Customer ID to check (defaults to self.customer_id)

        Returns:
            True if context_graph toggle is active, False otherwise
        """
        cid = customer_id or self.customer_id
        response = self.get('/api/features/context-graph', params={'customer_id': cid})
        if response and response.get('status') == 'success':
            # 'active' = global AND customer toggle both on
            return response.get('active', False)
        return False

    def ingest_context_graph(
        self,
        customer_id: int,
        nodes: list,
        edges: list,
    ) -> Optional[Dict[str, Any]]:
        """
        Incrementally upsert context graph nodes and edges.
        Non-destructive: deduplicates via source_event_id (nodes) and
        (from_node_id, to_node_id, edge_type, source_platform) for edges.

        Args:
            customer_id: Customer owning the data
            nodes: List of node dicts (account_id, node_type, title, ...)
            edges: List of edge dicts (from_source_event_id, to_source_event_id, edge_type, ...)

        Returns:
            {status, nodes_upserted, nodes_created, edges_upserted, edges_created, ...}
        """
        response = self.post(
            '/api/context-graph/ingest',
            {
                'customer_id': customer_id,
                'nodes': nodes,
                'edges': edges,
            }
        )
        return response

    def get_dc2s_health_score(
        self, account_id: int, month: str = "aggregate"
    ) -> Optional[Dict[str, Any]]:
        """
        DC2S health from latest KPI rows (works right after onboarding ingest).

        Unlike get_account_scores(), this does not require health_scores rows.
        """
        params = {"month": month} if month else None
        return self.get(f"/api/dc2s/health-score/{account_id}", params=params)

    def enable_context_graph(self, customer_id: int = None) -> bool:
        """
        Enable context_graph feature toggle (global + per-customer).

        The global toggle activates the platform-level CONTEXT_GRAPH flag.
        The per-customer toggle (via POST /api/features/context-graph) enables
        context graph for the specific customer using the X-Customer-ID header
        already set on the session.

        Args:
            customer_id: Customer ID (defaults to self.customer_id)

        Returns:
            True if both toggles were set successfully, False otherwise
        """
        cid = customer_id or self.customer_id

        # 1) Global toggle — enables the platform-level CONTEXT_GRAPH flag
        global_resp = self.post(
            '/api/feature-toggle',
            {'feature': 'context_graph', 'enabled': True},
        )
        if not global_resp:
            logger.warning("Failed to set global context_graph toggle")

        # 2) Per-customer toggle — uses X-Customer-ID header (already set)
        per_cust_resp = self.post(
            '/api/features/context-graph',
            {
                'enabled': True,
                'sub_toggles': {
                    'story_arcs': True,
                    'signal_edges': True,
                    'stakeholder_tracking': True,
                    'decision_lifecycle': True,
                    'outcome_economics': True,
                    'industry_benchmarks': True,
                },
            },
        )
        if not per_cust_resp:
            logger.warning(f"Failed to set per-customer context_graph toggle for customer {cid}")
            return False

        active = per_cust_resp.get('active', False)
        logger.info(f"Context graph enabled for customer {cid} (active={active})")
        return True

    def get_context_graph_summary(
        self,
        account_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get context graph summary (node counts, edge counts, revenue) for an account."""
        return self.get('/api/context-graph/summary', params={'account_id': account_id})


# Convenience function for quick setup
def create_authenticated_client(
    base_url: str,
    email: str,
    password: str,
    customer_id: Optional[int] = None
) -> Optional[CSPulseClient]:
    """Create and authenticate a client in one call"""
    client = CSPulseClient(
        base_url=base_url,
        email=email,
        password=password,
        customer_id=customer_id
    )
    if client.health_check() and client.login():
        return client
    return None
