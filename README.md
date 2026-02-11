# Kamesh Demo Skills

A collection of [Cortex Code](https://docs.snowflake.com/en/developer-guide/snowflake-cli/cortex-code-cli/overview) skills for Snowflake demos and tutorials.

## Skills

| Skill | Description | Demo (w/o CoCo) |
|-------|-------------|-----------------|
| [hirc-duckdb-demo](./hirc-duckdb-demo/) | Query Snowflake Iceberg tables with DuckDB via Horizon Iceberg REST Catalog | [hirc-duckdb-demo](https://github.com/kameshsampath/hirc-duckdb-demo) |

## Prerequisites

- **Cortex Code** -- [Sign up here](https://signup.snowflake.com/cortex-code)

These skills depend on [snow-utils-skills](https://github.com/kameshsampath/snow-utils-skills):

| Skill | Purpose |
|-------|---------|
| `snow-utils-volumes` | External volume for Iceberg storage |
| `snow-utils-pat` | Programmatic Access Token for authentication |

> [!NOTE]
> Skills will prompt you to install dependencies automatically during setup.

## Usage

Demo skills are typically used with a **shared manifest** -- a portable configuration file that captures all resource names and settings so another user can replay the entire demo on their account.

**Setting up from a shared manifest**

You can use a local file or a remote URL:

```
Setup from shared manifest
```

```
Setup from https://github.com/kameshsampath/kamesh-demo-skills/blob/main/example-manifests/hirc-duckdb-demo-manifest.md
```

> [!TIP]
> Example shared manifests are in [`example-manifests/`](./example-manifests/). Use them directly via URL or copy to your project directory. Cortex Code will download, adapt `# ADAPT:` values for your account, and replay.

**Or start fresh:**

An example to use _hirc-duckdb-demo_ skill:

First, install the skill:

```bash
cortex skill add https://github.com/kameshsampath/kamesh-demo-skills/hirc-duckdb-demo
```

Then invoke it in Cortex Code `cortex`:

```
Set up hirc duckdb demo
```

## License

[Apache License 2.0](./LICENSE)
