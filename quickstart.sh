#!/bin/bash
# ============================================
# StudyBuddy AI — Quick Start Script
# ============================================
# Run from the backend/ directory:
#   chmod +x quickstart.sh
#   ./quickstart.sh

echo "🎓 StudyBuddy AI — Backend Setup"
echo "================================="

# Step 1: Create virtual environment
echo ""
echo "📦 Step 1: Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
else
    echo "   ℹ️  Virtual environment already exists"
fi

# Step 2: Activate venv
echo ""
echo "🔌 Step 2: Activating virtual environment..."
source venv/bin/activate
echo "   ✅ Activated: $(which python)"

# Step 3: Install dependencies
echo ""
echo "📥 Step 3: Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt --quiet
echo "   ✅ Dependencies installed"

# Step 4: Create directories
echo ""
echo "📁 Step 4: Creating directories..."
mkdir -p api core models schemas db middleware uploads chroma_data

# Create __init__.py files
touch api/__init__.py core/__init__.py schemas/__init__.py db/__init__.py middleware/__init__.py
echo "   ✅ Directories and __init__.py files created"

# Step 5: Check .env
echo ""
echo "🔑 Step 5: Checking .env configuration..."
if [ ! -f ".env" ]; then
    echo "   ❌ .env file not found! Create it with your Gemini API key."
    echo "   Get a FREE key at: https://aistudio.google.com/apikey"
    exit 1
fi

if grep -q "your_gemini_api_key_here" .env; then
    echo "   ⚠️  Gemini API key not set in .env"
    echo "   Get a FREE key at: https://aistudio.google.com/apikey"
    echo "   Replace 'your_gemini_api_key_here' in .env with your key"
    exit 1
else
    echo "   ✅ .env file configured"
fi

# Step 6: Run tests
echo ""
echo "🧪 Step 6: Running backend tests..."
echo ""
python test_backend.py

# Step 7: Prompt to start server
echo ""
echo "================================="
echo "🚀 To start the API server, run:"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload"
echo ""
echo "   API will be at:  http://localhost:8000"
echo "   Docs will be at: http://localhost:8000/docs"
echo "================================="