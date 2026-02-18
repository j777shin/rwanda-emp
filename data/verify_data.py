#!/usr/bin/env python3
"""
Data Verification and Query Tool
Run various checks and queries on the loaded data
"""

import psycopg
from psycopg.rows import dict_row
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration (from environment variables or defaults)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'dbname': os.getenv('DB_NAME', 'rwanda_emp')
}

def connect_db():
    """Create database connection"""
    try:
        return psycopg.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

def basic_statistics():
    """Display basic statistics about the data"""
    conn = connect_db()
    cursor = conn.cursor()

    print_section("BASIC STATISTICS")

    # Total counts
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM beneficiaries")
    beneficiaries_count = cursor.fetchone()[0]

    print(f"\nTotal users: {users_count:,}")
    print(f"Total beneficiaries: {beneficiaries_count:,}")

    # Gender distribution
    cursor.execute("""
        SELECT
            gender,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
        FROM beneficiaries
        GROUP BY gender
        ORDER BY gender
    """)

    print("\nGender Distribution:")
    for row in cursor.fetchall():
        print(f"  {row[0].capitalize()}: {row[1]:,} ({row[2]}%)")

    # District distribution
    cursor.execute("""
        SELECT
            district,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
        FROM beneficiaries
        GROUP BY district
        ORDER BY count DESC
    """)

    print("\nDistrict Distribution:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,} ({row[2]}%)")

    # Age distribution
    cursor.execute("""
        SELECT
            CASE
                WHEN age BETWEEN 16 AND 19 THEN '16-19'
                WHEN age BETWEEN 20 AND 24 THEN '20-24'
                WHEN age BETWEEN 25 AND 29 THEN '25-29'
                WHEN age BETWEEN 30 AND 34 THEN '30-34'
            END as age_group,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
        FROM beneficiaries
        GROUP BY age_group
        ORDER BY age_group
    """)

    print("\nAge Group Distribution:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,} ({row[2]}%)")

    cursor.close()
    conn.close()

