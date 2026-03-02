#!/usr/bin/env python3
"""
Database Initialization and Data Loading Script
Initializes PostgreSQL database with schema and loads synthetic data
"""

import psycopg
from psycopg import sql
import csv
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

# Database connection parameters (from environment variables or defaults)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'dbname': os.getenv('DB_NAME', 'rwanda_emp')
}

# File paths - use directory of this script so it works for any user
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_FILE = os.path.join(BASE_DIR, "database_schema.sql")
USERS_CSV = os.path.join(BASE_DIR, "synthetic_users.csv")
BENEFICIARIES_CSV = os.path.join(BASE_DIR, "synthetic_beneficiaries.csv")

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def create_database(db_name: str, admin_config: dict) -> bool:
    """
    Create the database if it doesn't exist
    """
    try:
        # Connect to PostgreSQL server (to default 'postgres' database)
        conn = psycopg.connect(
            host=admin_config['host'],
            port=admin_config['port'],
            user=admin_config['user'],
            password=admin_config['password'],
            dbname='postgres',  # Connect to default database
            autocommit=True
        )
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()

        if exists:
            print(f"✓ Database '{db_name}' already exists")
            cursor.close()
            conn.close()
            return True

        # Create database
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier(db_name)
        ))
        print(f"✓ Created database '{db_name}'")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"✗ Error creating database: {e}")
        return False


def initialize_schema(config: dict, schema_file: str) -> bool:
    """
    Initialize database schema from SQL file
    """
    try:
        # Read schema file
        if not os.path.exists(schema_file):
            print(f"✗ Schema file not found: {schema_file}")
            return False

        with open(schema_file, 'r') as f:
            schema_sql = f.read()

        # Connect to database
        conn = psycopg.connect(**config)
        cursor = conn.cursor()

        # Execute schema
        print(f"Executing schema from {schema_file}...")
        cursor.execute(schema_sql)
        conn.commit()

        print("✓ Database schema initialized successfully")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"✗ Error initializing schema: {e}")
        return False


