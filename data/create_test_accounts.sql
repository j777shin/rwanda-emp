-- ============================================================================
-- TEST ACCOUNTS FOR RWANDA EMPLOYMENT PROJECT
-- ============================================================================
-- This script creates test accounts for both admin and beneficiary portals
-- Run this after initializing the database schema

-- ============================================================================
-- 1. ADMIN TEST ACCOUNT
-- ============================================================================

-- Insert admin user
INSERT INTO users (email, password_hash, role, is_active, created_at, updated_at)
VALUES (
    'admin@rwanda.gov.rw',
    crypt('Admin@2026', gen_salt('bf')),
    'admin',
    TRUE,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (email) DO UPDATE
SET password_hash = crypt('Admin@2026', gen_salt('bf')),
    is_active = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 2. BENEFICIARY TEST ACCOUNT
-- ============================================================================

-- Insert beneficiary user
WITH new_user AS (
    INSERT INTO users (email, password_hash, role, is_active, created_at, updated_at)
    VALUES (
        'uwase.ingabire@gmail.com',
        crypt('User@2026', gen_salt('bf')),
        'beneficiary',
        TRUE,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ) ON CONFLICT (email) DO UPDATE
    SET password_hash = crypt('User@2026', gen_salt('bf')),
        is_active = TRUE,
        updated_at = CURRENT_TIMESTAMP
    RETURNING id
)
-- Insert beneficiary profile
INSERT INTO beneficiaries (
    user_id,
    name,
    age,
    gender,
    contact,
    marriage_status,
    disability,
    education_level,
    occupation,
    informal_working,
    num_goats,
    num_sheep,
    num_pigs,
    land_ownership,
    land_size,
    num_radio,
    num_phone,
    num_tv,
    cooking_firewood,
    cooking_gas,
    cooking_charcoal,
    floor_earth_sand,
    floor_tiles,
    lighting,
    num_cattle,
    children_under_18,
    household_size,
    hh_head_university,
    hh_head_primary,
    hh_head_secondary,
    hh_head_married,
    hh_head_widow,
    hh_head_divorced,
    hh_head_female,
    district,
    skillcraft_score,
    pathways_completion_rate,
    eligibility_score,
    selection_status,
    track,
    wants_entrepreneurship,
    created_at,
    updated_at
)
SELECT
    new_user.id,
    'Uwase Ingabire',
    24,
    'female',
    '+250788123456',
    FALSE,
    FALSE,
    'secondary',
    FALSE,
    FALSE,
    2,
    0,
    0,
    FALSE,
    0.0,
    1,
    1,
    0,
    TRUE,
    FALSE,
    FALSE,
    TRUE,
    FALSE,
    FALSE,
    0,
    0,
    4,
    FALSE,
    FALSE,
    TRUE,
    FALSE,
    FALSE,
    FALSE,
    TRUE,
    'Gasabo',
    75.50,
    65.00,
    70.25,
    'pending',
    'both',
    TRUE,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM new_user
ON CONFLICT (user_id) DO UPDATE
SET
    name = 'Uwase Ingabire',
    age = 24,
    gender = 'female',
    contact = '+250788123456',
    skillcraft_score = 75.50,
    pathways_completion_rate = 65.00,
    eligibility_score = 70.25,
    selection_status = 'pending',
    track = 'both',
    wants_entrepreneurship = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 3. ADDITIONAL TEST BENEFICIARY (Selected status)
-- ============================================================================

-- Insert another beneficiary user (selected)
WITH new_user AS (
    INSERT INTO users (email, password_hash, role, is_active, created_at, updated_at)
    VALUES (
        'john.mugisha@gmail.com',
        crypt('User@2026', gen_salt('bf')),
        'beneficiary',
        TRUE,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ) ON CONFLICT (email) DO UPDATE
    SET password_hash = crypt('User@2026', gen_salt('bf')),
        is_active = TRUE,
        updated_at = CURRENT_TIMESTAMP
    RETURNING id
)
-- Insert beneficiary profile
INSERT INTO beneficiaries (
    user_id,
    name,
    age,
    gender,
    contact,
    marriage_status,
    disability,
    education_level,
    occupation,
    informal_working,
    num_goats,
    num_sheep,
    num_pigs,
    land_ownership,
    land_size,
    num_radio,
    num_phone,
    num_tv,
    cooking_firewood,
    cooking_gas,
    cooking_charcoal,
    floor_earth_sand,
    floor_tiles,
    lighting,
    num_cattle,
    children_under_18,
    household_size,
    hh_head_university,
    hh_head_primary,
    hh_head_secondary,
    hh_head_married,
    hh_head_widow,
    hh_head_divorced,
    hh_head_female,
    district,
    skillcraft_score,
    pathways_completion_rate,
    eligibility_score,
    selection_status,
    track,
    wants_entrepreneurship,
    created_at,
    updated_at
)
SELECT
    new_user.id,
    'Mugisha Gasana',
    28,
    'male',
    '+250789654321',
    TRUE,
    FALSE,
    'tertiary_and_above',
    TRUE,
    FALSE,
    0,
    0,
    0,
    FALSE,
    0.0,
    1,
    1,
    1,
    FALSE,
    TRUE,
    FALSE,
    FALSE,
    TRUE,
    TRUE,
    0,
    2,
    5,
    TRUE,
    FALSE,
    FALSE,
    TRUE,
    FALSE,
    FALSE,
    FALSE,
    'Kicukiro',
    85.75,
    92.00,
    88.50,
    'selected',
    'employment',
    FALSE,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM new_user
ON CONFLICT (user_id) DO UPDATE
SET
    name = 'Mugisha Gasana',
    age = 28,
    gender = 'male',
    skillcraft_score = 85.75,
    pathways_completion_rate = 92.00,
    eligibility_score = 88.50,
    selection_status = 'selected',
    track = 'employment',
    wants_entrepreneurship = FALSE,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 4. ENTREPRENEURSHIP TRACK TEST BENEFICIARY
-- ============================================================================

WITH new_user AS (
    INSERT INTO users (email, password_hash, role, is_active, created_at, updated_at)
    VALUES (
        'alice.uwimana@gmail.com',
        crypt('User@2026', gen_salt('bf')),
        'beneficiary',
        TRUE,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ) ON CONFLICT (email) DO UPDATE
    SET password_hash = crypt('User@2026', gen_salt('bf')),
        is_active = TRUE,
        updated_at = CURRENT_TIMESTAMP
    RETURNING id
)
INSERT INTO beneficiaries (
    user_id,
    name,
    age,
    gender,
    contact,
    marriage_status,
    disability,
    education_level,
    occupation,
    informal_working,
    num_goats,
    num_sheep,
    num_pigs,
    land_ownership,
    land_size,
    num_radio,
    num_phone,
    num_tv,
    cooking_firewood,
    cooking_gas,
    cooking_charcoal,
    floor_earth_sand,
    floor_tiles,
    lighting,
    num_cattle,
    children_under_18,
    household_size,
    hh_head_university,
    hh_head_primary,
    hh_head_secondary,
    hh_head_married,
    hh_head_widow,
    hh_head_divorced,
    hh_head_female,
    district,
    skillcraft_score,
    pathways_completion_rate,
    eligibility_score,
    selection_status,
    track,
    wants_entrepreneurship,
    self_employed,
    business_development_text,
    created_at,
    updated_at
)
SELECT
    new_user.id,
    'Alice Uwimana',
    26,
    'female',
    '+250787112233',
    FALSE,
    FALSE,
    'secondary',
    FALSE,
    TRUE,
    1,
    0,
    2,
    TRUE,
    0.5,
    1,
    1,
    0,
    TRUE,
    FALSE,
    TRUE,
    TRUE,
    FALSE,
    FALSE,
    0,
    1,
    3,
    FALSE,
    TRUE,
    FALSE,
    FALSE,
    FALSE,
    FALSE,
    TRUE,
    'Nyarugenge',
    80.00,
    78.50,
    82.75,
    'selected',
    'entrepreneurship',
    TRUE,
    TRUE,
    'I plan to start a tailoring business in Nyarugenge district, providing affordable custom clothing and alterations to local residents. I have 2 years of experience in sewing and want to grow this into a full workshop.',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM new_user
ON CONFLICT (user_id) DO UPDATE
SET
    name = 'Alice Uwimana',
    age = 26,
    gender = 'female',
    contact = '+250787112233',
    skillcraft_score = 80.00,
    pathways_completion_rate = 78.50,
    eligibility_score = 82.75,
    selection_status = 'selected',
    track = 'entrepreneurship',
    wants_entrepreneurship = TRUE,
    self_employed = TRUE,
    business_development_text = 'I plan to start a tailoring business in Nyarugenge district, providing affordable custom clothing and alterations to local residents. I have 2 years of experience in sewing and want to grow this into a full workshop.',
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Display created test accounts
SELECT
    u.email,
    u.role,
    u.is_active,
    b.name,
    b.age,
    b.district,
    b.selection_status,
    b.track,
    b.eligibility_score
FROM users u
LEFT JOIN beneficiaries b ON u.user_id = b.id
WHERE u.email IN ('admin@rwanda.gov.rw', 'test.beneficiary@gmail.com', 'john.mugisha@gmail.com', 'alice.uwimana@gmail.com')
ORDER BY u.role DESC, u.email;
