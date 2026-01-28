import csv
import random
from database_schema import EDUCATION_LEVELS, FUEL_TYPES, WATER_SOURCES, GENDER_VALUES

# French and Rwandan names
FRENCH_FIRST_NAMES_MALE = [
    'Jean', 'Pierre', 'Paul', 'François', 'Michel', 'Philippe', 'André', 'Bernard',
    'Claude', 'Daniel', 'Henri', 'Jacques', 'Louis', 'Marc', 'Nicolas', 'Olivier',
    'Robert', 'Serge', 'Thomas', 'Vincent', 'Yves', 'Alain', 'Antoine', 'Bruno',
    'Christophe', 'David', 'Eric', 'Fabrice', 'Gérard', 'Hervé', 'Ivan', 'Julien',
    'Laurent', 'Marcel', 'Noël', 'Patrice', 'Quentin', 'Raphaël', 'Stéphane', 'Thierry'
]

FRENCH_FIRST_NAMES_FEMALE = [
    'Marie', 'Françoise', 'Monique', 'Catherine', 'Sylvie', 'Isabelle', 'Martine',
    'Nicole', 'Christine', 'Sophie', 'Nathalie', 'Valérie', 'Sandrine', 'Céline',
    'Julie', 'Caroline', 'Anne', 'Brigitte', 'Claire', 'Dominique', 'Élise', 'Fabienne',
    'Geneviève', 'Hélène', 'Ingrid', 'Jacqueline', 'Karine', 'Laurence', 'Marianne',
    'Nadine', 'Odile', 'Patricia', 'Rachel', 'Sabine', 'Tatiana', 'Véronique', 'Yvette'
]

FRENCH_LAST_NAMES = [
    'Martin', 'Bernard', 'Dubois', 'Thomas', 'Robert', 'Richard', 'Petit', 'Durand',
    'Leroy', 'Moreau', 'Simon', 'Laurent', 'Lefebvre', 'Michel', 'Garcia', 'David',
    'Bertrand', 'Roux', 'Vincent', 'Fournier', 'Morel', 'Girard', 'André', 'Lefevre',
    'Mercier', 'Dupont', 'Lambert', 'Bonnet', 'François', 'Martinez', 'Legrand',
    'Garnier', 'Faure', 'Rousseau', 'Blanc', 'Guerin', 'Muller', 'Henry', 'Roussel',
    'Nicolas', 'Perrin', 'Morin', 'Mathieu', 'Clement', 'Gauthier', 'Dumont', 'Lopez'
]

RWANDAN_LAST_NAMES = [
    'Mukamana', 'Nkurunziza', 'Niyonsaba', 'Uwimana', 'Mukamurenzi', 'Niyomugabo',
    'Mukamuganga', 'Niyonshuti', 'Mukamuhirwa', 'Niyonsenga', 'Mukamurezi', 'Niyonshima',
    'Mukamutara', 'Niyonshuti', 'Mukamukiza', 'Niyonshima', 'Mukamukiza', 'Niyonshuti',
    'Mukamukiza', 'Niyonshima', 'Mukamukiza', 'Niyonshuti', 'Mukamukiza', 'Niyonshima'
]

def generate_name(gender):
    """Generate a French name based on gender."""
    if gender == 'female':
        first_name = random.choice(FRENCH_FIRST_NAMES_FEMALE)
    else:
        first_name = random.choice(FRENCH_FIRST_NAMES_MALE)
    
    # Mix French and Rwandan last names
    last_name = random.choice(FRENCH_LAST_NAMES + RWANDAN_LAST_NAMES)
    return f"{first_name} {last_name}"

def generate_age():
    """Generate age between 18-30 with fair distribution."""
    return random.randint(18, 30)

def generate_education_level():
    """Generate education level - mostly low for low-income households."""
    # Weighted distribution favoring lower education
    weights = [0.35, 0.30, 0.20, 0.08, 0.05, 0.02]  # below primary, primary, secondary, etc.
    return random.choices(EDUCATION_LEVELS, weights=weights)[0]

def generate_marriage_status(age):
    """Generate marriage status - more likely to be married if older."""
    if age >= 25:
        return 1 if random.random() < 0.6 else 0
    elif age >= 22:
        return 1 if random.random() < 0.4 else 0
    else:
        return 1 if random.random() < 0.15 else 0

def generate_contact():
    """Generate phone contact (Rwandan format: +250XXXXXXXXX)."""
    if random.random() < 0.65:  # 65% have phone
        number = ''.join([str(random.randint(0, 9)) for _ in range(9)])
        return f"+250{number}"
    return ""

def generate_animals():
    """Generate animal counts - most have few or none."""
    # Most households have 0-2 animals, some have more
    if random.random() < 0.4:  # 40% have no animals
        return 0, 0, 0, 0, 0, 0
    
    # Weighted towards small numbers
    num_cows = random.choices([0, 1, 2, 3, 4], weights=[0.6, 0.25, 0.10, 0.04, 0.01])[0]
    num_goats = random.choices([0, 1, 2, 3, 4, 5], weights=[0.5, 0.25, 0.15, 0.06, 0.03, 0.01])[0]
    num_chickens = random.choices([0, 1, 2, 3, 4, 5, 6, 7, 8], 
                                  weights=[0.3, 0.2, 0.2, 0.15, 0.08, 0.04, 0.02, 0.01, 0.0])[0]
    num_sheep = random.choices([0, 1, 2, 3], weights=[0.7, 0.2, 0.08, 0.02])[0]
    num_pigs = random.choices([0, 1, 2], weights=[0.8, 0.15, 0.05])[0]
    num_rabbits = random.choices([0, 1, 2, 3], weights=[0.85, 0.10, 0.04, 0.01])[0]
    
    return num_cows, num_goats, num_chickens, num_sheep, num_pigs, num_rabbits

