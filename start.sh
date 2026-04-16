#!/bin/bash
# Solar System Small Bodies Explorer - Startup Script

echo "=========================================="
echo "Solar System Small Bodies Explorer"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

echo ""
echo "Starting server on http://localhost:5050"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the application
python3 app.py

