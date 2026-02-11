--!jinja
-- Smart Crowd Counter - Cleanup Demo Role
-- Revokes the demo role from the user and drops it.
-- Run this AFTER cleanup.sql (which drops the database).
--
-- Usage:
--   snow sql -f sql/cleanup_role.sql \
--     --enable-templating ALL \
--     --variable admin_role=$ADMIN_ROLE \
--     --variable demo_role=$DEMO_ROLE \
--     --variable snowflake_user=$SNOWFLAKE_USER

USE ROLE {{admin_role}};

REVOKE ROLE {{demo_role}} FROM USER {{snowflake_user}};
DROP ROLE IF EXISTS {{demo_role}};

SELECT 'Demo role ' || '{{demo_role}}' || ' dropped' AS status;
