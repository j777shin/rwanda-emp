import sqlite3
import csv
import sys
import os
from typing import Optional
from database_schema import SURVEY_DATA_SCHEMA, EDUCATION_LEVELS, FUEL_TYPES, WATER_SOURCES, GENDER_VALUES


def convert_to_int(value: Optional[str], default: int = 0) -> Optional[int]:
    if value is None or value == '' or value.strip() == '':
        return default
    try:
        return int(float(value))  # Handle float strings like "1.0"
    except (ValueError, TypeError):
        return default


def convert_to_real(value: Optional[str]) -> Optional[float]:
    if value is None or value == '' or value.strip() == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def normalize_column_name(col_name: str) -> str:
    return col_name.strip().lower().replace(' ', '_').replace('-', '_')


def validate_education_level(value: Optional[str]) -> Optional[str]:
    if value is None or value == '' or value.strip() == '':
        return None
    
    value = value.strip()
    
    # Case-insensitive matching
    value_lower = value.lower()
    for valid in EDUCATION_LEVELS:
        if value_lower == valid.lower():
            return valid
    
    # If not found, raise error with helpful message
    raise ValueError(f"Invalid education_level '{value}'. Must be one of: {', '.join(EDUCATION_LEVELS)}")


def validate_fuel(value: Optional[str]) -> Optional[str]:
    if value is None or value == '' or value.strip() == '':
        return None
    
    value = value.strip().upper()
    
    if value in FUEL_TYPES:
        return value
    
    raise ValueError(f"Invalid fuel '{value}'. Must be one of: {', '.join(FUEL_TYPES)}")


def validate_water_source(value: Optional[str]) -> Optional[str]:
    if value is None or value == '' or value.strip() == '':
        return None
    
    value = value.strip().upper()
    
    if value in WATER_SOURCES:
        return value
    
    raise ValueError(f"Invalid water_source '{value}'. Must be one of: {', '.join(WATER_SOURCES)}")


def validate_gender(value: Optional[str]) -> Optional[str]:
    if value is None or value == '' or value.strip() == '':
        return None
    
    value = value.strip()
    
    # Case-insensitive matching
    value_lower = value.lower()
    for valid in GENDER_VALUES:
        if value_lower == valid.lower():
            return valid
    
    raise ValueError(f"Invalid gender '{value}'. Must be one of: {', '.join(GENDER_VALUES)}")


def insert_csv_to_db(csv_file: str, db_name: str = 'user_info.db', skip_header: bool = True):
    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found.")
        sys.exit(1)
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute(SURVEY_DATA_SCHEMA)
    
    inserted_count = 0
    error_count = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            csv_columns = reader.fieldnames
            if csv_columns is None:
                print("Error: CSV file appears to be empty or has no headers.")
                conn.close()
                sys.exit(1)
            
            print(f"CSV columns found: {', '.join(csv_columns)}")
            print(f"\nStarting import from '{csv_file}' to '{db_name}'...\n")
            
            insert_sql = '''
            INSERT INTO survey_data (
                name, age, gender, marriage_status, disability, education_level,
                occupation, informal_working, contact,
                num_cows, num_goats, num_chickens, num_sheep, num_pigs, num_rabbits,
                land_ownership, land_size,
                num_radio, num_phone, num_tv,
                fuel, water_source,
                floor, roof, walls, toilet
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is header
                try:
                    normalized_row = {normalize_column_name(k): v for k, v in row.items()}
                    
                    name = normalized_row.get('name', '').strip()
                    if not name:
                        print(f"Warning: Row {row_num} skipped - missing name field")
                        error_count += 1
                        continue
                    
                    try:
                        gender = validate_gender(normalized_row.get('gender'))
                        education_level = validate_education_level(normalized_row.get('education_level'))
                        fuel = validate_fuel(normalized_row.get('fuel'))
                        water_source = validate_water_source(normalized_row.get('water_source'))
                    except ValueError as e:
                        print(f"Warning: Row {row_num} - {e}")
                        error_count += 1
                        continue
                    
                    values = (
                        name,
                        convert_to_int(normalized_row.get('age')),
                        gender,
                        convert_to_int(normalized_row.get('marriage_status'), 0),
                        convert_to_int(normalized_row.get('disability'), 0),
                        education_level,
                        convert_to_int(normalized_row.get('occupation'), 0),
                        convert_to_int(normalized_row.get('informal_working'), 0),
                        normalized_row.get('contact', '').strip() or None,
                        convert_to_int(normalized_row.get('num_cows'), 0),
                        convert_to_int(normalized_row.get('num_goats'), 0),
                        convert_to_int(normalized_row.get('num_chickens'), 0),
                        convert_to_int(normalized_row.get('num_sheep'), 0),
                        convert_to_int(normalized_row.get('num_pigs'), 0),
                        convert_to_int(normalized_row.get('num_rabbits'), 0),
                        convert_to_int(normalized_row.get('land_ownership'), 0),
                        convert_to_real(normalized_row.get('land_size')),
                        convert_to_int(normalized_row.get('num_radio'), 0),
                        convert_to_int(normalized_row.get('num_phone'), 0),
                        convert_to_int(normalized_row.get('num_tv'), 0),
                        fuel,
                        water_source,
                        convert_to_int(normalized_row.get('floor'), 0),
                        convert_to_int(normalized_row.get('roof'), 0),
                        convert_to_int(normalized_row.get('walls'), 0),
                        convert_to_int(normalized_row.get('toilet'), 0),
                    )
                    
                    cursor.execute(insert_sql, values)
                    inserted_count += 1
                    
                    if inserted_count % 100 == 0:
                        print(f"Inserted {inserted_count} records...")
                
                except sqlite3.IntegrityError as e:
                    print(f"Error inserting row {row_num}: {e}")
                    error_count += 1
                except Exception as e:
                    print(f"Error processing row {row_num}: {e}")
                    error_count += 1
        
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM survey_data")
        total_count = cursor.fetchone()[0]
        
        print(f"\n{'='*60}")
        print(f"Import completed!")
        print(f"{'='*60}")
        print(f"Records inserted: {inserted_count}")
        print(f"Errors encountered: {error_count}")
        print(f"Total records in database: {total_count}")
        print(f"{'='*60}")
        
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file}' not found.")
        conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_csv_to_db.py <csv_file> [db_name]")
        print("Example: python import_csv_to_db.py data.csv user_info.db")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    db_name = sys.argv[2] if len(sys.argv) > 2 else 'user_info.db'
    
    insert_csv_to_db(csv_file, db_name)

