#!/bin/bash
# Solar System Small Bodies Explorer - Streamlit Version
# Standalone startup script
# Version: 2.0.0-streamlit (November 2025)

echo "════════════════════════════════════════════════════════════════════════════"
echo "  🌌 SOLAR SYSTEM SMALL BODIES EXPLORER - STREAMLIT VERSION 🌌"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "✓ Virtual environment activated"
echo ""

# Check if Flask backend is running
if ! lsof -ti:5050 > /dev/null 2>&1; then
    echo "🔧 Starting Flask backend (API server on port 5050)..."
    nohup python app.py > flask_backend.log 2>&1 &
    sleep 3
    if lsof -ti:5050 > /dev/null 2>&1; then
        echo "✓ Flask backend started successfully"
    else
        echo "⚠️  Flask backend may have issues, check flask_backend.log"
    fi
else
    echo "✓ Flask backend already running on port 5050"
fi

echo ""

# Check if Streamlit is already running
if lsof -ti:8501 > /dev/null 2>&1; then
    echo "⚠️  Streamlit already running on port 8501"
    echo "   Stop it first with: pkill -f 'streamlit run streamlit_app.py'"
    echo ""
    read -p "Press Enter to continue anyway or Ctrl+C to exit..."
fi

echo "🚀 Starting Streamlit Explorer..."
echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "  📡 Application will open in your browser automatically"
echo "  🌐 URL: http://localhost:8501"
echo ""
echo "  Features:"
echo "    • 3D Orbital Visualizations (Plotly)"
echo "    • Interactive Charts & Filtering"
echo "    • Merged Data: JPL + SsODNet + Wikipedia"
echo "    • Real-time Object Counts"
echo "    • CSV/JSON Export"
echo ""
echo "  Press Ctrl+C to stop the application"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Start Streamlit (this will open browser automatically)
streamlit run streamlit_app.py --server.port 8501

