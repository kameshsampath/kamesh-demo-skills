--!jinja
-- Smart Crowd Counter - Create Demo Role
-- Creates a least-privilege demo role, bootstraps the database,
-- transfers DB ownership, and grants warehouse access.
--
-- The demo role has NO account-level privileges. It only owns
-- the demo database and has USAGE on the warehouse.
--
-- Prerequisites:
-- - admin_role must be able to CREATE ROLE, CREATE DATABASE, and GRANT
--
-- Usage:
--   snow sql -f sql/create_role.sql \
--     --enable-templating ALL \
--     --variable admin_role=$ADMIN_ROLE \
--     --variable demo_role=$DEMO_ROLE \
--     --variable snowflake_user=$SNOWFLAKE_USER \
--     --variable database=$DEMO_DATABASE \
--     --variable warehouse=$SNOWFLAKE_WAREHOUSE

USE ROLE {{admin_role}};

-- ============================================================================
-- Create Demo Role
-- ============================================================================

CREATE ROLE IF NOT EXISTS {{demo_role}};
GRANT ROLE {{demo_role}} TO USER {{snowflake_user}};

-- ============================================================================
-- Create Database and Transfer Ownership
-- ============================================================================
-- The demo role owns the database and can create all schema-level objects
-- (schemas, stages, views, Streamlit apps) without any account-level grants.

CREATE DATABASE IF NOT EXISTS {{database}};
GRANT OWNERSHIP ON DATABASE {{database}} TO ROLE {{demo_role}} COPY CURRENT GRANTS;

-- ============================================================================
-- Grant Warehouse Access
-- ============================================================================
-- USAGE: allows running queries with the warehouse
-- OPERATE: allows resuming a suspended warehouse (needed for AUTO_RESUME)

GRANT USAGE ON WAREHOUSE {{warehouse}} TO ROLE {{demo_role}};
GRANT OPERATE ON WAREHOUSE {{warehouse}} TO ROLE {{demo_role}};

SELECT 'Demo role ' || '{{demo_role}}' || ' created with ownership of ' || '{{database}}' AS status;
