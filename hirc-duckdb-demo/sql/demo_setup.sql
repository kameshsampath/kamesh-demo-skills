--!jinja
-- Demo database setup
-- Creates database and grants USAGE (not SELECT) to SA_ROLE
-- SA_ROLE can see database/schema but cannot query tables until rbac.sql grants SELECT
--
-- Usage:
--   snow sql -f sql/demo_setup.sql \
--     --enable-templating ALL \
--     --variable admin_role=$ADMIN_ROLE \
--     --variable database_name=$DEMO_DATABASE \
--     --variable sa_role=$SA_ROLE \
--     --variable external_volume_name=$EXTERNAL_VOLUME_NAME

USE ROLE {{admin_role}};

CREATE DATABASE IF NOT EXISTS {{database_name}};
GRANT USAGE ON DATABASE {{database_name}} TO ROLE {{sa_role}};
GRANT USAGE ON SCHEMA {{database_name}}.PUBLIC TO ROLE {{sa_role}};

ALTER DATABASE IF EXISTS {{database_name}}
  SET EXTERNAL_VOLUME = '{{external_volume_name}}';
