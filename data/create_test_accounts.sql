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
-- 2. BENEFICIARY TEST ACCOUNT (Full Access - All Tabs)
-- ============================================================================

-- Insert beneficiary user with track='both' so all Phase 2 tabs are unlocked
WITH new_user AS (
    INSERT INTO users (email, password_hash, role, is_active, created_at, updated_at)
    VALUES (
        'test@gmail.com',
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
    'Test User',
    26,
    'female',
    '+250788000000',
    FALSE,
    FALSE,
    'secondary',
    FALSE,
    TRUE,
    2,
    0,
    1,
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
    4,
    FALSE,
    TRUE,
    FALSE,
    FALSE,
    FALSE,
    FALSE,
    TRUE,
    'Gasabo',
    'selected',
    'both',
    TRUE,
    FALSE,
    'I want to open a tailoring shop in Kicukiro district that makes affordable, trendy clothes for young people in Rwanda. Many youth want modern outfits for school events, church, and going out, but imported clothes are expensive and local tailors mostly cater to older customers. I will offer custom school uniforms, casual streetwear, and event outfits at youth-friendly prices starting from 3,000 RWF. I completed a 6-month tailoring course at a vocational training centre and have been making clothes for friends and family. I already own a sewing machine and basic supplies. My plan is to start from a small rented space near a secondary school, build a customer base through social media and word of mouth, and hire one assistant within six months. Eventually I want to expand into selling my designs online and training other young people in tailoring skills.',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM new_user
ON CONFLICT (user_id) DO UPDATE
SET
    name = 'Test User',
    age = 26,
    gender = 'female',
    contact = '+250788000000',
    skillcraft_score = NULL,
    pathways_completion_rate = NULL,
    eligibility_score = NULL,
    selection_status = 'selected',
    track = 'both',
    wants_entrepreneurship = TRUE,
    self_employed = FALSE,
    business_development_text = 'I want to open a tailoring shop in Kicukiro district that makes affordable, trendy clothes for young people in Rwanda. Many youth want modern outfits for school events, church, and going out, but imported clothes are expensive and local tailors mostly cater to older customers. I will offer custom school uniforms, casual streetwear, and event outfits at youth-friendly prices starting from 3,000 RWF. I completed a 6-month tailoring course at a vocational training centre and have been making clothes for friends and family. I already own a sewing machine and basic supplies. My plan is to start from a small rented space near a secondary school, build a customer base through social media and word of mouth, and hire one assistant within six months. Eventually I want to expand into selling my designs online and training other young people in tailoring skills.',
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
LEFT JOIN beneficiaries b ON b.user_id = u.id
WHERE u.email IN ('admin@rwanda.gov.rw', 'test@gmail.com')
ORDER BY u.role DESC, u.email;
