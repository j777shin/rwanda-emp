-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('beneficiary', 'admin')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE beneficiaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- Personal Information
    name VARCHAR(255) NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 15 AND age <= 35),
    gender VARCHAR(10) CHECK (gender IN ('male', 'female')),
    contact VARCHAR(50),
    
    -- Household Information
    marriage_status BOOLEAN DEFAULT FALSE,
    disability BOOLEAN DEFAULT FALSE,
    education_level VARCHAR(30) CHECK (education_level IN (
        'below_primary', 'primary', 'secondary', 
        'secondary_professional', 'professional', 'tertiary_and_above'
    )),
    occupation BOOLEAN DEFAULT FALSE,
    informal_working BOOLEAN DEFAULT FALSE,
    
    -- Livestock Assets
    num_goats INTEGER DEFAULT 0,
    num_sheep INTEGER DEFAULT 0,
    num_pigs INTEGER DEFAULT 0,
    
    -- Land & Housing
    land_ownership BOOLEAN DEFAULT FALSE,
    land_size DECIMAL(10, 2) DEFAULT 0,
    num_radio INTEGER DEFAULT 0,
    num_phone INTEGER DEFAULT 0,
    num_tv INTEGER DEFAULT 0,
    
    -- Cooking, floor, lighting (PMT variables)
    cooking_firewood BOOLEAN DEFAULT FALSE,
    cooking_gas BOOLEAN DEFAULT FALSE,
    cooking_charcoal BOOLEAN DEFAULT FALSE,
    floor_earth_sand BOOLEAN DEFAULT FALSE,
    floor_tiles BOOLEAN DEFAULT FALSE,
    lighting BOOLEAN DEFAULT FALSE,
    
    -- Livestock (PMT)
    num_cattle INTEGER DEFAULT 0,
    
    -- Household (PMT variables)
    children_under_18 INTEGER DEFAULT 0,
    household_size INTEGER DEFAULT 0,
    hh_head_university BOOLEAN DEFAULT FALSE,
    hh_head_primary BOOLEAN DEFAULT FALSE,
    hh_head_secondary BOOLEAN DEFAULT FALSE,
    hh_head_married BOOLEAN DEFAULT FALSE,
    hh_head_widow BOOLEAN DEFAULT FALSE,
    hh_head_divorced BOOLEAN DEFAULT FALSE,
    hh_head_female BOOLEAN DEFAULT FALSE,
    
    -- District (categorical)
    district VARCHAR(30) CHECK (district IN (
        'Burera', 'Gasabo', 'Gatsibo', 'Gicumbi', 'Gisagara', 'Kamonyi', 'Karongi',
        'Kayonza', 'Kicukiro', 'Kirehe', 'Muhanga', 'Musanze', 'Ngoma', 'Ngororero',
        'Nyabihu', 'Nyagatare', 'Nyamagabe', 'Nyamasheke', 'Nyanza', 'Nyarugenge',
        'Nyaruguru', 'Rubavu', 'Ruhango', 'Rusizi', 'Rutsiro', 'Rwamagana'
    )),
    
    -- SkillCraft & Pathways 
    skillcraft_user_id VARCHAR(100),
    skillcraft_score DECIMAL(5, 2),
    skillcraft_last_sync TIMESTAMP,
    
    pathways_user_id VARCHAR(100),
    pathways_completion_rate DECIMAL(5, 2),
    pathways_last_sync TIMESTAMP,
    pathways_course_progress JSONB,

    eligibility_score DECIMAL(5, 2),
    selection_status VARCHAR(20) DEFAULT 'pending' CHECK (
        selection_status IN ('pending', 'phase1', 'selected', 'rejected', 'waitlist')
    ),
    track VARCHAR(20) CHECK (track IN ('employment', 'entrepreneurship', 'both')),
    
    -- Employment / programme outcomes
    self_employed BOOLEAN DEFAULT FALSE,
    hired BOOLEAN DEFAULT FALSE,
    hired_company_name VARCHAR(255),
    self_employed_description TEXT,
    offline_attendance INTEGER DEFAULT 0,
    phase1_satisfactory DECIMAL(5, 2),
    emp_track_satisfactory DECIMAL(5, 2),
    ent_track_satisfactory DECIMAL(5, 2),
    
    -- Grant
    grant_received BOOLEAN DEFAULT FALSE,
    grant_amount INTEGER DEFAULT 0,

    -- Business development (for entrepreneurship interest)
    business_development_text TEXT,
    wants_entrepreneurship BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chatbot_stages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    beneficiary_id UUID NOT NULL REFERENCES beneficiaries(id) ON DELETE CASCADE,
    stage_number INTEGER NOT NULL CHECK (stage_number BETWEEN 1 AND 5),
    stage_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed')),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    stage_data JSONB,
    UNIQUE(beneficiary_id, stage_number)
);

