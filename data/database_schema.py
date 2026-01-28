SURVEY_DATA_SCHEMA = '''
CREATE TABLE IF NOT EXISTS survey_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    gender TEXT CHECK(gender IN ('male', 'female')),
    marriage_status INTEGER CHECK(marriage_status IN (0, 1)),
    disability INTEGER CHECK(disability IN (0, 1)),
    education_level TEXT CHECK(education_level IN ('below primary', 'primary', 'secondary', 'secondary-professional', 'professional', 'tertiary-and-above')),
    occupation INTEGER CHECK(occupation IN (0, 1)),
    informal_working INTEGER CHECK(informal_working IN (0, 1)),
    contact TEXT,
    num_cows INTEGER DEFAULT 0,
    num_goats INTEGER DEFAULT 0,
    num_chickens INTEGER DEFAULT 0,
    num_sheep INTEGER DEFAULT 0,
    num_pigs INTEGER DEFAULT 0,
    num_rabbits INTEGER DEFAULT 0,
    land_ownership INTEGER CHECK(land_ownership IN (0, 1)),
    land_size REAL,
    num_radio INTEGER DEFAULT 0,
    num_phone INTEGER DEFAULT 0,
    num_tv INTEGER DEFAULT 0,
    fuel TEXT CHECK(fuel IN ('EU4', 'EU8', 'EU9')),
    water_source TEXT CHECK(water_source IN ('WS1', 'WS2')),
    floor INTEGER CHECK(floor IN (0, 1)),
    roof INTEGER CHECK(roof IN (0, 1)),
    walls INTEGER CHECK(walls IN (0, 1)),
    toilet INTEGER CHECK(toilet IN (0, 1))
)
'''

EDUCATION_LEVELS = ['below primary', 'primary', 'secondary', 'secondary-professional', 'professional', 'tertiary-and-above']
FUEL_TYPES = ['EU4', 'EU8', 'EU9']
WATER_SOURCES = ['WS1', 'WS2']
GENDER_VALUES = ['male', 'female']

