// API utility functions

/**
 * Get the best customer identifier for X-Customer-ID header.
 * Prefers UUID when available (from UUID migration), falls back to integer ID.
 * Backend resolve_customer_id() handles both formats.
 */
export const getCustomerIdentifier = (session: { customer_id: number; customer_uuid?: string } | null): string => {
  if (!session) return '1';
  return session.customer_uuid || session.customer_id.toString();
};

export const getApiBaseUrl = (): string => {
  // In Docker, use the environment variable
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  
  // In development, use relative URLs (proxy handles routing)
  // This works with Vite proxy or React dev server proxy
  return '';
};

export const apiCall = async (endpoint: string, options: RequestInit = {}): Promise<Response> => {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint}`;
  
  const defaultOptions: RequestInit = {
    credentials: 'include', // Always include cookies for session auth
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    }
  };
  
  // Merge options, with user-provided options taking precedence
  const mergedOptions: RequestInit = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...options.headers
    }
  };
  
  return fetch(url, mergedOptions);
};
