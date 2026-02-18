#!/bin/bash
# Setup script for Rwanda Employment Project database

set -e  # Exit on error

echo "=========================================="
echo "Rwanda Employment Project - Database Setup"
echo "=========================================="

# Check Python version
echo ""
echo "[1/4] Checking Python version..."
python3 --version || { echo "Error: Python 3 is not installed"; exit 1; }

# Install Python dependencies
echo ""
echo "[2/4] Installing Python dependencies..."
pip3 install -r requirements.txt

# Create .env file if it doesn't exist
echo ""
echo "[3/4] Setting up environment configuration..."
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and update your database credentials!"
    echo "   File location: $(pwd)/.env"
else
    echo "✓ .env file already exists"
fi

# Check if PostgreSQL is running
echo ""
echo "[4/4] Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "✓ PostgreSQL client found"

    # Try to connect (this will fail if not running, but that's ok)
    if psql -h localhost -U postgres -c '\q' 2>/dev/null; then
        echo "✓ PostgreSQL server is running"
    else
        echo "⚠️  Could not connect to PostgreSQL server"
        echo "   Make sure PostgreSQL is running and credentials are correct"
    fi
else
    echo "⚠️  PostgreSQL client not found in PATH"
    echo "   Please ensure PostgreSQL is installed"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your database credentials"
echo "2. Run: python3 load_data_to_db.py"
echo "3. Verify: python3 verify_data.py"
echo ""
