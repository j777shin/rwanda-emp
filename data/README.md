# Rwanda Youth Employment Project - Synthetic Data Generation

This directory contains scripts and data for generating and loading synthetic beneficiary data into the PostgreSQL database.

## 📁 Files Overview

### Scripts
- **`generate_synthetic_data.py`** - Generates 100k synthetic users and beneficiaries based on Kigali Pilot proportions
- **`load_data_to_db.py`** - Initializes database schema and loads CSV data into PostgreSQL

### Data Files
- **`database_schema.sql`** - PostgreSQL database schema definition
- **`Kigali Pilot_Variables Proportion_260206.csv`** - Real census proportions used for data generation
- **`synthetic_users.csv`** - Generated user accounts (100k records, ~10MB)
- **`synthetic_beneficiaries.csv`** - Generated beneficiary data (100k records, ~32MB)

### Configuration
- **`requirements.txt`** - Python dependencies
- **`db_config.example.py`** - Database configuration template

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Database Connection

Edit `load_data_to_db.py` and update the `DB_CONFIG` section (lines 17-23) with your PostgreSQL credentials:

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'your_username',      # Change this
    'password': 'your_password',  # Change this
    'database': 'rwanda_emp'
}
```

### 3. Initialize Database and Load Data

```bash
python3 load_data_to_db.py
```

This will:
1. ✓ Create the `rwanda_emp` database (if it doesn't exist)
2. ✓ Execute the schema SQL to create all tables
3. ✓ Load 100k users from CSV
4. ✓ Load 100k beneficiaries from CSV
5. ✓ Verify data integrity

## 📊 Generated Data Overview

### User Records (100,000)
- UUID-based unique identifiers
- Email addresses (format: `name.userid@domain.com`)
- Password hashes (default: `defaultPassword123`)
- All users have `beneficiary` role
- All accounts are active

### Beneficiary Records (100,000)
Based on Rwanda Population and Household Census 2022 (Kigali City data):

#### Demographics
- **Age**: 16-34 years (equal distribution)
- **Gender**: 50% Male / 50% Female
- **Districts**: Gasabo (50.4%), Kicukiro (28.2%), Nyarugenge (21.4%)

#### Socioeconomic Characteristics
- Marriage status (varies by age: 2% for 16-19, 70% for 30-34)
- Education levels (35.5% primary, 24.5% upper secondary, 14% university)
- Employment status (55.8% male employed, 41.8% female employed)
- 50% of employed work in informal sector
- Disability rate: 2.3%

#### Household Data
- Average household size: 3.7 persons
- Housing type varies by urban/rural status
- Floor materials, cooking fuel, lighting sources
- Asset ownership (mobile phones, TV, radio, etc.)
- Livestock ownership (varies by urban/rural)
- Land ownership and size

All distributions follow the proportions from the Kigali Pilot census data.

## 🔄 Regenerating Data

If you need to regenerate the synthetic data with different parameters:

```bash
python3 generate_synthetic_data.py
```

Edit the script to:
- Change `NUM_USERS` (line 15) for different dataset size
- Modify proportions in the configuration section (lines 25-126)
- Adjust low-income bias by tweaking distribution weights

## 🗄️ Database Schema

The database includes:

### Tables
- **`users`** - Authentication and user accounts
- **`beneficiaries`** - Beneficiary demographic and household data
- **`chatbot_conversations`** - Chat message history
- **`chatbot_results`** - Entrepreneurship assessment results
- **`activity_log`** - User action tracking

### Views
- **`v_beneficiary_dashboard`** - Combined beneficiary and user data
- **`v_dashboard_summary`** - Aggregated statistics

### Functions
- **`calculate_eligibility_score()`** - Calculates beneficiary eligibility based on multiple factors

## 🔍 Data Verification

After loading, the script verifies:
- ✓ All beneficiaries have matching user records (foreign key integrity)
- ✓ Gender distribution matches expected proportions
- ✓ District distribution matches census data
- ✓ Average age and household size are realistic

Example output:
```
Total beneficiaries: 100,000
Male: 49,840 (49.8%)
Female: 50,160 (50.2%)

District distribution:
  Gasabo: 50,539 (50.5%)
  Kicukiro: 28,134 (28.1%)
  Nyarugenge: 21,327 (21.3%)
```

## 📝 Manual Database Operations

### Connect to Database
```bash
psql -h localhost -U postgres -d rwanda_emp
```

### Query Examples
```sql
-- View all beneficiaries from Gasabo district
SELECT * FROM beneficiaries WHERE district = 'Gasabo' LIMIT 10;

-- Count by gender
SELECT gender, COUNT(*) FROM beneficiaries GROUP BY gender;

-- Find low-income beneficiaries (earth floors, no electricity)
SELECT * FROM beneficiaries
WHERE floor_earth_sand = TRUE
  AND lighting = FALSE
  AND num_cattle = 0
LIMIT 20;

-- Calculate average eligibility scores
SELECT AVG(eligibility_score) FROM beneficiaries
WHERE eligibility_score IS NOT NULL;
```

### Reset Database
```sql
-- Drop all data
TRUNCATE users, beneficiaries, chatbot_conversations, chatbot_results, activity_log CASCADE;

-- Or drop entire database
DROP DATABASE rwanda_emp;
```

## 🛠️ Troubleshooting

### "Could not connect to PostgreSQL"
- Ensure PostgreSQL is running: `brew services start postgresql` (macOS) or `sudo systemctl start postgresql` (Linux)
- Check credentials in `DB_CONFIG`
- Verify PostgreSQL is listening on the correct port

### "Permission denied"
- Grant user necessary permissions:
```sql
GRANT ALL PRIVILEGES ON DATABASE rwanda_emp TO your_username;
```

### "CSV file not found"
- Make sure you've run `generate_synthetic_data.py` first
- Check file paths in `load_data_to_db.py` match your directory structure

### "COPY FROM STDIN failed"
- The script will automatically fall back to row-by-row insertion
- This is slower but more compatible with different PostgreSQL configurations

## 📚 Data Sources

- **Rwanda Population and Household Census 2022** (Kigali City)
- Source: [Rwanda National Institute of Statistics](https://www.statistics.gov.rw/district-statistics/kigali-city)

## 🔐 Security Notes

- Default password hash is for testing only
- In production, implement proper password hashing (bcrypt)
- Store database credentials in environment variables or secure vault
- Never commit actual passwords to version control

## 📈 Next Steps

After loading the data:
1. Verify data quality with sample queries
2. Calculate eligibility scores using `calculate_eligibility_score()` function
3. Integrate with SkillCraft and Pathways platforms
4. Set up user selection process based on eligibility scores
