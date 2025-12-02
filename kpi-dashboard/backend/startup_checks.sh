#!/bin/bash
# Startup checks for backend - run before starting the app
# This ensures all required migrations and validations are done

set -e

echo "🔍 Running startup checks..."

# Check if migration is needed
echo "📋 Checking database schema..."
python3 migrate_add_openai_key.py

# Validate OpenAI key support
echo ""
echo "📋 Validating OpenAI API key support..."
python3 validate_openai_key_support.py

echo ""
echo "✅ Startup checks complete!"

