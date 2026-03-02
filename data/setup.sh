#!/bin/bash
# Setup script for Rwanda Employment Project database

set -e  # Exit on error

# Load .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-rwanda_emp}"

echo "=========================================="
echo "Rwanda Employment Project - Database Setup"
echo "=========================================="

# Check Python version
echo ""
echo "[1/6] Checking Python version..."
python3 --version || { echo "Error: Python 3 is not installed"; exit 1; }

# Install Python dependencies
echo ""
echo "[2/6] Installing Python dependencies..."
pip3 install -r requirements.txt

# Create .env file if it doesn't exist
echo ""
echo "[3/6] Setting up environment configuration..."
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
echo "[4/6] Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "✓ PostgreSQL client found"

    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c '\q' 2>/dev/null; then
        echo "✓ PostgreSQL server is running"
    else
        echo "⚠️  Could not connect to PostgreSQL server"
        echo "   Make sure PostgreSQL is running and credentials are correct"
    fi
else
    echo "⚠️  PostgreSQL client not found in PATH"
    echo "   Please ensure PostgreSQL is installed"
fi

# Drop and recreate database
echo ""
echo "[5/6] Dropping and recreating database '${DB_NAME}'..."
if command -v dropdb &> /dev/null; then
    dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --if-exists "$DB_NAME" && \
        echo "✓ Dropped existing database '${DB_NAME}'" || \
        echo "⚠️  Could not drop database (may not exist yet)"
else
    echo "⚠️  dropdb command not found, skipping drop step"
fi

# Load schema, data, survey tables, and test accounts (run from data dir so paths resolve)
DATA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo ""
echo "[6/6] Loading schema, data, and test accounts..."
cd "$DATA_DIR" && python3 load_data_to_db.py

echo "  Adding survey tables..."
cd "$DATA_DIR" && PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f add_survey_tables.sql

echo "  Creating test accounts..."
cd "$DATA_DIR" && PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f create_test_accounts.sql

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Test Account Credentials:"
echo ""
echo "  Admin Portal:"
echo "    Email:    admin@rwanda.gov.rw"
echo "    Password: Admin@2026"
echo ""
echo "  Beneficiary (Full Access - All Tabs):"
echo "    Email:    test@gmail.com"
echo "    Password: User@2026"
echo ""
