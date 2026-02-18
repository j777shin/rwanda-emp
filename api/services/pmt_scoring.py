"""
PMT (Poverty Measurement Tool) scoring based on the 17-question recalibrated model.
Weights from: data/17_question_pmt_recalibrated_weights.csv
Lower PMT score = more vulnerable/poorer household.
"""

# District effects from the recalibrated PMT model
DISTRICT_EFFECTS = {
    "Nyarugenge": 0.278, "Gasabo": 0.183, "Kicukiro": 0.245,
    "Burera": -0.098, "Gatsibo": -0.156, "Gicumbi": -0.112,
    "Gisagara": -0.203, "Kamonyi": -0.087, "Karongi": -0.145,
    "Kayonza": -0.134, "Kirehe": -0.178, "Muhanga": -0.056,
    "Musanze": 0.012, "Ngoma": -0.123, "Ngororero": -0.167,
    "Nyabihu": -0.089, "Nyagatare": -0.145, "Nyamagabe": -0.134,
    "Nyamasheke": -0.156, "Nyanza": -0.098, "Nyaruguru": -0.178,
    "Rubavu": 0.034, "Ruhango": -0.078, "Rusizi": -0.112,
    "Rutsiro": -0.145, "Rwamagana": -0.067,
}

# Base weights from the PMT model
INTERCEPT = 12.903


def calculate_pmt_score(beneficiary_data: dict) -> float:
    """Calculate PMT score for a single beneficiary.

    Lower score = more vulnerable = higher priority for selection.
    """
    score = INTERCEPT

    # Cooking
    score += 0.062 if beneficiary_data.get("cooking_firewood", False) else 0
    score += 0.658 if beneficiary_data.get("cooking_gas", False) else 0
    score += 0.255 if beneficiary_data.get("cooking_charcoal", False) else 0

    # Floor
    score += -0.190 if beneficiary_data.get("floor_earth_sand", False) else 0
    score += 0.380 if beneficiary_data.get("floor_tiles", False) else 0

    # Lighting
    score += 0.072 if beneficiary_data.get("lighting", False) else 0

    # Assets
    score += 0.096 if beneficiary_data.get("num_phone", 0) > 0 else 0
    score += 0.067 if beneficiary_data.get("num_radio", 0) > 0 else 0
    score += 0.229 if beneficiary_data.get("num_tv", 0) > 0 else 0

    # Livestock (continuous)
    score += 0.061 * beneficiary_data.get("num_cattle", 0)
    score += 0.009 * beneficiary_data.get("num_goats", 0)
    score += 0.021 * beneficiary_data.get("num_sheep", 0)
    score += 0.032 * beneficiary_data.get("num_pigs", 0)

    # Land
    score += 0.065 if beneficiary_data.get("land_ownership", False) else 0

    # Household composition
    score += 0.039 * beneficiary_data.get("children_under_18", 0)
    score += -0.119 * beneficiary_data.get("household_size", 0)

    # Household head education
    score += 0.623 if beneficiary_data.get("hh_head_university", False) else 0
    score += 0.093 if beneficiary_data.get("hh_head_primary", False) else 0
    score += 0.235 if beneficiary_data.get("hh_head_secondary", False) else 0

    # Household head marital status
    score += -0.014 if beneficiary_data.get("hh_head_married", False) else 0
    score += 0.044 if beneficiary_data.get("hh_head_widow", False) else 0
    score += -0.064 if beneficiary_data.get("hh_head_divorced", False) else 0

    # Household head gender
    score += -0.169 if beneficiary_data.get("hh_head_female", False) else 0

    # District effect
    district = beneficiary_data.get("district", "")
    score += DISTRICT_EFFECTS.get(district, 0)

    return round(score, 4)
