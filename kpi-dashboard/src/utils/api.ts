// API utility functions
export const getApiBaseUrl = (): string => {
  // In Docker, use the environment variable
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  
  // In development, use localhost (matches proxy in package.json)
  return 'http://localhost:8001';
};

export const apiCall = async (endpoint: string, options: RequestInit = {}): Promise<Response> => {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint}`;
  
  const defaultOptions: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    }
    };
  
  return fetch(url, { ...defaultOptions, ...options });
};
