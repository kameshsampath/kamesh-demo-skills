---
name: hirc-duckdb-demo
description: "Set up Horizon Iceberg REST Catalog demo to query Snowflake Iceberg tables with DuckDB. Prerequisites: snow-utils-pat skill (which sets up infrastructure and PAT), then snow-utils-volumes which setups external volumes with defined object storage. Triggers: hirc duckdb demo, horizon catalog demo, duckdb iceberg, query iceberg duckdb, set up hirc demo, replay hirc demo, replay hirc-duckdb-demo manifest, recreate demo, export manifest for sharing, share hirc demo manifest, setup from shared manifest, replay from shared manifest, import shared manifest."
location: user
---

# Horizon Iceberg REST Catalog Demo

Query Snowflake-managed Iceberg tables with DuckDB through Horizon Catalog.

## Prerequisites

This skill depends on `snow-utils-*` skills which populate .env with:

- Connection details (SNOWFLAKE_DEFAULT_CONNECTION_NAME, ACCOUNT, USER, URL)
- Infrastructure (SA_ROLE, SNOW_UTILS_DB)
- PAT (SA_PAT) from snow-utils-pat
- External volume (EXTERNAL_VOLUME_NAME) from snow-utils-volumes

**Order of operations:**

1. Run `snow-utils-pat` first (sets up SA_ROLE, SNOW_UTILS_DB, and SA_PAT)
2. Run `snow-utils-volumes` (creates external volume using SA credentials)
3. Run this demo skill

**Credential usage:**

- **Setup SQL** (demo_setup, rbac, cleanup): Uses **user's connection** (requires admin_role from manifest)
- **Data SQL** (sample_data): Uses **admin_role** (owns all objects)
- **DuckDB queries**: Uses **SA_PAT** via Horizon Catalog REST API

## Workflow

**🚫 FORBIDDEN ACTIONS - NEVER DO THESE:**

