# Smart Crowd Counter - Shared Manifest

<!-- COCO_INSTRUCTION: This manifest can be imported by another user to replay the demo setup -->

## shared_info
shared_by: BOB
shared_on: 2026-02-11
source_account: sfdevrel_enterprise

---

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
