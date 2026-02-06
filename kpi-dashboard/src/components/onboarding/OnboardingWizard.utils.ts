/**
 * Onboarding Wizard - Utility Functions
 */

import { ValidationResult, DataSource } from './OnboardingWizard.types';

/**
 * Validate CSV file structure and content
 */
export const validateCSV = async (file: File, requiredColumns?: string[]): Promise<ValidationResult> => {
  const errors: string[] = [];
  const warnings: string[] = [];

  try {
    const text = await file.text();
    const lines = text.split('\n').filter(line => line.trim());
    
    if (lines.length < 2) {
      errors.push('CSV file must have at least a header row and one data row');
      return { valid: false, errors, warnings };
    }

    const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
    
    // Check required columns
    if (requiredColumns) {
      const missing = requiredColumns.filter(
        req => !headers.some(h => h.includes(req.toLowerCase()))
      );
      if (missing.length > 0) {
        errors.push(`Missing required columns: ${missing.join(', ')}`);
      }
    }

    // Validate data rows
    const dataRows = lines.slice(1);
    let rowNumber = 2; // Start from row 2 (after header)

    for (const row of dataRows.slice(0, 10)) { // Check first 10 rows
      const values = row.split(',');
      if (values.length !== headers.length) {
        warnings.push(`Row ${rowNumber}: Column count mismatch (expected ${headers.length}, got ${values.length})`);
      }
      rowNumber++;
    }

    // Check for empty rows
    const emptyRows = dataRows.filter(row => !row.trim());
    if (emptyRows.length > 0) {
      warnings.push(`Found ${emptyRows.length} empty row(s)`);
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
      row_count: dataRows.length,
      columns: headers
    };
  } catch (error) {
    errors.push(`Failed to parse CSV: ${error instanceof Error ? error.message : 'Unknown error'}`);
    return { valid: false, errors, warnings };
  }
};

/**
 * Preview CSV file (first N rows)
 */
export const previewCSV = async (file: File, rows: number = 5): Promise<any[]> => {
  try {
    const text = await file.text();
    const lines = text.split('\n').filter(line => line.trim());
    
    if (lines.length < 2) return [];

    const headers = lines[0].split(',').map(h => h.trim());
    const dataRows = lines.slice(1, rows + 1);

    return dataRows.map(row => {
      const values = row.split(',');
      const obj: any = {};
      headers.forEach((header, index) => {
        obj[header] = values[index]?.trim() || '';
      });
      return obj;
    });
  } catch (error) {
    console.error('Error previewing CSV:', error);
    return [];
  }
};

/**
 * Test API connection
 */
export const testAPIConnection = async (config: {
  endpoint: string;
  api_key?: string;
  auth_type?: string;
}): Promise<{ success: boolean; message: string; schema?: any }> => {
  try {
    // Simulate API connection test
    // In real implementation, this would make an actual API call
    
    await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate network delay

    // Mock successful connection
    if (config.endpoint && config.api_key) {
      return {
        success: true,
        message: 'Connection successful',
        schema: {
          tables: ['accounts', 'kpis', 'events'],
          last_updated: new Date().toISOString()
        }
      };
    }

    return {
      success: false,
      message: 'Missing required configuration (endpoint and API key)'
    };
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Connection failed'
    };
  }
};

/**
 * Calculate password strength (0-4)
 */
export const calculatePasswordStrength = (password: string): number => {
  let strength = 0;
  if (password.length >= 8) strength++;
  if (password.match(/[a-z]/) && password.match(/[A-Z]/)) strength++;
  if (password.match(/[0-9]/)) strength++;
  if (password.match(/[^a-zA-Z0-9]/)) strength++;
  return strength;
};

/**
 * Validate email format
 */
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Calculate required account IDs for customer
 */
export const calculateAccountIdStart = (customerId: number): number => {
  return 10000 + (customerId * 1000);
};

/**
 * Format file size for display
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};
