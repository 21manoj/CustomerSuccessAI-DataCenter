#!/bin/bash

# Backup original
cp backend/utils/cost_tracker.py backend/utils/cost_tracker.py.backup

# Fix the INSERT statement
python3 << 'PYTHON'
with open('backend/utils/cost_tracker.py', 'r') as f:
    content = f.read()

# Remove tokens_total from INSERT
old_insert = """                    INSERT INTO api_usage_log (
                        timestamp, customer_id, account_id, call_type,
                        provider, model, tokens_input, tokens_output, tokens_total,
                        cost, success, error_message, execution_time_ms
                    ) VALUES (
                        NOW(), :customer_id, :account_id, :call_type,
                        :provider, :model, :tokens_input, :tokens_output, :tokens_total,
                        :cost, :success, :error_message, :execution_time_ms
                    )"""

new_insert = """                    INSERT INTO api_usage_log (
                        timestamp, customer_id, account_id, call_type,
                        provider, model, tokens_input, tokens_output,
                        cost, success, error_message, execution_time_ms
                    ) VALUES (
                        NOW(), :customer_id, :account_id, :call_type,
                        :provider, :model, :tokens_input, :tokens_output,
                        :cost, :success, :error_message, :execution_time_ms
                    )"""

content = content.replace(old_insert, new_insert)

# Remove tokens_total from parameters
old_params = """                    'tokens_input': tokens_input,
                    'tokens_output': tokens_output,
                    'tokens_total': tokens_input + tokens_output,
                    'cost': cost,"""

new_params = """                    'tokens_input': tokens_input,
                    'tokens_output': tokens_output,
                    'cost': cost,"""

content = content.replace(old_params, new_params)

with open('backend/utils/cost_tracker.py', 'w') as f:
    f.write(content)

print("✅ Fixed cost_tracker.py")
PYTHON

