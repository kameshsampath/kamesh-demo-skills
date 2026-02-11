--!jinja
-- Smart Crowd Counter - Create Warehouse
-- Creates a warehouse for the Streamlit app and queries,
-- then grants USAGE and OPERATE to the demo role.
--
-- Usage:
--   snow sql -f sql/create_warehouse.sql \
--     --enable-templating ALL \
--     --variable admin_role=$ADMIN_ROLE \
--     --variable demo_role=$DEMO_ROLE \
--     --variable warehouse=$SNOWFLAKE_WAREHOUSE

USE ROLE {{admin_role}};

CREATE WAREHOUSE IF NOT EXISTS {{warehouse}}
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT = 'Warehouse for Smart Crowd Counter demo';

-- Grant warehouse access to demo role
GRANT USAGE ON WAREHOUSE {{warehouse}} TO ROLE {{demo_role}};
GRANT OPERATE ON WAREHOUSE {{warehouse}} TO ROLE {{demo_role}};
