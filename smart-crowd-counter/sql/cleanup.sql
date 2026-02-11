--!jinja
-- Smart Crowd Counter - Cleanup
-- Drops the demo database and all its objects (schema, stage, view)
--
-- The demo role OWNS the database, so it has the privilege to drop it.
-- No account-level admin role is needed for this phase.
--
-- Usage:
--   snow sql -f sql/cleanup.sql \
--     --enable-templating ALL \
--     --variable demo_role=$DEMO_ROLE \
--     --variable database=$DEMO_DATABASE

USE ROLE {{demo_role}};
DROP DATABASE IF EXISTS {{database}};

SELECT 'Database ' || '{{database}}' || ' dropped by ' || '{{demo_role}}' AS status;