- NEVER run SQL queries to discover/validate .env values
- NEVER use flags that bypass user interaction: `--yes`, `-y`, `--auto-setup`, `--auto-approve`, `--quiet`, `--force`, `--non-interactive`
- NEVER assume user consent - always ask and wait for explicit confirmation
- NEVER search for .env files outside the project directory
- NEVER scan user's home directory or other locations for existing files
- Trust .env - if values present, they are correct
- If values missing, direct user to prerequisite skill (don't search for files)

**✅ INTERACTIVE PRINCIPLE:** This skill is designed to be interactive. At every decision point, ASK the user and WAIT for their response before proceeding.

**🔄 RESILIENCE PRINCIPLE:** Always update the manifest IMMEDIATELY after each resource creation, not in batches. This ensures Resume Flow can recover from any interruption (user abort, network failure, etc).

Pattern:

```
1. Set overall Status: IN_PROGRESS at START of resource creation
2. Update each resource row to DONE immediately after creation
3. Set Status: COMPLETE only at the END when ALL resources done
```

If user aborts mid-flow, the manifest preserves progress:

- Overall Status stays IN_PROGRESS
- Completed resources show DONE
- Pending resources show PENDING
- Resume Flow picks up from first PENDING resource

**🛡️ IDEMPOTENCY PRINCIPLE:** Before editing any file, CHECK if the change is already applied. This prevents duplicate edit errors and improves UX.

Pattern for manifest updates:

```bash
# Check BEFORE editing
grep -q "Status.*COMPLETE" .snow-utils/snow-utils-manifest.md && echo "Already complete" || echo "Needs update"
```

Pattern for file edits:

```
1. Read current file state
2. Check if desired content already exists
3. Only edit if change is needed
4. Skip with message: "✓ Already applied: [description]"
```

**⚠️ ENVIRONMENT REQUIREMENT:** CLI tools (snow-utils-pat, snow-utils-networks, snow-utils-volumes) auto-load `.env` via `load_dotenv()`. For `snow sql`, `envsubst`, or other shell commands, always use `set -a && source .env && set +a` before running.

### Step 0: Detect or Create Project Directory

**First, check if already in a project directory:**

```bash
if [ -f .env ] && [ -d .snow-utils ]; then
  echo "✓ Detected existing project directory: $(pwd)"
  echo "  Found: .env, .snow-utils/"
  # Skip to Step 1a or Resume Flow based on manifest status
fi
```

**If existing project detected:**

- Check manifest status (`grep "Status:" .snow-utils/snow-utils-manifest.md`)
- If `IN_PROGRESS` or `DEMO_FAIL`: Use **Resume Flow** (skip to appropriate step)
- If `COMPLETE`: Inform user demo already exists, ask if they want to re-run
- If `REMOVED`: Proceed with **Replay Flow**

**If NOT in existing project, ask for directory name:**

```
Project directory for demo artifacts [default: hirc-duckdb-demo]:
```

**⚠️ STOP**: Wait for user input.

**Create project directory:**

```bash
PROJECT_DIR="${PROJECT_DIR:-hirc-duckdb-demo}"
mkdir -p "${PROJECT_DIR}"
cd "${PROJECT_DIR}"
```

> **📍 IMPORTANT:** All subsequent steps run within `${PROJECT_DIR}/`. The manifest, .env, and all artifacts live here.

### Step 0a: Initialize Manifest

**Create manifest directory and file inside project dir:**

```bash
mkdir -p .snow-utils && chmod 700 .snow-utils
if [ ! -f .snow-utils/snow-utils-manifest.md ]; then
cat > .snow-utils/snow-utils-manifest.md << 'EOF'
# Snow-Utils Manifest

This manifest tracks Snowflake resources created by snow-utils skills.

---

## project_recipe
project_name: hirc-duckdb-demo

## prereqs

## dependent_skills
snow-utils-pat: https://github.com/kameshsampath/snow-utils-skills/snow-utils-pat
snow-utils-volumes: https://github.com/kameshsampath/snow-utils-skills/snow-utils-volumes

## installed_skills
EOF
fi
chmod 600 .snow-utils/snow-utils-manifest.md
```

**📍 MANIFEST FILE:** `${PROJECT_DIR}/.snow-utils/snow-utils-manifest.md`

### Step 0b: Check Tools (Manifest-Cached)

**Check manifest for cached tool verification:**

```bash
grep "^tools_verified:" .snow-utils/snow-utils-manifest.md 2>/dev/null
```

**If `tools_verified:` exists with a date:** Skip tool checks, continue to Step 0c.

**Otherwise, check required tools:**

```bash
for t in uv snow; do command -v $t &>/dev/null && echo "$t: OK" || echo "$t: MISSING"; done
```

> **Note:** `cortex` is not checked - if this skill is running, cortex is already installed.

**If any tool is MISSING, stop and provide installation instructions:**

| Tool | Install Command |
|------|------------------|
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `snow` | `pip install snowflake-cli` or `uv tool install snowflake-cli` |

**⚠️ STOP**: Do not proceed until all prerequisites are installed.

**After all tools verified, update manifest:**

```bash
grep -q "^tools_verified:" .snow-utils/snow-utils-manifest.md || \
  sed -i '' '/^## prereqs/a\
tools_verified: '"$(date +%Y-%m-%d)"'' .snow-utils/snow-utils-manifest.md
```

### Step 0c: Check Installed Skills

**Check which skills are already installed:**

```bash
cortex skill list 2>/dev/null | grep -E "(snow-utils-pat|snow-utils-volumes)" || echo "No prereq skills found"
```

**Get dependent skills from manifest:**

```bash
grep -A10 "## dependent_skills" .snow-utils/snow-utils-manifest.md | grep -E "^snow-utils-"
```

**For each dependent skill NOT in `cortex skill list` output, ask user:**

```
Dependent skill required: snow-utils-pat
URL: https://github.com/kameshsampath/snow-utils-skills/snow-utils-pat

Install this skill? [yes/no]
```

**⚠️ STOP**: Wait for user confirmation.

**If yes:**

```bash
cortex skill add https://github.com/kameshsampath/snow-utils-skills/snow-utils-pat
```

**Update manifest installed_skills section:**

```bash
grep -q "^snow-utils-pat:" .snow-utils/snow-utils-manifest.md || \
  echo "snow-utils-pat: installed $(date +%Y-%m-%d)" >> .snow-utils/snow-utils-manifest.md
```

**Repeat for snow-utils-volumes if not installed.**

### Step 1: Setup Environment File

**Copy .env.example from skill directory:**

```bash
cp <SKILL_DIR>/.env.example .env
```

**Copy skill artifacts to project directory:**

```bash
cp <SKILL_DIR>/sql/demo.sql .
cp <SKILL_DIR>/workbook.ipynb .
cp <SKILL_DIR>/pyproject.toml .
mkdir -p sql
cp <SKILL_DIR>/sql/*.sql sql/
```

**Install Python dependencies:**

```bash
uv sync
```

### Step 1a: Check Prerequisite Values

**Check required values in .env:**

```bash
set -a && source .env && set +a

# Non-sensitive values: display normally
grep -E "^(SNOWFLAKE_DEFAULT_CONNECTION_NAME|SNOWFLAKE_ACCOUNT|SNOWFLAKE_USER|SNOWFLAKE_ACCOUNT_URL|SA_ROLE|SNOW_UTILS_DB|EXTERNAL_VOLUME_NAME)=" .env

# Sensitive values: existence check only (NEVER display SA_PAT)
grep -q "^SA_PAT=." .env && echo "SA_PAT=***REDACTED***" || echo "SA_PAT: MISSING"
```

**If SA_PAT is missing:**

```
SA_PAT is not set. Run the snow-utils-pat skill first:

  "Create a PAT for service account"

This sets up infrastructure (SA_ROLE, SNOW_UTILS_DB) and creates the PAT.
```

**⚠️ STOP** - Do not proceed until snow-utils-pat is complete and .env is updated.

**If EXTERNAL_VOLUME_NAME is missing (but SA_PAT is set):**

```
EXTERNAL_VOLUME_NAME is not set. Run the snow-utils-volumes skill:

  "Create an external volume for Iceberg"
```

**⚠️ STOP** - Do not proceed until snow-utils-volumes is complete.

**If other values are missing, list them with source skill:**

```
Missing prerequisites in .env:

| Variable | Source Skill |
|----------|--------------|
| SNOWFLAKE_DEFAULT_CONNECTION_NAME | Any snow-utils-* skill |
| SNOWFLAKE_ACCOUNT | Any snow-utils-* skill |
| SNOWFLAKE_USER | Any snow-utils-* skill |
| SNOWFLAKE_ACCOUNT_URL | Any snow-utils-* skill |
| SA_ROLE | snow-utils-pat |
| SNOW_UTILS_DB | snow-utils-pat |
| SA_PAT | snow-utils-pat |
| EXTERNAL_VOLUME_NAME | snow-utils-volumes |

Please run the prerequisite skill(s) in order:
1. snow-utils-pat (first)
2. snow-utils-volumes (after PAT is created)
```

**⚠️ STOP** - Do not proceed until prerequisites are met.

**If all present:** Continue to Step 1b.

### Step 1b: Fix Horizon Catalog URL Format

**IMPORTANT:** The Horizon Catalog API requires the org-account URL format: `<orgname>-<account_name>.snowflakecomputing.com`

See: [Snowflake Account Identifiers](https://docs.snowflake.com/en/user-guide/admin-account-identifier)

**Query Snowflake and construct correct URL:**

```bash
set -a && source .env && set +a
ORG_ACCOUNT=$(snow sql -c ${SNOWFLAKE_DEFAULT_CONNECTION_NAME} -q "SELECT LOWER(CURRENT_ORGANIZATION_NAME()) || '-' || LOWER(CURRENT_ACCOUNT_NAME()) as org_account" --format json 2>/dev/null | jq -r '.[0].ORG_ACCOUNT')
HORIZON_URL="https://${ORG_ACCOUNT}.snowflakecomputing.com"
echo "Horizon Catalog URL: ${HORIZON_URL}"
```

**Always write correct format back to .env:**

```bash
sed -i '' "s|^SNOWFLAKE_ACCOUNT_URL=.*|SNOWFLAKE_ACCOUNT_URL=${HORIZON_URL}|" .env
source .env
echo "SNOWFLAKE_ACCOUNT_URL set to: ${SNOWFLAKE_ACCOUNT_URL}"
```

> **Why this matters:** The legacy locator format (e.g., `sfdevrel_enterprise`) is missing the org prefix and doesn't work with Horizon Catalog OAuth. The org-account format (e.g., `sfdevrel-sfdevrel_enterprise`) is required.

### Step 2: Set Demo-Specific Values

**Read SNOWFLAKE_USER from .env and compute default database name:**

```bash
set -a && source .env && set +a
PROJECT_NAME=$(basename $(pwd) | tr '[:lower:]' '[:upper:]' | tr '-' '_')
DEFAULT_DB_NAME="${SNOWFLAKE_USER:-$USER}_${PROJECT_NAME}"
echo "Computed default: ${DEFAULT_DB_NAME}"
# e.g., hirc-duckdb-demo → ALICE_HIRC_DUCKDB_DEMO
```

**Ask user with computed default (allow them to accept or change):**

```
Demo database name [${DEFAULT_DB_NAME}]: 
```

**⚠️ STOP**: Wait for user input. If user presses Enter, use the default. If user types a name, use their input.

**Update .env with confirmed values:**

```bash
grep -q "^DEMO_DATABASE=" .env && \
  sed -i '' 's/^DEMO_DATABASE=.*/DEMO_DATABASE='"${DEMO_DATABASE}"'/' .env || \
  echo "DEMO_DATABASE=${DEMO_DATABASE}" >> .env
```

### Step 2a: Admin Role from Manifest

**Purpose:** Demo setup requires elevated privileges. Get admin_role from manifest (NOT .env).

**Check manifest for existing admin_role from any skill:**

```bash
grep -A10 "## admin_role" .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -E "^[a-z_-]+:" | head -1
```

**If admin_role exists for any skill (pat, networks, volumes):**

```
Found existing admin_role in manifest: <EXISTING_ROLE> (from <skill_name>)

Reuse this admin_role for hirc-duckdb-demo? [yes/no]
```

**If yes:** Use existing role, add entry for hirc-duckdb-demo pointing to same role.

**If NO admin_role exists anywhere, prompt:**

```
Demo setup requires these privileges:
  - CREATE DATABASE (Account)
  - GRANT privileges (Account)

Snowflake recommends: ACCOUNTADMIN (has all privileges by default)

Enter admin role for this demo [ACCOUNTADMIN]: 
```

**⚠️ STOP**: Wait for user input.

**Write to manifest (admin_role is ONLY stored in manifest, NOT in .env):**

```bash
if ! grep -q "## admin_role" .snow-utils/snow-utils-manifest.md; then
cat >> .snow-utils/snow-utils-manifest.md << 'EOF'

## admin_role
EOF
fi
grep -q "^hirc-duckdb-demo:" .snow-utils/snow-utils-manifest.md && \
  sed -i '' 's/^hirc-duckdb-demo:.*/hirc-duckdb-demo: '"${ADMIN_ROLE}"'/' .snow-utils/snow-utils-manifest.md || \
  echo "hirc-duckdb-demo: ${ADMIN_ROLE}" >> .snow-utils/snow-utils-manifest.md
```

**Read admin_role from manifest for subsequent steps:**

```bash
ADMIN_ROLE=$(grep -A10 "## admin_role" .snow-utils/snow-utils-manifest.md | grep "^hirc-duckdb-demo:" | cut -d: -f2 | tr -d ' ')
```

### Step 3: Confirm Settings

**Display configuration summary:**

```
Configuration Summary:
─────────────────────
Project Directory: ${PROJECT_DIR}
Connection: ${SNOWFLAKE_DEFAULT_CONNECTION_NAME}
Account: ${SNOWFLAKE_ACCOUNT}
User: ${SNOWFLAKE_USER}

Demo Settings:
─────────────────────
Demo Database: ${DEMO_DATABASE}
Admin Role: ${ADMIN_ROLE} (from manifest)

Prerequisites (from snow-utils):
─────────────────────
External Volume: ${EXTERNAL_VOLUME_NAME}
Service Role: ${SA_ROLE}
Utils Database: ${SNOW_UTILS_DB}

Proceed with these settings?
```

**⚠️ STOP**: Wait for user confirmation.

### Step 4: Create Demo Database

**Display SQL Preview (inline, not via bash to avoid truncation):**

```
╔══════════════════════════════════════════════════════════════════╗
║              📋 SQL TO BE EXECUTED (demo_setup.sql)              ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  USE ROLE ${ADMIN_ROLE};                                         ║
║                                                                  ║
║  CREATE DATABASE IF NOT EXISTS ${DEMO_DATABASE};                 ║
║  GRANT USAGE ON DATABASE ${DEMO_DATABASE} TO ROLE ${SA_ROLE};    ║
║  GRANT USAGE ON SCHEMA ${DEMO_DATABASE}.PUBLIC TO ROLE ${SA_ROLE};║
║                                                                  ║
║  ALTER DATABASE IF EXISTS ${DEMO_DATABASE}                       ║
║    SET EXTERNAL_VOLUME = '${EXTERNAL_VOLUME_NAME}';              ║
║                                                                  ║
║  NOTE: Grants USAGE only (not SELECT) - can see but not query    ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Note:** Display this box with actual variable values substituted from .env

**⚠️ STOP**: Show preview to user and get approval before executing.

**Execute (uses user's connection - requires admin_role):**

```bash
set -a && source .env && set +a && snow sql -c ${SNOWFLAKE_DEFAULT_CONNECTION_NAME} \
  -f sql/demo_setup.sql \
  --enable-templating ALL \
  --variable admin_role=${ADMIN_ROLE} \
  --variable database_name=${DEMO_DATABASE} \
  --variable sa_role=${SA_ROLE} \
  --variable external_volume_name=${EXTERNAL_VOLUME_NAME}
```

**Update manifest (IN_PROGRESS):**

```markdown
<!-- START -- hirc-duckdb-demo:{DEMO_DATABASE} -->
## HIRC DuckDB Demo: {DEMO_DATABASE}

**Created:** {TIMESTAMP}
**Database:** {DEMO_DATABASE}
**Admin Role:** {ADMIN_ROLE}
**Status:** IN_PROGRESS

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 1 | Database | {DEMO_DATABASE} | Account | DONE |
| 2 | Grant | USAGE on DB | {DEMO_DATABASE} → {SA_ROLE} | DONE |
| 3 | Iceberg Table | FRUITS (sample data) | {DEMO_DATABASE}.PUBLIC | PENDING |
| 4 | RBAC Grant | SELECT on FRUITS → {SA_ROLE} | Enables external query | PENDING |
<!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->
```

### Step 5: Create Iceberg Table and Load Data

**Display SQL Preview (inline, not via bash to avoid truncation):**

```
╔══════════════════════════════════════════════════════════════════╗
║           📋 LOADING SAMPLE DATA (sample_data.sql)               ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  USE ROLE ${ADMIN_ROLE};                                         ║
║  USE DATABASE ${DEMO_DATABASE};                                  ║
║  USE SCHEMA PUBLIC;                                              ║
║                                                                  ║
║  CREATE OR REPLACE ICEBERG TABLE fruits (                        ║
║      id INT, name VARCHAR, color VARCHAR,                        ║
║      price DECIMAL(10,2), in_stock BOOLEAN                       ║
║  )                                                               ║
║      CATALOG = 'SNOWFLAKE'                                       ║
║      EXTERNAL_VOLUME = '${EXTERNAL_VOLUME_NAME}'                 ║
║      BASE_LOCATION = 'fruits/';                                  ║
║                                                                  ║
║  INSERT INTO fruits (id, name, color, price, in_stock)           ║
║  VALUES (1, 'Apple', 'Red', 1.50, TRUE), ...                     ║
║         (10 rows total)                                          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Note:** Display this box with actual variable values substituted from .env

**⚠️ STOP**: Show preview to user and get approval before executing.

**Execute (uses admin_role - owns the database and table):**

```bash
set -a && source .env && set +a && snow sql -c ${SNOWFLAKE_DEFAULT_CONNECTION_NAME} \
  -f sql/sample_data.sql \
  --enable-templating ALL \
  --variable admin_role=${ADMIN_ROLE} \
  --variable database_name=${DEMO_DATABASE} \
  --variable external_volume_name=${EXTERNAL_VOLUME_NAME}
```

> **Note:** admin_role creates and owns the table. SA_ROLE only has USAGE on database/schema (no SELECT yet).

**Update manifest:** Mark "Iceberg Table" as DONE.

### Step 6: Run Demo (Expect Failure!)

**Display "What We're About To Run" to user:**

```
╔══════════════════════════════════════════════════════════════════╗
║           ⏳ RUNNING DUCKDB DEMO - EXPECT FAILURE!               ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ✅ Iceberg table FRUITS created successfully.                   ║
║                                                                  ║
║  📋 WHAT WE'RE ABOUT TO RUN:                                     ║
║  ─────────────────────────────────────────────────────────────── ║
║  DuckDB query via Horizon Iceberg REST Catalog:                  ║
║                                                                  ║
║    SELECT * FROM ${DEMO_DATABASE}.PUBLIC.FRUITS LIMIT 5          ║
║                                                                  ║
║  Authentication:                                                 ║
║    • OAuth2 client credentials via SA_PAT                        ║
║    • Token scope: session:role:${SA_ROLE}                        ║
║    • Catalog: ${SNOWFLAKE_ACCOUNT_URL}/polaris/api/catalog       ║
║                                                                  ║
║  🎯 THIS SHOULD FAIL because ${SA_ROLE} has:                     ║
║     ✓ USAGE on database (can see it)                             ║
║     ✓ USAGE on schema (can navigate)                             ║
║     ✗ NO SELECT on table (cannot read data)                      ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

**Run the DuckDB demo:**

```bash
set -a && source .env && set +a && envsubst < sql/demo.sql | uv run duckdb -bail
```

**Check the result:**

- **If FAILED (expected):** Continue to Step 6a (explain why)
- **If SUCCEEDED (unexpected):** SELECT grant already exists - skip to Step 8 summary

**Expected error (one of these):**

```
Catalog Error: Table with name FRUITS does not exist!
```

or

```
Forbidden: Role ... does not have permission to access table PUBLIC.FRUITS
```

> **Note:** Horizon Catalog may show "table does not exist" rather than "permission denied" -
> this is more secure as it doesn't leak that the table exists.

**⚠️ STOP**: Show user the result and explain (Step 6a if failed, Step 8 if succeeded).

**Update manifest status to DEMO_FAIL (if failed):**

```markdown
**Status:** DEMO_FAIL
```

### Step 6a: Why Did It Fail? (Interactive Learning)

**Display the failure explanation to the user:**

```
╔══════════════════════════════════════════════════════════════════╗
║                 🔴 DEMO FAILED (AS EXPECTED!)                    ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ❌ ERROR MESSAGE:                                               ║
║  ─────────────────────────────────────────────────────────────── ║
║  "Catalog Error: Table with name FRUITS does not exist!"         ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  🔒 WHY "DOES NOT EXIST" INSTEAD OF "PERMISSION DENIED"?         ║
║  ─────────────────────────────────────────────────────────────── ║
║  Horizon Catalog is MORE SECURE - it doesn't reveal whether      ║
║  a table exists if you can't access it. This prevents            ║
║  information leakage about your database structure.              ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  🎯 ROOT CAUSE:                                                  ║
║  ─────────────────────────────────────────────────────────────── ║
║  The service account role (${SA_ROLE}) has:                      ║
║                                                                  ║
║    ✓ USAGE on database ${DEMO_DATABASE}                          ║
║    ✓ USAGE on schema PUBLIC                                      ║
║    ✗ NO SELECT on table FRUITS ← Table invisible without this!   ║
║                                                                  ║
║  SNOWFLAKE RBAC HIERARCHY:                                       ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │ USAGE grants → "see" database/schema (navigate)             │ ║
║  │ SELECT grants → "see and read" tables/views                 │ ║
║  │ Without SELECT, tables are INVISIBLE via Horizon Catalog    │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                  ║
║  When external engines (DuckDB, Spark, Trino) query via the      ║
║  Horizon Catalog REST API, they use the service account's role.  ║
║  That role needs explicit SELECT grants on each table.           ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  📚 LEARN MORE (Snowflake Docs):                                 ║
║  • Access Control Privileges:                                    ║
║    https://docs.snowflake.com/en/user-guide/security-access-     ║
║    control-privileges                                            ║
║  • Horizon Catalog Overview:                                     ║
║    https://docs.snowflake.com/en/user-guide/tables-iceberg-      ║
║    open-catalog                                                  ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ➡️  NEXT STEP:                                                  ║
║  ─────────────────────────────────────────────────────────────── ║
║  Grant SELECT permission to the service account role:            ║
║                                                                  ║
║    GRANT SELECT ON TABLE ${DEMO_DATABASE}.PUBLIC.FRUITS          ║
║      TO ROLE ${SA_ROLE};                                         ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

**Ask user:** "Ready to grant SELECT permission and fix this?"

**⚠️ STOP**: Wait for user confirmation.

### Step 7: Grant Access (RBAC)

**Display SQL Preview (inline, not via bash to avoid truncation):**

```
╔══════════════════════════════════════════════════════════════════╗
║              📋 SQL TO BE EXECUTED (rbac.sql)                    ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  USE ROLE ${ADMIN_ROLE};                                         ║
║  GRANT SELECT ON TABLE ${DEMO_DATABASE}.PUBLIC.FRUITS            ║
║    TO ROLE ${SA_ROLE};                                           ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Note:** Display this box with actual variable values substituted from .env

**⚠️ STOP**: Show preview to user and get approval before executing.

**Execute (uses user's connection - requires admin_role):**

```bash
set -a && source .env && set +a && snow sql -c ${SNOWFLAKE_DEFAULT_CONNECTION_NAME} \
  -f sql/rbac.sql \
  --enable-templating ALL \
  --variable admin_role=${ADMIN_ROLE} \
  --variable database_name=${DEMO_DATABASE} \
  --variable schema=PUBLIC \
  --variable table=FRUITS \
  --variable sa_role=${SA_ROLE}
```

**Update manifest:** Mark "RBAC Grant: SELECT on FRUITS" as DONE.

### Step 8: Run Demo Again (Success!)

**Run the DuckDB demo again:**

```bash
set -a && source .env && set +a && envsubst < sql/demo.sql | uv run duckdb -bail
```

**Display success to user:**

```
╔══════════════════════════════════════════════════════════════════╗
║                    🟢 DEMO SUCCEEDED!                            ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  📋 WHAT WE RAN:                                                 ║
║  ─────────────────────────────────────────────────────────────── ║
║  DuckDB query via Horizon Iceberg REST Catalog:                  ║
║                                                                  ║
║    SELECT * FROM ${DEMO_DATABASE}.PUBLIC.FRUITS                  ║
║                                                                  ║
║  Authentication:                                                 ║
║    • OAuth2 client credentials flow                              ║
║    • Token scope: session:role:${SA_ROLE}                        ║
║    • Catalog URL: ${SNOWFLAKE_ACCOUNT_URL}/polaris/api/catalog   ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ✅ QUERY RESULTS (sample rows):                                 ║
║  ─────────────────────────────────────────────────────────────── ║
║                                                                  ║
║  ┌───────┬────────────┬─────────┬───────────┬──────────┐         ║
║  │  id   │   name     │  color  │   price   │ in_stock │         ║
║  │ int32 │  varchar   │ varchar │ decimal() │ boolean  │         ║
║  ├───────┼────────────┼─────────┼───────────┼──────────┤         ║
║  │   1   │ Apple      │ Red     │      1.50 │ true     │         ║
║  │   2   │ Banana     │ Yellow  │      0.75 │ true     │         ║
║  │   3   │ Orange     │ Orange  │      2.00 │ true     │         ║
║  │   4   │ Grape      │ Purple  │      3.50 │ true     │         ║
║  │   5   │ Mango      │ Yellow  │      2.50 │ false    │         ║
║  └───────┴────────────┴─────────┴───────────┴──────────┘         ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  🎯 WHY IT WORKED:                                               ║
║  ─────────────────────────────────────────────────────────────── ║
║  The service account role (${SA_ROLE}) now has:                  ║
║                                                                  ║
║    ✓ USAGE on database ${DEMO_DATABASE}                          ║
║    ✓ USAGE on schema PUBLIC                                      ║
║    ✓ SELECT on table FRUITS  ← Added in Step 7!                  ║
║                                                                  ║
║  External engines (DuckDB, Spark, Trino) can now query via       ║
║  the Horizon Catalog REST API using this role.                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

**Update manifest status to DEMO_SUCCESS:**

```markdown
**Status:** DEMO_SUCCESS
```

### Step 9: Verify & Summary

**Update manifest to COMPLETE:**

```markdown
<!-- START -- hirc-duckdb-demo:{DEMO_DATABASE} -->
## HIRC DuckDB Demo: {DEMO_DATABASE}

**Created:** {TIMESTAMP}
**Database:** {DEMO_DATABASE}
**Admin Role:** {ADMIN_ROLE}
**Status:** COMPLETE

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 1 | Database | {DEMO_DATABASE} | Account | DONE |
| 2 | Grant | USAGE on DB | {DEMO_DATABASE} → {SA_ROLE} | DONE |
| 3 | Iceberg Table | FRUITS (sample data) | {DEMO_DATABASE}.PUBLIC | DONE |
| 4 | RBAC Grant | SELECT on FRUITS → {SA_ROLE} | Enables external query | DONE |

### Cleanup Instructions

```bash
set -a && source .env && set +a && snow sql -c ${SNOWFLAKE_DEFAULT_CONNECTION_NAME} \
  -f sql/cleanup.sql --enable-templating ALL \
  --variable admin_role=${ADMIN_ROLE} \
  --variable database_name=${DEMO_DATABASE}
```
<!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->
```

**Display summary:**

```

╔══════════════════════════════════════════════════════════════════╗
║              HIRC DuckDB Demo - Setup Complete!                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  PROJECT DIRECTORY: ${PROJECT_DIR}                               ║
║                                                                  ║
║  SNOWFLAKE OBJECTS CREATED:                                      ║
║    Database:      ${DEMO_DATABASE}                               ║
║    Iceberg Table: ${DEMO_DATABASE}.PUBLIC.FRUITS                 ║
║                                                                  ║
║  REUSED FROM SNOW-UTILS:                                         ║
║    External Volume: ${EXTERNAL_VOLUME_NAME}                      ║
║    Service Role:    ${SA_ROLE}                                   ║
║    Utils Database:  ${SNOW_UTILS_DB}                             ║
║                                                                  ║
║  RUN THE DEMO (from project dir):                                ║
║    cd ${PROJECT_DIR}                                             ║
║                                                                  ║
║    DuckDB CLI:                                                   ║
║      set -a && source .env && set +a && \                        ║
║      envsubst < sql/demo.sql | uv run duckdb -bail                   ║
║                                                                  ║
║    Jupyter:                                                      ║
║      uv run jupyter notebook workbook.ipynb                      ║
║                                                                  ║
║  MANIFEST: ${PROJECT_DIR}/.snow-utils/snow-utils-manifest.md     ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

```

## Export for Sharing Flow

**Trigger phrases:** "export manifest for sharing", "share hirc demo manifest"

**Purpose:** Create a portable copy of the manifest that another developer (Bob) can use to replay the entire setup on their machine.

### Precondition

Cortex Code MUST verify ALL skill sections have `Status: COMPLETE`:

```bash
# Check all sections
grep "^\*\*Status:\*\*" .snow-utils/snow-utils-manifest.md
```

If any section is not COMPLETE, refuse with a clear listing of which sections need attention.

### Export Steps

1. **Read active manifest** from `.snow-utils/snow-utils-manifest.md`
2. **Read `project_name`** from `## project_recipe` section
3. **Determine `shared_by`** from `SNOWFLAKE_USER` in `.env` (fall back to asking user)
4. **Ask user for export location:**

```
Export manifest for sharing:

  Filename: {project_name}-manifest.md
  Default location: ./ (project root)

Save to [./]: 
```

**⚠️ STOP**: Wait for user input.

5. **If file already exists at target:** Ask overwrite / rename with timestamp / cancel

6. **Create export file** with these transformations:
   - Inject enriched `<!-- COCO_INSTRUCTION -->` at top (see format below)
   - Add `## shared_info` section after `# Snow-Utils Manifest` header
   - Add `## required_skills` section after `## shared_info` (see format below)
   - Change ALL `**Status:** COMPLETE` to `**Status:** REMOVED`
   - Add `# ADAPT: user-prefixed` to values containing the user's prefix
   - Remove `### Cleanup Instructions` subsections (not relevant for recipient)

   **COCO_INSTRUCTION format (inject at top of exported file):**

   ```markdown
   <!-- COCO_INSTRUCTION: This is a shared snow-utils manifest.
        project_name: {project_name}
        setup_steps:
          1. Check if required skills are installed: cortex skill list
          2. For each skill in ## required_skills NOT in the list, run: cortex skill add <url>
          3. Once all skills installed, follow hirc-duckdb-demo SKILL.md "Setup from Shared Manifest Flow"
        To trigger: ask "setup from shared manifest" -->
   ```

   **required_skills section (inject after shared_info):**

   ```markdown
   ## required_skills
   hirc-duckdb-demo: https://github.com/kameshsampath/kamesh-demo-skills/hirc-duckdb-demo
   snow-utils-pat: https://github.com/kameshsampath/snow-utils-skills/snow-utils-pat
   snow-utils-volumes: https://github.com/kameshsampath/snow-utils-skills/snow-utils-volumes
   ```

   > **Note:** `required_skills` includes ALL skills needed to replay, including the demo skill itself. This enables self-installation from a vanilla Cortex Code with no skills pre-installed.

7. **Show confirmation:**

```
Exported: hirc-duckdb-demo-manifest.md

  Location: ./hirc-duckdb-demo-manifest.md
  Shared by: {SNOWFLAKE_USER}
  Sections: snow-utils-pat, snow-utils-networks, snow-utils-volumes, hirc-duckdb-demo
  All statuses set to: REMOVED
  ADAPT markers added for user-prefixed values

Share this file with your colleague. They can open it in Cursor and ask Cortex Code:
  "setup from shared manifest"
```

> **Note:** The exported file is in the project root, NOT in `.snow-utils/`. Skills only read from `.snow-utils/snow-utils-manifest.md` so the export is invisible to all skill flows.

### Setup from Shared Manifest Flow

**Trigger phrases:** "setup from shared manifest", "replay from shared manifest", "import shared manifest"

When Cortex Code detects a shared manifest (file with `## shared_info` section or `<!-- COCO_INSTRUCTION -->` comment):

1. **Check and install required skills (self-install):**

   ```bash
   # Get list of installed skills
   cortex skill list 2>/dev/null
   ```

   **Read `## required_skills` section from the manifest:**

   ```bash
   grep -A20 "^## required_skills" <manifest_file> | grep -E "^[a-z].*:" | while read line; do
     skill=$(echo "$line" | cut -d: -f1)
     url=$(echo "$line" | cut -d' ' -f2)
     echo "$skill -> $url"
   done
   ```

   **For each skill NOT in `cortex skill list` output, ask user:**

   ```
   Required skill not installed: hirc-duckdb-demo
   URL: https://github.com/kameshsampath/kamesh-demo-skills/hirc-duckdb-demo

   Install this skill? [yes/no]
   ```

   **⚠️ STOP**: Wait for user confirmation for each missing skill.

   **If yes:** Run `cortex skill add <url>`.

   > **Why self-install matters:** This enables zero-to-hero bootstrapping. Bob receives a manifest, opens it in Cursor, and Cortex Code installs ALL required skills (including the demo skill itself) before proceeding. No manual `cortex skill add` needed.

2. **Read `project_name`** from `## project_recipe`
3. **Ask Bob:**

```
This is a shared manifest for project: hirc-duckdb-demo

Options:
1. Create project directory: ./hirc-duckdb-demo (recommended)
2. Use current directory
3. Specify a custom directory name
```

**⚠️ STOP**: Wait for user input.

4. **If target dir already has a manifest:** Offer backup (.bak) / abort / different directory
5. **Create directory + `.snow-utils/`**, move manifest to `.snow-utils/snow-utils-manifest.md`
6. **Proceed to Replay Flow** (step 3 below handles .env reconstruction and name adaptation)

---

## Cleanup Flow

**Trigger phrases:** "cleanup hirc demo", "remove hirc demo", "delete demo database"

**IMPORTANT:** This is the **hirc-duckdb-demo** skill. Only cleanup sections marked `<!-- START -- hirc-duckdb-demo:* -->`.

1. **Read manifest:**

   ```bash
   cat .snow-utils/snow-utils-manifest.md 2>/dev/null
   ```

1. **Find section using unique markers:**

   Look for the block between:

   ```
   <!-- START -- hirc-duckdb-demo:{DEMO_DATABASE} -->
   ...
   <!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->
   ```

   **Extract variables from the section:**
   - `DEMO_DATABASE` from `**Database:** {value}`
   - `ADMIN_ROLE` from `**Admin Role:** {value}`

2. **Display SQL Preview (inline, not via bash to avoid truncation):**

   ```
   ╔══════════════════════════════════════════════════════════════════╗
   ║              📋 SQL TO BE EXECUTED (cleanup.sql)                 ║
   ╠══════════════════════════════════════════════════════════════════╣
   ║                                                                  ║
   ║  USE ROLE ${ADMIN_ROLE};                                         ║
   ║  DROP DATABASE IF EXISTS ${DEMO_DATABASE};                       ║
   ║                                                                  ║
   ║  NOTE: SA_ROLE, external volume, and PAT are NOT deleted -       ║
   ║        they are managed by snow-utils-* skills                   ║
   ║                                                                  ║
   ╚══════════════════════════════════════════════════════════════════╝
   ```

   > **Note:** Display this box with actual variable values substituted

3. **Show cleanup confirmation:**

   ```
   Will remove: Database ${DEMO_DATABASE} and all its tables
   
   Command from manifest:
   set -a && source .env && set +a && snow sql -c ${SNOWFLAKE_DEFAULT_CONNECTION_NAME} \
     -f sql/cleanup.sql --enable-templating ALL \
     --variable admin_role=${ADMIN_ROLE} \
     --variable database_name=${DEMO_DATABASE}
   
   Proceed? [yes/no]
   ```

   **⚠️ STOP**: Wait for user confirmation.

4. **On confirmation:** Execute cleanup

5. **Update manifest section using unique markers:**

   **IMPORTANT:** Do NOT delete the manifest file. Update the status to REMOVED so the demo can be replayed later.

   **CRITICAL:** Use the full unique block markers for replacement to avoid "found N times" errors:

   ```
   old_string: <!-- START -- hirc-duckdb-demo:{DEMO_DATABASE} -->
   ... (entire existing block) ...
   <!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->
   
   new_string: <!-- START -- hirc-duckdb-demo:{DEMO_DATABASE} -->
   ## HIRC DuckDB Demo: {DEMO_DATABASE}
   
   **Created:** {original_timestamp}
   **Removed:** {current_timestamp}
   **Database:** {DEMO_DATABASE}
   **Admin Role:** {ADMIN_ROLE}
   **Status:** REMOVED
   
   | # | Type | Name | Location | Status |
   |---|------|------|----------|--------|
   | 1 | Database | {DEMO_DATABASE} | Account | REMOVED |
   | 2 | Grant | USAGE on DB | {DEMO_DATABASE} → {SA_ROLE} | REMOVED |
   | 3 | Iceberg Table | FRUITS (sample data) | {DEMO_DATABASE}.PUBLIC | REMOVED |
   | 4 | RBAC Grant | SELECT on FRUITS → {SA_ROLE} | Enables external query | REMOVED |
   <!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->
   ```

## Replay Flow

**Trigger phrases:** "replay hirc demo", "replay hirc-duckdb-demo manifest", "recreate demo"

**IMPORTANT:** This is the **hirc-duckdb-demo** skill. Only replay sections marked `<!-- START -- hirc-duckdb-demo:* -->`.

1. **Read manifest:**

   ```bash
   cat .snow-utils/snow-utils-manifest.md 2>/dev/null
   ```

2. **Check required skills installed:**

   ```bash
   cortex skill list 2>/dev/null | grep -E "(snow-utils-pat|snow-utils-volumes)"
   ```

   **Read skill URLs from `## required_skills` (if present) or `## dependent_skills` section:**

   ```bash
   grep -A20 "^## required_skills" .snow-utils/snow-utils-manifest.md | grep -E "^snow-utils-" || \
   grep -A10 "^## dependent_skills" .snow-utils/snow-utils-manifest.md | grep -E "^snow-utils-"
   ```

   **For each dependency skill not installed, ask user:**

   ```
   Required skill not installed: snow-utils-pat
   URL: https://github.com/kameshsampath/snow-utils-skills/snow-utils-pat

   Install this skill? [yes/no]
   ```

   **If yes:** Run `cortex skill add <skill_url>`.

3. **Reconstruct .env (if missing or incomplete):**

   > **Portable Manifest:** When replaying from a shared manifest, `.env` may not exist. Reconstruct it from the manifest + one user input.

   ```bash
   # Check if .env exists and has connection details
   grep -q "^SNOWFLAKE_DEFAULT_CONNECTION_NAME=." .env 2>/dev/null || echo "NEEDS_SETUP"
   ```

   **If NEEDS_SETUP (no .env or missing connection):**

   a. Copy `.env.example` from skill directory:

      ```bash
      cp <SKILL_DIR>/.env.example .env
      ```

   b. Ask user: "Which Snowflake connection?" then:

      ```bash
      snow connection list
      ```

      **⚠️ STOP**: Wait for user to select a connection.

   c. Test connection and extract details:

      ```bash
      snow connection test -c <selected_connection> --format json
      ```

      Write to .env: `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_ACCOUNT_URL`

   d. **Infer from manifest sections** (extract `**Field:**` values):

      ```bash
      # From snow-utils-pat section
      SA_USER=$(grep -A30 "<!-- START -- snow-utils-pat" .snow-utils/snow-utils-manifest.md | grep "^\*\*User:\*\*" | head -1 | sed 's/\*\*User:\*\* //')
      SA_ROLE=$(grep -A30 "<!-- START -- snow-utils-pat" .snow-utils/snow-utils-manifest.md | grep "^\*\*Role:\*\*" | head -1 | sed 's/\*\*Role:\*\* //')
      SNOW_UTILS_DB=$(grep -A30 "<!-- START -- snow-utils-pat" .snow-utils/snow-utils-manifest.md | grep "^\*\*Database:\*\*" | head -1 | sed 's/\*\*Database:\*\* //')

      # From snow-utils-volumes section (resource table)
      EXTERNAL_VOLUME_NAME=$(grep -A30 "<!-- START -- snow-utils-volumes" .snow-utils/snow-utils-manifest.md | grep "External Volume" | grep -o '[A-Z_]*EXTERNAL_VOLUME' | head -1)

      # From hirc-duckdb-demo section
      DEMO_DATABASE=$(grep -A30 "<!-- START -- hirc-duckdb-demo" .snow-utils/snow-utils-manifest.md | grep "^\*\*Database:\*\*" | head -1 | sed 's/\*\*Database:\*\* //')
      ADMIN_ROLE=$(grep -A30 "<!-- START -- hirc-duckdb-demo" .snow-utils/snow-utils-manifest.md | grep "^\*\*Admin Role:\*\*" | head -1 | sed 's/\*\*Admin Role:\*\* //')
      ```

   e. **Validate extracted values** (grep validation):

      ```bash
      # Validate critical values were extracted
      for var in SA_USER SA_ROLE SNOW_UTILS_DB EXTERNAL_VOLUME_NAME DEMO_DATABASE; do
        val=$(eval echo \$$var)
        if [ -z "$val" ]; then
          echo "WARNING: Could not extract ${var} from manifest. Check manifest format."
        fi
      done
      ```

      If any value is empty, ask user: "Some values couldn't be extracted. Enter them manually?" If yes, prompt for each. If no, abort replay.

   f. **Detect shared manifest and offer name adaptation:**

      If manifest contains `# ADAPT: user-prefixed` markers:

      ```bash
      grep -q "# ADAPT:" .snow-utils/snow-utils-manifest.md && echo "SHARED_MANIFEST"
      ```

      If SHARED_MANIFEST detected, extract `shared_by` from `## shared_info` section and Bob's `SNOWFLAKE_USER` from `.env`. If prefixes differ, show **combined summary + adaptation screen** (see BEST_PRACTICES "Name Adaptation During Replay"). One screen, one confirmation with three options: confirm all, edit specific value, keep originals.

      If NOT a shared manifest (no `# ADAPT`): skip adaptation.

   g. Write all values (adapted or original) to `.env`:

      ```bash
      # Update .env with inferred values (only if not already set)
      for var in SA_USER SA_ROLE SNOW_UTILS_DB EXTERNAL_VOLUME_NAME DEMO_DATABASE; do
        val=$(eval echo \$$var)
        [ -n "$val" ] && (grep -q "^${var}=" .env && \
          sed -i '' "s/^${var}=.*/${var}=${val}/" .env || \
          echo "${var}=${val}" >> .env)
      done
      ```

   f. **Create fresh PAT (pre-populated from manifest):**

      SA_PAT is a secret — never stored in manifest. But the creation command is **pre-populated from manifest values** so the user only confirms, not re-answers questions.

      > **⚠️ Dependency Skill Ownership:** Only pass identity values (`SA_USER`, `SA_ROLE`, `SNOW_UTILS_DB`) to the PAT skill.
      > PAT-specific parameters (expiry settings, auth policy config) are owned by `snow-utils-pat` and handled by its CLI defaults or its own manifest section. Do NOT duplicate them here.

      **Show pre-populated summary:**

      ```
      ⚠️ SA_PAT must be created fresh (secret — never stored in manifest).

      Pre-populated from manifest:
        Service User: {SA_USER}           (from manifest)
        PAT Role:     {SA_ROLE}           (from manifest)
        Database:     {SNOW_UTILS_DB}     (from manifest)
        Admin Role:   {ADMIN_ROLE}        (from manifest)
        → PAT-specific settings (expiry, auth policy) handled by snow-utils-pat

      Create fresh PAT with these values? [yes/no]
      ```

      **⚠️ STOP**: Wait for user confirmation.

      **On "yes":** Run PAT creation with identity values only — PAT skill handles its own parameters:

      ```bash
      uv run --project <SKILL_DIR> snow-utils-pat \
        create --user ${SA_USER} --role ${SA_ROLE} --db ${SNOW_UTILS_DB} --output json
      ```

      > **Note:** This skips snow-utils-pat Steps 3-4 (gather requirements + dry run) because identity values come from the manifest. PAT-specific settings (expiry, auth policy) are read by the PAT skill from its own manifest section or CLI defaults.

      **After PAT creation:** Update .env with the new SA_PAT value (redacted in output).

   g. **Recreate dependent resources if needed:**

      If the manifest also has `snow-utils-networks` or `snow-utils-volumes` sections with `Status: REMOVED`, pre-populate and run those too:

      ```
      Pre-populated from manifest:
        External Volume: {EXTERNAL_VOLUME_NAME}  (from manifest)
        Bucket:          {BUCKET}                (from manifest)
        Region:          {AWS_REGION}            (from manifest)

      Recreate external volume? [yes/no]
      ```

      Each dependent skill gets ONE confirmation with manifest values shown.

   **If .env exists and has all values (including SA_PAT):** Skip to step 4.

4. **Find section using unique markers:**

   Look for the block between:

   ```
   <!-- START -- hirc-duckdb-demo:{DEMO_DATABASE} -->
   ...
   <!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->
   ```

5. **Check Status:**

| Status | Action |
|--------|--------|
| `REMOVED` | Proceed to step 6 |
| `COMPLETE` | **Collision detected** — show collision strategy prompt |
| `IN_PROGRESS` | Use Resume Flow instead |

   **If Status is `COMPLETE` — Collision Strategy (demo's OWN resources only):**

   > **Dependency Skill Ownership:** Only check collision for `DEMO_DATABASE` here.
   > PAT, network, and volume collisions are handled by their respective skills.

   ```
   ⚠️ Demo resources already exist:

     Resource                    Status
     ─────────────────────────────────────
     Database: {DEMO_DATABASE}          EXISTS

   Choose a strategy:
   1. Use existing → skip database creation, verify grants only
   2. Replace → DROP DATABASE then recreate (DESTRUCTIVE — all tables lost)
   3. Rename → prompt for new database name
   4. Cancel → stop replay
   ```

   **⚠️ STOP**: Wait for user choice.

   | Choice | Action |
   |--------|--------|
   | **Use existing** | Skip database creation, verify grants to `SA_ROLE` are still valid. |
   | **Replace** | Confirm with "Type 'yes, destroy' to confirm". `DROP DATABASE {DEMO_DATABASE}`, then proceed to step 6. |
   | **Rename** | Ask for new database name. Update `DEMO_DATABASE` in `.env` and proceed to step 6. |
   | **Cancel** | Stop replay. |

6. **Display replay plan:**

   ```
   Replay from manifest will create:
   
     Database:      ${DEMO_DATABASE}
     Iceberg Table: FRUITS
     Grants:        USAGE, SELECT to ${SA_ROLE}
   
   Proceed? [yes/no]
   ```

   **⚠️ STOP**: Wait for user confirmation.

7. **On confirmation:** Execute Steps 4-9 sequentially.

   > **⚠️ MANDATORY:** Display every SQL preview box (Steps 4-8) BEFORE executing each step, even in replay.
   > Replay reduces confirmation stops but NEVER skips the preview boxes — they are educational and serve as an audit trail.
   > Flow: show preview box → execute → show next preview box → execute → ...

8. **Update manifest section using unique markers:**

   Replace entire block from `<!-- START -- hirc-duckdb-demo:{DEMO_DATABASE} -->` to `<!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->` with updated status COMPLETE.

## Resume Flow

**If manifest shows Status: IN_PROGRESS:**

1. **Find section using unique markers:**

   Look for the block between:

   ```
   <!-- START -- hirc-duckdb-demo:{DEMO_DATABASE} -->
   ...
   <!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->
   ```

2. **Read which resources have status DONE** (already created)

3. **Display resume info:**

   ```
   Resuming from partial creation:
   
     DONE: Database ${DEMO_DATABASE}
     DONE: Grant USAGE
     
     PENDING: Iceberg Table FRUITS
     PENDING: Grant SELECT
   
   Continue from Iceberg Table creation? [yes/no]
   ```

   **⚠️ STOP**: Wait for user confirmation.

4. **On confirmation:** Continue from first PENDING resource.

   > **⚠️ MANDATORY:** Display SQL preview boxes for each PENDING step BEFORE executing.
   > Skip boxes for DONE steps only. NEVER collapse or summarize — show each box in full.

5. **Update manifest section using unique markers:**

   Replace entire block from `<!-- START -- hirc-duckdb-demo:{DEMO_DATABASE} -->` to `<!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->` as each resource is created.

## Stopping Points

- Step 0: Ask for project directory name
- Step 0b: If tools missing (provide install instructions)
- Step 0c: Ask to install each missing skill
- Step 1a: If prerequisite values missing (direct to skills)
- Step 2: Ask for demo database name
- Step 2a: Ask for admin role
- Step 3: After configuration summary (get confirmation)
- Step 4: After database preview (get approval)
- Step 5: After sample data preview (get approval)
- Step 6: After expected failure (explain why)
- Step 6a: After explanation (confirm ready to fix)
- Step 7: After RBAC preview (get approval)

## Troubleshooting

**Prerequisites missing:** Run snow-utils-pat first (for SA_ROLE, SA_PAT), then snow-utils-volumes (for EXTERNAL_VOLUME_NAME).

**PAT not working:** Ensure snow-utils-pat completed and SA_PAT is in .env.

**Role not found in Horizon:** Hyphens don't work - use underscores in role names.

**Table not found:** Use UPPERCASE (PUBLIC.FRUITS not public.fruits).

**Demo still fails after RBAC:** Ensure Step 7 completed successfully. Check that SA_ROLE has SELECT on FRUITS.

## Security Notes

- Reuses SA_ROLE with scoped privileges
- PAT restricted to SA_ROLE only
- Network policy from snow-utils-pat restricts IP access
- admin_role stored in manifest (not hardcoded)

## Directory Structure

After setup, the project directory contains:

```
${PROJECT_DIR}/
├── .env                         # Environment variables
├── .snow-utils/
│   └── snow-utils-manifest.md   # Resource tracking
├── sql/
│   ├── sql/demo.sql             # DuckDB query script
│   ├── demo_setup.sql           # Database creation
│   ├── sample_data.sql          # Iceberg table creation
│   ├── rbac.sql                 # Grant SELECT
│   └── cleanup.sql              # Remove database
├── workbook.ipynb               # Jupyter notebook
└── pyproject.toml               # Python dependencies
```