def generate_land():
    """Generate land ownership and size - most have little or no land."""
    has_land = 1 if random.random() < 0.35 else 0  # 35% own land
    if has_land:
        # Most have small plots (0.1 to 2 hectares)
        land_size = round(random.uniform(0.1, 2.0), 2)
    else:
        land_size = None
    return has_land, land_size

def generate_electronics():
    """Generate electronics counts - most have few."""
    # Radio is most common
    num_radio = random.choices([0, 1, 2], weights=[0.3, 0.6, 0.1])[0]
    # Phone ownership (already handled in contact, but some may have multiple)
    num_phone = random.choices([0, 1, 2], weights=[0.35, 0.60, 0.05])[0]
    # TV is least common
    num_tv = random.choices([0, 1], weights=[0.75, 0.25])[0]
    return num_radio, num_phone, num_tv

def generate_housing():
    """Generate housing quality indicators - mostly basic for low-income."""
    # 0 = basic/poor, 1 = improved
    floor = 1 if random.random() < 0.25 else 0  # 25% have improved floor
    roof = 1 if random.random() < 0.30 else 0   # 30% have improved roof
    walls = 1 if random.random() < 0.35 else 0  # 35% have improved walls
    toilet = 1 if random.random() < 0.40 else 0 # 40% have improved toilet
    return floor, roof, walls, toilet

def generate_user(gender):
    """Generate a single user record."""
    age = generate_age()
    name = generate_name(gender)
    marriage_status = generate_marriage_status(age)
    disability = 1 if random.random() < 0.10 else 0  # 10% with disability
    education_level = generate_education_level()
    
    # Occupation - most work informally
    occupation = 1 if random.random() < 0.75 else 0  # 75% have occupation
    informal_working = 1 if occupation == 1 and random.random() < 0.85 else 0  # 85% of workers are informal
    
    contact = generate_contact()
    num_cows, num_goats, num_chickens, num_sheep, num_pigs, num_rabbits = generate_animals()
    land_ownership, land_size = generate_land()
    num_radio, num_phone, num_tv = generate_electronics()
    fuel = random.choice(FUEL_TYPES)  # EU4, EU8, EU9
    water_source = random.choice(WATER_SOURCES)  # WS1, WS2
    floor, roof, walls, toilet = generate_housing()
    
    return {
        'name': name,
        'age': age,
        'gender': gender,
        'marriage_status': marriage_status,
        'disability': disability,
        'education_level': education_level,
        'occupation': occupation,
        'informal_working': informal_working,
        'contact': contact,
        'num_cows': num_cows,
        'num_goats': num_goats,
        'num_chickens': num_chickens,
        'num_sheep': num_sheep,
        'num_pigs': num_pigs,
        'num_rabbits': num_rabbits,
        'land_ownership': land_ownership,
        'land_size': land_size if land_size is not None else '',
        'num_radio': num_radio,
        'num_phone': num_phone,
        'num_tv': num_tv,
        'fuel': fuel,
        'water_source': water_source,
        'floor': floor,
        'roof': roof,
        'walls': walls,
        'toilet': toilet
    }

def generate_csv(filename='user_data.csv', num_users=100000):
    """Generate CSV file with user data."""
    print(f"Generating {num_users:,} users...")
    print("70% female, 30% male")
    print("Age: 18-30")
    print("10% with disability")
    print("Low-income, low-educated characteristics\n")
    
    # Determine gender distribution
    num_female = int(num_users * 0.70)
    num_male = num_users - num_female
    
    genders = ['female'] * num_female + ['male'] * num_male
    random.shuffle(genders)
    
    fieldnames = [
        'name', 'age', 'gender', 'marriage_status', 'disability', 'education_level',
        'occupation', 'informal_working', 'contact',
        'num_cows', 'num_goats', 'num_chickens', 'num_sheep', 'num_pigs', 'num_rabbits',
        'land_ownership', 'land_size',
        'num_radio', 'num_phone', 'num_tv',
        'fuel', 'water_source',
        'floor', 'roof', 'walls', 'toilet'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, gender in enumerate(genders, 1):
            user = generate_user(gender)
            writer.writerow(user)
            
            if i % 10000 == 0:
                print(f"Generated {i:,} users...")
    
    print(f"\n✓ Successfully generated {num_users:,} users in '{filename}'")
    print(f"  - Female: {num_female:,} ({(num_female/num_users)*100:.1f}%)")
    print(f"  - Male: {num_male:,} ({(num_male/num_users)*100:.1f}%)")

if __name__ == "__main__":
    import sys
    
    num_users = 100000
    filename = 'user_data.csv'
    
    if len(sys.argv) > 1:
        try:
            num_users = int(sys.argv[1])
        except ValueError:
            print(f"Invalid number of users: {sys.argv[1]}. Using default: 100,000")
    
    if len(sys.argv) > 2:
        filename = sys.argv[2]
    
    generate_csv(filename, num_users)

