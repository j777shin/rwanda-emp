import csv
import io
from typing import Any


REQUIRED_FIELDS = ["name", "age", "gender", "email"]

OPTIONAL_FIELDS = [
    "contact", "district", "education_level", "marriage_status", "disability",
    "occupation", "informal_working", "num_goats", "num_sheep", "num_pigs",
    "num_cattle", "land_ownership", "land_size", "num_radio", "num_phone",
    "num_tv", "cooking_firewood", "cooking_gas", "cooking_charcoal",
    "floor_earth_sand", "floor_tiles", "lighting", "children_under_18",
    "household_size", "hh_head_university", "hh_head_primary",
    "hh_head_secondary", "hh_head_married", "hh_head_widow",
    "hh_head_divorced", "hh_head_female",
]

BOOLEAN_FIELDS = {
    "marriage_status", "disability", "occupation", "informal_working",
    "land_ownership", "cooking_firewood", "cooking_gas", "cooking_charcoal",
    "floor_earth_sand", "floor_tiles", "lighting", "hh_head_university",
    "hh_head_primary", "hh_head_secondary", "hh_head_married",
    "hh_head_widow", "hh_head_divorced", "hh_head_female",
}

INT_FIELDS = {
    "age", "num_goats", "num_sheep", "num_pigs", "num_cattle",
    "num_radio", "num_phone", "num_tv", "children_under_18", "household_size",
}

VALID_GENDERS = {"male", "female"}
VALID_EDUCATION = {
    "below_primary", "primary", "secondary",
    "secondary_professional", "professional", "tertiary_and_above",
}
VALID_DISTRICTS = {
    "Burera", "Gasabo", "Gatsibo", "Gicumbi", "Gisagara", "Kamonyi", "Karongi",
    "Kayonza", "Kicukiro", "Kirehe", "Muhanga", "Musanze", "Ngoma", "Ngororero",
    "Nyabihu", "Nyagatare", "Nyamagabe", "Nyamasheke", "Nyanza", "Nyarugenge",
    "Nyaruguru", "Rubavu", "Ruhango", "Rusizi", "Rutsiro", "Rwamagana",
}


def parse_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes", "t", "y")


def parse_csv(content: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse CSV content and return (records, errors)."""
    errors = []
    records = []

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return [], ["CSV file is empty or has no header row"]

    missing_required = [f for f in REQUIRED_FIELDS if f not in reader.fieldnames]
    if missing_required:
        return [], [f"Missing required columns: {', '.join(missing_required)}"]

    for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
        row_errors = []

        # Validate required fields
        for field in REQUIRED_FIELDS:
            if not row.get(field, "").strip():
                row_errors.append(f"Row {i}: Missing required field '{field}'")

        # Validate age
        age_str = row.get("age", "").strip()
        if age_str:
            try:
                age = int(age_str)
                if age < 15 or age > 35:
                    row_errors.append(f"Row {i}: Age must be between 15 and 35, got {age}")
            except ValueError:
                row_errors.append(f"Row {i}: Invalid age value '{age_str}'")

        # Validate gender
        gender = row.get("gender", "").strip().lower()
        if gender and gender not in VALID_GENDERS:
            row_errors.append(f"Row {i}: Invalid gender '{gender}'")

        # Validate district
        district = row.get("district", "").strip()
        if district and district not in VALID_DISTRICTS:
            row_errors.append(f"Row {i}: Invalid district '{district}'")

        # Validate education level
        edu = row.get("education_level", "").strip()
        if edu and edu not in VALID_EDUCATION:
            row_errors.append(f"Row {i}: Invalid education level '{edu}'")

        if row_errors:
            errors.extend(row_errors)
            continue

        # Build record
        record = {
            "email": row["email"].strip(),
            "name": row["name"].strip(),
            "age": int(row["age"].strip()),
            "gender": gender,
        }

        for field in OPTIONAL_FIELDS:
            value = row.get(field, "").strip()
            if not value:
                continue
            if field in BOOLEAN_FIELDS:
                record[field] = parse_bool(value)
            elif field in INT_FIELDS:
                try:
                    record[field] = int(value)
                except ValueError:
                    errors.append(f"Row {i}: Invalid integer value for '{field}': '{value}'")
            elif field == "land_size":
                try:
                    record[field] = float(value)
                except ValueError:
                    errors.append(f"Row {i}: Invalid decimal value for '{field}': '{value}'")
            else:
                record[field] = value

        records.append(record)

    return records, errors
