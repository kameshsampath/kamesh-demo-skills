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

> **Note:** Skills will prompt you to install dependencies automatically during setup.

## Installation

```bash
cortex skill add https://github.com/kameshsampath/kamesh-demo-skills/<skill-name>
```

## Usage

In Cortex Code, invoke by name:

```
Set up hirc duckdb demo
```

## License

[Apache License 2.0](./LICENSE)
