-- Migration: Rename pathways_* columns to ingazi_* in beneficiaries table
-- Run this on the existing database to match the updated codebase.

ALTER TABLE beneficiaries RENAME COLUMN pathways_user_id TO ingazi_user_id;
ALTER TABLE beneficiaries RENAME COLUMN pathways_completion_rate TO ingazi_completion_rate;
ALTER TABLE beneficiaries RENAME COLUMN pathways_last_sync TO ingazi_last_sync;
ALTER TABLE beneficiaries RENAME COLUMN pathways_course_progress TO ingazi_course_progress;

-- Recreate views that reference the renamed columns

DROP VIEW IF EXISTS v_beneficiary_dashboard;
CREATE VIEW v_beneficiary_dashboard AS
SELECT
    b.id,
    b.name,
    b.age,
    b.gender,
    b.education_level,
    b.contact,
    b.cooking_firewood,
    b.cooking_gas,
    b.cooking_charcoal,
    b.floor_earth_sand,
    b.floor_tiles,
    b.lighting,
    b.num_cattle,
    b.children_under_18,
    b.household_size,
    b.hh_head_university,
    b.hh_head_primary,
    b.hh_head_secondary,
    b.hh_head_married,
    b.hh_head_widow,
    b.hh_head_divorced,
    b.hh_head_female,
    b.district,
    b.skillcraft_score,
    b.ingazi_completion_rate,
    b.eligibility_score,
    b.selection_status,
    b.track,
    b.self_employed,
    b.hired,
    b.offline_attendance,
    b.phase1_satisfactory,
    b.emp_track_satisfactory,
    b.ent_track_satisfactory,
    u.email,
    u.is_active,
    b.created_at
FROM beneficiaries b
LEFT JOIN users u ON b.user_id = u.id;

DROP VIEW IF EXISTS v_dashboard_summary;
CREATE VIEW v_dashboard_summary AS
SELECT
    COUNT(*) AS total_beneficiaries,
    COUNT(*) FILTER (WHERE selection_status = 'selected') AS selected_count,
    COUNT(*) FILTER (WHERE gender = 'male') AS male_count,
    COUNT(*) FILTER (WHERE gender = 'female') AS female_count,
    AVG(skillcraft_score) AS avg_skillcraft,
    AVG(ingazi_completion_rate) AS avg_ingazi,
    AVG(eligibility_score) AS avg_eligibility,
    COUNT(*) FILTER (WHERE track = 'employment') AS employment_track,
    COUNT(*) FILTER (WHERE track = 'entrepreneurship') AS entrepreneurship_track
FROM beneficiaries;

-- Recreate the eligibility score function with renamed column reference
CREATE OR REPLACE FUNCTION calculate_eligibility_score(
    p_beneficiary_id UUID
) RETURNS DECIMAL AS $$
DECLARE
    v_skillcraft DECIMAL;
    v_ingazi DECIMAL;
    v_socioeconomic DECIMAL;
    v_total DECIMAL;
BEGIN
    SELECT
        COALESCE(skillcraft_score, 0),
        COALESCE(ingazi_completion_rate, 0)
    INTO v_skillcraft, v_ingazi
    FROM beneficiaries
    WHERE id = p_beneficiary_id;

    SELECT
        CASE
            WHEN (COALESCE(num_cattle, 0) + num_goats + num_sheep + num_pigs) > 20 THEN 30
            WHEN (COALESCE(num_cattle, 0) + num_goats + num_sheep + num_pigs) > 10 THEN 50
            WHEN (COALESCE(num_cattle, 0) + num_goats + num_sheep + num_pigs) > 5 THEN 70
            ELSE 100
        END +
        CASE WHEN land_ownership THEN 0 ELSE 20 END +
        CASE WHEN (NOT COALESCE(floor_earth_sand, FALSE) AND COALESCE(floor_tiles, FALSE)) THEN 0 ELSE 30 END
    INTO v_socioeconomic
    FROM beneficiaries
    WHERE id = p_beneficiary_id;

    v_socioeconomic := LEAST(100, GREATEST(0, 100 - (v_socioeconomic * 0.5)));

    -- Calculate weighted total (40% skill, 30% ingazi, 30% socioeconomic)
    v_total := (v_skillcraft * 0.4) + (v_ingazi * 0.3) + (v_socioeconomic * 0.3);

    UPDATE beneficiaries
    SET eligibility_score = v_total
    WHERE id = p_beneficiary_id;

    RETURN v_total;
END;
$$ LANGUAGE plpgsql;
