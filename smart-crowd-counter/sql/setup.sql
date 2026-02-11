--!jinja
-- Smart Crowd Counter - Schema Setup
-- Creates schema, stage, and AI-powered view for image analysis
-- (Database is created by create_role.sql and owned by the demo role)
--
-- Prerequisites:
-- - Demo role must own the database (created via create_role.sql)
-- - Snowflake account with Cortex AISQL enabled
--
-- Usage:
--   snow sql -f sql/setup.sql \
--     --enable-templating ALL \
--     --variable demo_role=$DEMO_ROLE \
--     --variable database=$DEMO_DATABASE \
--     --variable schema=$DEMO_SCHEMA \
--     --variable stage=$DEMO_STAGE \
--     --variable ai_model=$AI_MODEL

USE ROLE {{demo_role}};

-- ============================================================================
-- Schema (database already exists, owned by demo_role)
-- ============================================================================

USE DATABASE {{database}};

CREATE SCHEMA IF NOT EXISTS {{schema}};

USE SCHEMA {{schema}};

-- ============================================================================
-- Stage for Image Storage
-- ============================================================================
-- Directory table enables listing files and metadata queries
-- Reference: https://docs.snowflake.com/en/sql-reference/sql/create-stage

CREATE STAGE IF NOT EXISTS {{stage}}
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
  DIRECTORY = (ENABLE = TRUE, AUTO_REFRESH = TRUE)
  COMMENT = 'Stage for conference session photos';

-- ============================================================================
-- AI-Powered View for Image Analysis
-- ============================================================================
-- This view processes images using Cortex AISQL to:
-- 1. Count total attendees in each photo
-- 2. Detect raised hands
-- 3. Generate descriptive captions
--
-- Reference: https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql

CREATE OR REPLACE VIEW SMART_CROWD_COUNTER AS
WITH image_files AS (
  -- Get all supported images from the stage directory
  SELECT
    relative_path AS name,
    TO_FILE(CONCAT('@{{database}}.{{schema}}.{{stage}}/', relative_path)) AS file,
    last_modified
  FROM DIRECTORY('@{{database}}.{{schema}}.{{stage}}')
  WHERE LOWER(relative_path) LIKE '%.jpg'
    OR LOWER(relative_path) LIKE '%.jpeg'
    OR LOWER(relative_path) LIKE '%.png'
),
processed_images AS (
  -- Analyze each image for attendee count and raised hands
  SELECT
    name,
    file,
    last_modified,
    AI_COMPLETE(
      '{{ai_model}}',
      'Analyze this image and count people and raised hands. '
      || 'Return JSON only with this exact structure: '
      || '{"total_attendees": N, "raised_hands": N, "percentage_with_hands_up": N.NN}. '
      || 'Calculate percentage as (raised_hands/total_attendees)*100, rounded to 2 decimals. '
      || 'If no people are visible, return zeros.',
      file
    ) AS attendees_count
  FROM image_files
)
SELECT
  name,
  file AS file_name,
  -- Generate caption based on filename patterns
  AI_COMPLETE(
    '{{ai_model}}',
    'Create a brief caption for a conference photo with filename: ' || name || '. '
    || 'Context: SUM=Summit, NS=Northstar, SWT=Snowflake World Tour. '
    || 'Location codes like PUNE, DELHI, MEL indicate cities. '
    || 'Format: Event Name - Location - Session. '
    || 'Add "Workshop" if filename suggests hands-on session. '
    || 'Keep it under 10 words.'
  ) AS caption,
  attendees_count AS raw,
  TRY_PARSE_JSON(attendees_count):total_attendees::INTEGER AS total_attendees,
  TRY_PARSE_JSON(attendees_count):raised_hands::INTEGER AS raised_hands,
  TRY_PARSE_JSON(attendees_count):percentage_with_hands_up::FLOAT AS percentage_with_hands_up
FROM processed_images
ORDER BY name;

-- ============================================================================
-- Verify Setup
-- ============================================================================

SHOW STAGES LIKE '{{stage}}' IN SCHEMA {{database}}.{{schema}};
SHOW VIEWS LIKE 'SMART_CROWD_COUNTER' IN SCHEMA {{database}}.{{schema}};

SELECT 'Setup complete! Upload images to stage: @{{database}}.{{schema}}.{{stage}}' AS status;