CREATE TABLE chatbot_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    beneficiary_id UUID NOT NULL REFERENCES beneficiaries(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_user BOOLEAN NOT NULL, -- true = user message, false = bot response
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chatbot_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    beneficiary_id UUID UNIQUE NOT NULL REFERENCES beneficiaries(id) ON DELETE CASCADE,
    entrepreneurship_score DECIMAL(5, 2),
    readiness_level VARCHAR(50),
    summary TEXT,
    recommendations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE activity_log (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES 
-- ============================================================================

CREATE INDEX idx_beneficiaries_user_id ON beneficiaries(user_id);
CREATE INDEX idx_beneficiaries_selection_status ON beneficiaries(selection_status);
CREATE INDEX idx_beneficiaries_eligibility_score ON beneficiaries(eligibility_score);
CREATE INDEX idx_chatbot_conversations_beneficiary ON chatbot_conversations(beneficiary_id);
CREATE INDEX idx_chatbot_stages_beneficiary ON chatbot_stages(beneficiary_id);
CREATE INDEX idx_activity_log_user_id ON activity_log(user_id);

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_timestamp
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_beneficiaries_timestamp
    BEFORE UPDATE ON beneficiaries
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_chatbot_results_timestamp
    BEFORE UPDATE ON chatbot_results
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- ============================================================================
-- USEFUL VIEWS FOR MVP
-- ============================================================================

-- Complete beneficiary view with all data
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
    b.pathways_completion_rate,
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

-- Summary statistics for dashboard
CREATE VIEW v_dashboard_summary AS
SELECT 
    COUNT(*) AS total_beneficiaries,
    COUNT(*) FILTER (WHERE selection_status = 'selected') AS selected_count,
    COUNT(*) FILTER (WHERE gender = 'male') AS male_count,
    COUNT(*) FILTER (WHERE gender = 'female') AS female_count,
    AVG(skillcraft_score) AS avg_skillcraft,
    AVG(pathways_completion_rate) AS avg_pathways,
    AVG(eligibility_score) AS avg_eligibility,
    COUNT(*) FILTER (WHERE track = 'employment') AS employment_track,
    COUNT(*) FILTER (WHERE track = 'entrepreneurship') AS entrepreneurship_track
FROM beneficiaries;

-- ============================================================================
-- SEED DATA 
-- ============================================================================

-- Create admin user 
INSERT INTO users (email, password_hash, role) 
VALUES ('admin@admin@com', crypt('admin123', gen_salt('bf')), 'admin');

-- ============================================================================
-- HELPER FUNCTIONS 
-- ============================================================================

-- Simple function to calculate eligibility score
CREATE OR REPLACE FUNCTION calculate_eligibility_score(
    p_beneficiary_id UUID
) RETURNS DECIMAL AS $$
DECLARE
    v_skillcraft DECIMAL;
    v_pathways DECIMAL;
    v_socioeconomic DECIMAL;
    v_total DECIMAL;
BEGIN
    -- Get scores
    SELECT 
        COALESCE(skillcraft_score, 0),
        COALESCE(pathways_completion_rate, 0)
    INTO v_skillcraft, v_pathways
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
    
    -- Normalize socioeconomic to 0-100
    v_socioeconomic := LEAST(100, GREATEST(0, 100 - (v_socioeconomic * 0.5)));
    
    -- Calculate weighted total (40% skill, 30% pathways, 30% socioeconomic)
    v_total := (v_skillcraft * 0.4) + (v_pathways * 0.3) + (v_socioeconomic * 0.3);
    
    -- Update the beneficiary record
    UPDATE beneficiaries
    SET eligibility_score = v_total
    WHERE id = p_beneficiary_id;
    
    RETURN v_total;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE users IS 'MVP: Combined authentication and user data';
COMMENT ON TABLE beneficiaries IS 'MVP: All beneficiary data in single table for simplicity';
COMMENT ON COLUMN beneficiaries.cooking_firewood IS 'PMT: Cooking with firewood (q2_16=1)';
COMMENT ON COLUMN beneficiaries.cooking_gas IS 'PMT: Cooking with gas (q2_16=2 or 5)';
COMMENT ON COLUMN beneficiaries.cooking_charcoal IS 'PMT: Cooking with charcoal (q2_16=4)';
COMMENT ON COLUMN beneficiaries.floor_earth_sand IS 'PMT: Floor earth/sand (q2_7=1)';
COMMENT ON COLUMN beneficiaries.floor_tiles IS 'PMT: Floor tiles (q2_7=7)';
COMMENT ON COLUMN beneficiaries.lighting IS 'PMT: Lighting electricity/solar (q2_32=1 or 2)';
COMMENT ON COLUMN beneficiaries.num_cattle IS 'PMT: Number of cattle (q3_1_2_1)';
COMMENT ON COLUMN beneficiaries.children_under_18 IS 'PMT: Children under 18 in household';
COMMENT ON COLUMN beneficiaries.household_size IS 'PMT: Household size (count of members)';
COMMENT ON COLUMN beneficiaries.hh_head_university IS 'PMT: Household head education university (q1_15=8,9,14)';
COMMENT ON COLUMN beneficiaries.hh_head_primary IS 'PMT: Household head education primary (q1_15=3,12)';
COMMENT ON COLUMN beneficiaries.hh_head_secondary IS 'PMT: Household head education secondary (q1_15=4,5,6,7,13)';
COMMENT ON COLUMN beneficiaries.hh_head_married IS 'PMT: Household head married (q1_5=2)';
COMMENT ON COLUMN beneficiaries.hh_head_widow IS 'PMT: Household head widow(er) (q1_5=6)';
COMMENT ON COLUMN beneficiaries.hh_head_divorced IS 'PMT: Household head divorced/separated (q1_5=4,5)';
COMMENT ON COLUMN beneficiaries.hh_head_female IS 'PMT: Household head female (q1_3=1)';
COMMENT ON COLUMN beneficiaries.district IS 'PMT: District (categorical, see 17_question_pmt_recalibrated_weights.csv)';
COMMENT ON COLUMN beneficiaries.self_employed IS 'Whether beneficiary is self-employed';
COMMENT ON COLUMN beneficiaries.hired IS 'Whether beneficiary has been hired';
COMMENT ON COLUMN beneficiaries.offline_attendance IS 'Offline training attendance (e.g. score or count)';
COMMENT ON COLUMN beneficiaries.phase1_satisfactory IS 'Phase 1 satisfactory score (e.g. 0-100)';
COMMENT ON COLUMN beneficiaries.emp_track_satisfactory IS 'Employment track satisfactory score (e.g. 0-100)';
COMMENT ON COLUMN beneficiaries.ent_track_satisfactory IS 'Entrepreneurship track satisfactory score (e.g. 0-100)';
COMMENT ON TABLE chatbot_conversations IS 'MVP: Simple message history';
COMMENT ON TABLE chatbot_results IS 'MVP: One summary result per beneficiary';
COMMENT ON TABLE activity_log IS 'MVP: Simple action tracking';

COMMENT ON FUNCTION calculate_eligibility_score IS 'MVP: Basic eligibility calculation - can be refined later';