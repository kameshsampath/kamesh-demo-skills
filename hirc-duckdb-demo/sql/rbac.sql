--!jinja
-- Grant SELECT on Iceberg table to SA_ROLE
-- This completes the demo - SA_ROLE can now query via Horizon Catalog
--
-- Usage:
--   snow sql -f sql/rbac.sql \
--     --enable-templating ALL \
--     --variable admin_role=$ADMIN_ROLE \
--     --variable database_name=$DEMO_DATABASE \
--     --variable schema=PUBLIC \
--     --variable table=FRUITS \
--     --variable sa_role=$SA_ROLE

USE ROLE {{admin_role}};
GRANT SELECT ON TABLE {{database_name}}.{{schema}}.{{table}} TO ROLE {{sa_role}};
