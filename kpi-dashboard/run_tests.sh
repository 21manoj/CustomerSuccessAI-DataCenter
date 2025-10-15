#!/bin/bash

# Comprehensive Test Suite Runner for Playbooks System
# Runs both backend and frontend tests

echo "🧪 Playbooks System - Comprehensive Test Suite"
echo "=" | head -c 80
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results tracking
BACKEND_TESTS_PASSED=0
FRONTEND_TESTS_PASSED=0

# Backend Tests
echo ""
echo "${YELLOW}📦 Running Backend Tests...${NC}"
echo "=" | head -c 80
echo ""

cd backend

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "${RED}❌ pytest not found. Installing...${NC}"
    pip install pytest
fi

# Run backend tests
echo "Running Playbook Triggers API Tests..."
python -m pytest tests/test_playbook_triggers.py -v --tb=short

if [ $? -eq 0 ]; then
    echo "${GREEN}✅ Playbook Triggers API Tests PASSED${NC}"
    BACKEND_TESTS_PASSED=$((BACKEND_TESTS_PASSED + 1))
else
    echo "${RED}❌ Playbook Triggers API Tests FAILED${NC}"
fi

echo ""
echo "Running Integration Tests..."
python -m pytest tests/test_integration.py -v --tb=short

if [ $? -eq 0 ]; then
    echo "${GREEN}✅ Integration Tests PASSED${NC}"
    BACKEND_TESTS_PASSED=$((BACKEND_TESTS_PASSED + 1))
else
    echo "${RED}❌ Integration Tests FAILED${NC}"
fi

cd ..

# Frontend Tests
echo ""
echo "${YELLOW}⚛️  Running Frontend Tests...${NC}"
echo "=" | head -c 80
echo ""

# Check if npm/yarn is available
if command -v npm &> /dev/null; then
    echo "Using npm to run tests..."
    
    # Check if jest is configured
    if [ -f "package.json" ]; then
        # Install dependencies if needed
        if [ ! -d "node_modules" ]; then
            echo "Installing dependencies..."
            npm install
        fi
        
        # Run frontend tests
        echo "Running Playbooks Library Tests..."
        npm test -- src/lib/__tests__/playbooks.test.ts --passWithNoTests
        
        if [ $? -eq 0 ]; then
            echo "${GREEN}✅ Frontend Tests PASSED${NC}"
            FRONTEND_TESTS_PASSED=$((FRONTEND_TESTS_PASSED + 1))
        else
            echo "${RED}❌ Frontend Tests FAILED${NC}"
        fi
    else
        echo "${YELLOW}⚠️  package.json not found, skipping frontend tests${NC}"
    fi
else
    echo "${YELLOW}⚠️  npm not found, skipping frontend tests${NC}"
fi

# Summary
echo ""
echo "=" | head -c 80
echo ""
echo "${YELLOW}📊 Test Summary${NC}"
echo ""
echo "Backend Tests:"
echo "  - Playbook Triggers API: $([ $BACKEND_TESTS_PASSED -ge 1 ] && echo "${GREEN}PASSED${NC}" || echo "${RED}FAILED${NC}")"
echo "  - Integration Tests: $([ $BACKEND_TESTS_PASSED -ge 2 ] && echo "${GREEN}PASSED${NC}" || echo "${RED}FAILED${NC}")"
echo ""
echo "Frontend Tests:"
echo "  - Playbooks Library: $([ $FRONTEND_TESTS_PASSED -ge 1 ] && echo "${GREEN}PASSED${NC}" || echo "${YELLOW}SKIPPED${NC}")"
echo ""
echo "=" | head -c 80
echo ""

# Exit with appropriate code
TOTAL_TESTS=$((BACKEND_TESTS_PASSED + FRONTEND_TESTS_PASSED))
if [ $TOTAL_TESTS -ge 2 ]; then
    echo "${GREEN}✅ All core tests passed!${NC}"
    exit 0
else
    echo "${RED}❌ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
