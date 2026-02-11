<!-- COCO_INSTRUCTION: This is a shared snow-utils manifest.
     project_name: smart-crowd-counter
     setup_steps:
       1. Check if required skills are installed: cortex skill list
       2. For each skill in ## required_skills NOT in the list, run: cortex skill add <url>
       3. Once all skills installed, follow smart-crowd-counter SKILL.md "Setup from Shared Manifest Flow"
     To trigger: ask "setup from shared manifest" -->

# Smart Crowd Counter - Shared Manifest

This manifest tracks Snowflake resources created by the smart-crowd-counter skill.

---

## shared_info
shared_by: BOB
shared_date: 2026-02-11
source_account: sfdevrel_enterprise
notes: |
  Smart Crowd Counter - Streamlit app using Cortex AISQL to analyze conference photos.
  To replay: open in Cortex Code, ask "setup from shared manifest"

## required_skills
smart-crowd-counter: https://github.com/kameshsampath/kamesh-demo-skills/smart-crowd-counter

## project_recipe
project_name: smart-crowd-counter

## prereqs
tools_verified: 2026-02-11

## admin_role
smart-crowd-counter: ACCOUNTADMIN

<!-- START -- smart-crowd-counter -->
## Smart Crowd Counter

**Database:** BOB_CROWD_COUNTER_DB  # ADAPT: Change prefix to your username
**Schema:** CONFERENCES
**Stage:** SNAPS
**AI Model:** claude-4-sonnet
**Admin Role:** ACCOUNTADMIN
**Demo Role:** BOB_SCC_ACCESS  # ADAPT: Change prefix to your username
**Warehouse:** BOB_WH  # ADAPT: Use your warehouse

| # | Type | Name | Location | Notes |
|---|------|------|----------|-------|
| 0 | Role | BOB_SCC_ACCESS | Account | # ADAPT: Change prefix |
| 1 | Database | BOB_CROWD_COUNTER_DB | Account | # ADAPT: Change prefix |
| 2 | Schema | CONFERENCES | Database | |
| 3 | Stage | SNAPS | Schema | |
| 4 | View | SMART_CROWD_COUNTER | Schema | AI-powered crowd counter |
| 5 | Streamlit App | SMART_CROWD_COUNTER | Schema | |
<!-- END -- smart-crowd-counter -->
