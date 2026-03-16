# Prompt 04: Metadata Schema

## Input Variables
- `{VERTICAL_ID}`, `{VERTICAL_NAME}`, `{INDUSTRY_DESCRIPTION}`
- `{TYPICAL_ACCOUNT_PROFILE}`: What an account looks like in this vertical

## Prompt

```
You are a data architect designing the account metadata schema for
{VERTICAL_NAME} ({INDUSTRY_DESCRIPTION}). Generate a metadata validation
schema that captures industry-specific account attributes.

CONTEXT:
- Each account in this vertical has specific attributes beyond the generic
  (name, ARR, region, industry) that are critical for health scoring and
  segmentation.
- The schema validates the `profile_metadata` JSON field on the Account model.

GENERATE:

1. REQUIRED_FIELDS (5-8 fields):
   Fields that every account MUST have for the vertical to function.
   For each: field_name, type, description, validation_rule, example_value

2. OPTIONAL_FIELDS (8-12 fields):
   Fields that enrich segmentation and analysis but aren't blocking.
   For each: field_name, type, description, default_value, example_value

3. ENUMERATIONS:
   For any field with a fixed set of valid values, define the enum.
   Examples for DC2S: deployment_type (on_prem/colo/hybrid/cloud),
   gpu_model (A100/H100/B200), use_case (training/inference/fine_tuning)

4. VALIDATION_RULES:
   - Required field presence check
   - Enum validation
   - Numeric range validation (e.g., server_count > 0)
   - Date format validation (ISO 8601)

5. SEGMENTATION_DIMENSIONS:
   Which metadata fields are most useful for portfolio segmentation.
   Rank top 5 with justification.

OUTPUT FORMAT:
Python module with:
- REQUIRED_METADATA_FIELDS dict
- OPTIONAL_METADATA_FIELDS dict
- ENUMERATIONS dict
- validate_metadata(data: dict) -> Tuple[bool, List[str]] function
- SEGMENTATION_DIMENSIONS list

Match the structure of verticals/dc2_s/metadata_schema.py.

INDUSTRY-SPECIFIC GUIDANCE:
- For SaaS: include license_type, seat_count, integration_count, sso_enabled
- For Data Center: include gpu_count, rack_count, power_capacity_kw, cooling_type
- For FinTech: include aum, regulatory_tier, compliance_framework, transaction_volume
- For Healthcare: include bed_count, ehr_system, hipaa_tier, patient_volume
- For Manufacturing: include plant_count, iot_device_count, shift_model, erp_system
```
