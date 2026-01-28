-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table (combined authentication and basic info)
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
    num_cows INTEGER DEFAULT 0,
    num_goats INTEGER DEFAULT 0,
    num_chickens INTEGER DEFAULT 0,
    num_sheep INTEGER DEFAULT 0,
    num_pigs INTEGER DEFAULT 0,
    num_rabbits INTEGER DEFAULT 0,
    
    -- Land & Housing
    land_ownership BOOLEAN DEFAULT FALSE,
    land_size DECIMAL(10, 2) DEFAULT 0,
    num_radio INTEGER DEFAULT 0,
    num_phone INTEGER DEFAULT 0,
    num_tv INTEGER DEFAULT 0,
    fuel VARCHAR(10) CHECK (fuel IN ('EU4', 'EU8', 'EU9')),
    water_source VARCHAR(10) CHECK (water_source IN ('WS1', 'WS2')),
    floor BOOLEAN DEFAULT FALSE,
    roof BOOLEAN DEFAULT FALSE,
    walls BOOLEAN DEFAULT FALSE,
    toilet BOOLEAN DEFAULT FALSE,
    
    -- SkillCraft & Pathways (stored directly, no separate tables for MVP)
    skillcraft_user_id VARCHAR(100),
    skillcraft_score DECIMAL(5, 2),
    skillcraft_last_sync TIMESTAMP,
    
    pathways_user_id VARCHAR(100),
    pathways_completion_rate DECIMAL(5, 2),
    pathways_last_sync TIMESTAMP,
    
    eligibility_score DECIMAL(5, 2),
    selection_status VARCHAR(20) DEFAULT 'pending' CHECK (
        selection_status IN ('pending', 'selected', 'rejected', 'waitlist')
    ),
    track VARCHAR(20) CHECK (track IN ('employment', 'entrepreneurship', 'both')),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    b.skillcraft_score,
    b.pathways_completion_rate,
    b.eligibility_score,
    b.selection_status,
    b.track,
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

-- Create admin user (password: admin123)
INSERT INTO users (email, password_hash, role) 
VALUES ('admin@rwanda-mvp.local', crypt('admin123', gen_salt('bf')), 'admin');

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
            WHEN (num_cows + num_goats + num_chickens + num_sheep + num_pigs + num_rabbits) > 20 THEN 30
            WHEN (num_cows + num_goats + num_chickens + num_sheep + num_pigs + num_rabbits) > 10 THEN 50
            WHEN (num_cows + num_goats + num_chickens + num_sheep + num_pigs + num_rabbits) > 5 THEN 70
            ELSE 100
        END +
        CASE WHEN land_ownership THEN 0 ELSE 20 END +
        CASE WHEN (floor AND roof AND walls AND toilet) THEN 0 ELSE 30 END
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
COMMENT ON TABLE chatbot_conversations IS 'MVP: Simple message history';
COMMENT ON TABLE chatbot_results IS 'MVP: One summary result per beneficiary';
COMMENT ON TABLE activity_log IS 'MVP: Simple action tracking';

COMMENT ON FUNCTION calculate_eligibility_score IS 'MVP: Basic eligibility calculation - can be refined later';