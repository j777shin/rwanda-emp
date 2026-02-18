-- ============================================================================
-- SURVEY TABLES FOR RWANDA EMPLOYMENT PROJECT
-- ============================================================================
-- Add survey response tracking tables to the database

-- Survey Responses Table
CREATE TABLE IF NOT EXISTS survey_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    beneficiary_id UUID NOT NULL REFERENCES beneficiaries(id) ON DELETE CASCADE,
    survey_type VARCHAR(50) NOT NULL CHECK (survey_type IN ('phase1', 'employment', 'entrepreneurship')),
    responses JSONB NOT NULL,
    completion_time INTEGER, -- in seconds
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(beneficiary_id, survey_type)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_survey_responses_beneficiary ON survey_responses(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_survey_responses_type ON survey_responses(survey_type);
CREATE INDEX IF NOT EXISTS idx_survey_responses_completed ON survey_responses(completed_at);

-- Add update timestamp trigger
CREATE TRIGGER update_survey_responses_timestamp
    BEFORE UPDATE ON survey_responses
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Comments
COMMENT ON TABLE survey_responses IS 'Stores survey responses from beneficiaries for Phase 1, Employment, and Entrepreneurship tracks';
COMMENT ON COLUMN survey_responses.survey_type IS 'Type of survey: phase1, employment, or entrepreneurship';
COMMENT ON COLUMN survey_responses.responses IS 'JSONB object containing all survey question responses';
COMMENT ON COLUMN survey_responses.completion_time IS 'Time taken to complete survey in seconds';

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================

-- Insert some sample survey responses
INSERT INTO survey_responses (beneficiary_id, survey_type, responses, completion_time)
SELECT
    b.id,
    'phase1',
    jsonb_build_object(
        'satisfaction', (ARRAY['Very Satisfied', 'Satisfied', 'Neutral', 'Dissatisfied'])[floor(random() * 4 + 1)],
        'training_quality', floor(random() * 5 + 1)::int,
        'recommend', random() > 0.2,
        'skills_improved', random() > 0.3,
        'feedback', 'Great program!'
    ),
    floor(random() * 600 + 300)::int -- 5-15 minutes
FROM beneficiaries b
WHERE b.selection_status = 'selected'
LIMIT 50
ON CONFLICT (beneficiary_id, survey_type) DO NOTHING;

-- Verify
SELECT COUNT(*) as survey_count, survey_type
FROM survey_responses
GROUP BY survey_type;
