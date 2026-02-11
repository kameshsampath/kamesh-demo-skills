<!-- COCO_INSTRUCTION: This is a shared snow-utils manifest.
     project_name: hirc-duckdb-demo
     setup_steps:
       1. Check if required skills are installed: cortex skill list
       2. For each skill in ## required_skills NOT in the list, run: cortex skill add <url>
       3. Once all skills installed, follow hirc-duckdb-demo SKILL.md "Setup from Shared Manifest Flow"
     To trigger: ask "setup from shared manifest" -->

# Snow-Utils Manifest

This manifest tracks Snowflake resources created by snow-utils skills.

---

## shared_info

shared_by: ALICE
shared_date: 2026-02-11
original_project_dir: hirc-duckdb-demo
notes: |
  HIRC DuckDB Demo - Query Snowflake Iceberg tables from DuckDB via Horizon Catalog REST API.
  To replay: open in Cortex Code, ask "setup from shared manifest"

## required_skills

hirc-duckdb-demo: https://github.com/kameshsampath/kamesh-demo-skills/hirc-duckdb-demo
snow-utils-pat: https://github.com/kameshsampath/snow-utils-skills/snow-utils-pat
snow-utils-volumes: https://github.com/kameshsampath/snow-utils-skills/snow-utils-volumes

## project_recipe

project_name: hirc-duckdb-demo

## prereqs

tools_verified: 2026-02-11
required_tools:

- snow CLI
- aws CLI (with SSO configured)
- duckdb CLI

## dependent_skills

- snow-utils-pat: https://github.com/kameshsampath/snow-utils-skills/snow-utils-pat
- snow-utils-volumes: https://github.com/kameshsampath/snow-utils-skills/snow-utils-volumes

## admin_role
hirc-duckdb-demo: ACCOUNTADMIN

<!-- START -- snow-utils-pat:ALICE_HIRC_DUCKDB_DEMO_RUNNER -->
## PAT: ALICE_HIRC_DUCKDB_DEMO_RUNNER

**Created:** 2026-02-11
**User:** ALICE_HIRC_DUCKDB_DEMO_RUNNER  # ADAPT: user-prefixed
**Role:** ALICE_HIRC_DUCKDB_DEMO_ACCESS  # ADAPT: user-prefixed
**Database:** ALICE_SNOW_UTILS  # ADAPT: user-prefixed
**PAT Name:** ALICE_HIRC_DUCKDB_DEMO_RUNNER_PAT  # ADAPT: user-prefixed
**Default Expiry (days):** 90
**Max Expiry (days):** 365
**Auth Policy:** ALICE_HIRC_DUCKDB_DEMO_RUNNER_AUTH_POLICY  # ADAPT: user-prefixed
**admin_role:** ACCOUNTADMIN
**Status:** REMOVED

| # | Type | Name | Status |
|---|------|------|--------|
| 1 | Database | ALICE_SNOW_UTILS | DONE |
| 2 | User | ALICE_HIRC_DUCKDB_DEMO_RUNNER | DONE |
| 3 | Role | ALICE_HIRC_DUCKDB_DEMO_ACCESS | DONE |
| 4 | Auth Policy | ALICE_HIRC_DUCKDB_DEMO_RUNNER_AUTH_POLICY | DONE |
| 5 | PAT | ALICE_HIRC_DUCKDB_DEMO_RUNNER_PAT | DONE |
<!-- END -- snow-utils-pat:ALICE_HIRC_DUCKDB_DEMO_RUNNER -->

<!-- START -- snow-utils-networks:ALICE_HIRC_DUCKDB_DEMO_RUNNER -->
## Network: ALICE_HIRC_DUCKDB_DEMO_RUNNER

**Created:** 2026-02-11
**Network Rule:** ALICE_HIRC_DUCKDB_DEMO_RUNNER_NETWORK_RULE  # ADAPT: user-prefixed
**Network Policy:** ALICE_HIRC_DUCKDB_DEMO_RUNNER_NETWORK_POLICY  # ADAPT: user-prefixed
**Database:** ALICE_SNOW_UTILS  # ADAPT: user-prefixed
**Schema:** NETWORKS
**Mode:** INGRESS
**Type:** IPV4
**admin_role:** ACCOUNTADMIN
**Status:** REMOVED

| # | Type | Name | Status |
|---|------|------|--------|
| 1 | Network Rule | ALICE_HIRC_DUCKDB_DEMO_RUNNER_NETWORK_RULE | DONE |
| 2 | Network Policy | ALICE_HIRC_DUCKDB_DEMO_RUNNER_NETWORK_POLICY | DONE |
| 3 | Policy Assignment | → ALICE_HIRC_DUCKDB_DEMO_RUNNER | DONE |
<!-- END -- snow-utils-networks:ALICE_HIRC_DUCKDB_DEMO_RUNNER -->

<!-- START -- snow-utils-volumes:ALICE_HIRC_DUCKDB_DEMO_VOL -->
## External Volume: ALICE_HIRC_DUCKDB_DEMO_VOL

**Created:** 2026-02-11
**Volume Name:** ALICE_HIRC_DUCKDB_DEMO_VOL  # ADAPT: user-prefixed
**S3 Bucket:** alice-hirc-duckdb-demo  # ADAPT: user-prefixed
**AWS Region:** us-west-2
**IAM Role ARN:** arn:aws:iam::123456789012:role/alice-hirc-duckdb-demo-snowflake-role  # ADAPT: user-prefixed
**admin_role:** ACCOUNTADMIN
**Status:** REMOVED

| # | Type | Name | Status |
|---|------|------|--------|
| 1 | S3 Bucket | alice-hirc-duckdb-demo | DONE |
| 2 | IAM Role | alice-hirc-duckdb-demo-role | DONE |
| 3 | IAM Policy | alice-hirc-duckdb-demo-policy | DONE |
| 4 | External Volume | ALICE_HIRC_DUCKDB_DEMO_VOL | DONE |
<!-- END -- snow-utils-volumes:ALICE_HIRC_DUCKDB_DEMO_VOL -->

<!-- START -- hirc-duckdb-demo:ALICE_HIRC_DUCKDB_DEMO -->
## HIRC DuckDB Demo: ALICE_HIRC_DUCKDB_DEMO

**Created:** 2026-02-11
**Database:** ALICE_HIRC_DUCKDB_DEMO  # ADAPT: user-prefixed
**Admin Role:** ACCOUNTADMIN
**Status:** REMOVED

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 1 | Database | ALICE_HIRC_DUCKDB_DEMO | Account | DONE |
| 2 | Grant | USAGE on DB | ALICE_HIRC_DUCKDB_DEMO → ALICE_HIRC_DUCKDB_DEMO_ACCESS | DONE |
| 3 | Iceberg Table | FRUITS (sample data) | ALICE_HIRC_DUCKDB_DEMO.PUBLIC | DONE |
| 4 | Demo Run | DuckDB query (MUST FAIL - no SELECT yet) | Step 6 | DONE |
| 5 | RBAC Grant | SELECT on FRUITS → ALICE_HIRC_DUCKDB_DEMO_ACCESS | Enables external query | DONE |
<!-- END -- hirc-duckdb-demo:ALICE_HIRC_DUCKDB_DEMO -->
