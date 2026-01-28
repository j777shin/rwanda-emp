import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
import os
from pathlib import Path


def read_sql_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove comments and split by semicolons
    statements = []
    current_statement = []
    in_comment = False
    
    for line in content.split('\n'):
        # Handle block comments
        if '/*' in line:
            in_comment = True
        if '*/' in line:
            in_comment = False
            continue
        if in_comment:
            continue
        
        # Handle line comments
        if '--' in line:
            line = line.split('--')[0]
        
        line = line.strip()
        if line:
            current_statement.append(line)
            if line.endswith(';'):
                statement = ' '.join(current_statement)
                if statement.strip() and not statement.strip().startswith('--'):
                    statements.append(statement)
                current_statement = []
    
    return statements


def create_database(host='localhost', port=5432, user='postgres', password='postgres', 
                    database='rwanda_emp', schema_file='database_schema.sql'):
    """
    Create database and execute schema file.
    
    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        user: PostgreSQL user
        password: PostgreSQL password
        database: Database name to create
        schema_file: Path to SQL schema file
    """
    try:
        # Connect to postgres database to create new database
        print(f"Connecting to PostgreSQL server...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
        exists = cursor.fetchone()
        
        if exists:
            print(f"Database '{database}' already exists. Dropping it...")
            cursor.execute(f"DROP DATABASE {database}")
        
        print(f"Creating database '{database}'...")
        cursor.execute(f"CREATE DATABASE {database}")
        cursor.close()
        conn.close()
        
        # Connect to new database
        print(f"Connecting to database '{database}'...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()
        
        # Read and execute schema file
        schema_path = Path(__file__).parent / schema_file
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        print(f"Reading schema file: {schema_path}")
        statements = read_sql_file(schema_path)
        
        print(f"Executing {len(statements)} SQL statements...")
        for i, statement in enumerate(statements, 1):
            try:
                cursor.execute(statement)
                if i % 10 == 0:
                    print(f"  Executed {i}/{len(statements)} statements...")
            except Exception as e:
                print(f"Warning: Error executing statement {i}: {e}")
                print(f"Statement: {statement[:100]}...")
                # Continue with other statements
        
        conn.commit()
        print(f"\n✓ Database '{database}' created successfully!")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"\nCreated tables: {', '.join([t[0] for t in tables])}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create database from schema file')
    parser.add_argument('--host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--port', type=int, default=5432, help='PostgreSQL port')
    parser.add_argument('--user', default='postgres', help='PostgreSQL user')
    parser.add_argument('--password', default='postgres', help='PostgreSQL password')
    parser.add_argument('--database', default='rwanda_emp', help='Database name')
    parser.add_argument('--schema-file', default='database_schema.sql', help='Schema file path')
    
    args = parser.parse_args()
    
    success = create_database(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        schema_file=args.schema_file
    )
    
    sys.exit(0 if success else 1)

