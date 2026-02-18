# Quick Start Guide

Get the Rwanda Employment Project database up and running in 3 steps.

## Prerequisites

- Python 3.7+ installed
- PostgreSQL installed and running
- PostgreSQL credentials (username/password)

## Installation

### Option 1: Automated Setup (Recommended)

```bash
cd /Users/j777shin/code/rwanda/rwanda-emp/data

# Run the setup script
./setup.sh

# Edit the .env file with your database credentials
nano .env  # or use any text editor

# Load the data
python3 load_data_to_db.py

# Verify the data
python3 verify_data.py
```

### Option 2: Manual Setup

```bash
cd /Users/j777shin/code/rwanda/rwanda-emp/data

# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Create .env file
cp .env.example .env

# 3. Edit .env with your credentials
# Update DB_USER and DB_PASSWORD in .env file

# 4. Load the data
python3 load_data_to_db.py

# 5. Verify the data
python3 verify_data.py
```

## Configuration

Edit `.env` file:

```bash
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres          # ← Change this
DB_PASSWORD=your_password # ← Change this
DB_NAME=rwanda_emp
```

## What Gets Created

- **Database**: `rwanda_emp`
- **Tables**: users, beneficiaries, chatbot_conversations, chatbot_results, activity_log
- **Records**: 100,000 users and 100,000 beneficiaries
- **Data Size**: ~42MB total

## Troubleshooting

### "Could not connect to PostgreSQL"

**macOS:**
```bash
brew services start postgresql
```

**Linux:**
```bash
sudo systemctl start postgresql
```

**Check if running:**
```bash
psql -h localhost -U postgres -c '\q'
```

### "Package not installed" errors

```bash
pip3 install --upgrade -r requirements.txt
```

### "Permission denied"

```bash
# Make sure you have database creation privileges
psql -U postgres -c "ALTER USER your_username CREATEDB;"
```

## Verify Installation

After running `load_data_to_db.py`, you should see:

```
✓ Created database 'rwanda_emp'
✓ Database schema initialized successfully
✓ Loaded 100,000 rows into 'users' table
✓ Loaded 100,000 rows into 'beneficiaries' table
✓ All beneficiaries have matching user records
```

Run `verify_data.py` to see detailed statistics:

```bash
python3 verify_data.py
```

## Next Steps

1. **Connect to database:**
   ```bash
   psql -h localhost -U postgres -d rwanda_emp
   ```

2. **Query the data:**
   ```sql
   SELECT * FROM beneficiaries LIMIT 10;
   ```

3. **Use in your application:**
   ```python
   import psycopg2
   from dotenv import load_dotenv
   import os

   load_dotenv()

   conn = psycopg2.connect(
       host=os.getenv('DB_HOST'),
       port=os.getenv('DB_PORT'),
       user=os.getenv('DB_USER'),
       password=os.getenv('DB_PASSWORD'),
       database=os.getenv('DB_NAME')
   )
   ```

## Need Help?

- See [README.md](README.md) for detailed documentation
- Check PostgreSQL logs: `tail -f /usr/local/var/log/postgresql@14.log` (macOS)
- Verify Python version: `python3 --version` (needs 3.7+)
