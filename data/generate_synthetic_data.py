#!/usr/bin/env python3
"""
Synthetic Data Generator for Rwanda Youth Employment Project
Generates 100,000 beneficiary records based on Kigali Pilot proportions
"""

import csv
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import hashlib

# Set random seed for reproducibility
random.seed(42)

# ============================================================================
# CONFIGURATION
# ============================================================================

NUM_USERS = 100000
OUTPUT_DIR = "/Users/j777shin/code/rwanda/rwanda-emp/data"

# ============================================================================
# PROPORTIONS FROM CSV (Kigali Pilot Data)
# ============================================================================

# District distribution (Kigali only)
DISTRICT_PROPS = {
    'Nyarugenge': 21.4,
    'Gasabo': 50.4,
    'Kicukiro': 28.2
}

# Gender distribution
GENDER_PROPS = {
    'male': 50.0,
    'female': 50.0
}

# Urban/Rural by district
URBAN_RURAL_BY_DISTRICT = {
    'Nyarugenge': {'urban': 84.4, 'rural': 15.6},
    'Gasabo': {'urban': 81.2, 'rural': 18.8},
    'Kicukiro': {'urban': 99.1, 'rural': 0.9}
}

# Marriage status by age group
MARRIAGE_BY_AGE = {
    '16-19': {'married': 2.0, 'ever_married': 0.1, 'never_married': 97.9},
    '20-24': {'married': 20.2, 'ever_married': 0.6, 'never_married': 79.4},
    '25-29': {'married': 47.0, 'ever_married': 1.4, 'never_married': 51.6},
    '30-34': {'married': 70.0, 'ever_married': 2.4, 'never_married': 27.6}
}

# Disability
DISABILITY_PROPS = {True: 2.3, False: 97.7}

# School attendance
SCHOOL_ATTENDANCE_PROPS = {
    'never': 3.1,
    'currently': 23.0,
    'previously': 73.8,
    'not_stated': 0.1
}

# Education level
EDUCATION_LEVEL_PROPS = {
    'never': 3.1,
    'nursery': 0.1,
    'primary': 35.5,
    'vocational': 0.9,
    'lower_secondary': 21.8,
    'upper_secondary': 24.5,
    'university': 14.0,
    'not_stated': 0.1
}

# Occupation by sex
OCCUPATION_BY_SEX = {
    'male': {True: 55.8, False: 44.2},
    'female': {True: 41.8, False: 58.2}
}

# NEET by sex
NEET_BY_SEX = {
    'male': {True: 23.7, False: 76.3},
    'female': {True: 38.3, False: 61.7}
}

# Informal worker (among those working)
INFORMAL_WORKER_PROPS = {True: 50.0, False: 50.0}

# House type by urban/rural
HOUSE_TYPE_BY_URBAN = {
    'urban': {
        'planned_rural': 0.0, 'integrated_village': 1.3, 'old_settlement': 3.0,
        'dispersed': 2.7, 'modern_urban': 47.9, 'spontaneous': 43.4, 'other': 1.7
    },
    'rural': {
        'planned_rural': 32.6, 'integrated_village': 0.8, 'old_settlement': 1.2,
        'dispersed': 49.1, 'modern_urban': 2.2, 'spontaneous': 13.0, 'other': 1.1
    }
}

# House ownership (urban vs rural)
HOUSE_OWNER_BY_URBAN = {
    'urban': {'owner': 30.0, 'tenant': 65.0, 'free': 3.0, 'other': 2.0},
    'rural': {'owner': 75.0, 'tenant': 20.0, 'free': 3.0, 'other': 2.0}
}

# Floor material by urban/rural
FLOOR_BY_URBAN = {
    'urban': {'cement': 64.0, 'tile': 20.0, 'earth': 15.0, 'other': 1.0},
    'rural': {'cement': 30.0, 'tile': 1.0, 'earth': 65.0, 'other': 4.0}
}

# Wall material by urban/rural
WALL_BY_URBAN = {
    'urban': {'sun_dried_cement': 70.0, 'sun_dried_no_cement': 5.0, 'wood_mud_cement': 5.0,
              'wood_mud_no_cement': 1.0, 'burnt_bricks': 5.0, 'other': 14.0},
    'rural': {'sun_dried_cement': 35.0, 'sun_dried_no_cement': 10.0, 'wood_mud_cement': 20.0,
              'wood_mud_no_cement': 25.0, 'burnt_bricks': 1.0, 'other': 9.0}
}

