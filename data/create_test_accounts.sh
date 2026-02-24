#!/bin/bash
# Script to create test accounts for Rwanda Employment Portal

set -e

echo "=========================================="
echo "Creating Test Accounts"
echo "=========================================="
echo ""

# Load .env if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Database configuration
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-postgres}
DB_NAME=${DB_NAME:-rwanda_emp}

echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo ""

# Check if PostgreSQL is accessible
if ! command -v psql &> /dev/null; then
    echo "❌ Error: psql command not found"
    echo "Please install PostgreSQL client"
    exit 1
fi

# Run the SQL script
echo "Creating test accounts..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f create_test_accounts.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Test Accounts Created Successfully!"
    echo "=========================================="
    echo ""
    echo "📋 Login Credentials:"
    echo ""
    echo "👤 Admin Portal:"
    echo "   Email:    admin@rwanda.gov.rw"
    echo "   Password: Admin@2026"
    echo ""
    echo "👤 Beneficiary Portal (Full Access - All Tabs):"
    echo "   Email:    test@gmail.com"
    echo "   Password: User@2026"
    echo ""
    echo "🌐 Access the portal at: http://localhost:5173/"
    echo "=========================================="
else
    echo ""
    echo "❌ Failed to create test accounts"
    echo "Please check your database connection and try again"
    exit 1
fi
