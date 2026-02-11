---
name: smart-crowd-counter
description: "Set up Smart Crowd Counter demo: a Streamlit-in-Snowflake app using Cortex AISQL to analyze conference photos, count attendees, and detect raised hands. Triggers: smart crowd counter, crowd counter demo, conference photo analysis, cortex aisql demo, streamlit crowd counter, set up crowd counter, replay crowd counter, replay smart-crowd-counter manifest, recreate crowd counter demo, export manifest for sharing, share crowd counter manifest, setup from shared manifest, replay from shared manifest, import shared manifest, setup from manifest URL, replay from URL, use manifest from URL, re-run crowd counter, redeploy crowd counter app."
location: user
---

# Smart Crowd Counter Demo

A Streamlit-in-Snowflake app that counts people in conference session photos using Snowflake Cortex AISQL. It detects raised hands too, which is handy for tracking badge giveaways or audience engagement.

## Prerequisites

This skill is **standalone** -- it only requires a Snowflake connection with sufficient privileges. No snow-utils-* skills are needed.

**Required:**

- Snowflake account with Cortex AISQL enabled
- An admin role that can CREATE ROLE, CREATE DATABASE, and GRANT (ACCOUNTADMIN recommended)
- A warehouse for running queries and the Streamlit app

**Least Privilege:** This skill creates a dedicated demo role (`${USER}_SCC_ACCESS`) that owns the database and has USAGE on the warehouse. The demo role has **no account-level privileges**. ACCOUNTADMIN is only used to create/drop the role and database.

## Streamlit Development Guidance

For Streamlit-related tasks (editing the app, improving UI, deploying), use the bundled `developing-with-streamlit` cortex skill. Key sub-skills:

- `deploying-streamlit-to-snowflake` -- deployment via `snow streamlit deploy`
- `building-streamlit-dashboards` -- dashboard layout patterns
- `displaying-streamlit-data` -- charts, dataframes, column config
- `using-streamlit-session-state` -- session state patterns
- `improving-streamlit-design` -- Material icons, badges, visual polish

## Workflow

**FORBIDDEN ACTIONS - NEVER DO THESE:**