def table_exists(config: dict, table_name: str) -> bool:
    """
    Check if a table exists in the database
    """
    try:
        conn = psycopg.connect(**config)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            );
        """, (table_name,))

        exists = cursor.fetchone()[0]

        cursor.close()
        conn.close()
        return exists

    except Exception as e:
        print(f"✗ Error checking table existence: {e}")
        return False


def get_table_count(config: dict, table_name: str) -> int:
    """
    Get the number of rows in a table
    """
    try:
        conn = psycopg.connect(**config)
        cursor = conn.cursor()

        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()
        return count

    except Exception as e:
        print(f"✗ Error getting table count: {e}")
        return 0


def load_csv_to_table(config: dict, csv_file: str, table_name: str) -> bool:
    """
    Load CSV file into database table using COPY command (fast for large files)
    """
    try:
        if not os.path.exists(csv_file):
            print(f"✗ CSV file not found: {csv_file}")
            return False

        # Get file size for progress info
        file_size_mb = os.path.getsize(csv_file) / (1024 * 1024)
        print(f"\nLoading {csv_file}")
        print(f"  File size: {file_size_mb:.2f} MB")

        conn = psycopg.connect(**config)
        cursor = conn.cursor()

        # Use COPY command for efficient bulk loading
        with open(csv_file, 'r') as f:
            # Skip header
            next(f)
            cursor.copy_expert(
                sql.SQL("COPY {} FROM STDIN WITH CSV").format(
                    sql.Identifier(table_name)
                ),
                f
            )

        conn.commit()

        # Get count
        count = get_table_count(config, table_name)
        print(f"✓ Loaded {count:,} rows into '{table_name}' table")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"✗ Error loading CSV to table: {e}")
        return False


def load_csv_to_table_row_by_row(config: dict, csv_file: str, table_name: str) -> bool:
    """
    Alternative method: Load CSV file row by row (slower but more compatible)
    Use this if COPY method fails
    """
    try:
        if not os.path.exists(csv_file):
            print(f"✗ CSV file not found: {csv_file}")
            return False

        print(f"\nLoading {csv_file} (row-by-row method)...")

        conn = psycopg.connect(**config)
        cursor = conn.cursor()

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            if not rows:
                print("✗ CSV file is empty")
                return False

            # Get column names from CSV
            columns = rows[0].keys()

            # Prepare INSERT statement
            insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table_name),
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join(sql.Placeholder() * len(columns))
            )

            # Insert rows in batches
            batch_size = 1000
            total_rows = len(rows)

            for i in range(0, total_rows, batch_size):
                batch = rows[i:i + batch_size]

                for row in batch:
                    # Convert string 'None' to actual None
                    values = [None if v == 'None' or v == '' else v for v in row.values()]
                    cursor.execute(insert_sql, values)

                conn.commit()

                if (i + batch_size) % 10000 == 0 or (i + batch_size) >= total_rows:
                    print(f"  Loaded {min(i + batch_size, total_rows):,} / {total_rows:,} rows...")

        count = get_table_count(config, table_name)
        print(f"✓ Loaded {count:,} rows into '{table_name}' table")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"✗ Error loading CSV row by row: {e}")
        return False


def verify_data_integrity(config: dict) -> bool:
    """
    Verify that the data was loaded correctly
    """
    try:
        conn = psycopg.connect(**config)
        cursor = conn.cursor()

        print("\n" + "=" * 70)
        print("DATA INTEGRITY VERIFICATION")
        print("=" * 70)

        # Check users table
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        print(f"\nUsers table: {users_count:,} rows")

        # Check beneficiaries table
        cursor.execute("SELECT COUNT(*) FROM beneficiaries")
        beneficiaries_count = cursor.fetchone()[0]
        print(f"Beneficiaries table: {beneficiaries_count:,} rows")

        # Check foreign key integrity
        cursor.execute("""
            SELECT COUNT(*)
            FROM beneficiaries b
            LEFT JOIN users u ON b.user_id = u.id
            WHERE u.id IS NULL
        """)
        orphaned = cursor.fetchone()[0]

        if orphaned > 0:
            print(f"⚠ Warning: {orphaned} beneficiaries have no matching user!")
        else:
            print(f"✓ All beneficiaries have matching user records")

        # Sample data verification
        print("\nSample data check:")
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE gender = 'male') as male_count,
                COUNT(*) FILTER (WHERE gender = 'female') as female_count,
                AVG(age) as avg_age,
                AVG(household_size) as avg_household
            FROM beneficiaries
        """)

        stats = cursor.fetchone()
        print(f"  Total: {stats[0]:,}")
        print(f"  Male: {stats[1]:,} ({stats[1]/stats[0]*100:.1f}%)")
        print(f"  Female: {stats[2]:,} ({stats[2]/stats[0]*100:.1f}%)")
        print(f"  Average age: {stats[3]:.1f} years")
        print(f"  Average household size: {stats[4]:.1f} persons")

        # District distribution
        print("\nDistrict distribution:")
        cursor.execute("""
            SELECT district, COUNT(*) as count
            FROM beneficiaries
            GROUP BY district
            ORDER BY count DESC
        """)

        for row in cursor.fetchall():
            district, count = row
            print(f"  {district}: {count:,} ({count/beneficiaries_count*100:.1f}%)")

        cursor.close()
        conn.close()

        print("\n" + "=" * 70)
        return True

    except Exception as e:
        print(f"✗ Error verifying data: {e}")
        return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main execution function
    """
    print("=" * 70)
    print("RWANDA EMPLOYMENT PROJECT - DATABASE INITIALIZATION")
    print("=" * 70)

    # Step 1: Create database
    print("\n[Step 1/4] Creating database...")
    if not create_database(DB_CONFIG['dbname'], DB_CONFIG):
        print("\n✗ Failed to create database. Please check your PostgreSQL connection.")
        print("Make sure PostgreSQL is running and credentials are correct.")
        return

    # Step 2: Initialize schema
    print("\n[Step 2/4] Initializing database schema...")
    if not initialize_schema(DB_CONFIG, SCHEMA_FILE):
        print("\n✗ Failed to initialize schema.")
        return

    # Verify tables exist
    if not table_exists(DB_CONFIG, 'users'):
        print("✗ Users table was not created!")
        return

    if not table_exists(DB_CONFIG, 'beneficiaries'):
        print("✗ Beneficiaries table was not created!")
        return

    print("✓ Database tables created successfully")

    # Step 3: Load users data
    print("\n[Step 3/4] Loading users data...")

    # Try COPY method first (faster)
    success = load_csv_to_table(DB_CONFIG, USERS_CSV, 'users')

    # If COPY fails, try row-by-row method
    if not success:
        print("Trying alternative loading method...")
        success = load_csv_to_table_row_by_row(DB_CONFIG, USERS_CSV, 'users')

    if not success:
        print("✗ Failed to load users data")
        return

    # Step 4: Load beneficiaries data
    print("\n[Step 4/4] Loading beneficiaries data...")

    # Try COPY method first (faster)
    success = load_csv_to_table(DB_CONFIG, BENEFICIARIES_CSV, 'beneficiaries')

    # If COPY fails, try row-by-row method
    if not success:
        print("Trying alternative loading method...")
        success = load_csv_to_table_row_by_row(DB_CONFIG, BENEFICIARIES_CSV, 'beneficiaries')

    if not success:
        print("✗ Failed to load beneficiaries data")
        return

    # Step 5: Verify data
    verify_data_integrity(DB_CONFIG)

    # Final message
    print("\n" + "=" * 70)
    print("DATABASE INITIALIZATION COMPLETE!")
    print("=" * 70)
    print("\nYou can now connect to the database:")
    print(f"  Database: {DB_CONFIG['dbname']}")
    print(f"  Host: {DB_CONFIG['host']}")
    print(f"  Port: {DB_CONFIG['port']}")
    print("\nExample connection string:")
    print(f"  postgresql://{DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