def employment_statistics():
    """Display employment-related statistics"""
    conn = connect_db()
    cursor = conn.cursor()

    print_section("EMPLOYMENT STATISTICS")

    # Overall employment
    cursor.execute("""
        SELECT
            occupation,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
        FROM beneficiaries
        GROUP BY occupation
        ORDER BY occupation DESC
    """)

    print("\nEmployment Status:")
    for row in cursor.fetchall():
        status = "Employed" if row[0] else "Unemployed"
        print(f"  {status}: {row[1]:,} ({row[2]}%)")

    # Employment by gender
    cursor.execute("""
        SELECT
            gender,
            COUNT(*) FILTER (WHERE occupation = TRUE) as employed,
            COUNT(*) as total,
            ROUND(COUNT(*) FILTER (WHERE occupation = TRUE) * 100.0 / COUNT(*), 2) as percentage
        FROM beneficiaries
        GROUP BY gender
        ORDER BY gender
    """)

    print("\nEmployment by Gender:")
    for row in cursor.fetchall():
        print(f"  {row[0].capitalize()}: {row[1]:,} / {row[2]:,} ({row[3]}%)")

    # Informal workers
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE informal_working = TRUE) as informal,
            COUNT(*) FILTER (WHERE occupation = TRUE) as total_employed,
            ROUND(COUNT(*) FILTER (WHERE informal_working = TRUE) * 100.0 /
                  NULLIF(COUNT(*) FILTER (WHERE occupation = TRUE), 0), 2) as percentage
        FROM beneficiaries
    """)

    row = cursor.fetchone()
    print(f"\nInformal Workers (among employed): {row[0]:,} / {row[1]:,} ({row[2]}%)")

    # Education levels
    cursor.execute("""
        SELECT
            education_level,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
        FROM beneficiaries
        GROUP BY education_level
        ORDER BY count DESC
    """)

    print("\nEducation Levels:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,} ({row[2]}%)")

    cursor.close()
    conn.close()

def household_statistics():
    """Display household-related statistics"""
    conn = connect_db()
    cursor = conn.cursor()

    print_section("HOUSEHOLD STATISTICS")

    # Average household metrics
    cursor.execute("""
        SELECT
            ROUND(AVG(age), 1) as avg_age,
            ROUND(AVG(household_size), 1) as avg_household_size,
            ROUND(AVG(children_under_18), 1) as avg_children,
            ROUND(AVG(CASE WHEN land_ownership THEN land_size ELSE 0 END), 2) as avg_land_size
        FROM beneficiaries
    """)

    row = cursor.fetchone()
    print(f"\nAverage Metrics:")
    print(f"  Age: {row[0]} years")
    print(f"  Household size: {row[1]} persons")
    print(f"  Children under 18: {row[2]}")
    print(f"  Land size (when owned): {row[3]} hectares")

    # Housing conditions
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE floor_earth_sand = TRUE) as earth_floor,
            COUNT(*) FILTER (WHERE floor_tiles = TRUE) as tile_floor,
            COUNT(*) FILTER (WHERE lighting = TRUE) as has_electricity,
            COUNT(*) FILTER (WHERE cooking_firewood = TRUE) as uses_firewood,
            COUNT(*) FILTER (WHERE cooking_gas = TRUE) as uses_gas,
            COUNT(*) as total
        FROM beneficiaries
    """)

    row = cursor.fetchone()
    total = row[5]
    print(f"\nHousing Conditions:")
    print(f"  Earth/sand floor: {row[0]:,} ({row[0]/total*100:.1f}%)")
    print(f"  Tile floor: {row[1]:,} ({row[1]/total*100:.1f}%)")
    print(f"  Has electricity: {row[2]:,} ({row[2]/total*100:.1f}%)")
    print(f"  Cooks with firewood: {row[3]:,} ({row[3]/total*100:.1f}%)")
    print(f"  Cooks with gas: {row[4]:,} ({row[4]/total*100:.1f}%)")

    # Marriage status
    cursor.execute("""
        SELECT
            marriage_status,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
        FROM beneficiaries
        GROUP BY marriage_status
        ORDER BY marriage_status DESC
    """)

    print("\nMarriage Status:")
    for row in cursor.fetchall():
        status = "Married/Ever Married" if row[0] else "Never Married"
        print(f"  {status}: {row[1]:,} ({row[2]}%)")

    # Disability
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE disability = TRUE) as with_disability,
            COUNT(*) as total,
            ROUND(COUNT(*) FILTER (WHERE disability = TRUE) * 100.0 / COUNT(*), 2) as percentage
        FROM beneficiaries
    """)

    row = cursor.fetchone()
    print(f"\nWith Disability: {row[0]:,} ({row[2]}%)")

    cursor.close()
    conn.close()

def assets_and_livestock():
    """Display assets and livestock statistics"""
    conn = connect_db()
    cursor = conn.cursor()

    print_section("ASSETS & LIVESTOCK")

    # Assets
    cursor.execute("""
        SELECT
            SUM(num_phone) as phones,
            SUM(num_radio) as radios,
            SUM(num_tv) as tvs,
            COUNT(*) FILTER (WHERE num_phone > 0) as households_with_phone,
            COUNT(*) FILTER (WHERE num_radio > 0) as households_with_radio,
            COUNT(*) FILTER (WHERE num_tv > 0) as households_with_tv,
            COUNT(*) as total
        FROM beneficiaries
    """)

    row = cursor.fetchone()
    total = row[6]
    print(f"\nHousehold Assets:")
    print(f"  Mobile phones: {row[0]:,} total, {row[3]:,} households ({row[3]/total*100:.1f}%)")
    print(f"  Radios: {row[1]:,} total, {row[4]:,} households ({row[4]/total*100:.1f}%)")
    print(f"  TVs: {row[2]:,} total, {row[5]:,} households ({row[5]/total*100:.1f}%)")

    # Livestock
    cursor.execute("""
        SELECT
            SUM(num_cattle) as cattle,
            SUM(num_goats) as goats,
            SUM(num_sheep) as sheep,
            SUM(num_pigs) as pigs,
            COUNT(*) FILTER (WHERE num_cattle > 0) as households_with_cattle,
            COUNT(*) FILTER (WHERE num_goats > 0) as households_with_goats,
            COUNT(*) as total
        FROM beneficiaries
    """)

    row = cursor.fetchone()
    total = row[6]
    print(f"\nLivestock:")
    print(f"  Cattle: {row[0]:,} total, {row[4]:,} households ({row[4]/total*100:.1f}%)")
    print(f"  Goats: {row[1]:,} total, {row[5]:,} households ({row[5]/total*100:.1f}%)")
    print(f"  Sheep: {row[2]:,} total")
    print(f"  Pigs: {row[3]:,} total")

    # Land ownership
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE land_ownership = TRUE) as owns_land,
            COUNT(*) as total,
            ROUND(AVG(CASE WHEN land_ownership THEN land_size ELSE NULL END), 2) as avg_land_size
        FROM beneficiaries
    """)

    row = cursor.fetchone()
    print(f"\nLand Ownership:")
    print(f"  Owns land: {row[0]:,} ({row[0]/row[1]*100:.1f}%)")
    print(f"  Average land size (among owners): {row[2]} hectares")

    cursor.close()
    conn.close()

