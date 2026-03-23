/**
 * Admin UI API Client
 *
 * Typed functions for every Admin UI backend endpoint.
 * All requests include credentials (session cookie) and JSON content-type.
 */

import { getApiBaseUrl } from '../utils/api';

const API_BASE = '/api/admin-ui';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Customer {
  customer_id: number;
  customer_name: string;
  domain: string;
  vertical: string;
  created_at: string;
  is_reference: boolean;
}

export interface LicenseInfo {
  license_type: string;
  max_seats: number;
  max_accounts: number | null;
  license_start: string;
  license_end: string;
  auto_renew: boolean;
}

export interface SeatUsage {
  used: number;
  max: number;
  available: number;
  utilization_pct: number;
}

export interface UserInfo {
  user_id: number;
  user_name: string;
  email: string;
  role: string;
  active: boolean;
  last_login: string | null;
  is_contractor: boolean;
  expires_at: string | null;
  allowed_account_ids: number[] | null;
  allowed_customer_ids: number[] | null;
}

export interface ApiKeyInfo {
  id: number;
  key_prefix: string;
  name: string;
  scopes: string[];
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
  expires_at: string | null;
  partner_tier: string | null;
  allowed_account_ids: number[] | null;
}

export interface KpiConfig {
  vertical: string;
  pillar_weights: Record<string, number> | null;
  enabled_kpis: string[] | null;
  kpi_weights: Record<string, Record<string, number>> | null;
  kpi_overrides: Record<string, unknown> | null;
  config_version: string;
}

export interface CustomerDetail extends Customer {
  license: LicenseInfo;
  seat_usage: SeatUsage;
  users: UserInfo[];
  api_keys: ApiKeyInfo[];
  kpi_config: KpiConfig | null;
}

export interface VerticalInfo {
  vertical: string;
  label: string;
  pillar_count: number;
  kpi_count: number;
  pillar_names: Record<string, string>;
  default_weights: Record<string, number>;
}

export interface DashboardStats {
  total_customers: number;
  active_users: number;
  seat_warnings: number;
  license_warnings: number;
  verticals: string[];
}

export interface CreateCustomerPayload {
  company_name: string;
  admin_email: string;
  admin_name: string;
  password: string;
  vertical: string;
  tier?: 'starter' | 'professional' | 'enterprise';
  domain?: string;
}

export interface CreateUserPayload {
  user_name: string;
  email: string;
  role: string;
  password: string;
}

export interface LicenseWarning {
  customer_id: number;
  customer_name: string;
  license_type: string;
  seats_used: number;
  seats_max: number;
  license_end: string;
  status: 'expired' | 'expiring_soon' | 'over_limit' | 'ok';
  days_remaining: number | null;
}

export interface ActivityEntry {
  id: number;
  timestamp: string;
  customer_id: number | null;
  customer_name: string | null;
  user_name: string | null;
  action: string;
  description: string;
  status: string;
}

export interface ContractorInfo {
  user_id: number;
  user_name: string;
  email: string;
  role: string;
  active: boolean;
  is_contractor: boolean;
  expires_at: string | null;
  allowed_account_ids: number[] | null;
  allowed_customer_ids: number[] | null;
  created_at: string;
}

export interface PaginatedActivity {
  entries: ActivityEntry[];
  total: number;
  page: number;
  limit: number;
}

export interface VerticalTemplate {
  config_type: string;
  version: number;
  config: Record<string, unknown>;
  updated_at: string;
}

export interface CustomerConfig {
  config_type: string;
  config: Record<string, unknown>;
  updated_at: string;
}

