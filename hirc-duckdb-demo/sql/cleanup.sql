--!jinja
-- Cleanup demo resources
-- Note: SA_ROLE, external volume, and PAT are NOT deleted - they are managed by snow-utils-* skills
--
-- Usage:
--   snow sql -f sql/cleanup.sql \
--     --enable-templating ALL \
--     --variable admin_role=$ADMIN_ROLE \
--     --variable database_name=$DEMO_DATABASE

USE ROLE {{admin_role}};
DROP DATABASE IF EXISTS {{database_name}};
