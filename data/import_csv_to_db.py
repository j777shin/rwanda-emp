"""
Import user_data.csv into the beneficiaries table.
This script reads the CSV file and inserts data into the PostgreSQL database.
"""
import psycopg2
import csv
import sys
import os
from pathlib import Path
from typing import Optional


def normalize_education_level(edu_level: str) -> str:
    """Convert CSV education level format to database format."""
    if not edu_level or edu_level.strip() == '':
        return None
    
    # Map CSV format to database format
    mapping = {
        'below primary': 'below_primary',
        'primary': 'primary',
        'secondary': 'secondary',
        'secondary-professional': 'secondary_professional',
        'professional': 'professional',
        'tertiary-and-above': 'tertiary_and_above'
    }
    
    edu_level = edu_level.strip().lower()
    return mapping.get(edu_level, edu_level.replace('-', '_'))


def convert_to_bool(value) -> bool:
    """Convert various formats to boolean."""
    if value is None or value == '':
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        value = value.strip().lower()
        if value in ('true', '1', 'yes', 'y'):
            return True
        if value in ('false', '0', 'no', 'n', ''):
            return False
    return False


def convert_to_int(value, default=0) -> int:
    """Convert value to integer."""
    if value is None or value == '' or value.strip() == '':
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def convert_to_float(value) -> Optional[float]:
    """Convert value to float."""
    if value is None or value == '' or value.strip() == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def import_csv_to_db(csv_file: str, host='localhost', port=5432, user='postgres', 
                    password='postgres', database='rwanda_emp', batch_size=1000):
    """
    Import CSV file into beneficiaries table.
    
    Args:
        csv_file: Path to CSV file
        host: PostgreSQL host
        port: PostgreSQL port
        user: PostgreSQL user
        password: PostgreSQL password
        database: Database name
        batch_size: Number of records to insert per batch
    """
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"Error: CSV file '{csv_file}' not found.")
        sys.exit(1)
    
    try:
        print(f"Connecting to database '{database}'...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()
        
        # Check if beneficiaries table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'beneficiaries'
            )
        """)
        if not cursor.fetchone()[0]:
            print("Error: 'beneficiaries' table does not exist. Please run create_db_from_schema.py first.")
            conn.close()
            sys.exit(1)
        
        print(f"Reading CSV file: {csv_path}")
        inserted_count = 0
        error_count = 0
        batch = []
        
        insert_sql = """
        INSERT INTO beneficiaries (
            name, age, gender, contact,
            marriage_status, disability, education_level,
            occupation, informal_working,
            num_cows, num_goats, num_chickens, num_sheep, num_pigs, num_rabbits,
            land_ownership, land_size,
            num_radio, num_phone, num_tv,
            fuel, water_source,
            floor, roof, walls, toilet
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            print(f"\nStarting import...\n")
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Normalize education level
                    education_level = normalize_education_level(row.get('education_level', ''))
                    
                    # Prepare values
                    values = (
                        row.get('name', '').strip() or None,
                        convert_to_int(row.get('age')),
                        row.get('gender', '').strip() or None,
                        row.get('contact', '').strip() or None,
                        convert_to_bool(row.get('marriage_status')),
                        convert_to_bool(row.get('disability')),
                        education_level,
                        convert_to_bool(row.get('occupation')),
                        convert_to_bool(row.get('informal_working')),
                        convert_to_int(row.get('num_cows'), 0),
                        convert_to_int(row.get('num_goats'), 0),
                        convert_to_int(row.get('num_chickens'), 0),
                        convert_to_int(row.get('num_sheep'), 0),
                        convert_to_int(row.get('num_pigs'), 0),
                        convert_to_int(row.get('num_rabbits'), 0),
                        convert_to_bool(row.get('land_ownership')),
                        convert_to_float(row.get('land_size')),
                        convert_to_int(row.get('num_radio'), 0),
                        convert_to_int(row.get('num_phone'), 0),
                        convert_to_int(row.get('num_tv'), 0),
                        row.get('fuel', '').strip() or None,
                        row.get('water_source', '').strip() or None,
                        convert_to_bool(row.get('floor')),
                        convert_to_bool(row.get('roof')),
                        convert_to_bool(row.get('walls')),
                        convert_to_bool(row.get('toilet')),
                    )
                    
                    batch.append(values)
                    
                    # Insert in batches
                    if len(batch) >= batch_size:
                        cursor.executemany(insert_sql, batch)
                        conn.commit()
                        inserted_count += len(batch)
                        print(f"Inserted {inserted_count:,} records...")
                        batch = []
                
                except Exception as e:
                    print(f"Error processing row {row_num}: {e}")
                    error_count += 1
                    continue
            
            # Insert remaining records
            if batch:
                cursor.executemany(insert_sql, batch)
                conn.commit()
                inserted_count += len(batch)
        
        # Get final count
        cursor.execute("SELECT COUNT(*) FROM beneficiaries")
        total_count = cursor.fetchone()[0]
        
        print(f"\n{'='*60}")
        print(f"Import completed!")
        print(f"{'='*60}")
        print(f"Records inserted: {inserted_count:,}")
        print(f"Errors encountered: {error_count:,}")
        print(f"Total records in database: {total_count:,}")
        print(f"{'='*60}")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Import CSV data into database')
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--port', type=int, default=5432, help='PostgreSQL port')
    parser.add_argument('--user', default='postgres', help='PostgreSQL user')
    parser.add_argument('--password', default='postgres', help='PostgreSQL password')
    parser.add_argument('--database', default='rwanda_emp', help='Database name')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for inserts')
    
    args = parser.parse_args()
    
    import_csv_to_db(
        csv_file=args.csv_file,
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        batch_size=args.batch_size
    )