# Toilet type by urban/rural
TOILET_BY_URBAN = {
    'urban': {'flush_not_shared': 10.0, 'flush_shared': 2.0, 'pit_not_shared': 35.0,
              'pit_shared': 50.0, 'other': 3.0},
    'rural': {'flush_not_shared': 0.5, 'flush_shared': 0.0, 'pit_not_shared': 75.0,
              'pit_shared': 15.0, 'other': 9.5}
}

# Lighting source by urban/rural
LIGHTING_BY_URBAN = {
    'urban': {'electricity': 93.7, 'flashlight': 2.3, 'other': 4.0},
    'rural': {'electricity': 58.6, 'flashlight': 26.4, 'other': 15.0}
}

# Cooking source by urban/rural
COOKING_BY_URBAN = {
    'urban': {'firewood': 12.0, 'charcoal': 65.0, 'gas': 20.0, 'none': 3.0, 'other': 0.0},
    'rural': {'firewood': 75.0, 'charcoal': 21.0, 'gas': 2.0, 'none': 2.0, 'other': 0.0}
}

# Household assets (% ownership)
ASSET_OWNERSHIP = {
    'mobile': 92.4, 'radio': 93.9, 'tv': 36.1, 'fridge': 12.3,
    'cooker': 34.7, 'washing': 2.0, 'microwave': 4.4, 'iron': 37.0,
    'bed': 55.2, 'table': 64.6, 'sofa': 34.9, 'computer': 16.3,
    'vehicle': 7.6, 'motorcycle': 2.4, 'bicycle': 6.5
}

