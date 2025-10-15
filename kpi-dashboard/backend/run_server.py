#!/usr/bin/env python3
"""Simple server runner for testing"""
from app import app

if __name__ == '__main__':
    print("Starting Flask server on port 5059...")
    app.run(host='0.0.0.0', port=5059, debug=False)