def low_income_indicators():
    """Identify low-income beneficiaries"""
    conn = connect_db()
    cursor = conn.cursor(row_factory=dict_row)

    print_section("LOW-INCOME INDICATORS")

    # Define low-income criteria
    cursor.execute("""
        SELECT
            COUNT(*) as total_low_income,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM beneficiaries), 2) as percentage
        FROM beneficiaries
        WHERE (
            floor_earth_sand = TRUE OR
            cooking_firewood = TRUE OR
            lighting = FALSE OR
            num_cattle = 0 OR
            (occupation = FALSE AND age > 24)
        )
    """)

    row = cursor.fetchone()
    print(f"\nBeneficiaries with low-income indicators:")
    print(f"  Total: {row['total_low_income']:,} ({row['percentage']}%)")
    print("\nCriteria: earth floor OR firewood cooking OR no electricity OR no cattle OR (unemployed and age > 24)")

    # Very low income (multiple indicators)
    cursor.execute("""
        SELECT COUNT(*) as very_low_income
        FROM beneficiaries
        WHERE (
            (floor_earth_sand = TRUE)::int +
            (cooking_firewood = TRUE)::int +
            (lighting = FALSE)::int +
            (num_cattle = 0)::int +
            (num_goats = 0)::int +
            (occupation = FALSE)::int
        ) >= 4
    """)

    row = cursor.fetchone()
    print(f"\nBeneficiaries with 4+ low-income indicators: {row['very_low_income']:,}")

    cursor.close()
    conn.close()

def sample_records():
    """Display sample beneficiary records"""
    conn = connect_db()
    cursor = conn.cursor(row_factory=dict_row)

    print_section("SAMPLE RECORDS")

    cursor.execute("""
        SELECT
            name,
            age,
            gender,
            district,
            education_level,
            occupation,
            household_size,
            CASE
                WHEN floor_earth_sand THEN 'Earth'
                WHEN floor_tiles THEN 'Tiles'
                ELSE 'Cement'
            END as floor_type,
            lighting,
            num_cattle,
            num_goats
        FROM beneficiaries
        ORDER BY RANDOM()
        LIMIT 5
    """)

    print("\nRandom sample of 5 beneficiaries:\n")
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"{i}. {row['name']}")
        print(f"   Age: {row['age']}, Gender: {row['gender']}, District: {row['district']}")
        print(f"   Education: {row['education_level']}, Employed: {row['occupation']}")
        print(f"   Household size: {row['household_size']}, Floor: {row['floor_type']}")
        print(f"   Electricity: {row['lighting']}, Cattle: {row['num_cattle']}, Goats: {row['num_goats']}")
        print()

    cursor.close()
    conn.close()

def main():
    """Run all verification checks"""
    print("\n" + "=" * 70)
    print("RWANDA EMPLOYMENT PROJECT - DATA VERIFICATION")
    print("=" * 70)

    try:
        basic_statistics()
        employment_statistics()
        household_statistics()
        assets_and_livestock()
        low_income_indicators()
        sample_records()

        print("\n" + "=" * 70)
        print("VERIFICATION COMPLETE")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n✗ Error during verification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
