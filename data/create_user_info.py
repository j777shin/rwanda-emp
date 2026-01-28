import sqlite3
from database_schema import SURVEY_DATA_SCHEMA

def create_user_info_db(db_name='user_info.db'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute(SURVEY_DATA_SCHEMA)
    
    conn.commit()
    print(f"Database '{db_name}' created successfully!")
    
    return conn


def view_table_info(conn):
    cursor = conn.cursor()
    
    # Get table schema
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='survey_data'")
    schema = cursor.fetchone()
    print("\n" + "="*60)
    print("TABLE SCHEMA:")
    print("="*60)
    print(schema[0])
    
    # Get column info
    cursor.execute("PRAGMA table_info(survey_data)")
    columns = cursor.fetchall()
    print("\n" + "="*60)
    print("COLUMN DETAILS:")
    print("="*60)
    print(f"{'Column':<20} {'Type':<10} {'Not Null':<10} {'Default':<10}")
    print("-" * 60)
    for col in columns:
        print(f"{col[1]:<20} {col[2]:<10} {str(bool(col[3])):<10} {str(col[4]):<10}")
    
    # Count records
    cursor.execute("SELECT COUNT(*) FROM survey_data")
    count = cursor.fetchone()[0]
    print(f"\nTotal records in table: {count}")


if __name__ == "__main__":
    conn = create_user_info_db()
    
    # Display table information
    view_table_info(conn)

    conn.close()
    print("\nDatabase connection closed.")