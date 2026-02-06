-- Query Snowflake Iceberg tables with DuckDB via Horizon Catalog
--
-- Usage: 
--   set -a && source .env && set +a && envsubst < demo.sql | uv run duckdb -bail
--
-- Required env vars: DEMO_DATABASE, SNOWFLAKE_ACCOUNT_URL, SA_ROLE, SA_PAT

INSTALL iceberg;
INSTALL httpfs;
LOAD iceberg;
LOAD httpfs;

-- Create secret for PAT authentication (CLIENT_ID is empty for HIRC)
CREATE OR REPLACE SECRET snowflake_secret ( 
    TYPE iceberg, 
    CLIENT_ID '',
    CLIENT_SECRET getenv('SA_PAT'),
    OAUTH2_SERVER_URI '$SNOWFLAKE_ACCOUNT_URL/polaris/api/catalog/v1/oauth/tokens',
    OAUTH2_GRANT_TYPE 'client_credentials',
    OAUTH2_SCOPE 'session:role:$SA_ROLE'
);

-- Attach to Snowflake database via Horizon Catalog
ATTACH '$DEMO_DATABASE' AS snowflake_catalog (
    TYPE iceberg,
    SECRET snowflake_secret,
    ENDPOINT '$SNOWFLAKE_ACCOUNT_URL/polaris/api/catalog',
    SUPPORT_NESTED_NAMESPACES false
);

-- List all available tables
SHOW ALL TABLES;

-- Example query (note: Snowflake identifiers are case sensitive and should be in uppercase. Check the results from previous command)
SELECT * FROM snowflake_catalog.PUBLIC.FRUITS LIMIT 5;
