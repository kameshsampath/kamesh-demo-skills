---
name: hirc-duckdb-demo
description: "Set up Horizon Iceberg REST Catalog demo to query Snowflake Iceberg tables with DuckDB. Prerequisites: snow-utils-pat skill (which sets up infrastructure and PAT), then snow-utils-volumes which setups external volumes with defined object storage. Triggers: hirc duckdb demo, horizon catalog demo, duckdb iceberg, query iceberg duckdb, set up hirc demo, replay hirc demo, replay hirc-duckdb-demo manifest, recreate demo, export manifest for sharing, share hirc demo manifest, setup from shared manifest, replay from shared manifest, import shared manifest, re-run hirc demo, show RBAC failure again, demo fail and fix."
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
- NEVER use flags that bypass user interaction: `--auto-setup`, `--auto-approve`, `--quiet`, `--non-interactive`
- **`--yes` / `-y` is REQUIRED** when executing commands after user has approved the dry-run (CLIs prompt interactively which does not work in Cortex Code's non-interactive shell)
- NEVER assume user consent - always ask and wait for explicit confirmation
- NEVER search for .env files outside the project directory
- NEVER scan user's home directory or other locations for existing files
- **NEVER offer to drop SNOW_UTILS_DB** - it is shared infrastructure used by ALL skills/projects
- **NEVER use sed/awk/bash to edit manifest files** -- use the file editing tool (Edit/StrReplace) to update manifest content. sed commands fail on macOS and with complex markdown.
- **NEVER guess or invent CLI options** - ONLY use options from the CLI Reference tables; if a command fails with "No such option", run `<command> --help` and use ONLY those options
- **NEVER run Step 7 (RBAC grant) before Step 6 (demo failure)** - the fail-then-fix sequence is the core teaching purpose of this demo. Step 6 MUST execute and the failure MUST be shown and explained to the user before granting SELECT. Do NOT "optimize" by combining data loading and RBAC into one batch.
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

**⚠️ ENVIRONMENT REQUIREMENT:** All CLI tools auto-load `.env` via `load_dotenv()`:
- snow-utils-pat, snow-utils-networks, snow-utils-volumes (dependency skills)
- hirc-demo-setup, hirc-demo-data, hirc-demo-rbac, hirc-demo-cleanup (this demo)

For `snow sql`, `envsubst`, or other raw shell commands, use `set -a && source .env && set +a` before running.

### Step 0: Detect or Create Project Directory

**First, check if already in a project directory:**

```bash
if [ -f .env ] || [ -d .snow-utils ]; then
  echo "✓ Detected existing project directory: $(pwd)"
  [ -f .env ] && echo "  Found: .env"
  [ -d .snow-utils ] && echo "  Found: .snow-utils/"
fi
```

**If existing project detected → go to Step 0-manifest-check.**

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

### Step 0-manifest-check: Manifest Detection & Selection

**🔴 CRITICAL: Before proceeding, detect ALL manifests and let the user choose.**

A project directory may contain:

- **Working manifest:** `.snow-utils/snow-utils-manifest.md` (created during a previous run, may be partial/IN_PROGRESS)
- **Shared manifest:** `*-manifest.md` in the project root (received from another developer, contains `## shared_info` or `<!-- COCO_INSTRUCTION -->`)

**Detect both:**

```bash
WORKING_MANIFEST=""
SHARED_MANIFEST=""
SHARED_MANIFEST_FILE=""

# 1. Check for working manifest
if [ -f .snow-utils/snow-utils-manifest.md ]; then
  WORKING_MANIFEST="EXISTS"
  WORKING_STATUS=$(grep "^Status:" .snow-utils/snow-utils-manifest.md | head -1 | awk '{print $2}')
  echo "Working manifest: .snow-utils/snow-utils-manifest.md (Status: ${WORKING_STATUS})"
fi

# 2. Check for shared manifest in project root
for f in *-manifest.md; do
  [ -f "$f" ] && grep -q "## shared_info\|COCO_INSTRUCTION" "$f" 2>/dev/null && {
    SHARED_MANIFEST="EXISTS"
    SHARED_MANIFEST_FILE="$f"
    echo "Shared manifest: $f"
  }
done
```

**Decision matrix:**

| Working Manifest | Shared Manifest | Action |
|-----------------|-----------------|--------|
| None | None | Fresh start → Step 0a (Initialize Manifest) |
| None | Exists | Copy shared to `.snow-utils/`, run adapt-check → Step 0-adapt |
| Exists | None | Check Status (see below) |
| Exists | Exists | **Conflict — ask user which to use** |

**If BOTH manifests exist, show:**

```
⚠️ Found two manifests in this project:

  1. Working manifest: .snow-utils/snow-utils-manifest.md
     Status: <WORKING_STATUS>
     (from your previous run — may have partial progress)

  2. Shared manifest: <SHARED_MANIFEST_FILE>
     (received from another developer — contains their resource definitions)

Which manifest should we use?
  A. Resume working manifest (continue where you left off)
  B. Start fresh from shared manifest (discard working, adapt values for your account)
  C. Cancel
```

**⚠️ STOP**: Wait for user choice.

| Choice | Action |
|--------|--------|
| **A — Resume working** | Use working manifest → check its Status (below) |
| **B — Use shared** | Backup working to `.snow-utils/snow-utils-manifest.md.bak`, copy shared to `.snow-utils/snow-utils-manifest.md` → Step 0-adapt |
| **C — Cancel** | Stop. |

**If ONLY working manifest exists, check its status:**

1. If `IN_PROGRESS` or `DEMO_FAIL`: Use **Resume Flow** (skip to appropriate step)
2. If `COMPLETE`: Inform user demo already exists, ask if they want to re-run
3. If `REMOVED`: Proceed with **Replay Flow**

**If ONLY shared manifest exists:**
Copy to `.snow-utils/snow-utils-manifest.md` → Step 0-adapt.

### Step 0-adapt: Shared Manifest Adapt-Check

**🔴 ALWAYS run this step when using a shared manifest. Prompt user ONLY if `# ADAPT:` markers are found.**

```bash
# 1. Detect shared manifest origin
IS_SHARED=$(grep -c "## shared_info\|COCO_INSTRUCTION" .snow-utils/snow-utils-manifest.md 2>/dev/null)

if [ "$IS_SHARED" -gt 0 ]; then
  # 2. Scan for ADAPT markers
  ADAPT_COUNT=$(grep -c "# ADAPT:" .snow-utils/snow-utils-manifest.md 2>/dev/null)
  echo "Shared manifest detected. ADAPT markers found: ${ADAPT_COUNT}"
fi
```

**If `ADAPT_COUNT` > 0 (markers found):**

1. Extract `shared_by` from `## shared_info`
2. Get current user's `SNOWFLAKE_USER` from `.env` or ask
3. Extract ALL values with `# ADAPT:` markers
4. Compute adapted values by replacing shared-user prefix with current-user prefix
5. Present combined adaptation screen:

```
📋 Shared Manifest Value Review
─────────────────────────────────
Shared by: ALICE
Your user: BOB

  Resource                  Shared Value                    → Adapted Value
  ────────────────────────  ──────────────────────────────  ──────────────────────────────
  Service User:             ALICES_HIRC_DUCKDB_DEMO_RUNNER  → BOBS_HIRC_DUCKDB_DEMO_RUNNER
  Service Role:             ALICES_HIRC_DUCKDB_DEMO_ACCESS  → BOBS_HIRC_DUCKDB_DEMO_ACCESS
  Database (utils):         ALICES_SNOW_UTILS               → BOBS_SNOW_UTILS
  Network Rule:             ALICES_..._NETWORK_RULE         → BOBS_..._NETWORK_RULE
  External Volume:          ALICES_..._EXTERNAL_VOLUME      → BOBS_..._EXTERNAL_VOLUME
  Demo Database:            ALICES_HIRC_DUCKDB_DEMO         → BOBS_HIRC_DUCKDB_DEMO
  Admin Role:               ACCOUNTADMIN                    → ACCOUNTADMIN (unchanged)

Options:
  1. Accept all adapted values (recommended)
  2. Edit a specific value
  3. Keep all original values (use as-is)
```

**⚠️ STOP**: Wait for user choice.

| Choice | Action |
|--------|--------|
| **1 — Accept all** | Apply adaptations to manifest in-place, proceed to Replay Flow |
| **2 — Edit specific** | Ask which value to change, let user provide value, re-display |
| **3 — Keep originals** | Proceed with original values (user's choice) |

**If `ADAPT_COUNT` = 0 (no markers):**

```
ℹ️ Shared manifest detected but no adaptation markers found.
   Using values as-is. Proceeding to Replay Flow.
```

Proceed to **Replay Flow**.

### Step 0a: Initialize Manifest

> **⛔ DO NOT hand-edit manifests.** Manifests are machine-managed by Cortex Code. Manual edits can corrupt the format and break replay, cleanup, and export flows. Use skill commands to modify resources instead.

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
- snow-utils-pat: https://github.com/kameshsampath/snow-utils-skills/snow-utils-pat
- snow-utils-volumes: https://github.com/kameshsampath/snow-utils-skills/snow-utils-volumes

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
uv run --project <SKILL_DIR> hirc-demo-setup --admin-role ${ADMIN_ROLE}
```

> Reads DEMO_DATABASE, SA_ROLE, EXTERNAL_VOLUME_NAME from `.env`. `--admin-role` value comes from manifest (Step 2a).

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
| 4 | Demo Run | DuckDB query (MUST FAIL - no SELECT yet) | Step 6 | PENDING |
| 5 | RBAC Grant | SELECT on FRUITS → {SA_ROLE} | Enables external query | BLOCKED_BY:4 |
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
uv run --project <SKILL_DIR> hirc-demo-data --admin-role ${ADMIN_ROLE}
```

> Reads DEMO_DATABASE, EXTERNAL_VOLUME_NAME from `.env`. `--admin-role` value comes from manifest (Step 2a).

> **Note:** admin_role creates and owns the table. SA_ROLE only has USAGE on database/schema (no SELECT yet).

**Update manifest:** Mark "Iceberg Table" as DONE.

> **🔴 NEXT STEP IS THE DEMO, NOT THE RBAC GRANT.** Do NOT skip ahead to grant SELECT. The demo MUST fail first to teach the user about Snowflake RBAC.

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

**Update manifest:** Mark "Demo Run" (row 4) as DONE and change "RBAC Grant" (row 5) status from `BLOCKED_BY:4` to `PENDING`.

**Update manifest status to DEMO_FAIL (if failed):** Use the file editing tool (Edit/StrReplace) to change the status:

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

> **🔴 PREREQUISITE:** Step 6 (Run Demo - Expect Failure) MUST have been executed and the failure shown to the user BEFORE this step. The fail-then-fix sequence is the core teaching purpose of this demo. If Step 6 was skipped, go back and run it now.

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
uv run --project <SKILL_DIR> hirc-demo-rbac --admin-role ${ADMIN_ROLE}
```

> Reads DEMO_DATABASE, SA_ROLE from `.env`. `--admin-role` value comes from manifest (Step 2a). Defaults: schema=PUBLIC, table=FRUITS.

**Update manifest:** Mark "RBAC Grant" (row 5) as DONE.

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

**Update manifest status to DEMO_SUCCESS:** Use the file editing tool (Edit/StrReplace) to change the status:

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
| 4 | Demo Run | DuckDB query (MUST FAIL - no SELECT yet) | Step 6 | DONE |
| 5 | RBAC Grant | SELECT on FRUITS → {SA_ROLE} | Enables external query | DONE |

### Cleanup Instructions

```bash
uv run --project <SKILL_DIR> hirc-demo-cleanup --admin-role ${ADMIN_ROLE}
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
5. **Create directory + `.snow-utils/`**, **copy** manifest to `.snow-utils/snow-utils-manifest.md` (preserve original for reference/audit -- do NOT move or delete it)
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
   
   Command:
   uv run --project <SKILL_DIR> hirc-demo-cleanup --admin-role ${ADMIN_ROLE}
   
   Proceed? [yes/no]
   ```

   **⚠️ STOP**: Wait for user confirmation.

4. **On confirmation:** Execute cleanup using the CLI command:

   ```bash
   uv run --project <SKILL_DIR> hirc-demo-cleanup --admin-role ${ADMIN_ROLE}
   ```

   > **NEVER run raw SQL for cleanup.** ALWAYS use the CLI command above.

5. **Update manifest section using unique markers:**

   **IMPORTANT:** Do NOT delete the manifest file. Update the status to REMOVED so the demo can be replayed later.

   **CRITICAL:** Use the **file editing tool** (Edit/StrReplace) with the full unique block markers to avoid "found N times" errors. NEVER use `sed` or shell commands for this:

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
   | 4 | Demo Run | DuckDB query (MUST FAIL - no SELECT yet) | Step 6 | REMOVED |
   | 5 | RBAC Grant | SELECT on FRUITS → {SA_ROLE} | Enables external query | REMOVED |
   <!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->
   ```

6. **Cascading dependency cleanup (interactive -- ask for each):**

   > **🔴 CRITICAL: ALWAYS use the respective skill's CLI command for dependency cleanup. NEVER run raw SQL.**
   >
   > **🔴 NEVER offer to drop SNOW_UTILS_DB.** It is shared infrastructure used by ALL skills and projects. Cleanup only removes resources *inside* that database (policies, network rules, schemas), never the database itself.

   After demo cleanup succeeds, read the manifest for dependency skill sections and offer to clean each one:

   ```
   ✓ Demo database ${DEMO_DATABASE} cleaned up.

   The following dependency resources still exist:
     1. PAT:      ${SA_USER} (managed by snow-utils-pat)
     2. Volumes:  ${EXTERNAL_VOLUME_NAME} (managed by snow-utils-volumes)
     3. Networks: ${NW_RULE_NAME} (managed by snow-utils-networks)

   Would you like to clean up dependency resources?
   ```

   **⚠️ STOP**: Wait for user input.

   **For each dependency skill (reverse creation order: PAT -> Volumes -> Networks):**

   a. **Ask user:**

      ```
      Remove PAT resources (user: ${SA_USER}, role: ${SA_ROLE})? [yes/no]
      ```

      **⚠️ STOP**: Wait for user input.

   b. **On "yes":** Read the CLI command from that skill's **"Cleanup Instructions"** section in the manifest, then execute it:

      **PAT cleanup:**
      ```bash
      uv run --project <SKILL_DIR> snow-utils-pat \
        remove --user ${SA_USER} --db ${SNOW_UTILS_DB} --drop-user
      ```

      **Volumes cleanup:**
      ```bash
      uv run --project <SKILL_DIR> snow-utils-volumes \
        --region ${AWS_REGION} \
        delete --bucket ${BUCKET} --yes
      ```

      **Networks cleanup:**
      ```bash
      uv run --project <SKILL_DIR> snow-utils-networks \
        rule delete --name ${NW_RULE_NAME} --db ${NW_RULE_DB} --yes
      ```

   c. **After each successful cleanup:** Update that skill's manifest section status to `REMOVED`.

   d. **On "no":** Skip that skill and move to the next.

   e. **On failure:** Stop, present error, ask user whether to continue with remaining skills or abort.

   **After all steps complete, show summary:**

   ```
   Cleanup Summary:
     ✓ Demo Database:     ${DEMO_DATABASE}     → REMOVED
     ✓ PAT:               ${SA_USER}           → REMOVED  (or "SKIPPED" if user said no)
     ✓ External Volume:   ${EXTERNAL_VOLUME_NAME} → REMOVED
     ✓ Network Rule:      ${NW_RULE_NAME}      → REMOVED
   ```

## Replay Flow

**Trigger phrases:** "replay hirc demo", "replay hirc-duckdb-demo manifest", "recreate demo"

**Direct re-run triggers:** "re-run hirc demo", "show RBAC failure again", "demo fail and fix"
> If the user says one of these, read the manifest. If status is `COMPLETE`, skip the collision prompt and go directly to the **Re-run Flow** section. If status is not `COMPLETE`, fall through to the normal Replay Flow below.

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
      for var in SA_USER SA_ROLE SNOW_UTILS_DB EXTERNAL_VOLUME_NAME DEMO_DATABASE ADMIN_ROLE; do
        val=$(eval echo \$$var)
        if [ -z "$val" ]; then
          echo "WARNING: Could not extract ${var} from manifest. Check manifest format."
        fi
      done
      ```

      If any value is empty, ask user: "Some values couldn't be extracted. Enter them manually?" If yes, prompt for each. If no, abort replay.

   f. **Shared manifest adapt-check (ALWAYS run for shared manifests):**

      ```bash
      # 1. Detect shared manifest origin
      IS_SHARED=$(grep -c "## shared_info\|COCO_INSTRUCTION" .snow-utils/snow-utils-manifest.md 2>/dev/null)

      if [ "$IS_SHARED" -gt 0 ]; then
        # 2. Scan for ADAPT markers
        ADAPT_COUNT=$(grep -c "# ADAPT:" .snow-utils/snow-utils-manifest.md 2>/dev/null)
        echo "Shared manifest detected. ADAPT markers: ${ADAPT_COUNT}"
      fi
      ```

      **If shared manifest AND `ADAPT_COUNT` > 0:** Follow **Step 0-adapt** above -- extract `shared_by`, get current user's `SNOWFLAKE_USER`, present adaptation screen with all marked values, apply adaptations.

      **If shared manifest AND `ADAPT_COUNT` = 0:** No adaptation needed, proceed with values as-is.

      **If NOT a shared manifest:** Skip this step.

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

      **On "yes":** First run dry-run to show full SQL preview:

      ```bash
      uv run --project <SKILL_DIR> snow-utils-pat \
        create --user ${SA_USER} --role ${SA_ROLE} --db ${SNOW_UTILS_DB} --dry-run
      ```

      **🔴 CRITICAL:** Terminal output gets truncated by the UI. After running the command, read the terminal output and paste the ENTIRE result using language-tagged code blocks: ` ```text ` for summary, ` ```sql ` for SQL.

      First run `snow-utils-pat create --help` to confirm available options, then execute:

      ```bash
      uv run --project <SKILL_DIR> snow-utils-pat \
        create --user ${SA_USER} --role ${SA_ROLE} --db ${SNOW_UTILS_DB} \
        --dot-env-file .env --yes
      ```

      > **⚠️ CRITICAL:** ALWAYS include `--yes` (the CLI prompts interactively which does not work in Cortex Code).
      > **Fallback for `--yes`:** If not available ("No such option"), pipe: `echo y | <command>`.
      > **🔴 SECURITY:** NEVER use `sed` or shell commands to write the token.
      > **Fallback for `--dot-env-file`:** If not available, drop that flag -- the CLI writes SA_PAT to `.env` via `--env-path` anyway.

      **Verify PAT connection (MANDATORY -- do NOT skip):**

      ```bash
      uv run --project <SKILL_DIR> snow-utils-pat \
        verify --user ${SA_USER} --role ${SA_ROLE}
      ```

      > If verify fails, stop and present error. Do NOT proceed to dependent resources.

   g. **Recreate dependent resources if needed:**

      If the manifest also has `snow-utils-networks` or `snow-utils-volumes` sections with `Status: REMOVED`, pre-populate and run those too:

      **For each dependency skill:**

      1. Run `--dry-run` first, then paste the full output into your response using language-tagged code blocks (` ```text `, ` ```sql `, ` ```json `). For volumes: include IAM policy JSON, trust policy JSON, AND SQL -- do NOT omit JSON sections.
      2. Get ONE confirmation with manifest values shown
      3. Execute creation
      4. **Run verify (MANDATORY)** -- do NOT skip, even in replay

      **Example for volumes:**

      ```bash
      # 1. Dry-run preview
      uv run --project <SKILL_DIR> snow-utils-volumes \
        --region {AWS_REGION} create --bucket {BUCKET} --dry-run

      # 2. After user confirms, execute
      uv run --project <SKILL_DIR> snow-utils-volumes \
        --region {AWS_REGION} create --bucket {BUCKET} --output json

      # 3. Verify (MANDATORY)
      uv run --project <SKILL_DIR> snow-utils-volumes \
        verify --volume-name {EXTERNAL_VOLUME_NAME}
      ```

      **Example for networks:**

      ```bash
      # 1. Dry-run preview
      uv run --project <SKILL_DIR> snow-utils-networks \
        rule create --name {NW_RULE_NAME} --db {NW_RULE_DB} --dry-run

      # 2. After user confirms, execute
      uv run --project <SKILL_DIR> snow-utils-networks \
        rule create --name {NW_RULE_NAME} --db {NW_RULE_DB}

      # 3. Verify (MANDATORY)
      uv run --project <SKILL_DIR> snow-utils-networks \
        rule list --db {NW_RULE_DB}
      ```

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
   4. Re-run demo → revoke SELECT, re-experience fail-then-fix, re-grant
   5. Cancel → stop replay
   ```

   **⚠️ STOP**: Wait for user choice.

   | Choice | Action |
   |--------|--------|
   | **Use existing** | Skip database creation, verify grants to `SA_ROLE` are still valid. |
   | **Replace** | Confirm with "Type 'yes, destroy' to confirm". `DROP DATABASE {DEMO_DATABASE}`, then proceed to step 6. |
   | **Rename** | Ask for new database name. Update `DEMO_DATABASE` in `.env` and proceed to step 6. |
   | **Re-run demo** | Keep all infrastructure. Execute **Re-run Flow** (see below): REVOKE SELECT, demo failure, GRANT SELECT, demo success. |
   | **Cancel** | Stop replay. |

6. **Display replay plan:**

   ```
   Replay from manifest will create:
   
     Database:      ${DEMO_DATABASE}
     Iceberg Table: FRUITS
     Demo Run:      DuckDB query (MUST FAIL - shows RBAC gap)
     RBAC Grant:    SELECT to ${SA_ROLE} (only AFTER demo failure)
   
   Proceed? [yes/no]
   ```

   **⚠️ STOP**: Wait for user confirmation.

7. **On confirmation:** Execute Steps 4-9 sequentially.

   > **⚠️ MANDATORY:** Display every SQL preview box (Steps 4-8) BEFORE executing each step, even in replay.
   > Replay reduces confirmation stops but NEVER skips the preview boxes — they are educational and serve as an audit trail.
   > Flow: show preview box → execute → show next preview box → execute → ...
   >
   > **🔴 NEVER skip the demo failure step (Step 6), even in replay.** The fail-then-fix sequence is the core teaching purpose. After loading data (Step 5), you MUST run the DuckDB demo, show the failure and explanation (Step 6/6a), THEN grant SELECT (Step 7). The manifest tracks this as row 4 ("Demo Run") with BLOCKED_BY:4 on row 5 ("RBAC Grant").

8. **Update manifest section using unique markers:**

   Use the **file editing tool** (Edit/StrReplace) to replace the entire block from `<!-- START -- hirc-duckdb-demo:{DEMO_DATABASE} -->` to `<!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->` with updated status COMPLETE.

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
     PENDING: Demo Run (DuckDB query - MUST FAIL before RBAC grant)
     BLOCKED: RBAC Grant SELECT (blocked until Demo Run completes)
   
   Continue from Iceberg Table creation? [yes/no]
   ```

   **⚠️ STOP**: Wait for user confirmation.

4. **On confirmation:** Continue from first PENDING resource.

   > **⚠️ MANDATORY:** Display SQL preview boxes for each PENDING step BEFORE executing.
   > Skip boxes for DONE steps only. NEVER collapse or summarize — show each box in full.
   > **🔴 NEVER skip the demo failure step.** If "Demo Run" is PENDING, run Step 6 and show the failure before proceeding to RBAC Grant.

5. **Update manifest section using unique markers:**

   Use the **file editing tool** (Edit/StrReplace) to replace the entire block from `<!-- START -- hirc-duckdb-demo:{DEMO_DATABASE} -->` to `<!-- END -- hirc-duckdb-demo:{DEMO_DATABASE} -->` as each resource is created.

## Re-run Flow

**Trigger phrases:** "re-run hirc demo", "show RBAC failure again", "demo fail and fix"

**Precondition:** Manifest status must be `COMPLETE`. If not COMPLETE, use Resume Flow (IN_PROGRESS) or Replay Flow (REMOVED) instead.

This is a lightweight pedagogical loop that re-experiences the fail-then-fix RBAC sequence **without destroying or recreating any infrastructure**. All resources (database, table, data) remain intact.

1. **Read manifest and verify COMPLETE status:**

   ```bash
   cat .snow-utils/snow-utils-manifest.md 2>/dev/null
   ```

   If status is not `COMPLETE`, inform the user and suggest the appropriate flow.

2. **Read ADMIN_ROLE from manifest** (stored in metadata, NOT in `.env`).

3. **Display re-run plan:**

   ```
   Re-running the fail-then-fix RBAC demo:

     Step 1: REVOKE SELECT on ${DEMO_DATABASE}.PUBLIC.FRUITS from ${SA_ROLE}
     Step 2: Run DuckDB demo (EXPECT FAILURE - no SELECT)
     Step 3: Explain why it failed (RBAC lesson)
     Step 4: GRANT SELECT back to ${SA_ROLE}
     Step 5: Run DuckDB demo again (SUCCESS)

   Infrastructure is preserved — no databases or tables will be dropped.

   Proceed? [yes/no]
   ```

   **STOP**: Wait for user confirmation.

4. **REVOKE SELECT — dry-run preview:**

   Display the SQL that will be executed:

   ```
   ╔══════════════════════════════════════════════════════════════════╗
   ║        📋 SQL TO BE EXECUTED (revoke_rbac.sql)                   ║
   ╠══════════════════════════════════════════════════════════════════╣
   ║                                                                  ║
   ║  USE ROLE ${ADMIN_ROLE};                                         ║
   ║  REVOKE SELECT ON TABLE ${DEMO_DATABASE}.PUBLIC.FRUITS           ║
   ║    FROM ROLE ${SA_ROLE};                                         ║
   ║                                                                  ║
   ╚══════════════════════════════════════════════════════════════════╝
   ```

   **STOP**: Show preview and get approval.

5. **Execute REVOKE:**

   ```bash
   uv run --project <SKILL_DIR> hirc-demo-revoke-rbac --admin-role ${ADMIN_ROLE}
   ```

   > Reads DEMO_DATABASE, SA_ROLE from `.env`. `--admin-role` value comes from manifest. Defaults: schema=PUBLIC, table=FRUITS.

6. **Update manifest:** Reset "Demo Run" (row 4) to `PENDING` and "RBAC Grant" (row 5) to `BLOCKED_BY:4`. Use the **file editing tool** (Edit/StrReplace).

7. **Execute Step 6 (Run Demo - Expect Failure):**

   Follow the instructions in **Step 6: Run Demo (Expect Failure!)** exactly. Display the preview box, run the DuckDB demo, show the failure.

   After failure, update manifest: mark "Demo Run" (row 4) as `DONE`, change "RBAC Grant" (row 5) from `BLOCKED_BY:4` to `PENDING`.

8. **Execute Step 6a (Why Did It Fail?):**

   Follow **Step 6a: Why Did It Fail? (Interactive Learning)** — display the RBAC explanation. Wait for user to confirm ready to fix.

9. **Execute Step 7 (Grant Access):**

   Follow **Step 7: Grant Access (RBAC)** — display the GRANT SQL preview, get approval, execute.

   Update manifest: mark "RBAC Grant" (row 5) as `DONE`.

10. **Execute Step 8 (Run Demo Again - Success!):**

    Follow **Step 8: Run Demo Again (Success!)** — run DuckDB demo, display success box.

11. **Restore manifest to COMPLETE:**

    Use the **file editing tool** (Edit/StrReplace) to set status back to `COMPLETE` with all 5 rows as `DONE`.

    > The re-run flow is a pedagogical loop — the manifest returns to the same COMPLETE state it started in.

## Stopping Points

1. Step 0: Ask for project directory name
2. Step 0b: If tools missing (provide install instructions)
3. Step 0c: Ask to install each missing skill
4. Step 1a: If prerequisite values missing (direct to skills)
5. Step 2: Ask for demo database name
6. Step 2a: Ask for admin role
7. Step 3: After configuration summary (get confirmation)
8. Step 4: After database preview (get approval)
9. Step 5: After sample data preview (get approval)
10. Step 6: After expected failure (explain why)
11. Step 6a: After explanation (confirm ready to fix)
12. Step 7: After RBAC preview (get approval)

## CLI Reference (hirc-duckdb-demo)

All commands auto-load `.env` and pass required variables to `snow sql` with templating.

**🔴 OPTION NAMES (NEVER guess or invent options):**

> ONLY use options listed in the tables below and in each dependency skill's CLI Reference.
> If a command fails with "No such option", run `<command> --help` to see actual available options and use ONLY those.
> NEVER invent, abbreviate, or rename options. This applies to ALL CLIs: `hirc-demo-*`, `snow-utils-pat`, `snow-utils-networks`, `snow-utils-volumes`.

### `hirc-demo-setup`

Creates the demo database with USAGE grants and sets the external volume.

```bash
uv run --project <SKILL_DIR> hirc-demo-setup --admin-role <ROLE> [--dry-run]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--admin-role` | **Yes** | - | Admin role (from manifest, NOT .env) |
| `--dry-run` | No | false | Preview command without executing |

**Required .env:** `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `DEMO_DATABASE`, `SA_ROLE`, `EXTERNAL_VOLUME_NAME`

### `hirc-demo-data`

Creates Iceberg table and loads sample data.

```bash
uv run --project <SKILL_DIR> hirc-demo-data --admin-role <ROLE> [--dry-run]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--admin-role` | **Yes** | - | Admin role (from manifest, NOT .env) |
| `--dry-run` | No | false | Preview command without executing |

**Required .env:** `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `DEMO_DATABASE`, `EXTERNAL_VOLUME_NAME`

### `hirc-demo-rbac`

Grants SELECT on Iceberg table to SA_ROLE.

```bash
uv run --project <SKILL_DIR> hirc-demo-rbac --admin-role <ROLE> [--dry-run] [--schema PUBLIC] [--table FRUITS]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--admin-role` | **Yes** | - | Admin role (from manifest, NOT .env) |
| `--schema` | No | `PUBLIC` | Schema name |
| `--table` | No | `FRUITS` | Table name |
| `--dry-run` | No | false | Preview command without executing |

**Required .env:** `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `DEMO_DATABASE`, `SA_ROLE`

### `hirc-demo-revoke-rbac`

Revokes SELECT on Iceberg table from SA_ROLE. Used by the Re-run Flow to restore the RBAC-failure state.

```bash
uv run --project <SKILL_DIR> hirc-demo-revoke-rbac --admin-role <ROLE> [--dry-run] [--schema PUBLIC] [--table FRUITS]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--admin-role` | **Yes** | - | Admin role (from manifest, NOT .env) |
| `--schema` | No | `PUBLIC` | Schema name |
| `--table` | No | `FRUITS` | Table name |
| `--dry-run` | No | false | Preview command without executing |

**Required .env:** `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `DEMO_DATABASE`, `SA_ROLE`

### `hirc-demo-cleanup`

Drops the demo database and all its tables.

```bash
uv run --project <SKILL_DIR> hirc-demo-cleanup --admin-role <ROLE> [--dry-run]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--admin-role` | **Yes** | - | Admin role (from manifest, NOT .env) |
| `--dry-run` | No | false | Preview command without executing |

**Required .env:** `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `DEMO_DATABASE`

## SQL Reference (Snowflake Documentation)

> These links help Cortex Code infer correct SQL syntax when previewing or troubleshooting.

| Statement | Documentation |
|-----------|---------------|
| `CREATE DATABASE` | https://docs.snowflake.com/en/sql-reference/sql/create-database |
| `DROP DATABASE` | https://docs.snowflake.com/en/sql-reference/sql/drop-database |
| `ALTER DATABASE ... SET EXTERNAL_VOLUME` | https://docs.snowflake.com/en/sql-reference/sql/alter-database |
| `CREATE ICEBERG TABLE` (Snowflake catalog) | https://docs.snowflake.com/en/sql-reference/sql/create-iceberg-table-snowflake |
| `INSERT INTO` | https://docs.snowflake.com/en/sql-reference/sql/insert |
| `GRANT USAGE ON DATABASE` | https://docs.snowflake.com/en/sql-reference/sql/grant-privilege |
| `GRANT USAGE ON SCHEMA` | https://docs.snowflake.com/en/sql-reference/sql/grant-privilege |
| `GRANT SELECT ON TABLE` | https://docs.snowflake.com/en/sql-reference/sql/grant-privilege |
| `REVOKE SELECT ON TABLE` | https://docs.snowflake.com/en/sql-reference/sql/revoke-privilege |

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
│   ├── revoke_rbac.sql          # Revoke SELECT (re-run flow)
│   └── cleanup.sql              # Remove database
├── workbook.ipynb               # Jupyter notebook
└── pyproject.toml               # Python dependencies
```
