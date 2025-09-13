#!/bin/bash
# RAG Time Series Test Runner
# Run this script to verify RAG system functionality

echo "🧪 Running RAG Time Series Tests..."
echo "=================================="

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python first."
    exit 1
fi

# Check if requests module is available
python -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing required dependencies..."
    pip install requests
fi

# Run the tests
echo "🚀 Starting test execution..."
python test_rag_time_series.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed! RAG system is working correctly."
    echo "🎯 Your demo is ready to go!"
else
    echo ""
    echo "❌ Some tests failed. Please check the RAG system."
    echo "🔧 Check the logs and ensure the backend is running."
    exit 1
fi
