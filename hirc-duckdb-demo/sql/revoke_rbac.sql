--!jinja
-- Revoke SELECT on Iceberg table from SA_ROLE
-- Used by "Re-run demo" flow to restore the RBAC-failure state
--
-- Usage:
--   snow sql -f sql/revoke_rbac.sql \
--     --enable-templating ALL \
--     --variable admin_role=$ADMIN_ROLE \
--     --variable database_name=$DEMO_DATABASE \
--     --variable schema=PUBLIC \
--     --variable table=FRUITS \
--     --variable sa_role=$SA_ROLE

USE ROLE {{admin_role}};
REVOKE SELECT ON TABLE {{database_name}}.{{schema}}.{{table}} FROM ROLE {{sa_role}};
