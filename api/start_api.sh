#!/bin/bash
# API Server Startup Script for Rwanda Employment Project

set -e  # Exit on error

echo "=========================================="
echo "Rwanda Employment API - Server Startup"
echo "=========================================="

# Get the directory where this script is located
API_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$API_DIR"

# ============================================================================
# Step 1: Check Python version
# ============================================================================
echo ""
echo "[1/6] Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

# ============================================================================
# Step 2: Set up virtual environment
# ============================================================================
echo ""
echo "[2/6] Setting up virtual environment..."
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo "✓ Virtual environment activated"

# ============================================================================
# Step 3: Install/Update dependencies
# ============================================================================
echo ""
echo "[3/6] Checking dependencies..."
if [ -f "requirements.txt" ]; then
    echo "Installing/updating Python packages..."
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    echo "✓ Dependencies installed"
else
    echo "⚠️  Warning: requirements.txt not found"
fi

# ============================================================================
# Step 4: Set up environment variables
# ============================================================================
echo ""
echo "[4/6] Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and update the following:"
    echo "   - JWT_SECRET (generate a secure random string)"
    echo "   - MISTRAL_API_KEY (if using chatbot features)"
    echo "   - DB_PASSWORD (if your PostgreSQL has a password)"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to exit and edit .env..."
else
    echo "✓ .env file exists"
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# ============================================================================
# Step 5: Verify database connection
# ============================================================================
echo ""
echo "[5/6] Verifying database connection..."

# Check if PostgreSQL is running
if command -v pg_isready &> /dev/null; then
    if pg_isready -h ${DB_HOST:-localhost} -p ${DB_PORT:-5432} &> /dev/null; then
        echo "✓ PostgreSQL is running"
    else
        echo "⚠️  Warning: Cannot connect to PostgreSQL"
        echo "   Make sure PostgreSQL is running:"
        echo "   brew services start postgresql@15"
        echo ""
        read -p "Press Enter to continue anyway or Ctrl+C to exit..."
    fi
else
    echo "⚠️  pg_isready not found, skipping database check"
fi

# Check if database exists
if command -v psql &> /dev/null; then
    DB_EXISTS=$(psql -h ${DB_HOST:-localhost} -U ${DB_USER:-postgres} -lqt 2>/dev/null | cut -d \| -f 1 | grep -w ${DB_NAME:-rwanda_emp} | wc -l)
    if [ "$DB_EXISTS" -eq 1 ]; then
        echo "✓ Database '${DB_NAME:-rwanda_emp}' exists"
    else
        echo "⚠️  Warning: Database '${DB_NAME:-rwanda_emp}' not found"
        echo "   Please run the database initialization script:"
        echo "   cd ../data && python load_data_to_db.py"
        echo ""
        read -p "Press Enter to continue anyway or Ctrl+C to exit..."
    fi
fi

# ============================================================================
# Step 6: Start the API server
# ============================================================================
echo ""
echo "[6/6] Starting API server..."
echo ""
echo "=========================================="
echo "API Server Information"
echo "=========================================="
echo "Environment: Development"
echo "Host: http://localhost:8001"
echo "API Docs: http://localhost:8001/docs"
echo "ReDoc: http://localhost:8001/redoc"
echo ""
echo "Database: ${DB_NAME:-rwanda_emp}"
echo "Frontend: ${FRONTEND_URL:-http://localhost:5173}"
echo ""
echo "=========================================="
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

# Start uvicorn with auto-reload
python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --reload \
    --log-level info

# Note: Script will not reach here until server is stopped
echo ""
echo "API server stopped."