# Livestock by urban/rural
LIVESTOCK_BY_URBAN = {
    'urban': {'cow': 3.0, 'goat': 2.5, 'sheep': 0.3, 'pig': 1.2, 'rabbit': 7.8, 'chicken': 3.7, 'bee': 1.1},
    'rural': {'cow': 27.7, 'goat': 22.0, 'sheep': 1.3, 'pig': 8.9, 'rabbit': 7.9, 'chicken': 14.8, 'bee': 0.9}
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def weighted_choice(options: Dict[str, float]) -> str:
    """Select an item based on weighted probabilities"""
    items = list(options.keys())
    weights = list(options.values())
    return random.choices(items, weights=weights, k=1)[0]

def get_age_group(age: int) -> str:
    """Map age to age group"""
    if 16 <= age <= 19:
        return '16-19'
    elif 20 <= age <= 24:
        return '20-24'
    elif 25 <= age <= 29:
        return '25-29'
    elif 30 <= age <= 34:
        return '30-34'
    return '16-19'

def map_education_level(edu_raw: str) -> str:
    """Map CSV education categories to schema categories"""
    mapping = {
        'never': 'below_primary',
        'nursery': 'below_primary',
        'primary': 'primary',
        'vocational': 'secondary_professional',
        'lower_secondary': 'secondary',
        'upper_secondary': 'secondary',
        'university': 'tertiary_and_above',
        'not_stated': 'primary'  # default
    }
    return mapping.get(edu_raw, 'primary')

def generate_rwandan_name(gender: str) -> str:
    """Generate a realistic Rwandan name"""
    male_first = ['Gasana', 'Mugisha', 'Hakizimana', 'Niyonzima', 'Nsabimana', 'Uwimana',
                  'Habimana', 'Tuyisenge', 'Byiringiro', 'Nshuti', 'Kalisa', 'Mutoni']
    female_first = ['Uwase', 'Ingabire', 'Mutesi', 'Umutoni', 'Uwineza', 'Akimana',
                    'Iradukunda', 'Mukamana', 'Nyirahabimana', 'Murekatete', 'Uwera', 'Ishimwe']
    last_names = ['Mugabo', 'Habimana', 'Nkunda', 'Bizimana', 'Niyitegeka', 'Mukeshimana',
                  'Rutayisire', 'Ndayisaba', 'Murenzi', 'Ntaganda', 'Kamanzi', 'Uwamahoro']

    first = random.choice(male_first if gender == 'male' else female_first)
    last = random.choice(last_names)
    return f"{first} {last}"

def generate_phone_number() -> str:
    """Generate a realistic Rwandan phone number"""
    prefixes = ['078', '079', '072', '073']
    return f"+25{random.choice(prefixes)}{random.randint(1000000, 9999999)}"

def generate_email(name: str, user_id: str) -> str:
    """Generate a realistic email address"""
    name_parts = name.lower().replace(' ', '')
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
    return f"{name_parts}.{user_id[:8]}@{random.choice(domains)}"

def hash_password(password: str) -> str:
    """Simple password hash (in real system, use bcrypt)"""
    return hashlib.sha256(password.encode()).hexdigest()

def random_date_in_range(start_days_ago: int, end_days_ago: int) -> str:
    """Generate a random datetime within a range"""
    days_ago = random.randint(end_days_ago, start_days_ago)
    dt = datetime.now() - timedelta(days=days_ago)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def generate_household_size(marriage_status: bool, age: int) -> int:
    """Generate realistic household size"""
    if marriage_status and age >= 25:
        # Married adults likely have larger households
        return random.choices([1, 2, 3, 4, 5, 6, 7, 8],
                            weights=[2, 5, 15, 25, 25, 15, 10, 3], k=1)[0]
    else:
        # Single/younger people likely have smaller households
        return random.choices([1, 2, 3, 4, 5, 6],
                            weights=[10, 20, 25, 25, 15, 5], k=1)[0]

def generate_children_under_18(household_size: int, age: int, marriage_status: bool) -> int:
    """Generate number of children under 18"""
    if age < 20 or not marriage_status:
        return 0
    max_children = max(0, household_size - 2)
    if max_children == 0:
        return 0
    # Younger parents tend to have fewer children
    if age < 25:
        return random.choices([0, 1, 2], weights=[40, 40, 20], k=1)[0]
    return random.randint(0, min(max_children, 5))

# ============================================================================
# MAIN GENERATION FUNCTION
# ============================================================================

def generate_beneficiary() -> Tuple[Dict, Dict]:
    """Generate a single beneficiary with user account"""

    # Generate IDs
    user_id = str(uuid.uuid4())
    beneficiary_id = str(uuid.uuid4())

    # Basic demographics
    age = random.randint(16, 34)
    age_group = get_age_group(age)
    gender = weighted_choice(GENDER_PROPS)
    district = weighted_choice(DISTRICT_PROPS)
    urban_rural = weighted_choice(URBAN_RURAL_BY_DISTRICT[district])
    is_urban = (urban_rural == 'urban')

    # Personal info
    name = generate_rwandan_name(gender)
    email = generate_email(name, user_id)
    contact = generate_phone_number()

    # Marriage status (age-dependent)
    marriage_raw = weighted_choice(MARRIAGE_BY_AGE[age_group])
    marriage_status = (marriage_raw in ['married', 'ever_married'])

    # Disability
    disability = weighted_choice(DISABILITY_PROPS)

    # Education
    edu_raw = weighted_choice(EDUCATION_LEVEL_PROPS)
    education_level = map_education_level(edu_raw)

    # Employment
    occupation = weighted_choice(OCCUPATION_BY_SEX[gender])
    informal_working = False
    if occupation:
        informal_working = weighted_choice(INFORMAL_WORKER_PROPS)

    # Housing
    floor_raw = weighted_choice(FLOOR_BY_URBAN['urban' if is_urban else 'rural'])
    floor_earth_sand = (floor_raw == 'earth')
    floor_tiles = (floor_raw == 'tile')

    cooking_raw = weighted_choice(COOKING_BY_URBAN['urban' if is_urban else 'rural'])
    cooking_firewood = (cooking_raw == 'firewood')
    cooking_gas = (cooking_raw == 'gas')
    cooking_charcoal = (cooking_raw == 'charcoal')

    lighting_raw = weighted_choice(LIGHTING_BY_URBAN['urban' if is_urban else 'rural'])
    lighting = (lighting_raw == 'electricity')

    # Assets (phone, radio, TV as numbers)
    num_phone = 1 if random.random() * 100 < ASSET_OWNERSHIP['mobile'] else 0
    num_radio = 1 if random.random() * 100 < ASSET_OWNERSHIP['radio'] else 0
    num_tv = 1 if random.random() * 100 < ASSET_OWNERSHIP['tv'] else 0

    # Livestock
    livestock_probs = LIVESTOCK_BY_URBAN['urban' if is_urban else 'rural']
    num_cattle = 0
    if random.random() * 100 < livestock_probs['cow']:
        num_cattle = random.choices([1, 2, 3, 4, 5], weights=[50, 25, 15, 7, 3], k=1)[0]

    num_goats = 0
    if random.random() * 100 < livestock_probs['goat']:
        num_goats = random.choices([1, 2, 3, 4, 5, 6], weights=[30, 25, 20, 15, 7, 3], k=1)[0]

    num_sheep = 0
    if random.random() * 100 < livestock_probs['sheep']:
        num_sheep = random.choices([1, 2, 3], weights=[60, 30, 10], k=1)[0]

    num_pigs = 0
    if random.random() * 100 < livestock_probs['pig']:
        num_pigs = random.choices([1, 2, 3], weights=[60, 30, 10], k=1)[0]

    # Land ownership (more likely in rural areas)
    land_ownership = random.random() < (0.15 if is_urban else 0.65)
    land_size = 0.0
    if land_ownership:
        # Land size in hectares (small plots typical in Rwanda)
        land_size = round(random.uniform(0.1, 2.5), 2)

    # Household composition
    household_size = generate_household_size(marriage_status, age)
    children_under_18 = generate_children_under_18(household_size, age, marriage_status)

    # Household head characteristics (assume beneficiary is or knows HH head)
    # For simplicity, use beneficiary's own characteristics with some variation
    hh_head_female = (gender == 'female') if random.random() < 0.7 else (gender != 'female')
    hh_head_married = marriage_status if random.random() < 0.8 else not marriage_status
    hh_head_widow = False
    hh_head_divorced = False
    if not hh_head_married and age > 25:
        if random.random() < 0.2:
            hh_head_widow = True
        elif random.random() < 0.15:
            hh_head_divorced = True

    # HH head education (may differ from beneficiary)
    hh_edu_level = education_level if random.random() < 0.6 else map_education_level(weighted_choice(EDUCATION_LEVEL_PROPS))
    hh_head_university = (hh_edu_level == 'tertiary_and_above')
    hh_head_primary = (hh_edu_level == 'primary')
    hh_head_secondary = (hh_edu_level in ['secondary', 'secondary_professional'])

    # Program-related (all pending initially)
    created_at = random_date_in_range(365, 30)  # Created in last year

    # User record
    user = {
        'id': user_id,
        'email': email,
        'password_hash': hash_password('defaultPassword123'),  # In production, users would set their own
        'role': 'beneficiary',
        'is_active': True,
        'created_at': created_at,
        'updated_at': created_at
    }

    # Beneficiary record
    beneficiary = {
        'id': beneficiary_id,
        'user_id': user_id,
        'name': name,
        'age': age,
        'gender': gender,
        'contact': contact,
        'marriage_status': marriage_status,
        'disability': disability,
        'education_level': education_level,
        'occupation': occupation,
        'informal_working': informal_working,
        'num_goats': num_goats,
        'num_sheep': num_sheep,
        'num_pigs': num_pigs,
        'land_ownership': land_ownership,
        'land_size': land_size,
        'num_radio': num_radio,
        'num_phone': num_phone,
        'num_tv': num_tv,
        'cooking_firewood': cooking_firewood,
        'cooking_gas': cooking_gas,
        'cooking_charcoal': cooking_charcoal,
        'floor_earth_sand': floor_earth_sand,
        'floor_tiles': floor_tiles,
        'lighting': lighting,
        'num_cattle': num_cattle,
        'children_under_18': children_under_18,
        'household_size': household_size,
        'hh_head_university': hh_head_university,
        'hh_head_primary': hh_head_primary,
        'hh_head_secondary': hh_head_secondary,
        'hh_head_married': hh_head_married,
        'hh_head_widow': hh_head_widow,
        'hh_head_divorced': hh_head_divorced,
        'hh_head_female': hh_head_female,
        'district': district,
        'skillcraft_user_id': None,
        'skillcraft_score': None,
        'skillcraft_last_sync': None,
        'pathways_user_id': None,
        'pathways_completion_rate': None,
        'pathways_last_sync': None,
        'eligibility_score': None,
        'selection_status': 'pending',
        'track': None,
        'self_employed': False,
        'hired': False,
        'offline_attendance': 0,
        'phase1_satisfactory': None,
        'emp_track_satisfactory': None,
        'ent_track_satisfactory': None,
        'created_at': created_at,
        'updated_at': created_at
    }

    return user, beneficiary

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print(f"Generating {NUM_USERS:,} synthetic beneficiaries...")
    print("=" * 70)

    users = []
    beneficiaries = []

    # Generate all records
    for i in range(NUM_USERS):
        if (i + 1) % 10000 == 0:
            print(f"Generated {i + 1:,} / {NUM_USERS:,} records...")

        user, beneficiary = generate_beneficiary()
        users.append(user)
        beneficiaries.append(beneficiary)

    print(f"\nGeneration complete! Writing to CSV files...")

    # Write users CSV
    users_file = f"{OUTPUT_DIR}/synthetic_users.csv"
    with open(users_file, 'w', newline='', encoding='utf-8') as f:
        if users:
            writer = csv.DictWriter(f, fieldnames=users[0].keys())
            writer.writeheader()
            writer.writerows(users)
    print(f"✓ Wrote {len(users):,} users to: {users_file}")

    # Write beneficiaries CSV
    beneficiaries_file = f"{OUTPUT_DIR}/synthetic_beneficiaries.csv"
    with open(beneficiaries_file, 'w', newline='', encoding='utf-8') as f:
        if beneficiaries:
            writer = csv.DictWriter(f, fieldnames=beneficiaries[0].keys())
            writer.writeheader()
            writer.writerows(beneficiaries)
    print(f"✓ Wrote {len(beneficiaries):,} beneficiaries to: {beneficiaries_file}")

    # Print summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)

    total = len(beneficiaries)
    male_count = sum(1 for b in beneficiaries if b['gender'] == 'male')
    female_count = total - male_count

    district_counts = {}
    for b in beneficiaries:
        district_counts[b['district']] = district_counts.get(b['district'], 0) + 1

    employed = sum(1 for b in beneficiaries if b['occupation'])
    informal = sum(1 for b in beneficiaries if b['informal_working'])

    married = sum(1 for b in beneficiaries if b['marriage_status'])
    disabled = sum(1 for b in beneficiaries if b['disability'])

    print(f"\nTotal beneficiaries: {total:,}")
    print(f"\nGender distribution:")
    print(f"  Male: {male_count:,} ({male_count/total*100:.1f}%)")
    print(f"  Female: {female_count:,} ({female_count/total*100:.1f}%)")

    print(f"\nDistrict distribution:")
    for district, count in sorted(district_counts.items()):
        print(f"  {district}: {count:,} ({count/total*100:.1f}%)")

    print(f"\nEmployment:")
    print(f"  Employed: {employed:,} ({employed/total*100:.1f}%)")
    print(f"  Informal workers: {informal:,} ({informal/employed*100:.1f}% of employed)")

    print(f"\nOther characteristics:")
    print(f"  Married: {married:,} ({married/total*100:.1f}%)")
    print(f"  With disability: {disabled:,} ({disabled/total*100:.1f}%)")

    avg_age = sum(b['age'] for b in beneficiaries) / total
    avg_household = sum(b['household_size'] for b in beneficiaries) / total

    print(f"\nAverages:")
    print(f"  Age: {avg_age:.1f} years")
    print(f"  Household size: {avg_household:.1f} persons")

    print("\n" + "=" * 70)
    print("Data generation complete!")
    print("\nNext steps:")
    print("1. Review the CSV files to ensure data quality")
    print("2. Import into PostgreSQL using COPY command:")
    print(f"   \\copy users FROM '{users_file}' CSV HEADER")
    print(f"   \\copy beneficiaries FROM '{beneficiaries_file}' CSV HEADER")
    print("=" * 70)

if __name__ == "__main__":
    main()