export interface ResolvedConfig {
  config_type: string;
  source: 'customer' | 'template';
  config: Record<string, unknown>;
  template_config?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${API_BASE}${path}`;

  const resp = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> | undefined),
    },
    ...options,
  });

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ error: resp.statusText }));
    throw new Error(body.error || body.message || `Request failed: ${resp.status}`);
  }

  // 204 No Content
  if (resp.status === 204) return undefined as unknown as T;

  return resp.json() as Promise<T>;
}

function qs(params: Record<string, string | number | undefined>): string {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') {
      parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
    }
  }
  return parts.length ? `?${parts.join('&')}` : '';
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const raw = await request<{
    overview: {
      total_customers: number;
      active_customers: number;
      total_active_users: number;
      total_active_accounts: number;
    };
    seat_warnings: { count: number; customers: unknown[] };
    license_expiry_warnings: { count: number; customers: unknown[] };
    expired_licenses: { count: number; customers: unknown[] };
    vertical_distribution: Array<{ vertical: string; customer_count: number }>;
  }>('/dashboard/stats');

  return {
    total_customers: raw.overview?.total_customers ?? 0,
    active_users: raw.overview?.total_active_users ?? 0,
    seat_warnings: raw.seat_warnings?.count ?? 0,
    license_warnings: (raw.license_expiry_warnings?.count ?? 0) + (raw.expired_licenses?.count ?? 0),
    verticals: (raw.vertical_distribution ?? []).map((v) => v.vertical),
  };
}

// ---------------------------------------------------------------------------
// Customers
// ---------------------------------------------------------------------------

export async function fetchCustomers(
  params?: { search?: string; vertical?: string; page?: number },
): Promise<{ customers: Customer[]; total: number }> {
  const raw = await request<{
    customers: Customer[];
    pagination: { page: number; per_page: number; total: number; pages: number };
  }>(`/customers${qs(params || {})}`);
  return {
    customers: raw.customers ?? [],
    total: raw.pagination?.total ?? 0,
  };
}

export async function fetchCustomer(id: number): Promise<CustomerDetail> {
  const raw = await request<{
    customer: Customer & { email?: string; phone?: string; uuid?: string };
    config: Record<string, unknown>;
    license: {
      license: {
        license_type: string;
        max_seats: number;
        max_accounts: number | null;
        license_start: string;
        license_end: string;
        auto_renew: boolean;
      } | null;
      seat_usage: { used: number; max: number | null; available: number | null; utilisation_pct: number };
      warnings: string[];
      is_valid: boolean;
      is_expired: boolean;
      days_to_expiry: number | null;
    };
  }>(`/customers/${id}`);

  const c = raw.customer;
  const lic = raw.license?.license;
  const su = raw.license?.seat_usage;

  return {
    customer_id: c.customer_id,
    customer_name: c.customer_name,
    domain: c.domain ?? '',
    vertical: c.vertical,
    created_at: c.created_at,
    is_reference: c.is_reference ?? false,
    license: {
      license_type: lic?.license_type ?? 'none',
      max_seats: lic?.max_seats ?? 0,
      max_accounts: lic?.max_accounts ?? null,
      license_start: lic?.license_start ?? '',
      license_end: lic?.license_end ?? '',
      auto_renew: lic?.auto_renew ?? false,
    },
    seat_usage: {
      used: su?.used ?? 0,
      max: su?.max ?? 0,
      available: su?.available ?? 0,
      utilization_pct: su?.utilisation_pct ?? 0,
    },
    users: [],     // loaded lazily via fetchUsers
    api_keys: [],  // loaded lazily via fetchApiKeys
    kpi_config: raw.config ? {
      vertical: (raw.config.vertical as string) ?? 'dc2_s',
      pillar_weights: (raw.config.pillar_weights as Record<string, number>) ?? null,
      enabled_kpis: (raw.config.enabled_kpis as string[]) ?? null,
      kpi_weights: (raw.config.kpi_weights as Record<string, Record<string, number>>) ?? null,
      kpi_overrides: (raw.config.kpi_overrides as Record<string, unknown>) ?? null,
      config_version: (raw.config.config_version as string) ?? '1.0',
    } : null,
  };
}

export async function createCustomer(
  data: CreateCustomerPayload,
): Promise<{ customer_id: number; api_key: string }> {
  return request('/customers', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateCustomer(id: number, data: Partial<Customer>): Promise<Customer> {
  return request(`/customers/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deactivateCustomer(id: number): Promise<void> {
  return request(`/customers/${id}/deactivate`, { method: 'POST' });
}

export async function reactivateCustomer(id: number): Promise<void> {
  return request(`/customers/${id}/reactivate`, { method: 'POST' });
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export async function fetchUsers(customerId: number): Promise<UserInfo[]> {
  const raw = await request<{ users: UserInfo[] }>(`/customers/${customerId}/users`);
  return raw.users ?? [];
}

export async function createUser(
  customerId: number,
  data: CreateUserPayload,
): Promise<UserInfo> {
  return request(`/customers/${customerId}/users`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateUser(userId: number, data: Partial<UserInfo>): Promise<UserInfo> {
  return request(`/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// License
// ---------------------------------------------------------------------------

export async function fetchLicense(
  customerId: number,
): Promise<LicenseInfo & SeatUsage> {
  const raw = await request<{
    license: {
      license_type: string;
      max_seats: number;
      max_accounts: number | null;
      license_start: string;
      license_end: string;
      auto_renew: boolean;
    } | null;
    seat_usage: { used: number; max: number | null; available: number | null; utilisation_pct: number };
    warnings: string[];
  }>(`/customers/${customerId}/license`);

  const lic = raw.license;
  const su = raw.seat_usage;
  return {
    license_type: lic?.license_type ?? 'none',
    max_seats: lic?.max_seats ?? 0,
    max_accounts: lic?.max_accounts ?? null,
    license_start: lic?.license_start ?? '',
    license_end: lic?.license_end ?? '',
    auto_renew: lic?.auto_renew ?? false,
    used: su?.used ?? 0,
    max: su?.max ?? 0,
    available: su?.available ?? 0,
    utilization_pct: su?.utilisation_pct ?? 0,
  };
}

export async function updateLicense(
  customerId: number,
  data: Partial<LicenseInfo>,
): Promise<LicenseInfo> {
  return request(`/customers/${customerId}/license`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function fetchLicenseWarnings(): Promise<LicenseWarning[]> {
  const raw = await request<{ warnings: LicenseWarning[] }>('/license/warnings');
  return raw.warnings ?? [];
}

// ---------------------------------------------------------------------------
// Verticals
// ---------------------------------------------------------------------------

export async function fetchVerticals(): Promise<VerticalInfo[]> {
  const raw = await request<{ verticals: VerticalInfo[] }>('/verticals');
  return raw.verticals ?? [];
}

export async function fetchVerticalTemplates(vertical: string): Promise<VerticalTemplate[]> {
  const raw = await request<{ templates: VerticalTemplate[] }>(
    `/verticals/${encodeURIComponent(vertical)}/templates`,
  );
  return raw.templates ?? [];
}

export async function fetchTemplate(
  vertical: string,
  configType: string,
): Promise<VerticalTemplate> {
  return request(
    `/verticals/${encodeURIComponent(vertical)}/templates/${encodeURIComponent(configType)}`,
  );
}

export async function updateTemplate(
  vertical: string,
  configType: string,
  config: Record<string, unknown>,
): Promise<VerticalTemplate> {
  return request(
    `/verticals/${encodeURIComponent(vertical)}/templates/${encodeURIComponent(configType)}`,
    { method: 'PUT', body: JSON.stringify({ config }) },
  );
}

// ---------------------------------------------------------------------------
// Customer Config
// ---------------------------------------------------------------------------

export async function fetchCustomerConfig(customerId: number): Promise<CustomerConfig[]> {
  const raw = await request<{ overrides: CustomerConfig[] }>(`/customers/${customerId}/config`);
  return raw.overrides ?? [];
}

export async function fetchResolvedConfig(
  customerId: number,
  configType: string,
): Promise<ResolvedConfig> {
  return request(
    `/customers/${customerId}/config/${encodeURIComponent(configType)}/resolved`,
  );
}

export async function updateCustomerConfig(
  customerId: number,
  configType: string,
  config: Record<string, unknown>,
): Promise<CustomerConfig> {
  return request(
    `/customers/${customerId}/config/${encodeURIComponent(configType)}`,
    { method: 'PUT', body: JSON.stringify({ config }) },
  );
}

export async function deleteCustomerConfig(
  customerId: number,
  configType: string,
): Promise<void> {
  return request(
    `/customers/${customerId}/config/${encodeURIComponent(configType)}`,
    { method: 'DELETE' },
  );
}

// ---------------------------------------------------------------------------
// API Keys
// ---------------------------------------------------------------------------

export async function fetchApiKeys(customerId: number): Promise<ApiKeyInfo[]> {
  const raw = await request<{ api_keys: ApiKeyInfo[] }>(`/customers/${customerId}/api-keys`);
  return raw.api_keys ?? [];
}

export async function generateApiKey(
  customerId: number,
  data: {
    name: string;
    scopes: string[];
    duration_days?: number;
    allowed_account_ids?: number[] | null;
    partner_tier?: string | null;
  },
): Promise<{ key: string; key_info: ApiKeyInfo }> {
  const result = await request(`/customers/${customerId}/api-keys`, {
    method: 'POST',
    body: JSON.stringify(data),
  }) as { api_key?: string; key?: string; key_info: ApiKeyInfo };
  // Backend returns { api_key, key_info } — normalize to { key, key_info }
  return { key: (result.api_key || result.key) as string, key_info: result.key_info };
}

export async function revokeApiKey(keyId: number): Promise<void> {
  return request(`/api-keys/${keyId}/revoke`, { method: 'POST' });
}

export async function reinstateApiKey(keyId: number): Promise<void> {
  return request(`/api-keys/${keyId}/reinstate`, { method: 'POST' });
}

// ---------------------------------------------------------------------------
// Partner Key Management
// ---------------------------------------------------------------------------

export interface AccountSummary {
  account_id: number;
  account_name: string;
  vertical: string | null;
  arr: number | null;
  status: string;
}

export interface CreatePartnerKeyPayload {
  partner_name: string;
  partner_email: string;
  partner_tier: string;
  allowed_account_ids: number[];
  scopes: string[];
  duration_days: number;
  send_email: boolean;
}

export interface PartnerKeyResult {
  key: string;
  key_info: ApiKeyInfo;
  partner_name: string;
  partner_email: string;
  allowed_accounts: Array<{ id: number; name: string }>;
  email_sent: boolean;
}

export async function fetchCustomerAccounts(customerId: number): Promise<AccountSummary[]> {
  const raw = await request<{ accounts: AccountSummary[] }>(`/customers/${customerId}/accounts`);
  return raw.accounts ?? [];
}

export async function createPartnerKey(
  customerId: number,
  data: CreatePartnerKeyPayload,
): Promise<PartnerKeyResult> {
  return request(`/customers/${customerId}/partner-keys`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export interface PartnerAuditEntry {
  id: number;
  customer_id: number | null;
  action_type: string;
  action_description: string;
  resource_type: string | null;
  created_at: string;
}

export async function fetchPartnerAuditLog(
  params?: { customer_id?: number; page?: number; limit?: number },
): Promise<{ logs: PartnerAuditEntry[]; total: number; page: number }> {
  const bp: Record<string, string | number> = {};
  if (params?.customer_id) bp.customer_id = params.customer_id;
  if (params?.page) bp.page = params.page;
  if (params?.limit) bp.per_page = params.limit;

  const raw = await request<{
    partner_logs: PartnerAuditEntry[];
    pagination: { page: number; total: number };
  }>(`/partner-audit-log${qs(bp)}`);

  return {
    logs: raw.partner_logs ?? [],
    total: raw.pagination?.total ?? 0,
    page: raw.pagination?.page ?? 1,
  };
}

// ---------------------------------------------------------------------------
// Activity Log
// ---------------------------------------------------------------------------

export async function fetchActivityLog(
  params?: { customer_id?: number; page?: number; limit?: number },
): Promise<PaginatedActivity> {
  // Backend uses per_page instead of limit
  const backendParams: Record<string, string | number> = {};
  if (params?.customer_id) backendParams.customer_id = params.customer_id;
  if (params?.page) backendParams.page = params.page;
  if (params?.limit) backendParams.per_page = params.limit;

  const raw = await request<{
    activity_logs: Array<{
      id: number;
      customer_id: number | null;
      user_id: number | null;
      action_type: string;
      action_category: string | null;
      action_description: string | null;
      resource_type: string | null;
      resource_id: string | null;
      status: string;
      ip_address: string | null;
      created_at: string | null;
    }>;
    pagination: { page: number; per_page: number; total: number; pages: number };
  }>(`/activity-log${qs(backendParams)}`);

  return {
    entries: (raw.activity_logs ?? []).map((log) => ({
      id: log.id,
      timestamp: log.created_at ?? '',
      customer_id: log.customer_id,
      customer_name: null, // resolved on frontend if needed
      user_name: null,
      action: log.action_type ?? '',
      description: log.action_description ?? '',
      status: log.status ?? 'success',
    })),
    total: raw.pagination?.total ?? 0,
    page: raw.pagination?.page ?? 1,
    limit: raw.pagination?.per_page ?? 25,
  };
}

// ---------------------------------------------------------------------------
// Contractor Access
// ---------------------------------------------------------------------------

export async function createContractorAccess(
  customerId: number,
  data: {
    contractor_name: string;
    contractor_email: string;
    password: string;
    role: string;
    duration_days: number;
    allowed_account_ids?: number[] | null;
    allowed_customer_ids?: number[] | null;
    notes?: string;
  },
): Promise<{ user_id: number; email: string; expires_at: string }> {
  return request(`/customers/${customerId}/contractor-access`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function fetchContractors(
  customerId: number,
): Promise<ContractorInfo[]> {
  const raw = await request<{ contractors: ContractorInfo[] }>(`/customers/${customerId}/contractors`);
  return raw.contractors ?? [];
}

export async function revokeContractorAccess(
  userId: number,
): Promise<{ keys_revoked: number }> {
  return request(`/contractor-access/${userId}/revoke`, {
    method: 'PUT',
  });
}

// ---------------------------------------------------------------------------
// Security Log
// ---------------------------------------------------------------------------

export async function fetchSecurityLog(
  customerId: number,
  limit: number = 20,
): Promise<ActivityEntry[]> {
  const raw = await request<{
    activity_logs: Array<{
      id: number;
      customer_id: number | null;
      user_id: number | null;
      action_type: string;
      action_category: string | null;
      action_description: string | null;
      resource_type: string | null;
      resource_id: string | null;
      status: string;
      ip_address: string | null;
      created_at: string | null;
    }>;
  }>(`/activity-log${qs({ customer_id: customerId, category: 'security', per_page: limit })}`);

  return (raw.activity_logs ?? []).map((log) => ({
    id: log.id,
    timestamp: log.created_at ?? '',
    customer_id: log.customer_id,
    customer_name: null,
    user_name: null,
    action: log.action_type ?? '',
    description: log.action_description ?? '',
    status: log.status ?? 'success',
  }));
}
