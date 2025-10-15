#!/usr/bin/env python3
"""
Format Detection and Adaptation System
Handles different KPI file formats for customer uploads
"""

import pandas as pd
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class FormatInfo:
    """Information about detected file format"""
    format_type: str
    confidence: float
    required_fields: List[str]
    optional_fields: List[str]
    adapter_class: str

class FormatDetector:
    """Detects and validates different KPI file formats"""
    
    def __init__(self):
        self.supported_formats = {
            'excel_standard': {
                'description': 'Standard KPI Dashboard format',
                'required_sheets': ['Account Info', 'KPI Data', 'Summary'],
                'required_columns': ['Health Score Component', 'KPI/Parameter', 'Data'],
                'confidence_threshold': 0.8
            },
            'excel_simple': {
                'description': 'Simple KPI list format',
                'required_sheets': ['KPIs'],
                'required_columns': ['KPI Name', 'Value', 'Category'],
                'confidence_threshold': 0.7
            },
            'excel_custom': {
                'description': 'Custom Excel format with flexible columns',
                'required_sheets': ['Data'],
                'required_columns': ['KPI', 'Value'],
                'confidence_threshold': 0.6
            },
            'csv_basic': {
                'description': 'Basic CSV format',
                'required_columns': ['kpi_name', 'value', 'category'],
                'confidence_threshold': 0.8
            },
            'csv_standard': {
                'description': 'Standard CSV format',
                'required_columns': ['kpi_parameter', 'data', 'category', 'weight'],
                'confidence_threshold': 0.9
            }
        }
    
    def detect_format(self, file_path: str) -> FormatInfo:
        """Detect file format and return format information"""
        try:
            # Check file extension
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                return self._detect_excel_format(file_path)
            elif file_path.endswith('.csv'):
                return self._detect_csv_format(file_path)
            else:
                return FormatInfo(
                    format_type='unknown',
                    confidence=0.0,
                    required_fields=[],
                    optional_fields=[],
                    adapter_class='UnknownAdapter'
                )
        except Exception as e:
            print(f"Error detecting format: {str(e)}")
            return FormatInfo(
                format_type='error',
                confidence=0.0,
                required_fields=[],
                optional_fields=[],
                adapter_class='ErrorAdapter'
            )
    
    def _detect_excel_format(self, file_path: str) -> FormatInfo:
        """Detect Excel file format"""
        try:
            xls = pd.ExcelFile(file_path)
            sheet_names = xls.sheet_names
            
            # Check for standard format
            if self._is_standard_format(xls):
                return FormatInfo(
                    format_type='excel_standard',
                    confidence=0.9,
                    required_fields=['Health Score Component', 'KPI/Parameter', 'Data', 'Weight'],
                    optional_fields=['Impact Level', 'Source Review', 'Measurement Frequency'],
                    adapter_class='StandardFormatAdapter'
                )
            
            # Check for simple format
            elif self._is_simple_format(xls):
                return FormatInfo(
                    format_type='excel_simple',
                    confidence=0.8,
                    required_fields=['KPI Name', 'Value', 'Category'],
                    optional_fields=['Weight', 'Impact Level', 'Description'],
                    adapter_class='SimpleFormatAdapter'
                )
            
            # Check for custom format
            elif self._is_custom_format(xls):
                return FormatInfo(
                    format_type='excel_custom',
                    confidence=0.7,
                    required_fields=['KPI', 'Value'],
                    optional_fields=['Category', 'Weight', 'Impact', 'Description'],
                    adapter_class='CustomFormatAdapter'
                )
            
            else:
                return FormatInfo(
                    format_type='excel_unknown',
                    confidence=0.3,
                    required_fields=[],
                    optional_fields=[],
                    adapter_class='UnknownAdapter'
                )
                
        except Exception as e:
            print(f"Error detecting Excel format: {str(e)}")
            return FormatInfo(
                format_type='excel_error',
                confidence=0.0,
                required_fields=[],
                optional_fields=[],
                adapter_class='ErrorAdapter'
            )
    
    def _detect_csv_format(self, file_path: str) -> FormatInfo:
        """Detect CSV file format"""
        try:
            # Read first few rows to detect format
            df = pd.read_csv(file_path, nrows=5)
            columns = [col.lower().strip() for col in df.columns]
            
            # Check for standard CSV format
            if all(col in columns for col in ['kpi_parameter', 'data', 'category']):
                return FormatInfo(
                    format_type='csv_standard',
                    confidence=0.9,
                    required_fields=['kpi_parameter', 'data', 'category'],
                    optional_fields=['weight', 'impact_level', 'source_review'],
                    adapter_class='StandardCSVAdapter'
                )
            
            # Check for basic CSV format
            elif all(col in columns for col in ['kpi_name', 'value', 'category']):
                return FormatInfo(
                    format_type='csv_basic',
                    confidence=0.8,
                    required_fields=['kpi_name', 'value', 'category'],
                    optional_fields=['weight', 'impact_level', 'description'],
                    adapter_class='BasicCSVAdapter'
                )
            
            # Check for minimal CSV format
            elif all(col in columns for col in ['kpi', 'value']):
                return FormatInfo(
                    format_type='csv_minimal',
                    confidence=0.6,
                    required_fields=['kpi', 'value'],
                    optional_fields=['category', 'weight', 'impact'],
                    adapter_class='MinimalCSVAdapter'
                )
            
            else:
                return FormatInfo(
                    format_type='csv_unknown',
                    confidence=0.3,
                    required_fields=[],
                    optional_fields=[],
                    adapter_class='UnknownAdapter'
                )
                
        except Exception as e:
            print(f"Error detecting CSV format: {str(e)}")
            return FormatInfo(
                format_type='csv_error',
                confidence=0.0,
                required_fields=[],
                optional_fields=[],
                adapter_class='ErrorAdapter'
            )
    
    def _is_standard_format(self, xls: pd.ExcelFile) -> bool:
        """Check if file follows standard KPI Dashboard format"""
        required_sheets = ['Account Info', 'KPI Data', 'Summary']
        return all(sheet in xls.sheet_names for sheet in required_sheets)
    
    def _is_simple_format(self, xls: pd.ExcelFile) -> bool:
        """Check if file is simple KPI list format"""
        if len(xls.sheet_names) == 1:
            try:
                df = pd.read_excel(xls, xls.sheet_names[0], nrows=5)
                required_cols = ['KPI Name', 'Value', 'Category']
                return all(col in df.columns for col in required_cols)
            except:
                return False
        return False
    
    def _is_custom_format(self, xls: pd.ExcelFile) -> bool:
        """Check if file is custom format with flexible columns"""
        try:
            # Check first sheet for KPI data
            df = pd.read_excel(xls, xls.sheet_names[0], nrows=5)
            required_cols = ['KPI', 'Value']
            return all(col in df.columns for col in required_cols)
        except:
            return False
    
    def validate_format(self, file_path: str, format_info: FormatInfo) -> Tuple[bool, List[str]]:
        """Validate file against detected format"""
        errors = []
        
        try:
            if format_info.format_type.startswith('excel'):
                return self._validate_excel_format(file_path, format_info)
            elif format_info.format_type.startswith('csv'):
                return self._validate_csv_format(file_path, format_info)
            else:
                errors.append(f"Unsupported format: {format_info.format_type}")
                return False, errors
                
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return False, errors
    
    def _validate_excel_format(self, file_path: str, format_info: FormatInfo) -> Tuple[bool, List[str]]:
        """Validate Excel format"""
        errors = []
        
        try:
            xls = pd.ExcelFile(file_path)
            
            # Check required sheets
            if format_info.format_type == 'excel_standard':
                required_sheets = ['Account Info', 'KPI Data', 'Summary']
                missing_sheets = [sheet for sheet in required_sheets if sheet not in xls.sheet_names]
                if missing_sheets:
                    errors.append(f"Missing required sheets: {missing_sheets}")
            
            # Check required columns in data sheet
            data_sheet = 'KPI Data' if format_info.format_type == 'excel_standard' else xls.sheet_names[0]
            df = pd.read_excel(xls, data_sheet, nrows=5)
            
            missing_columns = [col for col in format_info.required_fields if col not in df.columns]
            if missing_columns:
                errors.append(f"Missing required columns: {missing_columns}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Excel validation error: {str(e)}")
            return False, errors
    
    def _validate_csv_format(self, file_path: str, format_info: FormatInfo) -> Tuple[bool, List[str]]:
        """Validate CSV format"""
        errors = []
        
        try:
            df = pd.read_csv(file_path, nrows=5)
            
            missing_columns = [col for col in format_info.required_fields if col not in df.columns]
            if missing_columns:
                errors.append(f"Missing required columns: {missing_columns}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"CSV validation error: {str(e)}")
            return False, errors

class FormatAdapterFactory:
    """Factory for creating format adapters"""
    
    @staticmethod
    def create_adapter(format_type: str):
        """Create appropriate adapter for format type"""
        adapters = {
            'excel_standard': StandardFormatAdapter,
            'excel_simple': SimpleFormatAdapter,
            'excel_custom': CustomFormatAdapter,
            'csv_standard': StandardCSVAdapter,
            'csv_basic': BasicCSVAdapter,
            'csv_minimal': MinimalCSVAdapter
        }
        
        adapter_class = adapters.get(format_type, UnknownAdapter)
        return adapter_class()

class BaseFormatAdapter:
    """Base class for format adapters"""
    
    def process(self, file_path: str, customer_id: int, account_name: str) -> List[Dict]:
        """Process file and return standardized KPI data"""
        raise NotImplementedError
    
    def map_category_to_component(self, category: str) -> str:
        """Map category to health score component"""
        mapping = {
            'Customer Satisfaction': 'Customer Sentiment',
            'Product Usage': 'Product Usage',
            'Revenue': 'Business Outcomes',
            'Support': 'Support',
            'Relationship': 'Relationship Strength',
            'General': 'Customer Sentiment'
        }
        return mapping.get(category, 'Customer Sentiment')

class StandardFormatAdapter(BaseFormatAdapter):
    """Adapter for standard KPI Dashboard format"""
    
    def process(self, file_path: str, customer_id: int, account_name: str) -> List[Dict]:
        """Process standard format file"""
        # This is the current implementation from upload_api.py
        # Return standardized KPI data
        pass

class SimpleFormatAdapter(BaseFormatAdapter):
    """Adapter for simple KPI list format"""
    
    def process(self, file_path: str, customer_id: int, account_name: str) -> List[Dict]:
        """Process simple format file"""
        df = pd.read_excel(file_path)
        
        kpi_data = []
        for _, row in df.iterrows():
            kpi_data.append({
                'category': row.get('Category', 'General'),
                'kpi_parameter': row['KPI Name'],
                'data': row['Value'],
                'health_score_component': self.map_category_to_component(row.get('Category', 'General')),
                'weight': str(row.get('Weight', 10)),
                'impact_level': row.get('Impact Level', 'Medium'),
                'source_review': row.get('Description', ''),
                'measurement_frequency': row.get('Frequency', 'Monthly')
            })
        
        return kpi_data

class CustomFormatAdapter(BaseFormatAdapter):
    """Adapter for custom Excel format"""
    
    def process(self, file_path: str, customer_id: int, account_name: str) -> List[Dict]:
        """Process custom format file"""
        df = pd.read_excel(file_path)
        
        kpi_data = []
        for _, row in df.iterrows():
            kpi_data.append({
                'category': row.get('Category', 'General'),
                'kpi_parameter': row['KPI'],
                'data': row['Value'],
                'health_score_component': self.map_category_to_component(row.get('Category', 'General')),
                'weight': str(row.get('Weight', 10)),
                'impact_level': row.get('Impact', 'Medium'),
                'source_review': row.get('Description', ''),
                'measurement_frequency': row.get('Frequency', 'Monthly')
            })
        
        return kpi_data

class StandardCSVAdapter(BaseFormatAdapter):
    """Adapter for standard CSV format"""
    
    def process(self, file_path: str, customer_id: int, account_name: str) -> List[Dict]:
        """Process standard CSV format file"""
        df = pd.read_csv(file_path)
        
        kpi_data = []
        for _, row in df.iterrows():
            kpi_data.append({
                'category': row.get('category', 'General'),
                'kpi_parameter': row['kpi_parameter'],
                'data': row['data'],
                'health_score_component': self.map_category_to_component(row.get('category', 'General')),
                'weight': str(row.get('weight', 10)),
                'impact_level': row.get('impact_level', 'Medium'),
                'source_review': row.get('source_review', ''),
                'measurement_frequency': row.get('measurement_frequency', 'Monthly')
            })
        
        return kpi_data

class BasicCSVAdapter(BaseFormatAdapter):
    """Adapter for basic CSV format"""
    
    def process(self, file_path: str, customer_id: int, account_name: str) -> List[Dict]:
        """Process basic CSV format file"""
        df = pd.read_csv(file_path)
        
        kpi_data = []
        for _, row in df.iterrows():
            kpi_data.append({
                'category': row.get('category', 'General'),
                'kpi_parameter': row['kpi_name'],
                'data': row['value'],
                'health_score_component': self.map_category_to_component(row.get('category', 'General')),
                'weight': str(row.get('weight', 10)),
                'impact_level': row.get('impact_level', 'Medium'),
                'source_review': row.get('description', ''),
                'measurement_frequency': row.get('frequency', 'Monthly')
            })
        
        return kpi_data

class MinimalCSVAdapter(BaseFormatAdapter):
    """Adapter for minimal CSV format"""
    
    def process(self, file_path: str, customer_id: int, account_name: str) -> List[Dict]:
        """Process minimal CSV format file"""
        df = pd.read_csv(file_path)
        
        kpi_data = []
        for _, row in df.iterrows():
            kpi_data.append({
                'category': row.get('category', 'General'),
                'kpi_parameter': row['kpi'],
                'data': row['value'],
                'health_score_component': self.map_category_to_component(row.get('category', 'General')),
                'weight': str(row.get('weight', 10)),
                'impact_level': row.get('impact', 'Medium'),
                'source_review': row.get('description', ''),
                'measurement_frequency': row.get('frequency', 'Monthly')
            })
        
        return kpi_data

class UnknownAdapter(BaseFormatAdapter):
    """Adapter for unknown formats"""
    
    def process(self, file_path: str, customer_id: int, account_name: str) -> List[Dict]:
        """Process unknown format file"""
        raise ValueError(f"Unknown file format: {file_path}")

class ErrorAdapter(BaseFormatAdapter):
    """Adapter for error cases"""
    
    def process(self, file_path: str, customer_id: int, account_name: str) -> List[Dict]:
        """Process error case"""
        raise ValueError(f"Error processing file: {file_path}")

# Example usage
if __name__ == "__main__":
    detector = FormatDetector()
    
    # Test format detection
    test_files = [
        "sample_standard.xlsx",
        "sample_simple.xlsx", 
        "sample_basic.csv"
    ]
    
    for file_path in test_files:
        print(f"\n🔍 Detecting format for: {file_path}")
        format_info = detector.detect_format(file_path)
        print(f"Format: {format_info.format_type}")
        print(f"Confidence: {format_info.confidence}")
        print(f"Required fields: {format_info.required_fields}")
        print(f"Adapter: {format_info.adapter_class}")
