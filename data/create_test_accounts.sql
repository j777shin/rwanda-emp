-- ============================================================================
-- TEST ACCOUNTS FOR RWANDA EMPLOYMENT PROJECT
-- ============================================================================
-- This script creates test accounts for both admin and beneficiary portals
-- Run this after initializing the database schema

-- ============================================================================
-- 2. BENEFICIARY TEST ACCOUNT (Full Access - All Tabs)
-- ============================================================================

-- Insert beneficiary user with track='both' so all Phase 2 tabs are unlocked
-- (see Python implementation for env-driven credentials)
WITH new_user AS (
    SELECT NULL::uuid AS id
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
    'Imanzi Wear – Affordable Urban Fashion in Kigali, Rwanda

Imanzi Wear will launch as a small-scale, print-on-demand clothing brand targeting youth aged 16–35. The initial focus will be on high-quality graphic t-shirts and caps featuring modern Rwandan-inspired designs. Production will follow a pre-order model to minimize inventory risk and reduce upfront costs.
Business Model:

Designs will be created digitally and printed through partnerships with local printing shops in Kigali. Products will be marketed and sold through Instagram, WhatsApp Business, and university pop-up sales. Customers will place orders during a two-week pre-order campaign, and production will begin after payments are collected, ensuring positive cash flow.',
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
    ingazi_completion_rate = NULL,
    eligibility_score = NULL,
    selection_status = 'selected',
    track = 'both',
    wants_entrepreneurship = TRUE,
    self_employed = FALSE,
    business_development_text = 'Imanzi Wear – Affordable Urban Fashion in Kigali, Rwanda

Imanzi Wear will launch as a small-scale, print-on-demand clothing brand targeting youth aged 16–35. The initial focus will be on high-quality graphic t-shirts and caps featuring modern Rwandan-inspired designs. Production will follow a pre-order model to minimize inventory risk and reduce upfront costs.
Business Model:

Designs will be created digitally and printed through partnerships with local printing shops in Kigali. Products will be marketed and sold through Instagram, WhatsApp Business, and university pop-up sales. Customers will place orders during a two-week pre-order campaign, and production will begin after payments are collected, ensuring positive cash flow.',
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