- NEVER run SQL queries to discover/validate .env values
- NEVER use flags that bypass user interaction: `--auto-setup`, `--auto-approve`, `--quiet`, `--non-interactive`
- **`--yes` / `-y` is REQUIRED** when executing commands after user has approved the dry-run (CLIs prompt interactively which does not work in Cortex Code's non-interactive shell)
- NEVER assume user consent - always ask and wait for explicit confirmation
- NEVER search for .env files outside the project directory
- NEVER scan user's home directory or other locations for existing files
- **NEVER use sed/awk/bash to edit manifest or .env files** -- use the file editing tool (Edit/StrReplace) for both. `sed -i` is platform-dependent and breaks on macOS vs Linux.
- **NEVER guess or invent CLI options** - ONLY use options from the CLI Reference tables; if a command fails with "No such option", run `<command> --help` and use ONLY those options
- **NEVER use `uv run --project <SKILL_DIR>`** for CLI commands -- it changes CWD and breaks `.env` discovery. Always use `uv run scc-xxx` from the project directory
- Trust .env - if values present, they are correct
- If values missing, prompt the user (don't search for files)

**INTERACTIVE PRINCIPLE:** This skill is designed to be interactive. At every decision point, ASK the user and WAIT for their response before proceeding.

**DISPLAY PRINCIPLE:** All **SHOW** and **SUMMARIZE** steps contain SQL/command templates with placeholders like `${ADMIN_ROLE}`, `${DEMO_ROLE}`, `${DEMO_DATABASE}`. When displaying to the user, **ALWAYS substitute actual values** from `.env` and the manifest. The user should see real values, never raw `${...}` placeholders.

**RESILIENCE PRINCIPLE:** Always update the manifest IMMEDIATELY after each resource creation, not in batches. This ensures Resume Flow can recover from any interruption.

Pattern:

```
1. Set overall Status: IN_PROGRESS at START of resource creation
2. Update each resource row to DONE immediately after creation
3. Set Status: COMPLETE only at the END when ALL resources done
```

**IDEMPOTENCY PRINCIPLE:** Before editing any file, CHECK if the change is already applied. This prevents duplicate edit errors and improves UX.

Pattern for manifest updates:

```bash
grep -q "Status.*COMPLETE" .snow-utils/snow-utils-manifest.md && echo "Already complete" || echo "Needs update"
```

Pattern for file edits:

```
1. Read current file state
2. Check if desired content already exists
3. Only edit if change is needed
4. Skip with message: "Already applied: [description]"
```

### Step 0: Detect or Create Project Directory

**First, check if already in a project directory:**

```bash
if [ -f .env ] || [ -d .snow-utils ]; then
  echo "Detected existing project directory: $(pwd)"
  [ -f .env ] && echo "  Found: .env"
  [ -d .snow-utils ] && echo "  Found: .snow-utils/"
fi
```

**If existing project detected:**

**SHOW** the user:

```
Using existing project directory: <CWD>
```

Then go to **Step 0-manifest-check**.

**If NOT in existing project, ask the user:**

```
Where should the demo artifacts live?

  1. Use current directory: <CWD>
  2. Create a new directory [default: smart-crowd-counter]

Choose [1 or 2]:
```

**STOP**: Wait for user input.

**If user chose 1 (current directory):**

Check for existing files that will be overwritten:

```bash
EXISTING=""
[ -f pyproject.toml ] && EXISTING="${EXISTING} pyproject.toml"
[ -d sql ] && EXISTING="${EXISTING} sql/"
[ -d app ] && EXISTING="${EXISTING} app/"
[ -d smart_crowd_counter ] && EXISTING="${EXISTING} smart_crowd_counter/"
[ -n "$EXISTING" ] && echo "Warning: existing files/dirs will be updated:${EXISTING}"
```

**If existing files detected, SHOW the user:**

```
Note: The following files/dirs in the current directory will be updated
with skill artifacts: <EXISTING>

This is safe if they are from a previous run of this demo.
Continue? [yes/no]
```

**STOP**: Wait for user confirmation. If no, go back to directory choice.

```bash
echo "Using current directory as project directory: $(pwd)"
```

**SHOW** the user: `Project directory: <CWD>`

**If user chose 2 (or pressed Enter for default):**

Ask for directory name if user wants something other than the default:

```
Directory name [default: smart-crowd-counter]:
```

```bash
PROJECT_DIR="${PROJECT_DIR:-smart-crowd-counter}"
mkdir -p "${PROJECT_DIR}"
cd "${PROJECT_DIR}"
```

**SHOW** the user: `Project directory: <CWD>/${PROJECT_DIR}`

> **IMPORTANT:** All subsequent steps run within the chosen project directory. The manifest, .env, and all artifacts live here.

### Step 0-manifest-check: Manifest Detection & Selection

**CRITICAL: Before proceeding, detect ALL manifests and let the user choose.**

#### Remote Manifest URL Detection

If the user provides a URL (in their prompt or pasted), detect and normalize it **before** local manifest detection:

**Supported URL patterns and translation rules:**

- **GitHub blob:** `https://github.com/{owner}/{repo}/blob/{branch}/{path}` -> replace host with `raw.githubusercontent.com` and remove `/blob/` segment -> `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}`
- **GitHub raw:** `https://raw.githubusercontent.com/...` -> use as-is
- **GitHub gist:** `https://gist.github.com/{user}/{id}` -> append `/raw` if not already present
- **Any other HTTPS URL ending in `.md`** -> use as-is

**After translating, show user and confirm:**

```
Found manifest URL. Download URL:
  <translated_raw_url>

Download to current directory as <filename>? [yes/no]
```

**STOP**: Wait for user confirmation.

**If yes:**

```bash
curl -fSL -o <filename> "<translated_raw_url>"
```

> **Filename derivation:** Extract the filename from the URL path (e.g., `smart-crowd-counter-manifest.md`). If the file already exists locally, ask user: overwrite / rename / cancel.

**If no:** Stop.

After successful download, continue with local manifest detection below -- the downloaded file will be picked up by the `*-manifest.md` glob.

---

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
| None | None | Fresh start -> Step 0a (Initialize Manifest) |
| None | Exists | Copy shared to `.snow-utils/`, run adapt-check -> Step 0-adapt |
| Exists | None | Check Status (see below) |
| Exists | Exists | **Conflict -- ask user which to use** |

**If BOTH manifests exist, show:**

```
Found two manifests in this project:

  1. Working manifest: .snow-utils/snow-utils-manifest.md
     Status: <WORKING_STATUS>
     (from your previous run -- may have partial progress)

  2. Shared manifest: <SHARED_MANIFEST_FILE>
     (received from another developer -- contains their resource definitions)

Which manifest should we use?
  A. Resume working manifest (continue where you left off)
  B. Start fresh from shared manifest (discard working, adapt values for your account)
  C. Cancel
```

**STOP**: Wait for user choice.

| Choice | Action |
|--------|--------|
| **A -- Resume working** | Use working manifest -> check its Status (below) |
| **B -- Use shared** | `mkdir -p .snow-utils && chmod 700 .snow-utils`, backup working to `.snow-utils/snow-utils-manifest.md.bak`, copy shared to `.snow-utils/snow-utils-manifest.md` -> Step 0-adapt |
| **C -- Cancel** | Stop. |

**If ONLY working manifest exists, check its status:**

1. If `IN_PROGRESS`: Use **Resume Flow** (skip to appropriate step)
2. If `COMPLETE`: Inform user demo already exists, ask if they want to re-run
3. If `REMOVED`: Proceed with **Replay Flow**

**If ONLY shared manifest exists:**
`mkdir -p .snow-utils && chmod 700 .snow-utils`, then copy to `.snow-utils/snow-utils-manifest.md` -> Step 0-adapt.

### Step 0-adapt: Shared Manifest Adapt-Check

**ALWAYS run this step when using a shared manifest. Prompt user ONLY if `# ADAPT:` markers are found.**

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
Shared Manifest Value Review

Shared by: ALICE
Your user: BOB

  Resource                  Shared Value                        -> Adapted Value
  Database:                 ALICES_CROWD_COUNTER_DB             -> BOBS_CROWD_COUNTER_DB
  Admin Role:               ACCOUNTADMIN                        -> ACCOUNTADMIN (unchanged)

Options:
  1. Accept all adapted values (recommended)
  2. Edit a specific value
  3. Keep all original values (use as-is)
```

**STOP**: Wait for user choice.

| Choice | Action |
|--------|--------|
| **1 -- Accept all** | Apply adaptations to manifest in-place, proceed to Replay Flow |
| **2 -- Edit specific** | Ask which value to change, let user provide value, re-display |
| **3 -- Keep originals** | Proceed with original values (user's choice) |

**If `ADAPT_COUNT` = 0 (no markers):**

```
Shared manifest detected but no adaptation markers found.
Using values as-is. Proceeding to Replay Flow.
```

Proceed to **Replay Flow**.

### Step 0a: Initialize Manifest

> **DO NOT hand-edit manifests.** Manifests are machine-managed by Cortex Code.

**Create manifest directory and file inside project dir:**

```bash
mkdir -p .snow-utils && chmod 700 .snow-utils
if [ ! -f .snow-utils/snow-utils-manifest.md ]; then
cat > .snow-utils/snow-utils-manifest.md << 'EOF'
# Snow-Utils Manifest

This manifest tracks Snowflake resources created by snow-utils skills.

---

## project_recipe
project_name: smart-crowd-counter

## prereqs

## dependent_skills

## installed_skills
EOF
fi
chmod 600 .snow-utils/snow-utils-manifest.md
```

**MANIFEST FILE:** `${PROJECT_DIR}/.snow-utils/snow-utils-manifest.md`

### Step 0b: Check Tools (Manifest-Cached)

**Check manifest for cached tool verification:**

```bash
grep "^tools_verified:" .snow-utils/snow-utils-manifest.md 2>/dev/null
```

**If `tools_verified:` exists with a date:** Skip tool checks, continue to Step 1.

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

**STOP**: Do not proceed until all prerequisites are installed.

**After all tools verified, update manifest:**

```bash
grep -q "^tools_verified:" .snow-utils/snow-utils-manifest.md || \
  sed -i '' '/^## prereqs/a\
tools_verified: '"$(date +%Y-%m-%d)"'' .snow-utils/snow-utils-manifest.md
```

### Step 1: Setup Environment File

**Copy .env.example from skill directory (only if .env does not already exist):**

```bash
[ -f .env ] && echo "Existing .env found -- keeping it." || cp <SKILL_DIR>/.env.example .env
```

> If `.env` already exists (e.g. from a previous run), it is preserved. Do NOT overwrite it.

**Copy skill artifacts AND install dependencies (run as a single block):**

> **CRITICAL:** ALL copy commands and `uv sync` MUST run together as a single block. Running `uv sync` before the `smart_crowd_counter/` package is copied will create broken entry points that fail with `ModuleNotFoundError`.

```bash
mkdir -p sql app smart_crowd_counter
cp <SKILL_DIR>/sql/*.sql sql/
cp <SKILL_DIR>/app/streamlit_app.py app/
cp <SKILL_DIR>/app/environment.yml app/
cp <SKILL_DIR>/app/snowflake.yml.template app/
cp <SKILL_DIR>/smart_crowd_counter/*.py smart_crowd_counter/
cp <SKILL_DIR>/pyproject.toml .
uv sync
```

> **NOTE:** All commands run from the project directory -- NEVER use `--project <SKILL_DIR>`.

**Verify CLI installation:**

```bash
uv run scc-setup --help
```

If the above fails with `ModuleNotFoundError`, re-run `uv sync` to rebuild the package.

### Step 1a: Check Snowflake Connection

**Check required values in .env:**

```bash
set -a && source .env && set +a

# Check connection values
grep -E "^(SNOWFLAKE_DEFAULT_CONNECTION_NAME|SNOWFLAKE_ACCOUNT|SNOWFLAKE_USER|SNOWFLAKE_WAREHOUSE)=" .env
```

**If SNOWFLAKE_DEFAULT_CONNECTION_NAME is missing:**

Ask user: "Which Snowflake connection should we use?" then:

```bash
snow connection list
```

**STOP**: Wait for user to select a connection.

Test the connection and extract details:

```bash
snow connection test -c <selected_connection> --format json
```

Write to .env: `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`

**If SNOWFLAKE_WAREHOUSE is missing:**

```bash
snow sql -c <connection> -q "SELECT CURRENT_WAREHOUSE() as wh" --format json
```

If still empty, offer to create one or use an existing one:

```
No default warehouse found for this connection.

Options:
  1. Create a new warehouse (recommended)
  2. Use an existing warehouse (enter name)
```

**STOP**: Wait for user choice.

**If option 1 (create new):**

Compute a default warehouse name from the user:

```bash
set -a && source .env && set +a
DEFAULT_WH_NAME="${SNOWFLAKE_USER:-$USER}_CROWD_COUNTER_WH"
echo "Computed default: ${DEFAULT_WH_NAME}"
```

```
Warehouse name [${DEFAULT_WH_NAME}]:
```

**STOP**: Wait for user input. If Enter, use the default.

> **Note:** This step requires admin_role and demo_role. If they have not been set yet (Steps 2a/2b haven't run), ask the user which admin role to use (default: ACCOUNTADMIN) and which demo role to use (default: `${SNOWFLAKE_USER}_SCC_ACCESS`).

**SHOW -- SQL Preview (create_warehouse.sql):**

```sql
USE ROLE ${ADMIN_ROLE};

CREATE WAREHOUSE IF NOT EXISTS ${SNOWFLAKE_WAREHOUSE}
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT = 'Warehouse for Smart Crowd Counter demo';

GRANT USAGE ON WAREHOUSE ${SNOWFLAKE_WAREHOUSE} TO ROLE ${DEMO_ROLE};
GRANT OPERATE ON WAREHOUSE ${SNOWFLAKE_WAREHOUSE} TO ROLE ${DEMO_ROLE};
```

**STOP**: Show preview and get approval.

**Execute:**

```bash
uv run scc-create-warehouse \
  --admin-role ${ADMIN_ROLE} \
  --demo-role ${DEMO_ROLE} \
  --warehouse ${SNOWFLAKE_WAREHOUSE}
```

**If option 2 (existing):**

```
Enter warehouse name:
```

**STOP**: Wait for user input.

**Update .env with the warehouse name using the file editing tool:**

Use Edit/StrReplace on `.env`:
- If `SNOWFLAKE_WAREHOUSE=` line exists, replace it with `SNOWFLAKE_WAREHOUSE=${SNOWFLAKE_WAREHOUSE}`
- If the line does not exist, append `SNOWFLAKE_WAREHOUSE=${SNOWFLAKE_WAREHOUSE}` to the file

**If all present:** Continue to Step 2.

### Step 2: Set Demo-Specific Values

**Read SNOWFLAKE_USER from .env and compute default database name:**

```bash
set -a && source .env && set +a
DEFAULT_DB_NAME="${SNOWFLAKE_USER:-$USER}_CROWD_COUNTER_DB"
echo "Computed default: ${DEFAULT_DB_NAME}"
```

**SHOW -- Display the following explanation to the user BEFORE asking for values:**

```
Demo Configuration

Database names are user-prefixed for isolation — this prevents collisions
when multiple users run the demo on the same Snowflake account.

  Pattern:      ${SNOWFLAKE_USER}_CROWD_COUNTER_DB
  Your default: ${DEFAULT_DB_NAME}

You can accept the default or enter a custom name.
```

**Then ask for each value (allow them to accept or change):**

```
  1. Database name [${DEFAULT_DB_NAME}]:
  2. Schema name [CONFERENCES]:
  3. Stage name [SNAPS]:
  4. AI model [claude-4-sonnet]:
```

> **Recommended Cortex Multimodal Models** (image analysis):
>
> | Model | Best For | Images/Prompt | Context Window |
> |---|---|---|---|
> | `claude-4-sonnet` (default) | Best balance of quality, cost & multi-image support | 20 | 200K |
> | `claude-4-opus` | Highest quality Anthropic model | 20 | 200K |
> | `llama4-maverick` | Top ChartQA/DocVQA scores, good cost efficiency | 10 | 128K |
> | `openai-o4-mini` | Best reasoning benchmarks (MMMU: 81.6) | 5 | 1M |
> | `openai-gpt-4.1` | Largest context window, strong all-round | 5 | 1M |
>
> All models support `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`. See [Cortex AI Functions: Images](https://docs.snowflake.com/en/user-guide/snowflake-cortex/complete-multimodal) for benchmarks and regional availability.

**STOP**: Wait for user input. If user presses Enter for a value, use the default.

**Update .env with confirmed values using the file editing tool:**

Use Edit/StrReplace on `.env` for each variable:
- Replace `DEMO_DATABASE=` line with `DEMO_DATABASE=${DEMO_DATABASE}`
- Replace `DEMO_SCHEMA=` line with `DEMO_SCHEMA=${DEMO_SCHEMA}`
- Replace `DEMO_STAGE=` line with `DEMO_STAGE=${DEMO_STAGE}`
- Replace `AI_MODEL=` line with `AI_MODEL=${AI_MODEL}`

If any variable line does not exist, append it to the file.

**SHOW** the user: `Demo values saved. Next: we'll use an admin role (e.g. ACCOUNTADMIN) to create a least-privilege demo role for this demo.`

### Step 2a: Admin Role from Manifest

**Purpose:** An admin role (typically ACCOUNTADMIN) is needed to create the demo role, database, and grant privileges. It is also used for role cleanup (the demo role drops its own database). Get admin_role from manifest (NOT .env).

**Check manifest for existing admin_role:**

```bash
grep -A10 "## admin_role" .snow-utils/snow-utils-manifest.md 2>/dev/null | grep -E "^[a-z_-]+:" | head -1
```

**If admin_role exists for any skill, ask to reuse:**

```
Found existing admin_role in manifest: <EXISTING_ROLE> (from <skill_name>)

Reuse this admin_role for smart-crowd-counter? [yes/no]
```

**If NO admin_role exists anywhere, prompt:**

```
An admin role is needed to:
  - CREATE ROLE (demo role for least-privilege access)
  - CREATE DATABASE (then transfer ownership to demo role)
  - GRANT warehouse access to demo role
  - Cleanup: DROP ROLE (the demo role drops its own DB)

The admin role is NOT used for day-to-day operations -- those use the demo role.

Snowflake recommends: ACCOUNTADMIN (has all privileges by default)

Enter admin role for this demo [ACCOUNTADMIN]:
```

**STOP**: Wait for user input.

**Write to manifest (admin_role is ONLY stored in manifest, NOT in .env):**

```bash
if ! grep -q "## admin_role" .snow-utils/snow-utils-manifest.md; then
cat >> .snow-utils/snow-utils-manifest.md << 'EOF'

## admin_role
EOF
fi
grep -q "^smart-crowd-counter:" .snow-utils/snow-utils-manifest.md && \
  sed -i '' 's/^smart-crowd-counter:.*/smart-crowd-counter: '"${ADMIN_ROLE}"'/' .snow-utils/snow-utils-manifest.md || \
  echo "smart-crowd-counter: ${ADMIN_ROLE}" >> .snow-utils/snow-utils-manifest.md
```

**Read admin_role from manifest for subsequent steps:**

```bash
ADMIN_ROLE=$(grep -A10 "## admin_role" .snow-utils/snow-utils-manifest.md | grep "^smart-crowd-counter:" | cut -d: -f2 | tr -d ' ')
```

### Step 2b: Create Demo Role

**Purpose:** Create a dedicated demo role with least-privilege access. The demo role owns the database and has USAGE on the warehouse -- no account-level privileges.

**Compute default role name from SNOWFLAKE_USER:**

```bash
set -a && source .env && set +a
DEFAULT_ROLE_NAME="${SNOWFLAKE_USER:-$USER}_SCC_ACCESS"
echo "Computed default: ${DEFAULT_ROLE_NAME}"
```

**Ask user for demo role name:**

```
Demo role name [${DEFAULT_ROLE_NAME}]:
```

**STOP**: Wait for user input. If Enter, use the default.

**Write DEMO_ROLE to .env using the file editing tool:**

Use Edit/StrReplace on `.env`:
- Replace `DEMO_ROLE=` line with `DEMO_ROLE=${DEMO_ROLE}`
- If the line does not exist, append `DEMO_ROLE=${DEMO_ROLE}` to the file

**SHOW -- SQL Preview (create_role.sql):**

> **What we're about to do:** Create a demo role, create the database, transfer ownership to the demo role, and grant warehouse access. The demo role has NO account-level privileges.

```sql
USE ROLE ${ADMIN_ROLE};

CREATE ROLE IF NOT EXISTS ${DEMO_ROLE};
GRANT ROLE ${DEMO_ROLE} TO USER ${SNOWFLAKE_USER};

CREATE DATABASE IF NOT EXISTS ${DEMO_DATABASE};
GRANT OWNERSHIP ON DATABASE ${DEMO_DATABASE} TO ROLE ${DEMO_ROLE} COPY CURRENT GRANTS;

GRANT USAGE ON WAREHOUSE ${SNOWFLAKE_WAREHOUSE} TO ROLE ${DEMO_ROLE};
GRANT OPERATE ON WAREHOUSE ${SNOWFLAKE_WAREHOUSE} TO ROLE ${DEMO_ROLE};
```

> **Note:** Display with actual variable values substituted from `.env` and manifest.

**STOP**: Show preview to user and get approval before executing.

**Execute:**

```bash
uv run scc-create-role \
  --admin-role ${ADMIN_ROLE} \
  --demo-role ${DEMO_ROLE}
```

> Reads SNOWFLAKE_USER, SNOWFLAKE_WAREHOUSE, DEMO_DATABASE from `.env`. `--admin-role` comes from manifest (Step 2a).

### Step 3: Confirm Settings

**Display configuration summary:**

```
Configuration Summary

Connection: ${SNOWFLAKE_DEFAULT_CONNECTION_NAME}
Account: ${SNOWFLAKE_ACCOUNT}
User: ${SNOWFLAKE_USER}
Warehouse: ${SNOWFLAKE_WAREHOUSE}

Demo Settings:
  Database: ${DEMO_DATABASE}
  Schema: ${DEMO_SCHEMA}
  Stage: ${DEMO_STAGE}
  AI Model: ${AI_MODEL}
  Admin Role: ${ADMIN_ROLE} (from manifest)
  Demo Role: ${DEMO_ROLE} (DB owner, from .env)

Proceed with these settings?
```

**STOP**: Wait for user confirmation.

### Step 4: Create Snowflake Objects

**SHOW -- SQL Preview (setup.sql):**

> **What we're about to do:** Create the schema, stage for image uploads, and an AI-powered view that uses Cortex AISQL to analyze uploaded photos. The database already exists (created in Step 2b and owned by the demo role).

```sql
USE ROLE ${DEMO_ROLE};
USE DATABASE ${DEMO_DATABASE};

CREATE SCHEMA IF NOT EXISTS ${DEMO_SCHEMA};
USE SCHEMA ${DEMO_SCHEMA};

CREATE STAGE IF NOT EXISTS ${DEMO_STAGE}
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
  DIRECTORY = (ENABLE = TRUE, AUTO_REFRESH = TRUE)
  COMMENT = 'Stage for conference session photos';

CREATE OR REPLACE VIEW SMART_CROWD_COUNTER AS
WITH image_files AS (
  SELECT
    relative_path AS name,
    TO_FILE(CONCAT('@${DEMO_DATABASE}.${DEMO_SCHEMA}.${DEMO_STAGE}/', relative_path)) AS file,
    last_modified
  FROM DIRECTORY('@${DEMO_DATABASE}.${DEMO_SCHEMA}.${DEMO_STAGE}')
  WHERE LOWER(relative_path) LIKE '%.jpg'
    OR LOWER(relative_path) LIKE '%.jpeg'
    OR LOWER(relative_path) LIKE '%.png'
),
processed_images AS (
  SELECT
    name, file, last_modified,
    AI_COMPLETE(
      '${AI_MODEL}',
      'Analyze this image and count people and raised hands. '
      || 'Return JSON only with this exact structure: '
      || '{"total_attendees": N, "raised_hands": N, "percentage_with_hands_up": N.NN}. '
      || 'Calculate percentage as (raised_hands/total_attendees)*100, rounded to 2 decimals. '
      || 'If no people are visible, return zeros.',
      file
    ) AS attendees_count
  FROM image_files
)
SELECT
  name,
  file AS file_name,
  AI_COMPLETE(
    '${AI_MODEL}',
    'Create a brief caption for a conference photo with filename: ' || name || '. '
    || 'Context: SUM=Summit, NS=Northstar, SWT=Snowflake World Tour. '
    || 'Location codes like PUNE, DELHI, MEL indicate cities. '
    || 'Format: Event Name - Location - Session. '
    || 'Add "Workshop" if filename suggests hands-on session. '
    || 'Keep it under 10 words.'
  ) AS caption,
  attendees_count AS raw,
  TRY_PARSE_JSON(attendees_count):total_attendees::INTEGER AS total_attendees,
  TRY_PARSE_JSON(attendees_count):raised_hands::INTEGER AS raised_hands,
  TRY_PARSE_JSON(attendees_count):percentage_with_hands_up::FLOAT AS percentage_with_hands_up
FROM processed_images
ORDER BY name;
```

> **Note:** Display with actual variable values substituted from `.env`.

**STOP**: Show preview to user and get approval before executing.

**Execute (uses demo_role -- DB owner):**

```bash
uv run scc-setup --demo-role ${DEMO_ROLE}
```

> Reads DEMO_DATABASE, DEMO_SCHEMA, DEMO_STAGE, AI_MODEL from `.env`. `--demo-role` value comes from `.env` (Step 2b).

**Update manifest (IN_PROGRESS):**

```markdown
<!-- START -- smart-crowd-counter:{DEMO_DATABASE} -->
## Smart Crowd Counter: {DEMO_DATABASE}

**Created:** {TIMESTAMP}
**Database:** {DEMO_DATABASE}
**Schema:** {DEMO_SCHEMA}
**Stage:** {DEMO_STAGE}
**AI Model:** {AI_MODEL}
**Admin Role:** {ADMIN_ROLE}
**Demo Role:** {DEMO_ROLE}
**App URL:** (pending deployment)
**Status:** IN_PROGRESS

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 0 | Role | {DEMO_ROLE} | Account | DONE |
| 1 | Database | {DEMO_DATABASE} | Account | DONE |
| 2 | Schema | {DEMO_SCHEMA} | {DEMO_DATABASE} | DONE |
| 3 | Stage | {DEMO_STAGE} | {DEMO_DATABASE}.{DEMO_SCHEMA} | DONE |
| 4 | View | SMART_CROWD_COUNTER | {DEMO_DATABASE}.{DEMO_SCHEMA} | DONE |
| 5 | Streamlit App | SMART_CROWD_COUNTER | {DEMO_DATABASE}.{DEMO_SCHEMA} | PENDING |
<!-- END -- smart-crowd-counter:{DEMO_DATABASE} -->
```

### Step 5: Deploy Streamlit App

**SHOW -- Deployment Preview:**

> **What we're about to do:** Deploy the Streamlit app to Snowflake. The app will be accessible via Snowsight under Projects > Streamlit.

**Generate snowflake.yml from template:**

```bash
set -a && source .env && set +a
envsubst < app/snowflake.yml.template > app/snowflake.yml
```

**Show the generated snowflake.yml to user:**

```yaml
definition_version: 2
entities:
  smart_crowd_counter:
    type: streamlit
    identifier:
      name: SMART_CROWD_COUNTER
      database: ${DEMO_DATABASE}
      schema: ${DEMO_SCHEMA}
    query_warehouse: ${SNOWFLAKE_WAREHOUSE}
    main_file: streamlit_app.py
    artifacts:
      - streamlit_app.py
      - environment.yml
```

> **Note:** Display with actual variable values substituted.

**STOP**: Show preview to user and get approval before deploying.

**Execute deployment (as demo_role):**

```bash
cd app && snow streamlit deploy --replace --role ${DEMO_ROLE} && cd ..
```

**STOP**: If deployment fails, show error and troubleshooting tips:

- **"No such compute pool"**: Ask user for their compute pool name, or suggest trying without `compute_pool` (uses default)
- **CLI version too old**: Use `uvx --from snowflake-cli snow streamlit deploy --replace`
- **Missing warehouse**: Update SNOWFLAKE_WAREHOUSE in .env

**On success, get the app URL using `snow streamlit get-url`:**

```bash
snow streamlit get-url SMART_CROWD_COUNTER \
  -c ${SNOWFLAKE_DEFAULT_CONNECTION_NAME} \
  --database ${DEMO_DATABASE} \
  --schema ${DEMO_SCHEMA}
```

This returns the direct URL to the deployed Streamlit app.

**Display the URL prominently to the user:**

```
Streamlit app deployed successfully!

Open your app: [<APP_URL>](<APP_URL>)
```

**Update manifest:** Mark "Streamlit App" (row 5) as DONE. Store the app URL in the `**App URL:**` manifest field. The demo role is recorded in `**Demo Role:**`.

### Step 6: Verify & Summary

**Update manifest to COMPLETE:**

```markdown
<!-- START -- smart-crowd-counter:{DEMO_DATABASE} -->
## Smart Crowd Counter: {DEMO_DATABASE}

**Created:** {TIMESTAMP}
**Database:** {DEMO_DATABASE}
**Schema:** {DEMO_SCHEMA}
**Stage:** {DEMO_STAGE}
**AI Model:** {AI_MODEL}
**Admin Role:** {ADMIN_ROLE}
**Demo Role:** {DEMO_ROLE}
**App URL:** {APP_URL}
**Status:** COMPLETE

| # | Type | Name | Location | Status |
|---|------|------|----------|--------|
| 0 | Role | {DEMO_ROLE} | Account | DONE |
| 1 | Database | {DEMO_DATABASE} | Account | DONE |
| 2 | Schema | {DEMO_SCHEMA} | {DEMO_DATABASE} | DONE |
| 3 | Stage | {DEMO_STAGE} | {DEMO_DATABASE}.{DEMO_SCHEMA} | DONE |
| 4 | View | SMART_CROWD_COUNTER | {DEMO_DATABASE}.{DEMO_SCHEMA} | DONE |
| 5 | Streamlit App | SMART_CROWD_COUNTER | {DEMO_DATABASE}.{DEMO_SCHEMA} | DONE |

### Cleanup Instructions

```bash
uv run scc-cleanup --demo-role ${DEMO_ROLE}
uv run scc-cleanup-role --admin-role ${ADMIN_ROLE} --demo-role ${DEMO_ROLE}
```
<!-- END -- smart-crowd-counter:{DEMO_DATABASE} -->
```

**Display summary:**

#### Smart Crowd Counter -- Setup Complete!

**Project directory:** `${PROJECT_DIR}`

**Snowflake objects created:**
- Demo Role: `${DEMO_ROLE}` (DB owner, no account-level privileges)
- Database: `${DEMO_DATABASE}` (owned by `${DEMO_ROLE}`)
- Schema: `${DEMO_DATABASE}.${DEMO_SCHEMA}`
- Stage: `${DEMO_DATABASE}.${DEMO_SCHEMA}.${DEMO_STAGE}`
- View: `${DEMO_DATABASE}.${DEMO_SCHEMA}.SMART_CROWD_COUNTER`
- Streamlit App: `SMART_CROWD_COUNTER`

**Next steps:**
1. **Open your app:** [${APP_URL}](${APP_URL})
2. The app automatically connects to the demo database and schema
3. Upload conference photos (JPG, PNG, JPEG)
4. Wait for the AI analysis to complete
5. Click on any row to see the image and detailed charts

**Upload images from CLI (supported: JPG, JPEG, PNG only):**

```bash
snow stage copy /path/to/photos/*.jpg @${DEMO_DATABASE}.${DEMO_SCHEMA}.${DEMO_STAGE}/
snow stage copy /path/to/photos/*.png @${DEMO_DATABASE}.${DEMO_SCHEMA}.${DEMO_STAGE}/
snow sql -q "ALTER STAGE ${DEMO_DATABASE}.${DEMO_SCHEMA}.${DEMO_STAGE} REFRESH"
```

> **Note:** Only `.jpg`, `.jpeg`, and `.png` files are processed by the AI view. Other formats will be ignored.

**Query results from CLI:**

```bash
snow sql -q "SELECT name, total_attendees, raised_hands, percentage_with_hands_up FROM ${DEMO_DATABASE}.${DEMO_SCHEMA}.SMART_CROWD_COUNTER"
```

**Manifest:** `${PROJECT_DIR}/.snow-utils/snow-utils-manifest.md`

---

**Open your app:** [${APP_URL}](${APP_URL})

## Export for Sharing Flow

**Trigger phrases:** "export manifest for sharing", "share crowd counter manifest"

**Purpose:** Create a portable copy of the manifest that another developer can use to replay the entire setup on their machine.

### Precondition

Cortex Code MUST verify ALL skill sections have `Status: COMPLETE`:

```bash
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

  Filename: smart-crowd-counter-manifest.md
  Default location: ./ (project root)

Save to [./]:
```

**STOP**: Wait for user input.

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
        project_name: smart-crowd-counter
        setup_steps:
          1. Check if required skills are installed: cortex skill list
          2. For each skill in ## required_skills NOT in the list, run: cortex skill add <url>
          3. Once all skills installed, follow smart-crowd-counter SKILL.md "Setup from Shared Manifest Flow"
        To trigger: ask "setup from shared manifest" -->
   ```

   **required_skills section (inject after shared_info):**

   ```markdown
   ## required_skills
   smart-crowd-counter: https://github.com/kameshsampath/kamesh-demo-skills/smart-crowd-counter
   ```

   > **Note:** `required_skills` includes the demo skill itself. This enables self-installation from a vanilla Cortex Code with no skills pre-installed.

7. **Show confirmation:**

```
Exported: smart-crowd-counter-manifest.md

  Location: ./smart-crowd-counter-manifest.md
  Shared by: {SNOWFLAKE_USER}
  Sections: smart-crowd-counter
  All statuses set to: REMOVED
  ADAPT markers added for user-prefixed values

Share this file with your colleague. They can open it in Cursor and ask Cortex Code:
  "setup from shared manifest"
```

> **Note:** The exported file is in the project root, NOT in `.snow-utils/`. Skills only read from `.snow-utils/snow-utils-manifest.md` so the export is invisible to all skill flows.

### Setup from Shared Manifest Flow

**Trigger phrases:** "setup from shared manifest", "replay from shared manifest", "import shared manifest", "setup from manifest URL", "replay from URL", "use manifest from `<url>`"

**If user provides a URL:** Apply the **Remote Manifest URL Detection** rules from Step 0-manifest-check above -- translate the URL, confirm download with user, `curl` to current directory. Then continue below.

When Cortex Code detects a shared manifest (file with `## shared_info` section or `<!-- COCO_INSTRUCTION -->` comment):

1. **Check and install required skills (self-install):**

   ```bash
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
   Required skill not installed: smart-crowd-counter
   URL: https://github.com/kameshsampath/kamesh-demo-skills/smart-crowd-counter

   Install this skill? [yes/no]
   ```

   **STOP**: Wait for user confirmation for each missing skill.

   **If yes:** Run `cortex skill add <url>`.

2. **Read `project_name`** from `## project_recipe`
3. **Ask user:**

```
This is a shared manifest for project: smart-crowd-counter

Options:
1. Create project directory: ./smart-crowd-counter (recommended)
2. Use current directory
3. Specify a custom directory name
```

**STOP**: Wait for user input.

4. **If target dir already has a manifest:** Offer backup (.bak) / abort / different directory
5. **Create directory + `.snow-utils/`**, **copy** manifest to `.snow-utils/snow-utils-manifest.md` (preserve original for reference -- do NOT move or delete it)
6. **Proceed to Replay Flow** (step 3 below handles .env reconstruction and name adaptation)

---

## Cleanup Flow

**Trigger phrases:** "cleanup crowd counter", "remove crowd counter demo", "delete crowd counter database"

**IMPORTANT:** This is the **smart-crowd-counter** skill. Only cleanup sections marked `<!-- START -- smart-crowd-counter:* -->`.

Cleanup is **two-phase**: first drop the database using the demo role (which owns the DB), then drop the demo role itself using the admin role.

> **WARNING:** Dropping the database is **irreversible** and removes ALL objects within it (schemas, stages, views, Streamlit apps, and uploaded data).

1. **Read manifest:**

   ```bash
   cat .snow-utils/snow-utils-manifest.md 2>/dev/null
   ```

2. **Find section using unique markers:**

   Look for the block between:

   ```
   <!-- START -- smart-crowd-counter:{DEMO_DATABASE} -->
   ...
   <!-- END -- smart-crowd-counter:{DEMO_DATABASE} -->
   ```

   **Extract variables from the section:**
   - `DEMO_DATABASE` from `**Database:** {value}`
   - `ADMIN_ROLE` from `**Admin Role:** {value}`
   - `DEMO_ROLE` from `**Demo Role:** {value}`

3. **SHOW -- SQL Preview (cleanup.sql + cleanup_role.sql):**

   > **What we're about to do:** Drop the demo database using the demo role (which owns it), then revoke and drop the demo role using the admin role.

   ```sql
   -- Phase 1: Drop database (cleanup.sql) -- demo role is the DB owner
   USE ROLE ${DEMO_ROLE};
   DROP DATABASE IF EXISTS ${DEMO_DATABASE};

   -- Phase 2: Drop demo role (cleanup_role.sql) -- requires admin role
   USE ROLE ${ADMIN_ROLE};
   REVOKE ROLE ${DEMO_ROLE} FROM USER ${SNOWFLAKE_USER};
   DROP ROLE IF EXISTS ${DEMO_ROLE};
   ```

   > **Note:** Display with actual variable values substituted from `.env` and manifest.

4. **Show cleanup confirmation with warning:**

   ```
   ⚠ WARNING: This action is IRREVERSIBLE.

   Dropping database ${DEMO_DATABASE} will permanently remove:
     - All schemas (${DEMO_SCHEMA})
     - All stages and uploaded images (${DEMO_STAGE})
     - All views (SMART_CROWD_COUNTER)
     - Streamlit App (SMART_CROWD_COUNTER)

   Additionally, the demo role ${DEMO_ROLE} will be revoked and dropped.

   Phase 1 (as ${DEMO_ROLE} -- DB owner):
     uv run scc-cleanup --demo-role ${DEMO_ROLE}

   Phase 2 (as ${ADMIN_ROLE}):
     uv run scc-cleanup-role --admin-role ${ADMIN_ROLE} --demo-role ${DEMO_ROLE}

   Type 'yes, destroy' to confirm:
   ```

   **STOP**: Wait for user to type `yes, destroy`. Any other input cancels cleanup.

5. **On confirmation:** Execute cleanup in **two separate commands** (in order):

   **Phase 1 -- Drop database (as demo role, the DB owner):**

   ```bash
   uv run scc-cleanup --demo-role ${DEMO_ROLE}
   ```

   > `scc-cleanup` only accepts `--demo-role`. Do NOT pass `--admin-role` to this command.

   **Phase 2 -- Revoke and drop the demo role (as admin):**

   ```bash
   uv run scc-cleanup-role --admin-role ${ADMIN_ROLE} --demo-role ${DEMO_ROLE}
   ```

   > `scc-cleanup-role` requires both `--admin-role` and `--demo-role`.

   > **NEVER run raw SQL for cleanup.** ALWAYS use the CLI commands above. **NEVER combine these into a single command.**

6. **Update manifest section using unique markers:**

   **IMPORTANT:** Do NOT delete the manifest file. Update the status to REMOVED so the demo can be replayed later.

   **CRITICAL:** Use the **file editing tool** (Edit/StrReplace) with the full unique block markers. NEVER use `sed` or shell commands for this:

   ```
   old_string: <!-- START -- smart-crowd-counter:{DEMO_DATABASE} -->
   ... (entire existing block) ...
   <!-- END -- smart-crowd-counter:{DEMO_DATABASE} -->

   new_string: <!-- START -- smart-crowd-counter:{DEMO_DATABASE} -->
   ## Smart Crowd Counter: {DEMO_DATABASE}

   **Created:** {original_timestamp}
   **Removed:** {current_timestamp}
   **Database:** {DEMO_DATABASE}
   **Schema:** {DEMO_SCHEMA}
   **Stage:** {DEMO_STAGE}
   **AI Model:** {AI_MODEL}
   **Admin Role:** {ADMIN_ROLE}
   **Demo Role:** {DEMO_ROLE}
   **Status:** REMOVED

   | # | Type | Name | Location | Status |
   |---|------|------|----------|--------|
   | 0 | Role | {DEMO_ROLE} | Account | REMOVED |
   | 1 | Database | {DEMO_DATABASE} | Account | REMOVED |
   | 2 | Schema | {DEMO_SCHEMA} | {DEMO_DATABASE} | REMOVED |
   | 3 | Stage | {DEMO_STAGE} | {DEMO_DATABASE}.{DEMO_SCHEMA} | REMOVED |
   | 4 | View | SMART_CROWD_COUNTER | {DEMO_DATABASE}.{DEMO_SCHEMA} | REMOVED |
   | 5 | Streamlit App | SMART_CROWD_COUNTER | {DEMO_DATABASE}.{DEMO_SCHEMA} | REMOVED |
   <!-- END -- smart-crowd-counter:{DEMO_DATABASE} -->
   ```

   **After cleanup complete, show summary:**

   ```
   Cleanup Summary:
     Demo Role:     ${DEMO_ROLE}           -> REMOVED
     Database:      ${DEMO_DATABASE}       -> REMOVED
     Schema:        ${DEMO_SCHEMA}         -> REMOVED
     Stage:         ${DEMO_STAGE}          -> REMOVED
     View:          SMART_CROWD_COUNTER    -> REMOVED
     Streamlit App: SMART_CROWD_COUNTER    -> REMOVED
   ```

## Replay Flow

**Trigger phrases:** "replay crowd counter", "replay smart-crowd-counter manifest", "recreate crowd counter demo"

**Direct re-run triggers:** "re-run crowd counter", "redeploy crowd counter app"
> If the user says one of these, read the manifest. If status is `COMPLETE`, skip the collision prompt and go directly to the **Re-run Flow** section. If status is not `COMPLETE`, fall through to the normal Replay Flow below.

**IMPORTANT:** This is the **smart-crowd-counter** skill. Only replay sections marked `<!-- START -- smart-crowd-counter:* -->`.

1. **Read manifest:**

   ```bash
   cat .snow-utils/snow-utils-manifest.md 2>/dev/null
   ```

2. **Reconstruct .env (if missing or incomplete):**

   > **Portable Manifest:** When replaying from a shared manifest, `.env` may not exist. Reconstruct it from the manifest + user input.

   ```bash
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

      **STOP**: Wait for user to select a connection.

   c. Test connection and extract details:

      ```bash
      snow connection test -c <selected_connection> --format json
      ```

      Write to .env: `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`

   d. **Infer from manifest sections** (extract `**Field:**` values):

      ```bash
      # From smart-crowd-counter section
      DEMO_DATABASE=$(grep -A30 "<!-- START -- smart-crowd-counter" .snow-utils/snow-utils-manifest.md | grep "^\*\*Database:\*\*" | head -1 | sed 's/\*\*Database:\*\* //')
      DEMO_SCHEMA=$(grep -A30 "<!-- START -- smart-crowd-counter" .snow-utils/snow-utils-manifest.md | grep "^\*\*Schema:\*\*" | head -1 | sed 's/\*\*Schema:\*\* //')
      DEMO_STAGE=$(grep -A30 "<!-- START -- smart-crowd-counter" .snow-utils/snow-utils-manifest.md | grep "^\*\*Stage:\*\*" | head -1 | sed 's/\*\*Stage:\*\* //')
      AI_MODEL=$(grep -A30 "<!-- START -- smart-crowd-counter" .snow-utils/snow-utils-manifest.md | grep "^\*\*AI Model:\*\*" | head -1 | sed 's/\*\*AI Model:\*\* //')
      ADMIN_ROLE=$(grep -A30 "<!-- START -- smart-crowd-counter" .snow-utils/snow-utils-manifest.md | grep "^\*\*Admin Role:\*\*" | head -1 | sed 's/\*\*Admin Role:\*\* //')
      DEMO_ROLE=$(grep -A30 "<!-- START -- smart-crowd-counter" .snow-utils/snow-utils-manifest.md | grep "^\*\*Demo Role:\*\*" | head -1 | sed 's/\*\*Demo Role:\*\* //')
      ```

   e. **Validate extracted values:**

      ```bash
      for var in DEMO_DATABASE DEMO_SCHEMA DEMO_STAGE AI_MODEL ADMIN_ROLE DEMO_ROLE; do
        val=$(eval echo \$$var)
        if [ -z "$val" ]; then
          echo "WARNING: Could not extract ${var} from manifest."
        fi
      done
      ```

      If any value is empty, ask user: "Some values couldn't be extracted. Enter them manually?"

   f. **Shared manifest adapt-check (ALWAYS run for shared manifests):**

      ```bash
      IS_SHARED=$(grep -c "## shared_info\|COCO_INSTRUCTION" .snow-utils/snow-utils-manifest.md 2>/dev/null)

      if [ "$IS_SHARED" -gt 0 ]; then
        ADAPT_COUNT=$(grep -c "# ADAPT:" .snow-utils/snow-utils-manifest.md 2>/dev/null)
        echo "Shared manifest detected. ADAPT markers: ${ADAPT_COUNT}"
      fi
      ```

      **If shared manifest AND `ADAPT_COUNT` > 0:** Follow **Step 0-adapt** above.

      **If NOT a shared manifest:** Skip this step.

   g. Write all values to `.env` using the file editing tool:

      Use Edit/StrReplace on `.env` for each variable extracted from the manifest:
      - Replace `DEMO_DATABASE=` line with `DEMO_DATABASE=${DEMO_DATABASE}`
      - Replace `DEMO_SCHEMA=` line with `DEMO_SCHEMA=${DEMO_SCHEMA}`
      - Replace `DEMO_STAGE=` line with `DEMO_STAGE=${DEMO_STAGE}`
      - Replace `AI_MODEL=` line with `AI_MODEL=${AI_MODEL}`
      - Replace `DEMO_ROLE=` line with `DEMO_ROLE=${DEMO_ROLE}`

      If any variable line does not exist, append it to the file.

   **If .env exists and has all values:** Skip to step 3.

3. **Find section using unique markers:**

   Look for the block between:

   ```
   <!-- START -- smart-crowd-counter:{DEMO_DATABASE} -->
   ...
   <!-- END -- smart-crowd-counter:{DEMO_DATABASE} -->
   ```

4. **Check Status:**

| Status | Action |
|--------|--------|
| `REMOVED` | Proceed to step 5 |
| `COMPLETE` | **Collision detected** -- show collision strategy prompt |
| `IN_PROGRESS` | Use Resume Flow instead |

   **If Status is `COMPLETE` -- Collision Strategy:**

   ```
   Demo resources already exist:

     Resource                        Status
     Database: {DEMO_DATABASE}       EXISTS
     Schema: {DEMO_SCHEMA}           EXISTS
     Stage: {DEMO_STAGE}             EXISTS
     View: SMART_CROWD_COUNTER       EXISTS
     App: SMART_CROWD_COUNTER        EXISTS

   Choose a strategy:
   1. Use existing -> skip creation, redeploy app only
   2. Replace -> DROP DATABASE then recreate (DESTRUCTIVE -- all data lost)
   3. Rename -> prompt for new database name
   4. Re-run -> redeploy app and/or recreate view
   5. Cancel -> stop replay
   ```

   **STOP**: Wait for user choice.

   | Choice | Action |
   |--------|--------|
   | **Use existing** | Skip creation, verify objects exist. |
   | **Replace** | Confirm with "Type 'yes, destroy' to confirm". Run cleanup, then proceed to step 5. |
   | **Rename** | Ask for new database name. Update `DEMO_DATABASE` in `.env` and proceed to step 5. |
   | **Re-run** | Execute **Re-run Flow** (see below). |
   | **Cancel** | Stop replay. |

5. **Display replay plan:**

   ```
   Replay from manifest will create:

     Demo Role:     ${DEMO_ROLE} (DB owner, no account-level privileges)
     Database:      ${DEMO_DATABASE} (owned by ${DEMO_ROLE})
     Schema:        ${DEMO_SCHEMA}
     Stage:         ${DEMO_STAGE}
     View:          SMART_CROWD_COUNTER (AI-powered, using ${AI_MODEL})
     Streamlit App: SMART_CROWD_COUNTER

   Proceed? [yes/no]
   ```

   **STOP**: Wait for user confirmation.

6. **On confirmation:** Execute Steps 2b, 4-6 sequentially (create role + DB first, then schema objects, then deploy).

   > **MANDATORY:** Display every SQL preview box (Steps 4-5) BEFORE executing each step, even in replay.
   > Replay reduces confirmation stops but NEVER skips the preview boxes -- they are educational and serve as an audit trail.

7. **Update manifest section using unique markers:**

   Use the **file editing tool** (Edit/StrReplace) to replace the entire block with updated status COMPLETE.

8. **Get the app URL and show next steps:**

   ```bash
   snow streamlit get-url SMART_CROWD_COUNTER \
     -c ${SNOWFLAKE_DEFAULT_CONNECTION_NAME} \
     --database ${DEMO_DATABASE} \
     --schema ${DEMO_SCHEMA}
   ```

   **SHOW** the user:

   ```
   Replay Complete!

   Open your app: [${APP_URL}](${APP_URL})
   ```

## Resume Flow

**If manifest shows Status: IN_PROGRESS:**

1. **Find section using unique markers:**

   Look for the block between:

   ```
   <!-- START -- smart-crowd-counter:{DEMO_DATABASE} -->
   ...
   <!-- END -- smart-crowd-counter:{DEMO_DATABASE} -->
   ```

2. **Read which resources have status DONE** (already created)

3. **Display resume info:**

   ```
   Resuming from partial creation:

     DONE: Database ${DEMO_DATABASE}
     DONE: Schema ${DEMO_SCHEMA}
     DONE: Stage ${DEMO_STAGE}
     DONE: View SMART_CROWD_COUNTER

     PENDING: Streamlit App SMART_CROWD_COUNTER

   Continue from Streamlit App deployment? [yes/no]
   ```

   **STOP**: Wait for user confirmation.

4. **On confirmation:** Continue from first PENDING resource.

   > **MANDATORY:** Display SQL/deployment preview boxes for each PENDING step BEFORE executing.
   > Skip boxes for DONE steps only.

5. **Update manifest section using unique markers** as each resource is created.

6. **Get the app URL and show next steps:**

   ```bash
   snow streamlit get-url SMART_CROWD_COUNTER \
     -c ${SNOWFLAKE_DEFAULT_CONNECTION_NAME} \
     --database ${DEMO_DATABASE} \
     --schema ${DEMO_SCHEMA}
   ```

   **SHOW** the user:

   ```
   Resume Complete!

   Open your app: [${APP_URL}](${APP_URL})
   ```

## Re-run Flow

**Trigger phrases:** "re-run crowd counter", "redeploy crowd counter app", "recreate crowd counter view"

**Precondition:** Manifest status must be `COMPLETE`. If not COMPLETE, use Resume Flow (IN_PROGRESS) or Replay Flow (REMOVED) instead.

This is a lightweight flow that redeploys the Streamlit app and optionally recreates the view (e.g., to change the AI model).

1. **Read manifest and verify COMPLETE status.**

2. **Read ADMIN_ROLE and DEMO_ROLE from manifest.**

3. **Ask user what to re-run:**

   ```
   Re-run options:

   1. Redeploy Streamlit app only (e.g., after editing streamlit_app.py)
   2. Recreate view + redeploy app (e.g., to change AI model)
   3. Cancel

   Choose [1/2/3]:
   ```

   **STOP**: Wait for user choice.

4. **If option 2 (recreate view), ask for AI model:**

   ```
   Current AI model: ${AI_MODEL}
   New AI model [${AI_MODEL}]:

   Recommended: claude-4-sonnet | claude-4-opus | llama4-maverick | openai-o4-mini | openai-gpt-4.1
   ```

   **STOP**: Wait for user input. If Enter, keep current.

   If model changed, update `.env` and show SQL preview:

   ```sql
   USE ROLE ${DEMO_ROLE};
   USE DATABASE ${DEMO_DATABASE};
   USE SCHEMA ${DEMO_SCHEMA};

   CREATE OR REPLACE VIEW SMART_CROWD_COUNTER AS
     -- (recreated with new model: ${AI_MODEL})
     ...
   ```

   **STOP**: Show preview and get approval.

   Execute:

   ```bash
   uv run scc-setup --demo-role ${DEMO_ROLE}
   ```

5. **Deploy Streamlit app (as demo_role):**

   ```bash
   cd app && snow streamlit deploy --replace --role ${DEMO_ROLE} && cd ..
   ```

   **Get the app URL:**

   ```bash
   snow streamlit get-url SMART_CROWD_COUNTER \
     -c ${SNOWFLAKE_DEFAULT_CONNECTION_NAME} \
     --database ${DEMO_DATABASE} \
     --schema ${DEMO_SCHEMA}
   ```

6. **Show summary:**

   ```
   Re-run Complete!

   Open your app: [${APP_URL}](${APP_URL})

   What was updated:
     - Streamlit App: SMART_CROWD_COUNTER -> redeployed
     - View: SMART_CROWD_COUNTER -> recreated (if option 2)
   ```

## Stopping Points

1. Step 0: Ask for project directory name
2. Step 0b: If tools missing (provide install instructions)
3. Step 1a: If Snowflake connection missing (ask for connection)
4. Step 1a: If warehouse missing (create new or use existing)
5. Step 1a: If creating warehouse (show SQL preview, get approval)
6. Step 2: Ask for demo database/schema/stage/model
7. Step 2a: Ask for admin role
8. Step 2b: Ask for demo role name
9. Step 2b: After create_role.sql SQL preview (get approval)
10. Step 3: After configuration summary (get confirmation)
11. Step 4: After setup SQL preview (get approval)
12. Step 5: After deployment preview (get approval)

## CLI Reference (smart-crowd-counter)

All commands auto-load `.env` and pass required variables to `snow sql` with templating.

**IMPORTANT -- Run from project directory:** All commands MUST be run from the user's project directory (where `.env` and `sql/` live). NEVER use `uv run --project <SKILL_DIR>` -- that changes CWD and breaks `.env` discovery. Step 1 copies the Python package locally so `uv run scc-xxx` works directly.

**OPTION NAMES (NEVER guess or invent options):**

> ONLY use options listed in the tables below.
> If a command fails with "No such option", run `<command> --help` and use ONLY those options.

### `scc-create-role`

Creates the demo role, database, and grants privileges (ownership + warehouse access).

```bash
uv run scc-create-role --admin-role <ROLE> --demo-role <ROLE> [--dry-run]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--admin-role` | **Yes** | - | Admin role (from manifest, NOT .env) |
| `--demo-role` | **Yes** | - | Demo role to create (from .env) |
| `--dry-run` | No | false | Preview command without executing |
| `--env-file` | No | `.env` | Override path to .env file |
| `--sql-dir` | No | `sql/` | Override path to sql/ directory |

**Required .env:** `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `SNOWFLAKE_USER`, `SNOWFLAKE_WAREHOUSE`, `DEMO_DATABASE`

### `scc-setup`

Creates the demo schema, stage, and AI-powered view. The database must already exist (created by `scc-create-role`).

```bash
uv run scc-setup --demo-role <ROLE> [--dry-run]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--demo-role` | **Yes** | - | Demo role (DB owner, from .env) |
| `--dry-run` | No | false | Preview command without executing |
| `--env-file` | No | `.env` | Override path to .env file |
| `--sql-dir` | No | `sql/` | Override path to sql/ directory |

**Required .env:** `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `DEMO_DATABASE`, `DEMO_SCHEMA`, `DEMO_STAGE`, `AI_MODEL`

### `scc-create-warehouse`

Creates a warehouse and grants USAGE + OPERATE to the demo role.

```bash
uv run scc-create-warehouse --admin-role <ROLE> --demo-role <ROLE> --warehouse <NAME> [--dry-run]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--admin-role` | **Yes** | - | Admin role (from manifest, NOT .env) |
| `--demo-role` | **Yes** | - | Demo role to grant warehouse access |
| `--warehouse` | **Yes** | - | Warehouse name to create |
| `--dry-run` | No | false | Preview command without executing |
| `--env-file` | No | `.env` | Override path to .env file |
| `--sql-dir` | No | `sql/` | Override path to sql/ directory |

**Required .env:** `SNOWFLAKE_DEFAULT_CONNECTION_NAME`

### `scc-cleanup`

Drops the demo database and all its objects. Uses the demo role (DB owner) -- no admin role needed.

```bash
uv run scc-cleanup --demo-role <ROLE> [--dry-run]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--demo-role` | **Yes** | - | Demo role that owns the database (from manifest/.env) |
| `--dry-run` | No | false | Preview command without executing |
| `--env-file` | No | `.env` | Override path to .env file |
| `--sql-dir` | No | `sql/` | Override path to sql/ directory |

**Required .env:** `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `DEMO_DATABASE`

### `scc-cleanup-role`

Revokes the demo role from the user and drops it. Run AFTER `scc-cleanup`.

```bash
uv run scc-cleanup-role --admin-role <ROLE> --demo-role <ROLE> [--dry-run]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--admin-role` | **Yes** | - | Admin role (from manifest, NOT .env) |
| `--demo-role` | **Yes** | - | Demo role to drop (from manifest/env) |
| `--dry-run` | No | false | Preview command without executing |
| `--env-file` | No | `.env` | Override path to .env file |
| `--sql-dir` | No | `sql/` | Override path to sql/ directory |

**Required .env:** `SNOWFLAKE_DEFAULT_CONNECTION_NAME`, `SNOWFLAKE_USER`

## SQL Reference (Snowflake Documentation)

> These links help Cortex Code infer correct SQL syntax when previewing or troubleshooting.

| Statement | Documentation |
|-----------|---------------|
| `CREATE ROLE` | https://docs.snowflake.com/en/sql-reference/sql/create-role |
| `DROP ROLE` | https://docs.snowflake.com/en/sql-reference/sql/drop-role |
| `GRANT OWNERSHIP` | https://docs.snowflake.com/en/sql-reference/sql/grant-ownership |
| `GRANT <privileges>` | https://docs.snowflake.com/en/sql-reference/sql/grant-privilege |
| `GRANT ROLE` | https://docs.snowflake.com/en/sql-reference/sql/grant-role |
| `CREATE DATABASE` | https://docs.snowflake.com/en/sql-reference/sql/create-database |
| `DROP DATABASE` | https://docs.snowflake.com/en/sql-reference/sql/drop-database |
| `CREATE WAREHOUSE` | https://docs.snowflake.com/en/sql-reference/sql/create-warehouse |
| `CREATE SCHEMA` | https://docs.snowflake.com/en/sql-reference/sql/create-schema |
| `CREATE STAGE` | https://docs.snowflake.com/en/sql-reference/sql/create-stage |
| `CREATE VIEW` | https://docs.snowflake.com/en/sql-reference/sql/create-view |
| `AI_COMPLETE` (Cortex AISQL) | https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql |
| `DIRECTORY` (Stage) | https://docs.snowflake.com/en/sql-reference/sql/create-stage#directory-table-parameters |
| `GET_PRESIGNED_URL` | https://docs.snowflake.com/en/sql-reference/functions/get_presigned_url |
| Streamlit in Snowflake | https://docs.snowflake.com/en/developer-guide/streamlit/create-streamlit-sql |
| Streamlit Privileges | https://docs.snowflake.com/en/developer-guide/streamlit/object-management/privileges |

## Troubleshooting

**Cortex AISQL not available:** Ensure your Snowflake account has Cortex AISQL enabled. Sign up at https://signup.snowflake.com/ if needed.

**AI model not found:** The model may not be available in your region. Recommended multimodal models: `claude-4-sonnet`, `claude-4-opus`, `llama4-maverick`, `openai-o4-mini`, `openai-gpt-4.1`. See [regional availability](https://docs.snowflake.com/en/user-guide/snowflake-cortex/complete-multimodal#regional-availability). Cross-region inference may be needed for some models.

**Streamlit deploy fails:** Ensure `snow` CLI version >= 3.14.0. Run `snow --version` to check.

**No images showing:** Upload images to the stage and refresh: `snow sql -q "ALTER STAGE ${DEMO_DATABASE}.${DEMO_SCHEMA}.${DEMO_STAGE} REFRESH"`.

**Presigned URL errors:** Ensure the role has access to the stage. Check with `SHOW GRANTS ON STAGE`.

## Security Notes

- **Least privilege:** Demo role has no account-level privileges -- only owns the DB and has USAGE on warehouse
- **ACCOUNTADMIN** is only used for role/DB creation and role cleanup (demo role drops its own DB)
- **Cleanup ownership:** Database is dropped by the demo role (as DB owner). Only role revocation/drop requires the admin role.
- admin_role stored in manifest, demo_role stored in .env and manifest (not hardcoded)
- All database objects are isolated in the demo database
- Stage uses SNOWFLAKE_SSE encryption
- Streamlit app runs within Snowflake's security boundary using the demo role (owner's rights model)

## Directory Structure

After setup, the project directory contains:

```
${PROJECT_DIR}/
├── .env                         # Environment variables (incl. DEMO_ROLE)
├── .snow-utils/
│   └── snow-utils-manifest.md   # Resource tracking
├── sql/
│   ├── create_role.sql          # Create demo role, DB, grant ownership
│   ├── setup.sql                # Schema, stage, view creation (as demo_role)
│   ├── create_warehouse.sql     # Create warehouse + grant to demo_role
│   ├── cleanup.sql              # Drop database
│   └── cleanup_role.sql         # Revoke and drop demo role
├── app/
│   ├── streamlit_app.py         # Streamlit application
│   ├── environment.yml          # SiS conda dependencies
│   ├── snowflake.yml.template   # Deployment manifest template
│   └── snowflake.yml            # Generated deployment manifest
└── pyproject.toml               # Python dependencies
```
